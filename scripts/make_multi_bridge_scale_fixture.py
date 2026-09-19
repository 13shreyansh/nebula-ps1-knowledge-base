from __future__ import annotations

import csv
import shutil
from datetime import date, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "fixtures" / "independent_multi_bridge_v1"
DATA = ROOT / "fixtures" / "independent_multi_bridge_scale_v1"


def write(name: str, fields: tuple[str, ...], rows: list[dict[str, object]]) -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    with (DATA / name).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    for name in (
        "01_LINES.csv",
        "02_STATIONS.csv",
        "03_SECTORS.csv",
        "04_LOCATION_SUPPLY.csv",
        "05_BUFFER_LOCATION.csv",
    ):
        shutil.copyfile(SOURCE / name, DATA / name)
    write(
        "06_PARAMETERS.csv",
        ("key", "value"),
        [{"key": "horizon_start", "value": "2031-01-06"}, {"key": "horizon_weeks", "value": 24}],
    )

    horizon_start = date(2031, 1, 6)
    project_fields = (
        "contract_number",
        "contract_description",
        "contract_award_date",
        "activity_type",
        "nature_of_activity",
        "contract_priority",
        "contract_completion_date",
        "planned_completion_date",
        "number_of_workfronts",
        "access_type",
        "number_of_maximum_access_per_week",
    )
    priorities = (3, 2, 1, 3, 2, 1, 3, 2)
    projects = []
    activities = []
    for index, priority in enumerate(priorities, 1):
        contract = f"K{400 + index}"
        activity = f"T{index:03d}"
        line = "LNX" if index % 2 else "LNY"
        bound = "EB" if index % 2 else "WB"
        planned = horizon_start + timedelta(days=7 * (2 * index) - 1)
        projects.append(
            {
                "contract_number": contract,
                "contract_description": f"Scaled interacting Live job {index}",
                "contract_award_date": "2030-06-01",
                "activity_type": "Synthetic",
                "nature_of_activity": "Live",
                "contract_priority": priority,
                "contract_completion_date": (horizon_start + timedelta(days=7 * 24 - 1)).isoformat(),
                "planned_completion_date": planned.isoformat(),
                "number_of_workfronts": 1,
                "access_type": "PM",
                "number_of_maximum_access_per_week": 1,
            }
        )
        activities.append(
            {
                "activity_id": activity,
                "contract_number": contract,
                "activity_type": "Synthetic",
                "start_location_id": f"SEC:{line}:X1_X2:{bound}",
                "end_location_id": f"SEC:{line}:X2_X3:{bound}",
                "total_accesses": 3,
                "planned_start_date": horizon_start.isoformat(),
                "predecessor_activity_id": "",
                "activity_priority": 3,
            }
        )
    write("07_PROJECT_DETAILS.csv", project_fields, projects)
    write(
        "08_ACTIVITY_DETAILS.csv",
        (
            "activity_id",
            "contract_number",
            "activity_type",
            "start_location_id",
            "end_location_id",
            "total_accesses",
            "planned_start_date",
            "predecessor_activity_id",
            "activity_priority",
        ),
        activities,
    )


if __name__ == "__main__":
    main()
