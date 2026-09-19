from __future__ import annotations

import csv
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path
import shutil


ROOT = Path(__file__).resolve().parents[1]
BASE_DATA = ROOT / "fixtures" / "independent_eclo_compaction_scale_v1"
DATA = ROOT / "fixtures" / "independent_idle_compaction_scale_v1"
BASE = ROOT / "fixtures" / "independent_eclo_compaction_scale_v1_source_c"
OUTPUT = ROOT / "fixtures" / "independent_idle_compaction_scale_v1_source_c"
HORIZON_START = date(2033, 1, 3)
ACTIVITY_COUNT = 60


def _read(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _write(path: Path, fields: tuple[str, ...], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _completion_date(week: int) -> str:
    return (HORIZON_START + timedelta(days=7 * week - 1)).isoformat()


def main() -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    for filename in (
        "01_LINES.csv",
        "02_STATIONS.csv",
        "03_SECTORS.csv",
        "04_LOCATION_SUPPLY.csv",
        "05_BUFFER_LOCATION.csv",
    ):
        shutil.copyfile(BASE_DATA / filename, DATA / filename)
    _write(
        DATA / "06_PARAMETERS.csv",
        ("key", "value"),
        [
            {"key": "horizon_start", "value": HORIZON_START.isoformat()},
            {"key": "horizon_weeks", "value": 4 * ACTIVITY_COUNT},
        ],
    )
    projects = _read(BASE_DATA / "07_PROJECT_DETAILS.csv")[:ACTIVITY_COUNT]
    activities = _read(BASE_DATA / "08_ACTIVITY_DETAILS.csv")[:ACTIVITY_COUNT]
    _write(DATA / "07_PROJECT_DETAILS.csv", tuple(projects[0]), projects)
    _write(DATA / "08_ACTIVITY_DETAILS.csv", tuple(activities[0]), activities)

    base_occupancy = _read(BASE / "SCHEDULE_OCCUPANCY.csv")
    footprint_by_activity: dict[str, list[str]] = defaultdict(list)
    for row in base_occupancy:
        location = row["location_id"]
        if location not in footprint_by_activity[row["activity_id"]]:
            footprint_by_activity[row["activity_id"]].append(location)

    access: list[dict[str, object]] = []
    occupancy: list[dict[str, object]] = []
    completion_by_activity: dict[str, int] = {}
    reverse_activities = [
        f"TS{index:03d}" for index in range(ACTIVITY_COUNT, 0, -1)
    ]
    for position, activity in enumerate(reverse_activities):
        start_week = 4 * position + 1
        weeks = range(start_week, start_week + 3)
        completion_by_activity[activity] = start_week + 2
        for sequence, week in enumerate(weeks, 1):
            access.append(
                {
                    "activity_id": activity,
                    "access_seq": sequence,
                    "week": week,
                    "eclo": 0,
                    "access_night": 1,
                }
            )
            occupancy.extend(
                {
                    "activity_id": activity,
                    "week": week,
                    "location_id": location,
                    "co_share_group": "g1",
                }
                for location in footprint_by_activity[activity]
            )
    results = []
    for project in projects:
        contract = project["contract_number"]
        activity = "T" + contract[1:]
        completion = _completion_date(completion_by_activity[activity])
        planned = date.fromisoformat(project["planned_completion_date"])
        results.append(
            {
                "scenario": "C",
                "contract_number": contract,
                "simulated_completion_date": completion,
                "overrun_days": max(
                    0, (date.fromisoformat(completion) - planned).days
                ),
            }
        )

    _write(
        OUTPUT / "SCHEDULE_ACCESS.csv",
        ("activity_id", "access_seq", "week", "eclo", "access_night"),
        access,
    )
    _write(
        OUTPUT / "SCHEDULE_OCCUPANCY.csv",
        ("activity_id", "week", "location_id", "co_share_group"),
        occupancy,
    )
    _write(
        OUTPUT / "RESULTS.csv",
        ("scenario", "contract_number", "simulated_completion_date", "overrun_days"),
        results,
    )


if __name__ == "__main__":
    main()
