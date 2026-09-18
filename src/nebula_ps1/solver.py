from __future__ import annotations

import csv
import json
import time
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path

from ortools.sat.python import cp_model

from .evaluate import load_submission
from .instance import Instance
from .topology import activity_footprint


@dataclass(frozen=True)
class SolveTelemetry:
    formulation: str
    status: str
    objective_score: float | None
    best_bound: float | None
    wall_time_seconds: float
    conflicts: int
    branches: int
    seed: int
    workers: int
    time_limit_seconds: float
    model_variables: int
    model_constraints: int
    limitation: str

    def as_json(self) -> str:
        return json.dumps(asdict(self), indent=2, sort_keys=True)


def _activity_costs(instance: Instance, activity_id: str) -> list[int]:
    activity = instance.activities[activity_id]
    project = instance.projects[activity.contract_number]
    weight_tenths = {
        1: {1: 1300, 2: 1200, 3: 1000},
        2: {1: 130, 2: 120, 3: 100},
        3: {1: 13, 2: 12, 3: 10},
    }[project.contract_priority][activity.activity_priority]
    return [
        max(0, (instance.completion_date(week) - project.planned_completion_date).days)
        * weight_tenths
        for week in range(1, instance.horizon_weeks + 1)
    ]


def _add_sample_hints(
    model: cp_model.CpModel,
    instance: Instance,
    sample_dir: Path,
    access_vars: dict[tuple[str, int], cp_model.IntVar],
    night_vars: dict[tuple[str, int, int], cp_model.IntVar],
    member_vars: dict[tuple[str, int, str, int], cp_model.IntVar],
) -> None:
    access_rows, occupancy_rows, _ = load_submission(sample_dir)
    sample_access = {(row.activity_id, row.week): row for row in access_rows}
    for key, variable in access_vars.items():
        model.add_hint(variable, int(key in sample_access))
    for (activity_id, week, night), variable in night_vars.items():
        row = sample_access.get((activity_id, week))
        model.add_hint(variable, int(row is not None and row.access_night == night))

    labels_by_location_week: dict[tuple[str, int], set[str]] = defaultdict(set)
    for row in occupancy_rows:
        labels_by_location_week[(row.location_id, row.week)].add(row.co_share_group)
    label_index = {
        (location_id, week, label): index
        for (location_id, week), labels in labels_by_location_week.items()
        for index, label in enumerate(sorted(labels))
    }
    positive_members = {
        (
            row.activity_id,
            row.week,
            row.location_id,
            label_index[(row.location_id, row.week, row.co_share_group)],
        )
        for row in occupancy_rows
    }
    for key, variable in member_vars.items():
        model.add_hint(variable, int(key in positive_members))


def _freeze_sample_outside_targets(
    model: cp_model.CpModel,
    instance: Instance,
    sample_dir: Path,
    free_activities: set[str],
    preserve_on_time_for_targets: bool,
    access_vars: dict[tuple[str, int], cp_model.IntVar],
    night_vars: dict[tuple[str, int, int], cp_model.IntVar],
    member_vars: dict[tuple[str, int, str, int], cp_model.IntVar],
) -> None:
    access_rows, occupancy_rows, _ = load_submission(sample_dir)
    sample_access = {(row.activity_id, row.week): row for row in access_rows}
    labels_by_location_week: dict[tuple[str, int], set[str]] = defaultdict(set)
    for row in occupancy_rows:
        labels_by_location_week[(row.location_id, row.week)].add(row.co_share_group)
    label_index = {
        (location_id, week, label): index
        for (location_id, week), labels in labels_by_location_week.items()
        for index, label in enumerate(sorted(labels))
    }
    positive_members = {
        (
            row.activity_id,
            row.week,
            row.location_id,
            label_index[(row.location_id, row.week, row.co_share_group)],
        )
        for row in occupancy_rows
    }
    preserved_target_weeks = {
        (activity_id, row.week)
        for (activity_id, _), row in sample_access.items()
        if activity_id in free_activities
        and preserve_on_time_for_targets
        and instance.completion_date(row.week)
        <= instance.projects[instance.activities[activity_id].contract_number].planned_completion_date
    }
    for key, variable in access_vars.items():
        if key[0] not in free_activities:
            model.add(variable == int(key in sample_access))
        elif key in preserved_target_weeks:
            model.add(variable == 1)
    for (activity_id, week, access_night), variable in night_vars.items():
        if activity_id not in free_activities:
            row = sample_access.get((activity_id, week))
            model.add(variable == int(row is not None and row.access_night == access_night))
        elif (activity_id, week) in preserved_target_weeks:
            row = sample_access[(activity_id, week)]
            model.add(variable == int(row.access_night == access_night))
    for key, variable in member_vars.items():
        if key[0] not in free_activities:
            model.add(variable == int(key in positive_members))
        elif (key[0], key[1]) in preserved_target_weeks:
            model.add(variable == int(key in positive_members))


def solve_scenario_a_relaxation(
    instance: Instance,
    output_dir: str | Path,
    *,
    time_limit_seconds: float = 60.0,
    workers: int = 8,
    seed: int = 1,
    sample_hint_dir: str | Path | None = None,
    freeze_except: set[str] | None = None,
    repair_late_only: bool = False,
) -> SolveTelemetry:
    """Solve Scenario A without closure/buffer conflicts.

    This is deliberately labelled a relaxation. Its output must never be promoted as
    validator-feasible until the missing closure rules and reference validator pass.
    """

    model = cp_model.CpModel()
    horizon = instance.horizon_weeks
    eligible: dict[str, range] = {}
    footprints: dict[str, tuple[str, ...]] = {}
    access: dict[tuple[str, int], cp_model.IntVar] = {}
    night: dict[tuple[str, int, int], cp_model.IntVar] = {}
    completion: dict[str, cp_model.IntVar] = {}
    start: dict[str, cp_model.IntVar] = {}
    scaled_cost: dict[str, cp_model.IntVar] = {}

    for activity_id, activity in instance.activities.items():
        first_week = max(1, instance.week_for_date(activity.planned_start_date))
        eligible[activity_id] = range(first_week, horizon + 1)
        footprints[activity_id] = activity_footprint(instance, activity)
        project = instance.projects[activity.contract_number]
        for week in eligible[activity_id]:
            access[(activity_id, week)] = model.new_bool_var(f"access[{activity_id},{week}]")
            for access_night in range(1, project.number_of_maximum_access_per_week + 1):
                night[(activity_id, week, access_night)] = model.new_bool_var(
                    f"night[{activity_id},{week},{access_night}]"
                )
            model.add(
                sum(
                    night[(activity_id, week, access_night)]
                    for access_night in range(1, project.number_of_maximum_access_per_week + 1)
                )
                == access[(activity_id, week)]
            )
        model.add(
            sum(access[(activity_id, week)] for week in eligible[activity_id])
            == activity.total_accesses
        )

        start_candidates: list[cp_model.IntVar] = []
        completion_candidates: list[cp_model.IntVar] = []
        for week in eligible[activity_id]:
            start_candidate = model.new_int_var(week, horizon + 1, f"start_c[{activity_id},{week}]")
            model.add(start_candidate == week).only_enforce_if(access[(activity_id, week)])
            model.add(start_candidate == horizon + 1).only_enforce_if(
                access[(activity_id, week)].Not()
            )
            start_candidates.append(start_candidate)
            completion_candidate = model.new_int_var(0, week, f"end_c[{activity_id},{week}]")
            model.add(completion_candidate == week).only_enforce_if(access[(activity_id, week)])
            model.add(completion_candidate == 0).only_enforce_if(access[(activity_id, week)].Not())
            completion_candidates.append(completion_candidate)
        start[activity_id] = model.new_int_var(first_week, horizon, f"start[{activity_id}]")
        completion[activity_id] = model.new_int_var(first_week, horizon, f"completion[{activity_id}]")
        model.add_min_equality(start[activity_id], start_candidates)
        model.add_max_equality(completion[activity_id], completion_candidates)

        costs = _activity_costs(instance, activity_id)
        scaled_cost[activity_id] = model.new_int_var(0, max(costs), f"cost10[{activity_id}]")
        model.add_element(completion[activity_id] - 1, costs, scaled_cost[activity_id])

    for activity_id, activity in instance.activities.items():
        if activity.predecessor_activity_id:
            model.add(start[activity_id] >= completion[activity.predecessor_activity_id] + 1)

    activities_by_contract: dict[str, list[str]] = defaultdict(list)
    for activity_id, activity in instance.activities.items():
        activities_by_contract[activity.contract_number].append(activity_id)
    for contract_number, activity_ids in activities_by_contract.items():
        project = instance.projects[contract_number]
        for week in range(1, horizon + 1):
            for access_night in range(1, project.number_of_maximum_access_per_week + 1):
                variables = [
                    night[(activity_id, week, access_night)]
                    for activity_id in activity_ids
                    if (activity_id, week, access_night) in night
                ]
                if variables:
                    model.add(sum(variables) <= project.number_of_workfronts)

    candidates_by_location_week: dict[tuple[str, int], list[str]] = defaultdict(list)
    for activity_id, weeks in eligible.items():
        for week in weeks:
            for location_id in footprints[activity_id]:
                candidates_by_location_week[(location_id, week)].append(activity_id)

    member: dict[tuple[str, int, str, int], cp_model.IntVar] = {}
    used: dict[tuple[str, int, int], cp_model.IntVar] = {}
    for (location_id, week), activity_ids in candidates_by_location_week.items():
        capacity = instance.locations[location_id].supply_capacity
        for group in range(capacity):
            used[(location_id, week, group)] = model.new_bool_var(
                f"used[{location_id},{week},{group}]"
            )
        for activity_id in activity_ids:
            group_vars = []
            for group in range(capacity):
                variable = model.new_bool_var(f"member[{activity_id},{week},{location_id},{group}]")
                member[(activity_id, week, location_id, group)] = variable
                group_vars.append(variable)
            model.add(sum(group_vars) == access[(activity_id, week)])

        for group in range(capacity):
            variables = [member[(activity_id, week, location_id, group)] for activity_id in activity_ids]
            for variable in variables:
                model.add(variable <= used[(location_id, week, group)])
            model.add(used[(location_id, week, group)] <= sum(variables))

            pm = [
                member[(activity_id, week, location_id, group)]
                for activity_id in activity_ids
                if instance.projects[instance.activities[activity_id].contract_number].access_type
                == "PM"
            ]
            pc = [
                member[(activity_id, week, location_id, group)]
                for activity_id in activity_ids
                if instance.projects[instance.activities[activity_id].contract_number].access_type
                == "PC"
            ]
            coworkers = [
                member[(activity_id, week, location_id, group)]
                for activity_id in activity_ids
                if instance.projects[instance.activities[activity_id].contract_number].access_type
                == "C"
            ]
            pm_sum = sum(pm) if pm else 0
            pc_sum = sum(pc) if pc else 0
            c_sum = sum(coworkers) if coworkers else 0
            model.add(pm_sum <= 1)
            model.add(pc_sum <= 1)
            model.add(c_sum <= 4 - pc_sum)
            model.add(pc_sum + c_sum <= 4 * (1 - pm_sum))
        for group in range(capacity - 1):
            model.add(used[(location_id, week, group + 1)] <= used[(location_id, week, group)])

    model.minimize(sum(scaled_cost.values()))
    if sample_hint_dir is not None:
        _add_sample_hints(
            model,
            instance,
            Path(sample_hint_dir),
            access,
            night,
            member,
        )
        if freeze_except is not None:
            unknown = sorted(freeze_except - set(instance.activities))
            if unknown:
                raise ValueError(f"unknown free activities: {unknown}")
            _freeze_sample_outside_targets(
                model,
                instance,
                Path(sample_hint_dir),
                freeze_except,
                repair_late_only,
                access,
                night,
                member,
            )

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit_seconds
    solver.parameters.num_search_workers = workers
    solver.parameters.random_seed = seed
    solver.parameters.log_search_progress = False
    started = time.monotonic()
    status_code = solver.solve(model)
    elapsed = time.monotonic() - started
    status = solver.status_name(status_code)
    has_solution = status_code in (cp_model.OPTIMAL, cp_model.FEASIBLE)

    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    if has_solution:
        access_output: list[dict[str, object]] = []
        occupancy_output: list[dict[str, object]] = []
        for activity_id in sorted(instance.activities):
            selected_weeks = [
                week
                for week in eligible[activity_id]
                if solver.value(access[(activity_id, week)])
            ]
            project = instance.projects[instance.activities[activity_id].contract_number]
            for sequence, week in enumerate(selected_weeks, 1):
                selected_night = next(
                    access_night
                    for access_night in range(1, project.number_of_maximum_access_per_week + 1)
                    if solver.value(night[(activity_id, week, access_night)])
                )
                access_output.append(
                    {
                        "activity_id": activity_id,
                        "access_seq": sequence,
                        "week": week,
                        "eclo": 0,
                        "access_night": selected_night,
                    }
                )
                for location_id in footprints[activity_id]:
                    capacity = instance.locations[location_id].supply_capacity
                    selected_group = next(
                        group
                        for group in range(capacity)
                        if solver.value(member[(activity_id, week, location_id, group)])
                    )
                    occupancy_output.append(
                        {
                            "activity_id": activity_id,
                            "week": week,
                            "location_id": location_id,
                            "co_share_group": f"g{selected_group + 1}",
                        }
                    )

        with (output_root / "SCHEDULE_ACCESS.csv").open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(
                handle, fieldnames=("activity_id", "access_seq", "week", "eclo", "access_night")
            )
            writer.writeheader()
            writer.writerows(access_output)
        with (output_root / "SCHEDULE_OCCUPANCY.csv").open(
            "w", newline="", encoding="utf-8"
        ) as handle:
            writer = csv.DictWriter(
                handle, fieldnames=("activity_id", "week", "location_id", "co_share_group")
            )
            writer.writeheader()
            writer.writerows(occupancy_output)

        results_output: list[dict[str, object]] = []
        for contract_number in sorted(instance.projects):
            project = instance.projects[contract_number]
            contract_week = max(
                solver.value(completion[activity_id])
                for activity_id in activities_by_contract[contract_number]
            )
            completion_date = instance.completion_date(contract_week)
            results_output.append(
                {
                    "scenario": "A",
                    "contract_number": contract_number,
                    "simulated_completion_date": completion_date.isoformat(),
                    "overrun_days": max(0, (completion_date - project.planned_completion_date).days),
                }
            )
        with (output_root / "RESULTS.csv").open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=(
                    "scenario",
                    "contract_number",
                    "simulated_completion_date",
                    "overrun_days",
                ),
            )
            writer.writeheader()
            writer.writerows(results_output)

    objective = solver.objective_value / 10.0 if has_solution else None
    bound = solver.best_objective_bound / 10.0 if has_solution else None
    proto = model.proto
    telemetry = SolveTelemetry(
        formulation=(
            "scenario_a_relaxation_without_closure_buffers"
            if freeze_except is None
            else "scenario_a_sample_preserving_repair_without_closure_buffers"
        ),
        status=status,
        objective_score=objective,
        best_bound=bound,
        wall_time_seconds=elapsed,
        conflicts=solver.num_conflicts,
        branches=solver.num_branches,
        seed=seed,
        workers=workers,
        time_limit_seconds=time_limit_seconds,
        model_variables=len(proto.variables),
        model_constraints=len(proto.constraints),
        limitation=(
            "Closure and buffer conflicts are omitted. Output is an optimistic candidate only and must not "
            "be called feasible or submitted without the reference validator."
        ),
    )
    (output_root / "TELEMETRY.json").write_text(telemetry.as_json() + "\n", encoding="utf-8")
    return telemetry
