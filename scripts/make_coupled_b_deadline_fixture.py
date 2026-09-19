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
        description=(
            "Generate a coupled Scenario B deadline fixture with independently "
            "countable ECLO and excess-capacity lower bounds."
        )
    )
    parser.add_argument("--output", required=True)
    parser.add_argument("--oracle-output", required=True)
    parser.add_argument("--pc-count", type=int, default=2)
    args = parser.parse_args()
    if args.pc_count < 2:
        raise ValueError("pc-count must be at least 2")
    output = Path(args.output)
    oracle = Path(args.oracle_output)
    if output.exists() and any(output.iterdir()):
        raise ValueError(f"output directory must be empty: {output}")
    if oracle.exists() and any(oracle.iterdir()):
        raise ValueError(f"oracle directory must be empty: {oracle}")
    output.mkdir(parents=True, exist_ok=True)
    oracle.mkdir(parents=True, exist_ok=True)

    horizon_start = date.fromisoformat("2034-01-02")

    def week_end(week: int) -> str:
        return (horizon_start + timedelta(days=7 * week - 1)).isoformat()

    line = "LCB"
    sector = "SEC:LCB:CB1_CB2"
    locations = (
        "SEC:LCB:CB1_CB2:EB",
        "PLAT:LCB:CB1:EB",
        "PLAT:LCB:CB2:EB",
    )
    pc_ids = tuple(f"BPC{index}" for index in range(1, args.pc_count + 1))
    bridge_ids = tuple(
        f"BC{args.pc_count + index}" for index in range(1, args.pc_count)
    )
    activity_ids = (*pc_ids, *bridge_ids)

    write(
        output / "01_LINES.csv",
        ("line_code", "line_name"),
        [{"line_code": line, "line_name": "Coupled deadline line"}],
    )
    write(
        output / "02_STATIONS.csv",
        ("station_id", "line_code", "seq", "is_interchange"),
        [
            {"station_id": "CB1", "line_code": line, "seq": 1, "is_interchange": 0},
            {"station_id": "CB2", "line_code": line, "seq": 2, "is_interchange": 0},
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
                "sector_id": sector,
                "line_code": line,
                "from_station_id": "CB1",
                "to_station_id": "CB2",
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
                "location_kind": "tunnel sector" if location.startswith("SEC:") else "platform",
                "line_code": line,
                "bound": "EB",
                "supply_capacity": 1,
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
            {"key": "horizon_weeks", "value": 4},
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
                "contract_description": f"Coupled deadline {activity_id}",
                "contract_award_date": "2033-06-01",
                "activity_type": "CoupledDeadline",
                "nature_of_activity": "Non-live (Consist)",
                "contract_priority": 3,
                "contract_completion_date": week_end(4),
                "planned_completion_date": week_end(2),
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
                "activity_type": "CoupledDeadline",
                "start_location_id": locations[0],
                "end_location_id": locations[0],
                "total_accesses": 3,
                "planned_start_date": horizon_start.isoformat(),
                "predecessor_activity_id": "",
                "activity_priority": 3,
            }
            for activity_id in activity_ids
        ],
    )

    access_rows: list[dict[str, object]] = []
    occupancy_rows: list[dict[str, object]] = []
    for activity_id in activity_ids:
        if activity_id in pc_ids:
            primary_group = pc_ids.index(activity_id) + 1
            secondary_group = primary_group
        else:
            bridge_index = bridge_ids.index(activity_id) + 1
            primary_group = bridge_index
            secondary_group = bridge_index + 1
        for sequence, week in enumerate((1, 2), start=1):
            access_rows.append(
                {
                    "activity_id": activity_id,
                    "access_seq": sequence,
                    "week": week,
                    "eclo": 1,
                    "access_night": 1,
                }
            )
            for location_index, location in enumerate(locations):
                local_group = (
                    secondary_group if location_index == 1 else primary_group
                )
                occupancy_rows.append(
                    {
                        "activity_id": activity_id,
                        "week": week,
                        "location_id": location,
                        "co_share_group": f"g{local_group}",
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
                "simulated_completion_date": week_end(2),
                "overrun_days": 0,
            }
            for activity_id in activity_ids
        ],
    )


if __name__ == "__main__":
    main()
