from __future__ import annotations

import argparse
import csv
from datetime import date, timedelta
from pathlib import Path


def write(path: Path, fields: tuple[str, ...], rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a targeted Scenario B strict-improvement group-cap case."
    )
    parser.add_argument("--output", required=True)
    parser.add_argument("--oracle-output", required=True)
    args = parser.parse_args()
    output = Path(args.output)
    oracle = Path(args.oracle_output)
    for directory in (output, oracle):
        if directory.exists() and any(directory.iterdir()):
            raise ValueError(f"output directory must be empty: {directory}")
        directory.mkdir(parents=True, exist_ok=True)

    horizon_start = date.fromisoformat("2036-01-07")
    week_end = (horizon_start + timedelta(days=6)).isoformat()
    line = "LBG"
    locations = (
        "SEC:LBG:G1_G2:EB",
        "PLAT:LBG:G1:EB",
        "PLAT:LBG:G2:EB",
    )
    pc_ids = tuple(f"GPC{index}" for index in range(1, 8))
    bridge_ids = tuple(f"GC{index}{index + 1}" for index in range(1, 7))
    activity_ids = (*pc_ids, *bridge_ids)

    write(
        output / "01_LINES.csv",
        ("line_code", "line_name"),
        [{"line_code": line, "line_name": "B excess budget line"}],
    )
    write(
        output / "02_STATIONS.csv",
        ("station_id", "line_code", "seq", "is_interchange"),
        [
            {"station_id": "G1", "line_code": line, "seq": 1, "is_interchange": 0},
            {"station_id": "G2", "line_code": line, "seq": 2, "is_interchange": 0},
        ],
    )
    write(
        output / "03_SECTORS.csv",
        (
            "sector_id",
            "line_code",
            "from_station_id",
            "to_station_id",
            "seq",
            "is_shared",
        ),
        [
            {
                "sector_id": "SEC:LBG:G1_G2",
                "line_code": line,
                "from_station_id": "G1",
                "to_station_id": "G2",
                "seq": 1,
                "is_shared": 0,
            }
        ],
    )
    write(
        output / "04_LOCATION_SUPPLY.csv",
        ("location_id", "location_kind", "line_code", "bound", "supply_capacity"),
        [
            {
                "location_id": location,
                "location_kind": (
                    "tunnel sector" if location.startswith("SEC:") else "platform"
                ),
                "line_code": line,
                "bound": "EB",
                "supply_capacity": 6,
            }
            for location in locations
        ],
    )
    write(
        output / "05_BUFFER_LOCATION.csv",
        ("nature_of_works", "up_to_buffer_sectors", "opposite_bound_required"),
        [
            {
                "nature_of_works": "Non-live (Consist)",
                "up_to_buffer_sectors": 0,
                "opposite_bound_required": 0,
            }
        ],
    )
    write(
        output / "06_PARAMETERS.csv",
        ("key", "value"),
        [
            {"key": "horizon_start", "value": horizon_start.isoformat()},
            {"key": "horizon_weeks", "value": 1},
        ],
    )
    write(
        output / "07_PROJECT_DETAILS.csv",
        (
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
        ),
        [
            {
                "contract_number": f"K{activity_id}",
                "contract_description": f"B excess budget {activity_id}",
                "contract_award_date": "2035-06-01",
                "activity_type": "BudgetCap",
                "nature_of_activity": "Non-live (Consist)",
                "contract_priority": 3,
                "contract_completion_date": week_end,
                "planned_completion_date": week_end,
                "number_of_workfronts": 1,
                "access_type": "C" if activity_id in bridge_ids else "PC",
                "number_of_maximum_access_per_week": 1,
            }
            for activity_id in activity_ids
        ],
    )
    write(
        output / "08_ACTIVITY_DETAILS.csv",
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
        [
            {
                "activity_id": activity_id,
                "contract_number": f"K{activity_id}",
                "activity_type": "BudgetCap",
                "start_location_id": locations[0],
                "end_location_id": locations[0],
                "total_accesses": 1,
                "planned_start_date": horizon_start.isoformat(),
                "predecessor_activity_id": "",
                "activity_priority": 3,
            }
            for activity_id in activity_ids
        ],
    )

    access_rows = [
        {
            "activity_id": activity_id,
            "access_seq": 1,
            "week": 1,
            "eclo": 0,
            "access_night": 1,
        }
        for activity_id in activity_ids
    ]
    occupancy_rows: list[dict[str, object]] = []
    for activity_id in activity_ids:
        if activity_id in pc_ids:
            primary_group = pc_ids.index(activity_id) + 1
            secondary_group = primary_group
        else:
            bridge_index = bridge_ids.index(activity_id) + 1
            primary_group = bridge_index
            secondary_group = bridge_index + 1
        for location_index, location in enumerate(locations):
            occupancy_rows.append(
                {
                    "activity_id": activity_id,
                    "week": 1,
                    "location_id": location,
                    "co_share_group": f"g{secondary_group if location_index == 1 else primary_group}",
                }
            )
    write(
        oracle / "SCHEDULE_ACCESS.csv",
        ("activity_id", "access_seq", "week", "eclo", "access_night"),
        access_rows,
    )
    write(
        oracle / "SCHEDULE_OCCUPANCY.csv",
        ("activity_id", "week", "location_id", "co_share_group"),
        occupancy_rows,
    )
    write(
        oracle / "RESULTS.csv",
        (
            "scenario",
            "contract_number",
            "simulated_completion_date",
            "overrun_days",
        ),
        [
            {
                "scenario": "B",
                "contract_number": f"K{activity_id}",
                "simulated_completion_date": week_end,
                "overrun_days": 0,
            }
            for activity_id in activity_ids
        ],
    )


if __name__ == "__main__":
    main()
