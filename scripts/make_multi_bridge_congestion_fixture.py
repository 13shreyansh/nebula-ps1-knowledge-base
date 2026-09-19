from __future__ import annotations

import csv
import shutil
from datetime import date, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "fixtures" / "independent_multi_bridge_v1"
DATA = ROOT / "fixtures" / "independent_multi_bridge_congestion_v1"


def write(root: Path, name: str, fields: tuple[str, ...], rows: list[dict[str, object]]) -> None:
    root.mkdir(parents=True, exist_ok=True)
    with (root / name).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def footprint(line: str, bound: str) -> tuple[str, ...]:
    return (
        f"SEC:{line}:X1_X2:{bound}",
        f"SEC:{line}:X2_X3:{bound}",
        f"PLAT:{line}:X1:{bound}",
        f"PLAT:{line}:X2:{bound}",
        f"PLAT:{line}:X3:{bound}",
    )


def main() -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    for name in (
        "01_LINES.csv",
        "02_STATIONS.csv",
        "03_SECTORS.csv",
        "04_LOCATION_SUPPLY.csv",
        "05_BUFFER_LOCATION.csv",
        "06_PARAMETERS.csv",
    ):
        shutil.copyfile(SOURCE / name, DATA / name)

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
    projects = [
        {
            "contract_number": "K301",
            "contract_description": "Urgent north Live bridge works",
            "contract_award_date": "2030-06-01",
            "activity_type": "Synthetic",
            "nature_of_activity": "Live",
            "contract_priority": 1,
            "contract_completion_date": "2031-02-23",
            "planned_completion_date": "2031-01-19",
            "number_of_workfronts": 1,
            "access_type": "PM",
            "number_of_maximum_access_per_week": 1,
        },
        {
            "contract_number": "K302",
            "contract_description": "South Live bridge works",
            "contract_award_date": "2030-06-01",
            "activity_type": "Synthetic",
            "nature_of_activity": "Live",
            "contract_priority": 3,
            "contract_completion_date": "2031-02-23",
            "planned_completion_date": "2031-02-16",
            "number_of_workfronts": 1,
            "access_type": "PM",
            "number_of_maximum_access_per_week": 1,
        },
    ]
    write(DATA, "07_PROJECT_DETAILS.csv", project_fields, projects)

    activity_fields = (
        "activity_id",
        "contract_number",
        "activity_type",
        "start_location_id",
        "end_location_id",
        "total_accesses",
        "planned_start_date",
        "predecessor_activity_id",
        "activity_priority",
    )
    activities = [
        {
            "activity_id": "R001",
            "contract_number": "K301",
            "activity_type": "Synthetic",
            "start_location_id": "SEC:LNX:X1_X2:EB",
            "end_location_id": "SEC:LNX:X2_X3:EB",
            "total_accesses": 3,
            "planned_start_date": "2031-01-06",
            "predecessor_activity_id": "",
            "activity_priority": 3,
        },
        {
            "activity_id": "R002",
            "contract_number": "K302",
            "activity_type": "Synthetic",
            "start_location_id": "SEC:LNY:X1_X2:WB",
            "end_location_id": "SEC:LNY:X2_X3:WB",
            "total_accesses": 3,
            "planned_start_date": "2031-01-06",
            "predecessor_activity_id": "",
            "activity_priority": 3,
        },
    ]
    write(DATA, "08_ACTIVITY_DETAILS.csv", activity_fields, activities)

    schedules = {
        "A": (("R001", (1, 2, 3), 0), ("R002", (4, 5, 6), 0)),
        "B": (("R001", (1, 2), 1), ("R002", (3, 4, 5), 0)),
        "C": (("R001", (1, 2), 1), ("R002", (3, 4, 5), 0)),
    }
    start = date(2031, 1, 6)
    for scenario, schedule in schedules.items():
        output = ROOT / "fixtures" / f"independent_multi_bridge_congestion_v1_oracle_{scenario.lower()}"
        access_rows = []
        occupancy_rows = []
        completion_by_activity: dict[str, date] = {}
        for activity_id, weeks, eclo in schedule:
            line, bound = ("LNX", "EB") if activity_id == "R001" else ("LNY", "WB")
            for access_seq, week in enumerate(weeks, 1):
                access_rows.append(
                    {
                        "activity_id": activity_id,
                        "access_seq": access_seq,
                        "week": week,
                        "eclo": eclo,
                        "access_night": 1,
                    }
                )
                occupancy_rows.extend(
                    {
                        "activity_id": activity_id,
                        "week": week,
                        "location_id": location,
                        "co_share_group": f"G{week}",
                    }
                    for location in footprint(line, bound)
                )
            completion_by_activity[activity_id] = start + timedelta(days=7 * max(weeks) - 1)
        result_rows = []
        for contract, activity_id, planned in (
            ("K301", "R001", date(2031, 1, 19)),
            ("K302", "R002", date(2031, 2, 16)),
        ):
            completion = completion_by_activity[activity_id]
            result_rows.append(
                {
                    "scenario": scenario,
                    "contract_number": contract,
                    "simulated_completion_date": completion.isoformat(),
                    "overrun_days": max(0, (completion - planned).days),
                }
            )
        write(
            output,
            "SCHEDULE_ACCESS.csv",
            ("activity_id", "access_seq", "week", "eclo", "access_night"),
            access_rows,
        )
        write(
            output,
            "SCHEDULE_OCCUPANCY.csv",
            ("activity_id", "week", "location_id", "co_share_group"),
            occupancy_rows,
        )
        write(
            output,
            "RESULTS.csv",
            ("scenario", "contract_number", "simulated_completion_date", "overrun_days"),
            result_rows,
        )


if __name__ == "__main__":
    main()
