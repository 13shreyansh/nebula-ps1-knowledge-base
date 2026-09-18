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
        description="Generate a public-independent modular stress fixture and A oracle."
    )
    parser.add_argument("--output", required=True)
    parser.add_argument("--oracle-output", required=True)
    parser.add_argument("--modules", type=int, default=4)
    args = parser.parse_args()
    if args.modules < 1:
        raise ValueError("modules must be positive")
    output = Path(args.output)
    oracle = Path(args.oracle_output)
    if output.exists() and any(output.iterdir()):
        raise ValueError(f"output directory must be empty: {output}")
    if oracle.exists() and any(oracle.iterdir()):
        raise ValueError(f"oracle directory must be empty: {oracle}")
    output.mkdir(parents=True, exist_ok=True)
    oracle.mkdir(parents=True, exist_ok=True)

    lines = (("LSX", "Scaled synthetic east"), ("LSY", "Scaled synthetic west"))
    stations_by_line: dict[str, list[tuple[str, int, int]]] = {line: [] for line, _ in lines}
    for line, _ in lines:
        sequence = 1
        suffix = "N" if line == "LSX" else "S"
        for module in range(1, args.modules + 1):
            names = (
                (f"J{module}A", 1),
                (f"J{module}B", 1),
                (f"{suffix}{module}C", 0),
                (f"{suffix}{module}D", 0),
                (f"{suffix}{module}G1", 0),
                (f"{suffix}{module}G2", 0),
                (f"{suffix}{module}G3", 0),
            )
            for station_id, interchange in names:
                stations_by_line[line].append((station_id, sequence, interchange))
                sequence += 1

    sectors: list[dict[str, object]] = []
    sector_by_line_and_seq: dict[tuple[str, int], dict[str, object]] = {}
    for line, _ in lines:
        stations = stations_by_line[line]
        for seq, (left, _, _), (right, _, _) in zip(
            range(1, len(stations)), stations[:-1], stations[1:], strict=True
        ):
            row = {
                "sector_id": f"SEC:{line}:{left}_{right}",
                "line_code": line,
                "from_station_id": left,
                "to_station_id": right,
                "seq": seq,
                "is_shared": int(left.startswith("J") and right.startswith("J")),
            }
            sectors.append(row)
            sector_by_line_and_seq[(line, seq)] = row

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
    for line, _ in lines:
        for station_id, _, _ in stations_by_line[line]:
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

    project_template = (
        (1, "C", "Non-live (Others)", 3, "2031-01-19", 1, 2),
        (2, "PC", "Non-live (Consist)", 2, "2031-02-09", 1, 2),
        (3, "PM", "Live", 1, "2031-02-16", 1, 1),
        (4, "C", "Non-live (Consist)", 2, "2031-03-09", 1, 2),
        (5, "PC", "Live", 1, "2031-03-23", 1, 2),
        (6, "C", "Non-live (Others)", 3, "2031-04-06", 1, 2),
        (7, "PM", "Non-live (Others)", 2, "2031-04-13", 1, 1),
        (8, "C", "Non-live (Others)", 1, "2031-02-09", 1, 2),
    )
    projects: list[dict[str, object]] = []
    activities: list[dict[str, object]] = []
    oracle_weeks: dict[str, tuple[int, ...]] = {}
    activity_endpoints: dict[str, tuple[str, str]] = {}

    for module in range(1, args.modules + 1):
        for local, access_type, nature, priority, planned, workfronts, weekly_max in project_template:
            contract = f"Z{module:02d}{local:02d}"
            projects.append(
                {
                    "contract_number": contract,
                    "contract_description": f"Scaled independent module {module} contract {local}",
                    "contract_award_date": "2030-06-01",
                    "activity_type": "ScaledSynthetic",
                    "nature_of_activity": nature,
                    "contract_priority": priority,
                    "contract_completion_date": "2031-06-22",
                    "planned_completion_date": planned,
                    "number_of_workfronts": workfronts,
                    "access_type": access_type,
                    "number_of_maximum_access_per_week": weekly_max,
                }
            )

        x = "LSX"
        y = "LSY"
        xa, xb = f"J{module}A", f"J{module}B"
        nc, nd = f"N{module}C", f"N{module}D"
        sc, sd = f"S{module}C", f"S{module}D"
        activity_template = (
            (1, 1, f"SEC:{x}:{xb}_{nc}:EB", f"SEC:{x}:{xb}_{nc}:EB", 3, "2031-01-06", "", 3, (1, 2, 3)),
            (2, 2, f"SEC:{x}:{nc}_{nd}:WB", f"SEC:{x}:{nc}_{nd}:WB", 2, "2031-01-27", "", 2, (4, 5)),
            (3, 3, f"SEC:{x}:{xa}_{xb}:EB", f"SEC:{x}:{xa}_{xb}:EB", 1, "2031-02-10", "", 1, (6,)),
            (4, 4, f"SEC:{y}:{xb}_{sc}:WB", f"SEC:{y}:{sc}_{sd}:WB", 2, "2031-02-17", "", 2, (7, 8)),
            (5, 4, f"SEC:{y}:{sc}_{sd}:WB", f"SEC:{y}:{sc}_{sd}:WB", 1, "2031-03-03", "PREV", 1, (9,)),
            (6, 5, f"SEC:{y}:{xa}_{xb}:EB", f"SEC:{y}:{xa}_{xb}:EB", 2, "2031-03-10", "", 2, (10, 11)),
            (7, 6, f"SEC:{x}:{xb}_{nc}:WB", f"SEC:{x}:{nc}_{nd}:WB", 2, "2031-03-24", "", 3, (12, 13)),
            (8, 7, f"SEC:{y}:{sc}_{sd}:EB", f"SEC:{y}:{sc}_{sd}:EB", 1, "2031-04-07", "", 1, (14,)),
            (9, 8, f"SEC:{x}:{nc}_{nd}:WB", f"SEC:{x}:{nc}_{nd}:WB", 2, "2031-01-27", "", 2, (4, 5)),
        )
        for local, contract_local, start, end, accesses, planned_start, predecessor, priority, weeks in activity_template:
            activity_id = f"R{module:02d}{local:02d}"
            predecessor_id = f"R{module:02d}04" if predecessor else ""
            activities.append(
                {
                    "activity_id": activity_id,
                    "contract_number": f"Z{module:02d}{contract_local:02d}",
                    "activity_type": "ScaledSynthetic",
                    "start_location_id": start,
                    "end_location_id": end,
                    "total_accesses": accesses,
                    "planned_start_date": planned_start,
                    "predecessor_activity_id": predecessor_id,
                    "activity_priority": priority,
                }
            )
            oracle_weeks[activity_id] = weeks
            activity_endpoints[activity_id] = (start, end)

    write(output / "01_LINES.csv", ("line_code", "line_name"), [
        {"line_code": code, "line_name": name} for code, name in lines
    ])
    write(
        output / "02_STATIONS.csv",
        ("station_id", "line_code", "seq", "is_interchange"),
        [
            {"station_id": station, "line_code": line, "seq": seq, "is_interchange": interchange}
            for line, _ in lines
            for station, seq, interchange in stations_by_line[line]
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
        {"key": "horizon_start", "value": "2031-01-06"},
        {"key": "horizon_weeks", "value": 24},
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

    sector_lookup = {str(row["sector_id"]): row for row in sectors}

    def independent_footprint(start_location: str, end_location: str) -> list[str]:
        start_parts = start_location.split(":")
        end_parts = end_location.split(":")
        line = start_parts[1]
        bound = start_parts[3]
        start_sector = sector_lookup[":".join(start_parts[:3])]
        end_sector = sector_lookup[":".join(end_parts[:3])]
        low, high = sorted((int(start_sector["seq"]), int(end_sector["seq"])))
        corridor = [sector_by_line_and_seq[(line, seq)] for seq in range(low, high + 1)]
        station_ids = [str(corridor[0]["from_station_id"])]
        station_ids.extend(str(row["to_station_id"]) for row in corridor)
        footprint = [f"{row['sector_id']}:{bound}" for row in corridor]
        footprint.extend(f"PLAT:{line}:{station}:{bound}" for station in station_ids)
        return sorted(footprint)

    access_rows: list[dict[str, object]] = []
    occupancy_rows: list[dict[str, object]] = []
    for activity in activities:
        activity_id = str(activity["activity_id"])
        module = int(activity_id[1:3])
        start, end = activity_endpoints[activity_id]
        for access_seq, week in enumerate(oracle_weeks[activity_id], start=1):
            access_rows.append(
                {"activity_id": activity_id, "access_seq": access_seq, "week": week, "eclo": 0, "access_night": 1}
            )
            group = f"M{module:02d}W{week:02d}"
            for location_id in independent_footprint(start, end):
                occupancy_rows.append(
                    {"activity_id": activity_id, "week": week, "location_id": location_id, "co_share_group": group}
                )
    write(oracle / "SCHEDULE_ACCESS.csv", ("activity_id", "access_seq", "week", "eclo", "access_night"), access_rows)
    write(oracle / "SCHEDULE_OCCUPANCY.csv", ("activity_id", "week", "location_id", "co_share_group"), occupancy_rows)

    project_by_contract = {str(row["contract_number"]): row for row in projects}
    activities_by_contract: dict[str, list[str]] = {}
    for activity in activities:
        activities_by_contract.setdefault(str(activity["contract_number"]), []).append(str(activity["activity_id"]))
    horizon_start = date.fromisoformat("2031-01-06")
    result_rows: list[dict[str, object]] = []
    for contract in sorted(project_by_contract):
        completion_week = max(
            max(oracle_weeks[activity_id]) for activity_id in activities_by_contract[contract]
        )
        completion_date = horizon_start + timedelta(days=7 * completion_week - 1)
        planned_completion = date.fromisoformat(str(project_by_contract[contract]["planned_completion_date"]))
        result_rows.append(
            {
                "scenario": "A",
                "contract_number": contract,
                "simulated_completion_date": completion_date.isoformat(),
                "overrun_days": max(0, (completion_date - planned_completion).days),
            }
        )
    write(oracle / "RESULTS.csv", ("scenario", "contract_number", "simulated_completion_date", "overrun_days"), result_rows)


if __name__ == "__main__":
    main()
