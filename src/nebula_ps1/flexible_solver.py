from __future__ import annotations

import csv
import math
import time
from collections import defaultdict
from pathlib import Path

from ortools.sat.python import cp_model

from .closure import screen_closures
from .evaluate import AccessRow, OccupancyRow, evaluate_submission, load_submission
from .instance import Instance
from .solver import SolveTelemetry, _activity_costs, _add_sample_hints
from .topology import activity_footprint, affects_interchange_cross_line, split_sector_location


def solve_flexible_supply_relaxation(
    instance: Instance,
    output_dir: str | Path,
    scenario: str,
    *,
    time_limit_seconds: float = 120.0,
    workers: int = 8,
    seed: int = 1,
    closure_round_limit: int = 50,
    sample_hint_dir: str | Path | None = None,
    round_time_limit_seconds: float | None = None,
    forbid_buffer_overlap: bool = False,
    freeze_access_hint: bool = False,
    freeze_access_except: set[str] | None = None,
    separator_mode: str = "bridge_safe",
) -> SolveTelemetry:
    """Solve a scenario with iterative cuts from the inferred closure screen.

    The model implements the published workload, dates, predecessor, ECLO,
    allocation, workfront, legal-mix, capacity, and score rules. Closure safety is
    screened after generation and must eventually be enforced by the official
    validator. Keeping this boundary explicit prevents an optimistic score from
    being promoted as a valid submission.
    """

    if scenario not in {"A", "B", "C"}:
        raise ValueError("scenario must be A, B, or C")
    if separator_mode not in {"bridge_safe", "direct_heuristic"}:
        raise ValueError("separator_mode must be bridge_safe or direct_heuristic")
    if freeze_access_hint and sample_hint_dir is None:
        raise ValueError("freeze_access_hint requires sample_hint_dir")
    if freeze_access_except and not freeze_access_hint:
        raise ValueError("freeze_access_except requires freeze_access_hint")
    free_activities = freeze_access_except or set()
    unknown_free_activities = sorted(free_activities - set(instance.activities))
    if unknown_free_activities:
        raise ValueError(f"unknown free activities: {unknown_free_activities}")
    effective_round_limit = (
        round_time_limit_seconds
        if round_time_limit_seconds is not None
        else (1.0 if scenario in {"A", "B"} else 3.0)
    )
    if effective_round_limit <= 0:
        raise ValueError("round_time_limit_seconds must be positive")

    model = cp_model.CpModel()
    horizon = instance.horizon_weeks
    eligible: dict[str, range] = {}
    footprints: dict[str, tuple[str, ...]] = {}
    access: dict[tuple[str, int], cp_model.IntVar] = {}
    eclo: dict[tuple[str, int], cp_model.IntVar] = {}
    night: dict[tuple[str, int, int], cp_model.IntVar] = {}
    completion: dict[str, cp_model.IntVar] = {}
    start: dict[str, cp_model.IntVar] = {}
    scaled_delay: dict[str, cp_model.IntVar] = {}

    for activity_id, activity in sorted(instance.activities.items()):
        project = instance.projects[activity.contract_number]
        first_week = max(1, instance.week_for_date(activity.planned_start_date))
        last_week = (
            instance.last_week_completing_by(project.planned_completion_date)
            if scenario == "B"
            else horizon
        )
        last_week = min(last_week, horizon)
        if first_week > last_week:
            raise ValueError(
                f"{activity_id}: no eligible week between planned start and Scenario {scenario} limit"
            )
        eligible[activity_id] = range(first_week, last_week + 1)
        footprints[activity_id] = activity_footprint(instance, activity)

        for week in eligible[activity_id]:
            access[(activity_id, week)] = model.new_bool_var(f"access[{activity_id},{week}]")
            eclo[(activity_id, week)] = model.new_bool_var(f"eclo[{activity_id},{week}]")
            model.add(eclo[(activity_id, week)] <= access[(activity_id, week)])
            if scenario == "A":
                model.add(eclo[(activity_id, week)] == 0)
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

        # Half-units avoid floating point: standard=2, ECLO=3.
        model.add(
            2 * sum(access[(activity_id, week)] for week in eligible[activity_id])
            + sum(eclo[(activity_id, week)] for week in eligible[activity_id])
            >= 2 * activity.total_accesses
        )

        start_candidates: list[cp_model.IntVar] = []
        completion_candidates: list[cp_model.IntVar] = []
        for week in eligible[activity_id]:
            start_candidate = model.new_int_var(
                week, last_week + 1, f"start_c[{activity_id},{week}]"
            )
            model.add(start_candidate == week).only_enforce_if(access[(activity_id, week)])
            model.add(start_candidate == last_week + 1).only_enforce_if(
                access[(activity_id, week)].Not()
            )
            start_candidates.append(start_candidate)
            completion_candidate = model.new_int_var(0, week, f"end_c[{activity_id},{week}]")
            model.add(completion_candidate == week).only_enforce_if(access[(activity_id, week)])
            model.add(completion_candidate == 0).only_enforce_if(
                access[(activity_id, week)].Not()
            )
            completion_candidates.append(completion_candidate)
        start[activity_id] = model.new_int_var(first_week, last_week, f"start[{activity_id}]")
        completion[activity_id] = model.new_int_var(
            first_week, last_week, f"completion[{activity_id}]"
        )
        model.add_min_equality(start[activity_id], start_candidates)
        model.add_max_equality(completion[activity_id], completion_candidates)

        costs = _activity_costs(instance, activity_id)
        scaled_delay[activity_id] = model.new_int_var(
            0, max(costs), f"delay10[{activity_id}]"
        )
        model.add_element(completion[activity_id] - 1, costs, scaled_delay[activity_id])

    for activity_id, activity in sorted(instance.activities.items()):
        if activity.predecessor_activity_id:
            model.add(start[activity_id] >= completion[activity.predecessor_activity_id] + 1)

    activities_by_contract: dict[str, list[str]] = defaultdict(list)
    for activity_id, activity in sorted(instance.activities.items()):
        activities_by_contract[activity.contract_number].append(activity_id)
    for contract_number, activity_ids in sorted(activities_by_contract.items()):
        activity_ids.sort()
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

    if scenario == "C":
        line_window_start = {
            line: model.new_int_var(1, horizon, f"eclo_window_start[{line}]")
            for line in sorted(instance.lines)
        }
        for (activity_id, week), variable in eclo.items():
            activity = instance.activities[activity_id]
            line, _, _ = split_sector_location(activity.start_location_id)
            affected_lines = set(instance.lines) if affects_interchange_cross_line(
                instance, activity
            ) else {line}
            for affected_line in sorted(affected_lines):
                model.add(line_window_start[affected_line] <= week).only_enforce_if(variable)
                model.add(line_window_start[affected_line] + 1 >= week).only_enforce_if(variable)

    candidates_by_location_week: dict[tuple[str, int], list[str]] = defaultdict(list)
    for activity_id, weeks in sorted(eligible.items()):
        for week in weeks:
            for location_id in footprints[activity_id]:
                candidates_by_location_week[(location_id, week)].append(activity_id)

    member: dict[tuple[str, int, str, int], cp_model.IntVar] = {}
    used: dict[tuple[str, int, int], cp_model.IntVar] = {}
    excess_terms: list[cp_model.IntVar] = []
    for (location_id, week), activity_ids in sorted(candidates_by_location_week.items()):
        activity_ids.sort()
        supply = instance.locations[location_id].supply_capacity
        if scenario == "B":
            group_limit = len(activity_ids)
        elif scenario == "C":
            group_limit = min(len(activity_ids), supply + 1)
        else:
            group_limit = min(len(activity_ids), supply)
        for group in range(group_limit):
            used[(location_id, week, group)] = model.new_bool_var(
                f"used[{location_id},{week},{group}]"
            )
            if group >= supply:
                excess_terms.append(used[(location_id, week, group)])
        for activity_id in activity_ids:
            group_vars = []
            for group in range(group_limit):
                variable = model.new_bool_var(
                    f"member[{activity_id},{week},{location_id},{group}]"
                )
                member[(activity_id, week, location_id, group)] = variable
                group_vars.append(variable)
            model.add(sum(group_vars) == access[(activity_id, week)])

        for group in range(group_limit):
            variables = [
                member[(activity_id, week, location_id, group)]
                for activity_id in activity_ids
            ]
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
        for group in range(group_limit - 1):
            model.add(used[(location_id, week, group + 1)] <= used[(location_id, week, group)])

    primary_terms: list[cp_model.LinearExpr] = []
    if scenario in {"A", "C"}:
        primary_terms.extend(scaled_delay.values())
    primary_terms.extend(70 * term for term in excess_terms)
    if scenario in {"B", "C"}:
        primary_terms.extend(50 * term for term in eclo.values())
    max_primary = (
        sum(max(_activity_costs(instance, activity_id)) for activity_id in sorted(instance.activities))
        + 70 * len(excess_terms)
        + 50 * len(eclo)
    )
    primary_score = model.new_int_var(0, max_primary, "primary_score_tenths")
    model.add(primary_score == sum(primary_terms))

    hint_root: Path | None = None
    if sample_hint_dir is not None:
        hint_root = Path(sample_hint_dir)
        _add_sample_hints(model, instance, hint_root, access, night, member)
        hint_access, _, _ = load_submission(hint_root)
        hinted_eclo = {(row.activity_id, row.week): row.eclo for row in hint_access}
        for key, variable in sorted(eclo.items()):
            model.add_hint(variable, hinted_eclo.get(key, 0))
        if freeze_access_hint:
            hint_by_key = {(row.activity_id, row.week): row for row in hint_access}
            unknown_keys = sorted(set(hint_by_key) - set(access))
            if unknown_keys:
                raise ValueError(f"hint contains ineligible access rows: {unknown_keys[:5]}")
            for key, variable in sorted(access.items()):
                if key[0] in free_activities:
                    continue
                row = hint_by_key.get(key)
                model.add(variable == int(row is not None))
                model.add(eclo[key] == (row.eclo if row is not None else 0))
            for (activity_id, week, access_night), variable in sorted(night.items()):
                if activity_id in free_activities:
                    continue
                row = hint_by_key.get((activity_id, week))
                model.add(
                    variable
                    == int(row is not None and row.access_night == access_night)
                )

    # Official penalty is lexicographically dominant; row count only removes
    # redundant, score-neutral access rows and cannot trade against one tenth.
    max_rows = len(access)
    tie_scale = max_rows + 1
    model.minimize(primary_score * tie_scale + sum(access.values()))

    def group_limit(location_id: str, week: int) -> int:
        candidates = len(candidates_by_location_week[(location_id, week)])
        if scenario == "B":
            return candidates
        supply = instance.locations[location_id].supply_capacity
        if scenario == "C":
            return min(candidates, supply + 1)
        return min(candidates, supply)

    def extract_rows(
        solver: cp_model.CpSolver,
    ) -> tuple[list[AccessRow], list[OccupancyRow]]:
        access_rows: list[AccessRow] = []
        occupancy_rows: list[OccupancyRow] = []
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
                access_rows.append(
                    AccessRow(
                        activity_id,
                        sequence,
                        week,
                        solver.value(eclo[(activity_id, week)]),
                        selected_night,
                    )
                )
                for location_id in footprints[activity_id]:
                    selected_group = next(
                        group
                        for group in range(group_limit(location_id, week))
                        if solver.value(member[(activity_id, week, location_id, group)])
                    )
                    occupancy_rows.append(
                        OccupancyRow(
                            activity_id,
                            week,
                            location_id,
                            f"g{selected_group + 1}",
                        )
                    )
        return access_rows, occupancy_rows

    solver = cp_model.CpSolver()
    solver.parameters.num_search_workers = workers
    solver.parameters.random_seed = seed
    solver.parameters.log_search_progress = False
    started = time.monotonic()
    deadline = started + time_limit_seconds
    status_code = cp_model.UNKNOWN
    has_solution = False
    final_access_rows: list[AccessRow] = []
    final_occupancy_rows: list[OccupancyRow] = []
    final_conflicts = ()
    safe_access_rows: list[AccessRow] | None = None
    safe_occupancy_rows: list[OccupancyRow] | None = None
    safe_objective_tenths: int | None = None
    safe_proven_optimal = False
    safe_tie_break_proven = False
    closure_rounds = 0
    solve_rounds = 0
    total_conflicts = 0
    total_branches = 0
    active_round_limit = effective_round_limit
    maximum_round_limit_used = 0.0
    unknown_retries = 0

    if hint_root is not None:
        hint_evaluation = evaluate_submission(instance, hint_root, scenario)
        hint_access_rows, hint_occupancy_rows, _ = load_submission(hint_root)
        hint_strict_conflicts = (
            screen_closures(
                instance,
                hint_access_rows,
                hint_occupancy_rows,
                forbid_buffer_overlap=True,
            )
            if forbid_buffer_overlap
            else ()
        )
        if hint_evaluation.internally_feasible and not hint_strict_conflicts:
            safe_access_rows = list(hint_access_rows)
            safe_occupancy_rows = list(hint_occupancy_rows)
            safe_objective_tenths = int(round(hint_evaluation.objective_score * 10))
            # The checked hint is already a deliverable incumbent. Search only
            # for a strict primary-score improvement; equal-score row cleanup is
            # handled by the full-gate pruner.
            model.add(primary_score <= safe_objective_tenths - 1)

    while closure_rounds <= closure_round_limit:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        solve_limit = min(remaining, active_round_limit)
        maximum_round_limit_used = max(maximum_round_limit_used, solve_limit)
        solver.parameters.max_time_in_seconds = solve_limit
        status_code = solver.solve(model)
        solve_rounds += 1
        total_conflicts += solver.num_conflicts
        total_branches += solver.num_branches
        has_solution = status_code in (cp_model.OPTIMAL, cp_model.FEASIBLE)
        if not has_solution:
            if safe_objective_tenths is not None and status_code == cp_model.INFEASIBLE:
                safe_proven_optimal = True
            if status_code == cp_model.UNKNOWN:
                next_limit = min(30.0, active_round_limit * 2)
                if next_limit > active_round_limit and deadline - time.monotonic() > 0:
                    active_round_limit = next_limit
                    unknown_retries += 1
                    continue
            break
        # Once a cut-augmented model needs a longer round, keep that budget.
        # Resetting after one feasible solve causes repeated UNKNOWN/retry cycles
        # as the relaxation becomes progressively harder.
        final_access_rows, final_occupancy_rows = extract_rows(solver)
        final_conflicts = screen_closures(
            instance,
            final_access_rows,
            final_occupancy_rows,
            forbid_buffer_overlap=forbid_buffer_overlap,
        )
        current_objective_tenths = solver.value(primary_score)
        if not final_conflicts:
            if safe_objective_tenths is None or current_objective_tenths < safe_objective_tenths:
                safe_access_rows = final_access_rows
                safe_occupancy_rows = final_occupancy_rows
                safe_objective_tenths = current_objective_tenths
            if status_code == cp_model.OPTIMAL:
                safe_proven_optimal = True
                safe_tie_break_proven = True
                break
            model.add(primary_score <= current_objective_tenths - 1)
            continue
        if closure_rounds == closure_round_limit:
            break

        cuts_added = 0
        # A valid repair must move one conflicting activity or add an edge that
        # expands the first component. Any direct or transitive merge with the
        # second component necessarily starts with such an edge. This is stronger
        # than an exact-layout no-good but preserves the public bridge pattern.
        for conflict_index, conflict in enumerate(final_conflicts):
            first = tuple(sorted(conflict.first_activities))
            second = tuple(sorted(conflict.second_activities))
            first_set = set(first)
            involved = set(first + second)
            repair_literals: list[cp_model.LiteralT] = [
                access[(activity_id, conflict.week)].Not()
                for activity_id in sorted(involved)
            ]

            join_targets = (
                sorted(second)
                if separator_mode == "direct_heuristic"
                else sorted(instance.activities)
            )
            for first_activity in first:
                for other_activity in join_targets:
                    if other_activity in first_set:
                        continue
                    if (other_activity, conflict.week) not in access:
                        continue
                    common_locations = set(footprints[first_activity]) & set(
                        footprints[other_activity]
                    )
                    for location_id in sorted(common_locations):
                        for group in range(group_limit(location_id, conflict.week)):
                            first_member = member.get(
                                (first_activity, conflict.week, location_id, group)
                            )
                            other_member = member.get(
                                (other_activity, conflict.week, location_id, group)
                            )
                            if first_member is None or other_member is None:
                                continue
                            together = model.new_bool_var(
                                "closure_direct_join["
                                f"{closure_rounds},{conflict_index},{first_activity},"
                                f"{other_activity},{conflict.week},{location_id},{group}]"
                            )
                            model.add(together <= first_member)
                            model.add(together <= other_member)
                            model.add(together >= first_member + other_member - 1)
                            repair_literals.append(together)

            model.add_bool_or(repair_literals)
            cuts_added += 1
        if cuts_added == 0:
            break
        closure_rounds += 1

    elapsed = time.monotonic() - started
    if safe_access_rows is not None:
        final_access_rows = safe_access_rows
        final_occupancy_rows = safe_occupancy_rows or []
        final_conflicts = ()
        if safe_tie_break_proven:
            status = "OPTIMAL"
        elif safe_proven_optimal:
            status = "PRIMARY_OPTIMAL_SAFE_INCUMBENT"
        else:
            status = "FEASIBLE_SAFE_INCUMBENT"
        if separator_mode == "direct_heuristic":
            status = "HEURISTIC_SAFE_INCUMBENT"
            safe_proven_optimal = False
            safe_tie_break_proven = False
    else:
        status = solver.status_name(status_code)

    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    output_available = safe_access_rows is not None or has_solution
    if output_available:
        access_output: list[dict[str, object]] = []
        occupancy_output: list[dict[str, object]] = []
        for row in final_access_rows:
            access_output.append(
                {
                    "activity_id": row.activity_id,
                    "access_seq": row.access_seq,
                    "week": row.week,
                    "eclo": row.eclo,
                    "access_night": row.access_night,
                }
            )
        for row in final_occupancy_rows:
            occupancy_output.append(
                {
                    "activity_id": row.activity_id,
                    "week": row.week,
                    "location_id": row.location_id,
                    "co_share_group": row.co_share_group,
                }
            )

        with (output_root / "SCHEDULE_ACCESS.csv").open(
            "w", newline="", encoding="utf-8"
        ) as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=("activity_id", "access_seq", "week", "eclo", "access_night"),
                lineterminator="\n",
            )
            writer.writeheader()
            writer.writerows(access_output)
        with (output_root / "SCHEDULE_OCCUPANCY.csv").open(
            "w", newline="", encoding="utf-8"
        ) as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=("activity_id", "week", "location_id", "co_share_group"),
                lineterminator="\n",
            )
            writer.writeheader()
            writer.writerows(occupancy_output)

        completion_by_activity = {
            activity_id: max(
                row.week for row in final_access_rows if row.activity_id == activity_id
            )
            for activity_id in sorted(instance.activities)
        }
        results_output: list[dict[str, object]] = []
        for contract_number in sorted(instance.projects):
            project = instance.projects[contract_number]
            contract_week = max(
                completion_by_activity[activity_id]
                for activity_id in activities_by_contract[contract_number]
            )
            completion_date = instance.completion_date(contract_week)
            results_output.append(
                {
                    "scenario": scenario,
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
                lineterminator="\n",
            )
            writer.writeheader()
            writer.writerows(results_output)

    if safe_objective_tenths is not None:
        objective = safe_objective_tenths / 10.0
    elif has_solution:
        objective = solver.value(primary_score) / 10.0
    else:
        objective = None
    if separator_mode == "direct_heuristic":
        bound = None
    elif safe_proven_optimal and safe_objective_tenths is not None:
        bound = safe_objective_tenths / 10.0
    elif has_solution:
        bound = math.floor(solver.best_objective_bound / tie_scale) / 10.0
    else:
        bound = None
    proto = model.proto
    telemetry = SolveTelemetry(
        formulation=(
            f"scenario_{scenario.lower()}_iterative_{separator_mode}_"
            f"{'strict_buffer' if forbid_buffer_overlap else 'sample_consistent'}_closure_relaxation"
            f"{'_partially_frozen_access' if free_activities else '_frozen_access' if freeze_access_hint else ''}"
        ),
        status=status,
        objective_score=objective,
        best_bound=bound,
        wall_time_seconds=elapsed,
        conflicts=total_conflicts,
        branches=total_branches,
        seed=seed,
        workers=workers,
        time_limit_seconds=time_limit_seconds,
        model_variables=len(proto.variables),
        model_constraints=len(proto.constraints),
        limitation=(
            (
                "Direct-component cuts are an over-restrictive candidate-generation heuristic; solver "
                "bounds and optimality statuses are suppressed. Every returned candidate still passes the "
                "full implemented checker."
                if separator_mode == "direct_heuristic"
                else
                "Closure and buffer conflicts use the stricter published buffer-to-buffer rule, which "
                "contradicts four cases in the organizer's stated-feasible sample. This output is a hedge, "
                "not validator confirmation."
                if forbid_buffer_overlap
                else "Closure and buffer conflicts are separated using an inferred rule set that matches "
                "the public fixture; reference-validator confirmation is still mandatory."
            )
            + " The row-count tie-breaker cannot alter the official penalty objective."
        ),
        closure_rounds=closure_rounds,
        remaining_closure_conflicts=len(final_conflicts),
        round_time_limit_seconds=effective_round_limit,
        solve_rounds=solve_rounds,
        maximum_round_time_seconds=maximum_round_limit_used,
        unknown_retries=unknown_retries,
        primary_score_proven_optimal=safe_proven_optimal,
        tie_break_proven_optimal=safe_tie_break_proven,
    )
    (output_root / "TELEMETRY.json").write_text(telemetry.as_json() + "\n", encoding="utf-8")
    return telemetry
