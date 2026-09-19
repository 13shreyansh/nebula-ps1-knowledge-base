from __future__ import annotations

import csv
from datetime import date, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE_DATA = ROOT / "fixtures" / "independent_eclo_multipass_v1"
BASE_SOURCE = ROOT / "fixtures" / "independent_eclo_multipass_v1_source_c"
DATA = ROOT / "fixtures" / "independent_idle_unlock_v1"
SOURCE = ROOT / "fixtures" / "independent_idle_unlock_v1_source_c"
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
    filters = {
        "01_LINES.csv": lambda row: row["line_code"] == "MPX",
        "02_STATIONS.csv": lambda row: row["line_code"] == "MPX",
        "03_SECTORS.csv": lambda row: row["line_code"] == "MPX",
        "04_LOCATION_SUPPLY.csv": lambda row: row["line_code"] == "MPX",
        "05_BUFFER_LOCATION.csv": lambda row: True,
    }
    for name, keep in filters.items():
        fields, rows = _read(BASE_DATA / name)
        _write(DATA / name, fields, [row for row in rows if keep(row)])
    _write(
        DATA / "06_PARAMETERS.csv",
        ("key", "value"),
        [
            {"key": "horizon_start", "value": HORIZON_START.isoformat()},
            {"key": "horizon_weeks", "value": 7},
        ],
    )
    project_fields, projects = _read(BASE_DATA / "07_PROJECT_DETAILS.csv")
    projects = [
        project
        for project in projects
        if project["contract_number"] in {"KMX1", "KMX2"}
    ]
    for project in projects:
        project["contract_completion_date"] = _date_for_week(7).isoformat()
        project["planned_completion_date"] = _date_for_week(
            2 if project["contract_number"] == "KMX1" else 7
        ).isoformat()
    _write(DATA / "07_PROJECT_DETAILS.csv", project_fields, projects)
    activity_fields, activities = _read(BASE_DATA / "08_ACTIVITY_DETAILS.csv")
    activities = [
        activity
        for activity in activities
        if activity["activity_id"] in {"MX1", "MX2"}
    ]
    _write(DATA / "08_ACTIVITY_DETAILS.csv", activity_fields, activities)

    _, base_occupancy = _read(BASE_SOURCE / "SCHEDULE_OCCUPANCY.csv")
    locations_by_activity = {
        activity_id: sorted(
            {
                row["location_id"]
                for row in base_occupancy
                if row["activity_id"] == activity_id
            }
        )
        for activity_id in ("MX1", "MX2")
    }
    access: list[dict[str, object]] = []
    occupancy: list[dict[str, object]] = []
    for activity_id, weeks in (("MX1", (1, 2, 3)), ("MX2", (5, 6, 7))):
        for sequence, week in enumerate(weeks, 1):
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
                for location_id in locations_by_activity[activity_id]
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
        [
            {
                "scenario": "C",
                "contract_number": "KMX1",
                "simulated_completion_date": _date_for_week(3).isoformat(),
                "overrun_days": 7,
            },
            {
                "scenario": "C",
                "contract_number": "KMX2",
                "simulated_completion_date": _date_for_week(7).isoformat(),
                "overrun_days": 0,
            },
        ],
    )


if __name__ == "__main__":
    main()
