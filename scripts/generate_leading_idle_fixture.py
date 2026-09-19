from __future__ import annotations

import csv
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE_DATA = ROOT / "fixtures" / "independent_eclo_multipass_v1"
BASE_SOURCE = ROOT / "fixtures" / "independent_eclo_multipass_v1_source_c"
DATA = ROOT / "fixtures" / "independent_leading_idle_v1"
SOURCE = ROOT / "fixtures" / "independent_leading_idle_v1_source_c"
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
            {"key": "horizon_weeks", "value": 13},
        ],
    )
    project_fields, projects = _read(BASE_DATA / "07_PROJECT_DETAILS.csv")
    for project in projects:
        project["contract_completion_date"] = _date_for_week(13).isoformat()
    _write(DATA / "07_PROJECT_DETAILS.csv", project_fields, projects)
    activity_fields, activities = _read(BASE_DATA / "08_ACTIVITY_DETAILS.csv")
    _write(DATA / "08_ACTIVITY_DETAILS.csv", activity_fields, activities)

    access_fields, access = _read(BASE_SOURCE / "SCHEDULE_ACCESS.csv")
    occupancy_fields, occupancy = _read(BASE_SOURCE / "SCHEDULE_OCCUPANCY.csv")
    for row in access:
        row["week"] = str(int(row["week"]) + 1)
    for row in occupancy:
        row["week"] = str(int(row["week"]) + 1)
    _write(SOURCE / "SCHEDULE_ACCESS.csv", access_fields, access)
    _write(SOURCE / "SCHEDULE_OCCUPANCY.csv", occupancy_fields, occupancy)

    contract_by_activity = {
        row["activity_id"]: row["contract_number"] for row in activities
    }
    completion_by_contract: dict[str, int] = defaultdict(int)
    for row in access:
        contract = contract_by_activity[row["activity_id"]]
        completion_by_contract[contract] = max(
            completion_by_contract[contract], int(row["week"])
        )
    results = []
    for project in projects:
        contract = project["contract_number"]
        completion = _date_for_week(completion_by_contract[contract])
        planned = date.fromisoformat(project["planned_completion_date"])
        results.append(
            {
                "scenario": "C",
                "contract_number": contract,
                "simulated_completion_date": completion.isoformat(),
                "overrun_days": max(0, (completion - planned).days),
            }
        )
    _write(
        SOURCE / "RESULTS.csv",
        ("scenario", "contract_number", "simulated_completion_date", "overrun_days"),
        sorted(results, key=lambda row: str(row["contract_number"])),
    )


if __name__ == "__main__":
    main()
