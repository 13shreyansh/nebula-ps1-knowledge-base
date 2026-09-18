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
        description="Generate a compact, dense, public-independent PS1 fixture."
    )
    parser.add_argument("--output", required=True)
    parser.add_argument("--oracle-output", required=True)
    parser.add_argument("--batches-per-line", type=int, default=10)
    args = parser.parse_args()
    if args.batches_per_line < 1:
        raise ValueError("batches-per-line must be positive")
    last_main_week = 2 * args.batches_per_line
    live_x_week = last_main_week + 1
    live_y_week = last_main_week + 2
    local_pm_week = last_main_week + 3
    horizon_weeks = local_pm_week + 4
    horizon_start = date.fromisoformat("2031-01-06")
    planned_completion = horizon_start + timedelta(days=7 * local_pm_week - 1)

    output = Path(args.output)
    oracle = Path(args.oracle_output)
    if output.exists() and any(output.iterdir()):
        raise ValueError(f"output directory must be empty: {output}")
    if oracle.exists() and any(oracle.iterdir()):
        raise ValueError(f"oracle directory must be empty: {oracle}")
    output.mkdir(parents=True, exist_ok=True)
    oracle.mkdir(parents=True, exist_ok=True)

    lines = (("LDX", "Dense synthetic north"), ("LDY", "Dense synthetic south"))
    stations = {
        "LDX": (("IX1", 1, 1), ("IX2", 2, 1), ("NX3", 3, 0), ("NX4", 4, 0), ("NX5", 5, 0), ("NX6", 6, 0)),
        "LDY": (("IX1", 1, 1), ("IX2", 2, 1), ("SY3", 3, 0), ("SY4", 4, 0), ("SY5", 5, 0), ("SY6", 6, 0)),
    }
    sectors: list[dict[str, object]] = []
    for line, line_stations in stations.items():
        for seq, (left, _, _), (right, _, _) in zip(
            range(1, len(line_stations)), line_stations[:-1], line_stations[1:], strict=True
        ):
            sectors.append(
                {
                    "sector_id": f"SEC:{line}:{left}_{right}",
                    "line_code": line,
                    "from_station_id": left,
                    "to_station_id": right,
                    "seq": seq,
                    "is_shared": int(seq == 1),
                }
            )
    locations: list[dict[str, object]] = []
    for sector in sectors:
        for bound in ("EB", "WB"):
            locations.append(
                {
                    "location_id": f"{sector['sector_id']}:{bound}",
                    "location_kind": "tunnel sector",
                    "line_code": sector["line_code"],
                    "bound": bound,
                    "supply_capacity": 1,
                }
            )
    for line, line_stations in stations.items():
        for station_id, _, _ in line_stations:
            for bound in ("EB", "WB"):
                locations.append(
                    {
                        "location_id": f"PLAT:{line}:{station_id}:{bound}",
                        "location_kind": "platform",
                        "line_code": line,
                        "bound": bound,
                        "supply_capacity": 1,
                    }
                )

    projects: list[dict[str, object]] = []
    activities: list[dict[str, object]] = []
    oracle_weeks: dict[str, tuple[int, ...]] = {}
    endpoint_by_activity: dict[str, tuple[str, str]] = {}

    def add_activity(
        activity_id: str,
        line: str,
        start: str,
        end: str,
        accesses: int,
        access_type: str,
        nature: str,
        weeks: tuple[int, ...],
        predecessor: str = "",
    ) -> None:
        contract = f"K{activity_id}"
        projects.append(
            {
                "contract_number": contract,
                "contract_description": f"Dense independent {activity_id}",
                "contract_award_date": "2030-06-01",
                "activity_type": "DenseSynthetic",
                "nature_of_activity": nature,
                "contract_priority": 1,
                "contract_completion_date": (planned_completion + timedelta(days=28)).isoformat(),
                "planned_completion_date": planned_completion.isoformat(),
                "number_of_workfronts": 1,
                "access_type": access_type,
                "number_of_maximum_access_per_week": 2 if nature == "Live" else 3,
            }
        )
        activities.append(
            {
                "activity_id": activity_id,
                "contract_number": contract,
                "activity_type": "DenseSynthetic",
                "start_location_id": start,
                "end_location_id": end,
                "total_accesses": accesses,
                "planned_start_date": horizon_start.isoformat(),
                "predecessor_activity_id": predecessor,
                "activity_priority": 1,
            }
        )
        oracle_weeks[activity_id] = weeks
        endpoint_by_activity[activity_id] = (start, end)

    for line, marker, third, fourth in (
        ("LDX", "X", "NX3", "NX4"),
        ("LDY", "Y", "SY3", "SY4"),
    ):
        corridor = f"SEC:{line}:{third}_{fourth}:EB"
        for batch in range(1, args.batches_per_line + 1):
            weeks = (2 * batch - 1, 2 * batch)
            add_activity(
                f"D{marker}{batch:02d}P",
                line,
                corridor,
                corridor,
                2,
                "PC",
                "Non-live (Consist)",
                weeks,
            )
            for member in range(1, 4):
                add_activity(
                    f"D{marker}{batch:02d}C{member}",
                    line,
                    corridor,
                    corridor,
                    2,
                    "C",
                    "Non-live (Others)",
                    weeks,
                )

        interchange = f"SEC:{line}:IX1_IX2:EB"
        live_week = live_x_week if line == "LDX" else live_y_week
        live_id = f"D{marker}LIVE"
        add_activity(live_id, line, interchange, interchange, 1, "PM", "Live", (live_week,))
        add_activity(
            f"D{marker}PM",
            line,
            corridor,
            corridor,
            1,
            "PM",
            "Non-live (Others)",
            (local_pm_week,),
            predecessor=live_id,
        )

    write(output / "01_LINES.csv", ("line_code", "line_name"), [
        {"line_code": code, "line_name": name} for code, name in lines
    ])
    write(
        output / "02_STATIONS.csv",
        ("station_id", "line_code", "seq", "is_interchange"),
        [
            {"station_id": station, "line_code": line, "seq": seq, "is_interchange": interchange}
            for line, values in stations.items()
            for station, seq, interchange in values
        ],
    )
    write(output / "03_SECTORS.csv", ("sector_id", "line_code", "from_station_id", "to_station_id", "seq", "is_shared"), sectors)
    write(output / "04_LOCATION_SUPPLY.csv", ("location_id", "location_kind", "line_code", "bound", "supply_capacity"), locations)
    write(
        output / "05_BUFFER_LOCATION.csv",
        ("nature_of_works", "up_to_buffer_sectors", "opposite_bound_required"),
        [
            {"nature_of_works": "Live", "up_to_buffer_sectors": 2, "opposite_bound_required": 1},
            {"nature_of_works": "Non-live (Consist)", "up_to_buffer_sectors": 1, "opposite_bound_required": 0},
            {"nature_of_works": "Non-live (Others)", "up_to_buffer_sectors": 0, "opposite_bound_required": 0},
        ],
    )
    write(output / "06_PARAMETERS.csv", ("key", "value"), [
        {"key": "horizon_start", "value": horizon_start.isoformat()},
        {"key": "horizon_weeks", "value": horizon_weeks},
    ])
    write(
        output / "07_PROJECT_DETAILS.csv",
        (
            "contract_number", "contract_description", "contract_award_date", "activity_type",
            "nature_of_activity", "contract_priority", "contract_completion_date",
            "planned_completion_date", "number_of_workfronts", "access_type",
            "number_of_maximum_access_per_week",
        ),
        projects,
    )
    write(
        output / "08_ACTIVITY_DETAILS.csv",
        (
            "activity_id", "contract_number", "activity_type", "start_location_id",
            "end_location_id", "total_accesses", "planned_start_date",
            "predecessor_activity_id", "activity_priority",
        ),
        activities,
    )

    sector_by_id = {str(row["sector_id"]): row for row in sectors}

    def independent_footprint(start_location: str, end_location: str) -> list[str]:
        start_parts = start_location.split(":")
        end_parts = end_location.split(":")
        line = start_parts[1]
        bound = start_parts[3]
        start_sector = sector_by_id[":".join(start_parts[:3])]
        end_sector = sector_by_id[":".join(end_parts[:3])]
        low, high = sorted((int(start_sector["seq"]), int(end_sector["seq"])))
        corridor = sorted(
            (row for row in sectors if row["line_code"] == line and low <= int(row["seq"]) <= high),
            key=lambda row: int(row["seq"]),
        )
        station_ids = [str(corridor[0]["from_station_id"])]
        station_ids.extend(str(row["to_station_id"]) for row in corridor)
        footprint = [f"{row['sector_id']}:{bound}" for row in corridor]
        footprint.extend(f"PLAT:{line}:{station}:{bound}" for station in station_ids)
        return sorted(footprint)

    access_rows: list[dict[str, object]] = []
    occupancy_rows: list[dict[str, object]] = []
    for activity in activities:
        activity_id = str(activity["activity_id"])
        start, end = endpoint_by_activity[activity_id]
        for access_seq, week in enumerate(oracle_weeks[activity_id], start=1):
            access_rows.append(
                {"activity_id": activity_id, "access_seq": access_seq, "week": week, "eclo": 0, "access_night": 1}
            )
            if activity_id.endswith("P") or "C" in activity_id:
                batch = activity_id[2:4]
                group = f"{activity_id[1]}B{batch}W{week}"
            else:
                group = f"{activity_id}W{week}"
            for location_id in independent_footprint(start, end):
                occupancy_rows.append(
                    {"activity_id": activity_id, "week": week, "location_id": location_id, "co_share_group": group}
                )
    write(oracle / "SCHEDULE_ACCESS.csv", ("activity_id", "access_seq", "week", "eclo", "access_night"), access_rows)
    write(oracle / "SCHEDULE_OCCUPANCY.csv", ("activity_id", "week", "location_id", "co_share_group"), occupancy_rows)

    result_rows = [
        {
            "scenario": "A",
            "contract_number": project["contract_number"],
            "simulated_completion_date": (
                horizon_start
                + timedelta(
                    days=7
                    * max(
                        max(oracle_weeks[str(activity["activity_id"])])
                        for activity in activities
                        if activity["contract_number"] == project["contract_number"]
                    )
                    - 1
                )
            ).isoformat(),
            "overrun_days": 0,
        }
        for project in projects
    ]
    write(oracle / "RESULTS.csv", ("scenario", "contract_number", "simulated_completion_date", "overrun_days"), result_rows)


if __name__ == "__main__":
    main()
