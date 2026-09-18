from __future__ import annotations

import csv
import json
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import date, timedelta
from pathlib import Path


@dataclass(frozen=True)
class IndependentScore:
    scenario: str
    priority_weighted_delay: float
    excess_access_nights: int
    eclo_nights: int
    objective_score: float
    access_rows: int
    occupancy_rows: int

    def as_json(self) -> str:
        return json.dumps(asdict(self), indent=2, sort_keys=True)


def _csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def independently_score(data_dir: str | Path, submission_dir: str | Path) -> IndependentScore:
    """Recompute published score components without importing project model code.

    This intentionally duplicates parsing and arithmetic. It is a correlated-error
    check for score reporting, not a feasibility validator and not an official score.
    """

    data_root = Path(data_dir)
    submission_root = Path(submission_dir)
    parameters = {row["key"]: row["value"] for row in _csv(data_root / "06_PARAMETERS.csv")}
    horizon_start = date.fromisoformat(parameters["horizon_start"])

    projects = {
        row["contract_number"]: row for row in _csv(data_root / "07_PROJECT_DETAILS.csv")
    }
    activities = {
        row["activity_id"]: row for row in _csv(data_root / "08_ACTIVITY_DETAILS.csv")
    }
    supply = {
        row["location_id"]: int(row["supply_capacity"])
        for row in _csv(data_root / "04_LOCATION_SUPPLY.csv")
    }
    access_rows = _csv(submission_root / "SCHEDULE_ACCESS.csv")
    occupancy_rows = _csv(submission_root / "SCHEDULE_OCCUPANCY.csv")
    result_rows = _csv(submission_root / "RESULTS.csv")
    scenarios = {row["scenario"] for row in result_rows}
    if len(scenarios) != 1:
        raise ValueError(f"expected one scenario, found {sorted(scenarios)}")
    scenario = next(iter(scenarios))
    if scenario not in {"A", "B", "C"}:
        raise ValueError(f"unknown scenario: {scenario}")

    by_activity: dict[str, list[dict[str, str]]] = defaultdict(list)
    seen_activity_weeks: set[tuple[str, int]] = set()
    for row in access_rows:
        activity_id = row["activity_id"]
        week = int(row["week"])
        key = (activity_id, week)
        if key in seen_activity_weeks:
            raise ValueError(f"duplicate activity-week: {key}")
        seen_activity_weeks.add(key)
        by_activity[activity_id].append(row)

    contract_weight = {1: 100.0, 2: 10.0, 3: 1.0}
    activity_nudge = {1: 0.3, 2: 0.2, 3: 0.0}
    completion_by_activity: dict[str, date] = {}
    for activity_id, activity in activities.items():
        rows = by_activity.get(activity_id, [])
        if not rows:
            raise ValueError(f"unscheduled activity: {activity_id}")
        supplied_half_units = sum(3 if int(row["eclo"]) else 2 for row in rows)
        required_half_units = 2 * int(activity["total_accesses"])
        if supplied_half_units < required_half_units:
            raise ValueError(
                f"insufficient workload for {activity_id}: "
                f"{supplied_half_units}/2 < {required_half_units}/2"
            )
        completion_week = max(int(row["week"]) for row in rows)
        completion_by_activity[activity_id] = horizon_start + timedelta(
            days=7 * completion_week - 1
        )

    delay_score = 0.0
    for contract_number, project in projects.items():
        contract_activities = [
            (activity_id, activity)
            for activity_id, activity in activities.items()
            if activity["contract_number"] == contract_number
        ]
        completion_date = max(
            completion_by_activity[activity_id]
            for activity_id, _ in contract_activities
        )
        planned = date.fromisoformat(project["planned_completion_date"])
        delay_days = max(0, (completion_date - planned).days)
        for _, activity in contract_activities:
            delay_score += (
                delay_days
                * contract_weight[int(project["contract_priority"])]
                * (1.0 + activity_nudge[int(activity["activity_priority"])])
            )

    groups: dict[tuple[str, int], set[str]] = defaultdict(set)
    for row in occupancy_rows:
        groups[(row["location_id"], int(row["week"]))].add(row["co_share_group"])
    excess = sum(
        max(0, len(labels) - supply[location_id])
        for (location_id, _), labels in groups.items()
    )
    eclo = sum(int(row["eclo"]) == 1 for row in access_rows)

    if scenario == "A":
        objective = delay_score
    elif scenario == "B":
        objective = 7.0 * excess + 5.0 * eclo
    else:
        objective = delay_score + 7.0 * excess + 5.0 * eclo
    return IndependentScore(
        scenario=scenario,
        priority_weighted_delay=round(delay_score, 10),
        excess_access_nights=excess,
        eclo_nights=eclo,
        objective_score=round(objective, 10),
        access_rows=len(access_rows),
        occupancy_rows=len(occupancy_rows),
    )
