from __future__ import annotations

import csv
import hashlib
import json
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path

from .instance import InputError, Instance
from .objective import ACTIVITY_NUDGE, CONTRACT_WEIGHT, ECLO_COST, EXCESS_COST
from .topology import activity_footprint, affects_interchange_cross_line, split_sector_location
from .closure import screen_closures


@dataclass(frozen=True)
class AccessRow:
    activity_id: str
    access_seq: int
    week: int
    eclo: int
    access_night: int


@dataclass(frozen=True)
class OccupancyRow:
    activity_id: str
    week: int
    location_id: str
    co_share_group: str


@dataclass(frozen=True)
class ResultRow:
    scenario: str
    contract_number: str
    simulated_completion_date: date
    overrun_days: int


@dataclass(frozen=True)
class Evaluation:
    scenario: str
    dataset_hash: str
    submission_hash: str
    hard_violations: tuple[str, ...]
    warnings: tuple[str, ...]
    checked_rules: tuple[str, ...]
    objective_score: float
    priority_weighted_score: float
    priority_overrun: dict[int, int]
    excess_access_nights_total: int
    eclo_nights_total: int
    access_rows: int
    occupancy_rows: int

    @property
    def internally_feasible(self) -> bool:
        return not self.hard_violations

    @property
    def reference_validator_confirmed(self) -> bool:
        return False

    def as_json(self) -> str:
        payload = asdict(self)
        payload["internally_feasible"] = self.internally_feasible
        payload["reference_validator_confirmed"] = self.reference_validator_confirmed
        return json.dumps(payload, indent=2, sort_keys=True)


def _read(path: Path, required: tuple[str, ...]) -> list[dict[str, str]]:
    try:
        with path.open(newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle)
            missing = set(required) - set(reader.fieldnames or ())
            if missing:
                raise InputError(f"{path.name}: missing columns {sorted(missing)}")
            return list(reader)
    except FileNotFoundError as exc:
        raise InputError(f"missing submission file: {path}") from exc


def _int(value: str, field: str, source: str) -> int:
    try:
        return int(value)
    except ValueError as exc:
        raise InputError(f"{source}: {field} must be an integer") from exc


def load_submission(
    submission_dir: str | Path,
) -> tuple[list[AccessRow], list[OccupancyRow], list[ResultRow]]:
    root = Path(submission_dir)
    access = [
        AccessRow(
            row["activity_id"].strip(),
            _int(row["access_seq"], "access_seq", "SCHEDULE_ACCESS.csv"),
            _int(row["week"], "week", "SCHEDULE_ACCESS.csv"),
            _int(row["eclo"], "eclo", "SCHEDULE_ACCESS.csv"),
            _int(row["access_night"], "access_night", "SCHEDULE_ACCESS.csv"),
        )
        for row in _read(
            root / "SCHEDULE_ACCESS.csv",
            ("activity_id", "access_seq", "week", "eclo", "access_night"),
        )
    ]
    occupancy = [
        OccupancyRow(
            row["activity_id"].strip(),
            _int(row["week"], "week", "SCHEDULE_OCCUPANCY.csv"),
            row["location_id"].strip(),
            row["co_share_group"].strip(),
        )
        for row in _read(
            root / "SCHEDULE_OCCUPANCY.csv",
            ("activity_id", "week", "location_id", "co_share_group"),
        )
    ]
    results = [
        ResultRow(
            row["scenario"].strip(),
            row["contract_number"].strip(),
            date.fromisoformat(row["simulated_completion_date"]),
            _int(row["overrun_days"], "overrun_days", "RESULTS.csv"),
        )
        for row in _read(
            root / "RESULTS.csv",
            ("scenario", "contract_number", "simulated_completion_date", "overrun_days"),
        )
    ]
    return access, occupancy, results


def _submission_hash(root: Path) -> str:
    digest = hashlib.sha256()
    for name in ("SCHEDULE_ACCESS.csv", "SCHEDULE_OCCUPANCY.csv", "RESULTS.csv"):
        digest.update(name.encode())
        digest.update(b"\0")
        digest.update((root / name).read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def evaluate_submission(
    instance: Instance, submission_dir: str | Path, scenario: str | None = None
) -> Evaluation:
    root = Path(submission_dir).resolve()
    access, occupancy, results = load_submission(root)
    violations: list[str] = []
    warnings: list[str] = []

    result_scenarios = {row.scenario for row in results}
    if len(result_scenarios) != 1:
        violations.append(f"results must contain exactly one scenario, found {sorted(result_scenarios)}")
    inferred_scenario = next(iter(result_scenarios), scenario or "")
    selected_scenario = scenario or inferred_scenario
    if selected_scenario not in {"A", "B", "C"}:
        violations.append(f"unknown scenario: {selected_scenario!r}")
    if scenario and result_scenarios and result_scenarios != {scenario}:
        violations.append(f"RESULTS scenario {sorted(result_scenarios)} disagrees with {scenario}")

    access_by_activity: dict[str, list[AccessRow]] = defaultdict(list)
    access_keys: set[tuple[str, int]] = set()
    for row in access:
        if row.activity_id not in instance.activities:
            violations.append(f"unknown activity in access output: {row.activity_id}")
            continue
        if row.eclo not in {0, 1}:
            violations.append(f"{row.activity_id} week {row.week}: eclo must be 0 or 1")
        if not 1 <= row.week <= instance.horizon_weeks:
            violations.append(f"{row.activity_id}: week {row.week} outside horizon")
        key = (row.activity_id, row.week)
        if key in access_keys:
            violations.append(f"{row.activity_id}: more than one access in week {row.week}")
        access_keys.add(key)
        access_by_activity[row.activity_id].append(row)

    activity_completion_week: dict[str, int] = {}
    for activity_id, activity in instance.activities.items():
        rows = sorted(access_by_activity.get(activity_id, ()), key=lambda item: item.week)
        if not rows:
            violations.append(f"{activity_id}: no scheduled access")
            continue
        seqs = [row.access_seq for row in rows]
        if seqs != list(range(1, len(rows) + 1)):
            violations.append(f"{activity_id}: access_seq does not follow chronological weeks")
        required_half_units = 2 * activity.total_accesses
        supplied_half_units = sum(3 if row.eclo else 2 for row in rows)
        if supplied_half_units < required_half_units:
            violations.append(
                f"{activity_id}: workload {supplied_half_units}/2 below {required_half_units}/2"
            )
        start_week = instance.week_for_date(activity.planned_start_date)
        if rows[0].week < start_week:
            violations.append(f"{activity_id}: starts in week {rows[0].week} before week {start_week}")
        activity_completion_week[activity_id] = rows[-1].week

    for activity_id, activity in instance.activities.items():
        predecessor = activity.predecessor_activity_id
        if not predecessor or activity_id not in access_by_activity or predecessor not in activity_completion_week:
            continue
        first_week = min(row.week for row in access_by_activity[activity_id])
        if first_week <= activity_completion_week[predecessor]:
            violations.append(
                f"{activity_id}: starts week {first_week} before predecessor {predecessor} finishes"
            )

    occupancy_map: dict[tuple[str, int, str], OccupancyRow] = {}
    for row in occupancy:
        key = (row.activity_id, row.week, row.location_id)
        if key in occupancy_map:
            violations.append(f"duplicate occupancy row: {key}")
        occupancy_map[key] = row
        if row.activity_id not in instance.activities:
            violations.append(f"unknown activity in occupancy output: {row.activity_id}")
        if row.location_id not in instance.locations:
            violations.append(f"unknown occupancy location: {row.location_id}")
        if not row.co_share_group:
            violations.append(f"empty co_share_group: {key}")
        if (row.activity_id, row.week) not in access_keys:
            violations.append(f"occupancy without access row: {key}")

    expected_occupancy: set[tuple[str, int, str]] = set()
    for row in access:
        activity = instance.activities.get(row.activity_id)
        if not activity:
            continue
        expected_occupancy.update(
            (row.activity_id, row.week, location_id)
            for location_id in activity_footprint(instance, activity)
        )
    actual_occupancy = set(occupancy_map)
    missing_occupancy = expected_occupancy - actual_occupancy
    extra_occupancy = actual_occupancy - expected_occupancy
    if missing_occupancy:
        violations.append(f"missing {len(missing_occupancy)} required occupancy rows")
    if extra_occupancy:
        violations.append(f"found {len(extra_occupancy)} unexpected occupancy rows")

    allocation_nights: dict[tuple[str, str, int], set[int]] = defaultdict(set)
    workfronts: dict[tuple[str, str, int, int], set[str]] = defaultdict(set)
    for row in access:
        activity = instance.activities.get(row.activity_id)
        if not activity:
            continue
        project = instance.projects[activity.contract_number]
        allocation_key = (project.contract_number, activity.activity_type, row.week)
        allocation_nights[allocation_key].add(row.access_night)
        workfronts[(*allocation_key, row.access_night)].add(activity.activity_id)
        if not 1 <= row.access_night <= project.number_of_maximum_access_per_week:
            violations.append(
                f"{activity.activity_id} week {row.week}: access_night {row.access_night} outside contract cap"
            )
    for (contract, activity_type, week), nights in allocation_nights.items():
        project = instance.projects[contract]
        if len(nights) > project.number_of_maximum_access_per_week:
            violations.append(f"{contract}/{activity_type} week {week}: weekly allocation exceeded")
    for (contract, activity_type, week, night), activities in workfronts.items():
        project = instance.projects[contract]
        if len(activities) > project.number_of_workfronts:
            violations.append(
                f"{contract}/{activity_type} week {week} night {night}: workfront cap exceeded"
            )

    local_groups: dict[tuple[int, str, str], set[str]] = defaultdict(set)
    location_week_groups: dict[tuple[int, str], set[str]] = defaultdict(set)
    for row in occupancy:
        if row.activity_id not in instance.activities or row.location_id not in instance.locations:
            continue
        local_groups[(row.week, row.location_id, row.co_share_group)].add(row.activity_id)
        location_week_groups[(row.week, row.location_id)].add(row.co_share_group)

    for (week, location_id, group), activity_ids in local_groups.items():
        access_types = [
            instance.projects[instance.activities[activity_id].contract_number].access_type
            for activity_id in activity_ids
        ]
        pm = access_types.count("PM")
        pc = access_types.count("PC")
        c = access_types.count("C")
        legal = (pm == 1 and len(access_types) == 1) or (
            pm == 0 and pc == 1 and c <= 3 and len(access_types) == pc + c
        ) or (pm == 0 and pc == 0 and c <= 4 and len(access_types) == c)
        if not legal:
            violations.append(
                f"week {week} {location_id} group {group}: illegal mix PM={pm} PC={pc} C={c}"
            )

    excess_total = 0
    for (week, location_id), groups in location_week_groups.items():
        supply = instance.locations[location_id].supply_capacity
        excess = max(0, len(groups) - supply)
        excess_total += excess
        if selected_scenario == "A" and excess:
            violations.append(f"week {week} {location_id}: Scenario A capacity exceeded by {excess}")
        if selected_scenario == "C" and excess > 1:
            violations.append(f"week {week} {location_id}: Scenario C capacity exceeded by {excess}")

    eclo_rows = [row for row in access if row.eclo == 1]
    if selected_scenario == "A" and eclo_rows:
        violations.append("Scenario A forbids ECLO")
    if selected_scenario == "C":
        eclo_by_line: dict[str, set[int]] = defaultdict(set)
        for row in eclo_rows:
            activity = instance.activities.get(row.activity_id)
            if not activity:
                continue
            line, _, _ = split_sector_location(activity.start_location_id)
            eclo_by_line[line].add(row.week)
            if affects_interchange_cross_line(instance, activity):
                for other_line in instance.lines:
                    eclo_by_line[other_line].add(row.week)
        for line, weeks in eclo_by_line.items():
            if weeks and max(weeks) - min(weeks) > 1:
                violations.append(f"Scenario C {line}: ECLO weeks do not fit a two-week window")

    closure_access = [row for row in access if row.activity_id in instance.activities]
    closure_occupancy = [
        row
        for row in occupancy
        if row.activity_id in instance.activities
        and row.location_id in instance.locations
        and (row.activity_id, row.week) in access_keys
    ]
    closure_conflicts = screen_closures(instance, closure_access, closure_occupancy)
    violations.extend(conflict.describe() for conflict in closure_conflicts)

    contract_completion: dict[str, date] = {}
    contract_overrun_days: dict[str, int] = {}
    for contract_number, project in instance.projects.items():
        contract_activities = [
            activity
            for activity in instance.activities.values()
            if activity.contract_number == contract_number
        ]
        completed = [
            instance.completion_date(activity_completion_week[activity.activity_id])
            for activity in contract_activities
            if activity.activity_id in activity_completion_week
        ]
        if len(completed) != len(contract_activities):
            continue
        contract_completion[contract_number] = max(completed)
        contract_overrun_days[contract_number] = max(
            0,
            (contract_completion[contract_number] - project.planned_completion_date).days,
        )
        for activity in contract_activities:
            completion = instance.completion_date(activity_completion_week[activity.activity_id])
            if selected_scenario == "B" and completion > project.planned_completion_date:
                violations.append(
                    f"{activity.activity_id}: Scenario B planned completion exceeded by "
                    f"{(completion - project.planned_completion_date).days} days"
                )

    result_by_contract: dict[str, ResultRow] = {}
    for row in results:
        if row.contract_number in result_by_contract:
            violations.append(f"duplicate RESULTS contract: {row.contract_number}")
        result_by_contract[row.contract_number] = row
    if set(result_by_contract) != set(instance.projects):
        missing = sorted(set(instance.projects) - set(result_by_contract))
        extra = sorted(set(result_by_contract) - set(instance.projects))
        violations.append(f"RESULTS contract mismatch: missing={missing}, extra={extra}")
    for contract_number, completion in contract_completion.items():
        row = result_by_contract.get(contract_number)
        if not row:
            continue
        project = instance.projects[contract_number]
        overrun = max(0, (completion - project.planned_completion_date).days)
        if row.simulated_completion_date != completion or row.overrun_days != overrun:
            violations.append(
                f"{contract_number}: RESULTS expected {completion.isoformat()}/{overrun}, "
                f"found {row.simulated_completion_date.isoformat()}/{row.overrun_days}"
            )

    priority_overrun: dict[int, int] = {1: 0, 2: 0, 3: 0}
    priority_weighted_score = 0.0
    for contract_number, days in contract_overrun_days.items():
        project = instance.projects[contract_number]
        priority_overrun[project.contract_priority] += days
        for activity in instance.activities.values():
            if activity.contract_number == contract_number:
                priority_weighted_score += (
                    days
                    * CONTRACT_WEIGHT[project.contract_priority]
                    * (1.0 + ACTIVITY_NUDGE[activity.activity_priority])
                )
    eclo_total = len(eclo_rows)
    if selected_scenario == "A":
        objective = priority_weighted_score
    elif selected_scenario == "B":
        objective = EXCESS_COST * excess_total + ECLO_COST * eclo_total
    elif selected_scenario == "C":
        objective = (
            priority_weighted_score
            + EXCESS_COST * excess_total
            + ECLO_COST * eclo_total
        )
    else:
        objective = float("nan")

    warnings.append(
        "closure screen reproduces official A-001 and accepts A-002/B-001/C-001; hidden-instance equivalence is not guaranteed"
    )
    checked_rules = (
        "schema",
        "workload",
        "planned_start",
        "predecessor",
        "horizon",
        "occupancy_footprint",
        "legal_mix",
        "weekly_allocation",
        "workfront",
        "scenario_capacity",
        "scenario_eclo",
        "sample_consistent_closure_screen",
        "results",
        "objective_formula",
    )
    return Evaluation(
        scenario=selected_scenario,
        dataset_hash=instance.dataset_hash,
        submission_hash=_submission_hash(root),
        hard_violations=tuple(violations),
        warnings=tuple(warnings),
        checked_rules=checked_rules,
        objective_score=round(objective, 10),
        priority_weighted_score=round(priority_weighted_score, 10),
        priority_overrun=priority_overrun,
        excess_access_nights_total=excess_total,
        eclo_nights_total=eclo_total,
        access_rows=len(access),
        occupancy_rows=len(occupancy),
    )
