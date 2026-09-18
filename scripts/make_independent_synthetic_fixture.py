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
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--oracle-output", required=True)
    args = parser.parse_args()
    output = Path(args.output)
    oracle = Path(args.oracle_output)
    output.mkdir(parents=True, exist_ok=True)
    oracle.mkdir(parents=True, exist_ok=True)

    lines = [("LNX", "Synthetic North"), ("LNY", "Synthetic South")]
    stations = {
        "LNX": (("X1", 1, 1), ("X2", 2, 1), ("N3", 3, 0), ("N4", 4, 0)),
        "LNY": (("X1", 1, 1), ("X2", 2, 1), ("S3", 3, 0), ("S4", 4, 0)),
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
        for station, _, _ in line_stations:
            for bound in ("EB", "WB"):
                locations.append(
                    {
                        "location_id": f"PLAT:{line}:{station}:{bound}",
                        "location_kind": "platform",
                        "line_code": line,
                        "bound": bound,
                        "supply_capacity": 1,
                    }
                )

    project_specs = (
        ("K101", "C", "Non-live (Others)", 3, "2031-01-19", 1, 2),
        ("K102", "PC", "Non-live (Consist)", 2, "2031-02-09", 1, 2),
        ("K103", "PM", "Live", 1, "2031-02-16", 1, 1),
        ("K104", "C", "Non-live (Consist)", 2, "2031-03-09", 1, 2),
        ("K105", "PC", "Live", 1, "2031-03-23", 1, 2),
        ("K106", "C", "Non-live (Others)", 3, "2031-04-06", 1, 2),
        ("K107", "PM", "Non-live (Others)", 2, "2031-04-13", 1, 1),
        ("K108", "C", "Non-live (Others)", 1, "2031-02-09", 1, 2),
    )
    projects = [
        {
            "contract_number": contract,
            "contract_description": f"Independent synthetic {contract}",
            "contract_award_date": "2030-06-01",
            "activity_type": "Synthetic",
            "nature_of_activity": nature,
            "contract_priority": priority,
            "contract_completion_date": "2031-06-22",
            "planned_completion_date": planned,
            "number_of_workfronts": workfronts,
            "access_type": access_type,
            "number_of_maximum_access_per_week": weekly_max,
        }
        for contract, access_type, nature, priority, planned, workfronts, weekly_max in project_specs
    ]

    activity_specs = (
        ("Q001", "K101", "SEC:LNX:X2_N3:EB", "SEC:LNX:X2_N3:EB", 3, "2031-01-06", "", 3),
        ("Q002", "K102", "SEC:LNX:N3_N4:WB", "SEC:LNX:N3_N4:WB", 2, "2031-01-27", "", 2),
        ("Q003", "K103", "SEC:LNX:X1_X2:EB", "SEC:LNX:X1_X2:EB", 1, "2031-02-10", "", 1),
        ("Q004", "K104", "SEC:LNY:X2_S3:WB", "SEC:LNY:S3_S4:WB", 2, "2031-02-17", "", 2),
        ("Q005", "K104", "SEC:LNY:S3_S4:WB", "SEC:LNY:S3_S4:WB", 1, "2031-03-03", "Q004", 1),
        ("Q006", "K105", "SEC:LNY:X1_X2:EB", "SEC:LNY:X1_X2:EB", 2, "2031-03-10", "", 2),
        ("Q007", "K106", "SEC:LNX:X2_N3:WB", "SEC:LNX:N3_N4:WB", 2, "2031-03-24", "", 3),
        ("Q008", "K107", "SEC:LNY:S3_S4:EB", "SEC:LNY:S3_S4:EB", 1, "2031-04-07", "", 1),
        ("Q009", "K108", "SEC:LNX:N3_N4:WB", "SEC:LNX:N3_N4:WB", 2, "2031-01-27", "", 2),
    )
    activities = [
        {
            "activity_id": activity,
            "contract_number": contract,
            "activity_type": "Synthetic",
            "start_location_id": start,
            "end_location_id": end,
            "total_accesses": accesses,
            "planned_start_date": planned_start,
            "predecessor_activity_id": predecessor,
            "activity_priority": priority,
        }
        for activity, contract, start, end, accesses, planned_start, predecessor, priority in activity_specs
    ]

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
    write(
        output / "03_SECTORS.csv",
        ("sector_id", "line_code", "from_station_id", "to_station_id", "seq", "is_shared"),
        sectors,
    )
    write(
        output / "04_LOCATION_SUPPLY.csv",
        ("location_id", "location_kind", "line_code", "bound", "supply_capacity"),
        locations,
    )
    write(
        output / "05_BUFFER_LOCATION.csv",
        ("nature_of_works", "up_to_buffer_sectors", "opposite_bound_required"),
        [
            {"nature_of_works": "Live", "up_to_buffer_sectors": 2, "opposite_bound_required": 1},
            {"nature_of_works": "Non-live (Consist)", "up_to_buffer_sectors": 1, "opposite_bound_required": 0},
            {"nature_of_works": "Non-live (Others)", "up_to_buffer_sectors": 0, "opposite_bound_required": 0},
        ],
    )
    write(
        output / "06_PARAMETERS.csv",
        ("key", "value"),
        [{"key": "horizon_start", "value": "2031-01-06"}, {"key": "horizon_weeks", "value": 24}],
    )
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

    weeks = {
        "Q001": (1, 2, 3), "Q002": (4, 5), "Q009": (4, 5), "Q003": (6,),
        "Q004": (7, 8), "Q005": (9,), "Q006": (10, 11), "Q007": (12, 13),
        "Q008": (14,),
    }
    access_rows: list[dict[str, object]] = []
    occupancy_rows: list[dict[str, object]] = []
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
            (
                row
                for row in sectors
                if row["line_code"] == line and low <= int(row["seq"]) <= high
            ),
            key=lambda row: int(row["seq"]),
        )
        station_ids = [str(corridor[0]["from_station_id"])]
        station_ids.extend(str(row["to_station_id"]) for row in corridor)
        footprint = [f"{row['sector_id']}:{bound}" for row in corridor]
        footprint.extend(f"PLAT:{line}:{station}:{bound}" for station in station_ids)
        return sorted(footprint)

    activity_by_id = {row[0]: row for row in activity_specs}
    for activity_id, activity_weeks in weeks.items():
        activity = activity_by_id[activity_id]
        for access_seq, week in enumerate(activity_weeks, start=1):
            access_rows.append(
                {"activity_id": activity_id, "access_seq": access_seq, "week": week, "eclo": 0, "access_night": 1}
            )
            group = f"G{week:02d}"
            for location_id in independent_footprint(activity[2], activity[3]):
                occupancy_rows.append(
                    {"activity_id": activity_id, "week": week, "location_id": location_id, "co_share_group": group}
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
    project_by_contract = {row[0]: row for row in project_specs}
    activities_by_contract: dict[str, list[str]] = {}
    for activity in activity_specs:
        activities_by_contract.setdefault(activity[1], []).append(activity[0])
    horizon_start = date.fromisoformat("2031-01-06")
    result_rows: list[dict[str, object]] = []
    for contract in sorted(project_by_contract):
        completion_week = max(
            max(weeks[activity_id]) for activity_id in activities_by_contract[contract]
        )
        completion_date = horizon_start + timedelta(days=7 * completion_week - 1)
        planned_completion = date.fromisoformat(project_by_contract[contract][4])
        result_rows.append(
            {
                "scenario": "A",
                "contract_number": contract,
                "simulated_completion_date": completion_date.isoformat(),
                "overrun_days": max(0, (completion_date - planned_completion).days),
            }
        )
    write(
        oracle / "RESULTS.csv",
        ("scenario", "contract_number", "simulated_completion_date", "overrun_days"),
        result_rows,
    )


if __name__ == "__main__":
    main()
