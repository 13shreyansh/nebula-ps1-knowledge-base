from __future__ import annotations

import csv
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE_DATA = ROOT / "fixtures" / "independent_eclo_multipass_v1"
BASE_SOURCE = ROOT / "fixtures" / "independent_eclo_multipass_v1_source_c"
DATA = ROOT / "fixtures" / "independent_eclo_long_access_v1"
SOURCE = ROOT / "fixtures" / "independent_eclo_long_access_v1_source_c"
HORIZON_START = date(2035, 1, 1)


def _read(path: Path) -> tuple[tuple[str, ...], list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return tuple(reader.fieldnames or ()), list(reader)


def _write(path: Path, fields: tuple[str, ...], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _date_for_week(week: int) -> date:
    return HORIZON_START + timedelta(days=7 * week - 1)


def main() -> None:
    for name in (
        "01_LINES.csv",
        "02_STATIONS.csv",
        "03_SECTORS.csv",
        "04_LOCATION_SUPPLY.csv",
        "05_BUFFER_LOCATION.csv",
    ):
        fields, rows = _read(BASE_DATA / name)
        _write(DATA / name, fields, rows)
    _write(
        DATA / "06_PARAMETERS.csv",
        ("key", "value"),
        [
            {"key": "horizon_start", "value": HORIZON_START.isoformat()},
            {"key": "horizon_weeks", "value": 16},
        ],
    )
    project_fields, projects = _read(BASE_DATA / "07_PROJECT_DETAILS.csv")
    for project in projects:
        project["contract_completion_date"] = _date_for_week(16).isoformat()
    _write(DATA / "07_PROJECT_DETAILS.csv", project_fields, projects)
    activity_fields, activities = _read(BASE_DATA / "08_ACTIVITY_DETAILS.csv")
    for activity in activities:
        activity["total_accesses"] = "4"
    _write(DATA / "08_ACTIVITY_DETAILS.csv", activity_fields, activities)

    _, base_occupancy = _read(BASE_SOURCE / "SCHEDULE_OCCUPANCY.csv")
    locations_by_activity: dict[str, set[str]] = defaultdict(set)
    for row in base_occupancy:
        locations_by_activity[row["activity_id"]].add(row["location_id"])
    order = ("MX1", "MX2", "MY1", "MY2")
    access: list[dict[str, object]] = []
    occupancy: list[dict[str, object]] = []
    results: list[dict[str, object]] = []
    project_by_contract = {
        project["contract_number"]: project for project in projects
    }
    contract_by_activity = {
        activity["activity_id"]: activity["contract_number"]
        for activity in activities
    }
    for position, activity_id in enumerate(order, 1):
        completion_week = 4 * position
        for sequence, week in enumerate(
            range(completion_week - 3, completion_week + 1), 1
        ):
            access.append(
                {
                    "activity_id": activity_id,
                    "access_seq": sequence,
                    "week": week,
                    "eclo": 0,
                    "access_night": 1,
                }
            )
            occupancy.extend(
                {
                    "activity_id": activity_id,
                    "week": week,
                    "location_id": location_id,
                    "co_share_group": "g1",
                }
                for location_id in sorted(locations_by_activity[activity_id])
            )
        contract = contract_by_activity[activity_id]
        planned = date.fromisoformat(
            project_by_contract[contract]["planned_completion_date"]
        )
        completion = _date_for_week(completion_week)
        results.append(
            {
                "scenario": "C",
                "contract_number": contract,
                "simulated_completion_date": completion.isoformat(),
                "overrun_days": max(0, (completion - planned).days),
            }
        )
    _write(
        SOURCE / "SCHEDULE_ACCESS.csv",
        ("activity_id", "access_seq", "week", "eclo", "access_night"),
        access,
    )
    _write(
        SOURCE / "SCHEDULE_OCCUPANCY.csv",
        ("activity_id", "week", "location_id", "co_share_group"),
        occupancy,
    )
    _write(
        SOURCE / "RESULTS.csv",
        ("scenario", "contract_number", "simulated_completion_date", "overrun_days"),
        sorted(results, key=lambda row: str(row["contract_number"])),
    )


if __name__ == "__main__":
    main()
