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
            "Generate an irregular Scenario B fixture with asymmetric footprints, "
            "mixed PC/C/PM work, staggered availability, and an analytical optimum."
        )
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

    horizon_start = date.fromisoformat("2035-01-01")

    def week_start(week: int) -> str:
        return (horizon_start + timedelta(days=7 * (week - 1))).isoformat()

    def week_end(week: int) -> str:
        return (horizon_start + timedelta(days=7 * week - 1)).isoformat()

    line = "LIB"
    stations = tuple(f"I{index}" for index in range(1, 8))
    sectors = tuple(
        f"SEC:{line}:I{index}_I{index + 1}" for index in range(1, 7)
    )
    sector_locations = tuple(f"{sector}:EB" for sector in sectors)
    platform_locations = tuple(
        f"PLAT:{line}:{station}:EB" for station in stations
    )
    all_locations = (*sector_locations, *platform_locations)

    pc_ids = ("IPC1", "IPC2", "IPC3", "IPC4")
    bridge_ids = ("IC12", "IC23", "IC34")
    pm_id = "IPM6"
    activity_ids = (*pc_ids, *bridge_ids, pm_id)

    write(
        output / "01_LINES.csv",
        ("line_code", "line_name"),
        [{"line_code": line, "line_name": "Irregular coupled line"}],
    )
    write(
        output / "02_STATIONS.csv",
        ("station_id", "line_code", "seq", "is_interchange"),
        [
            {
                "station_id": station,
                "line_code": line,
                "seq": index,
                "is_interchange": 0,
            }
            for index, station in enumerate(stations, start=1)
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
                "from_station_id": stations[index - 1],
                "to_station_id": stations[index],
                "seq": index,
                "is_shared": 0,
            }
            for index, sector in enumerate(sectors, start=1)
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
                "supply_capacity": 1,
            }
            for location in all_locations
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
            {"key": "horizon_weeks", "value": 6},
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
                "contract_description": f"Irregular coupled {activity_id}",
                "contract_award_date": "2034-06-01",
                "activity_type": "IrregularCoupled",
                "nature_of_activity": "Non-live (Consist)",
                "contract_priority": 3,
                "contract_completion_date": week_end(6),
                "planned_completion_date": week_end(4 if activity_id == pm_id else 2),
                "number_of_workfronts": 1,
                "access_type": (
                    "PM"
                    if activity_id == pm_id
                    else "C"
                    if activity_id in bridge_ids
                    else "PC"
                ),
                "number_of_maximum_access_per_week": 1,
            }
            for activity_id in activity_ids
        ],
    )

    endpoints: dict[str, tuple[int, int]] = {
        **{activity_id: (index, index) for index, activity_id in enumerate(pc_ids, 1)},
        "IC12": (1, 2),
        "IC23": (2, 3),
        "IC34": (3, 4),
        pm_id: (6, 6),
    }
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
                "activity_type": "IrregularCoupled",
                "start_location_id": sector_locations[endpoints[activity_id][0] - 1],
                "end_location_id": sector_locations[endpoints[activity_id][1] - 1],
                "total_accesses": 3,
                "planned_start_date": week_start(3 if activity_id == pm_id else 1),
                "predecessor_activity_id": "",
                "activity_priority": 3,
            }
            for activity_id in activity_ids
        ],
    )

    def footprint(first_sector: int, last_sector: int) -> tuple[str, ...]:
        return tuple(
            sorted(
                (*sector_locations[first_sector - 1 : last_sector],
                 *platform_locations[first_sector - 1 : last_sector + 1])
            )
        )

    access_rows: list[dict[str, object]] = []
    occupancy_rows: list[dict[str, object]] = []
    for activity_id in activity_ids:
        weeks = (3, 4) if activity_id == pm_id else (1, 2)
        first_sector, last_sector = endpoints[activity_id]
        for sequence, week in enumerate(weeks, start=1):
            access_rows.append(
                {
                    "activity_id": activity_id,
                    "access_seq": sequence,
                    "week": week,
                    "eclo": 1,
                    "access_night": 1,
                }
            )
            for location in footprint(first_sector, last_sector):
                if activity_id in pc_ids:
                    group = pc_ids.index(activity_id) + 1
                elif activity_id == pm_id:
                    group = 1
                else:
                    bridge_index = bridge_ids.index(activity_id) + 1
                    right_sector = sector_locations[bridge_index]
                    right_platform = platform_locations[bridge_index + 1]
                    group = (
                        bridge_index + 1
                        if location in {right_sector, right_platform}
                        else bridge_index
                    )
                occupancy_rows.append(
                    {
                        "activity_id": activity_id,
                        "week": week,
                        "location_id": location,
                        "co_share_group": f"g{group}",
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
                "simulated_completion_date": week_end(
                    4 if activity_id == pm_id else 2
                ),
                "overrun_days": 0,
            }
            for activity_id in activity_ids
        ],
    )


if __name__ == "__main__":
    main()
