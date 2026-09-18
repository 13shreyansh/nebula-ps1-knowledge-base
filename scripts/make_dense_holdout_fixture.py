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
    parser = argparse.ArgumentParser(description="Generate the frozen-hint dense holdout fixture.")
    parser.add_argument("--output", required=True)
    parser.add_argument("--oracle-output", required=True)
    args = parser.parse_args()
    output = Path(args.output)
    oracle = Path(args.oracle_output)
    if output.exists() and any(output.iterdir()):
        raise ValueError(f"output directory must be empty: {output}")
    if oracle.exists() and any(oracle.iterdir()):
        raise ValueError(f"oracle directory must be empty: {oracle}")
    output.mkdir(parents=True, exist_ok=True)
    oracle.mkdir(parents=True, exist_ok=True)

    horizon_start = date.fromisoformat("2032-01-05")

    def week_end(week: int) -> str:
        return (horizon_start + timedelta(days=7 * week - 1)).isoformat()

    lines = (("LHX", "Holdout dense north"), ("LHY", "Holdout dense south"))
    stations = {
        "LHX": (("HX1", 1, 1), ("HX2", 2, 1), ("HN3", 3, 0), ("HN4", 4, 0), ("HN5", 5, 0), ("HN6", 6, 0)),
        "LHY": (("HX1", 1, 1), ("HX2", 2, 1), ("HS3", 3, 0), ("HS4", 4, 0), ("HS5", 5, 0), ("HS6", 6, 0)),
    }
    sectors: list[dict[str, object]] = []
    for line, values in stations.items():
        for seq, (left, _, _), (right, _, _) in zip(
            range(1, len(values)), values[:-1], values[1:], strict=True
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
    locations = [
        {
            "location_id": f"{sector['sector_id']}:{bound}",
            "location_kind": "tunnel sector",
            "line_code": sector["line_code"],
            "bound": bound,
            "supply_capacity": 1,
        }
        for sector in sectors
        for bound in ("EB", "WB")
    ]
    locations.extend(
        {
            "location_id": f"PLAT:{line}:{station_id}:{bound}",
            "location_kind": "platform",
            "line_code": line,
            "bound": bound,
            "supply_capacity": 1,
        }
        for line, values in stations.items()
        for station_id, _, _ in values
        for bound in ("EB", "WB")
    )

    projects: list[dict[str, object]] = []
    activities: list[dict[str, object]] = []
    oracle_weeks: dict[str, tuple[int, ...]] = {}
    endpoints: dict[str, tuple[str, str]] = {}

    def add_project(contract: str, access_type: str, nature: str, planned_week: int) -> None:
        projects.append(
            {
                "contract_number": contract,
                "contract_description": f"Held-out dense {contract}",
                "contract_award_date": "2031-06-01",
                "activity_type": "HeldoutDense",
                "nature_of_activity": nature,
                "contract_priority": 1,
                "contract_completion_date": week_end(24),
                "planned_completion_date": week_end(planned_week),
                "number_of_workfronts": 1,
                "access_type": access_type,
                "number_of_maximum_access_per_week": 2 if nature == "Live" else 3,
            }
        )

    def add_activity(
        activity_id: str,
        contract: str,
        start: str,
        end: str,
        accesses: int,
        weeks: tuple[int, ...],
        predecessor: str = "",
    ) -> None:
        activities.append(
            {
                "activity_id": activity_id,
                "contract_number": contract,
                "activity_type": "HeldoutDense",
                "start_location_id": start,
                "end_location_id": end,
                "total_accesses": accesses,
                "planned_start_date": horizon_start.isoformat(),
                "predecessor_activity_id": predecessor,
                "activity_priority": 1,
            }
        )
        oracle_weeks[activity_id] = weeks
        endpoints[activity_id] = (start, end)

    for line, marker, third, fourth, fifth in (
        ("LHX", "X", "HN3", "HN4", "HN5"),
        ("LHY", "Y", "HS3", "HS4", "HS5"),
    ):
        corridors = (
            ("E", f"SEC:{line}:{third}_{fourth}:EB", 12),
            ("W", f"SEC:{line}:{fourth}_{fifth}:WB", 14),
        )
        for corridor_tag, corridor, deadline in corridors:
            for batch in range(1, 7):
                weeks = (2 * batch - 1, 2 * batch)
                for member, access_type, nature in (
                    ("P", "PC", "Non-live (Consist)"),
                    ("C1", "C", "Non-live (Others)"),
                    ("C2", "C", "Non-live (Others)"),
                    ("C3", "C", "Non-live (Others)"),
                ):
                    activity_id = f"V{marker}{corridor_tag}{batch:02d}{member}"
                    contract = f"K{activity_id}"
                    add_project(contract, access_type, nature, deadline)
                    add_activity(activity_id, contract, corridor, corridor, 2, weeks)

        chain_contract = f"KH{marker}"
        add_project(chain_contract, "C", "Non-live (Others)", 18)
        corridor_one = corridors[0][1]
        corridor_two = corridors[1][1]
        span_end = f"SEC:{line}:{fourth}_{fifth}:EB"
        add_activity(f"H{marker}1", chain_contract, corridor_one, corridor_one, 1, (13,))
        add_activity(f"H{marker}2", chain_contract, corridor_two, corridor_two, 1, (14,), f"H{marker}1")
        add_activity(f"H{marker}3", chain_contract, corridor_one, span_end, 1, (15,), f"H{marker}2")

        live_id = f"V{marker}LIVE"
        live_contract = f"K{live_id}"
        add_project(live_contract, "PM", "Live", 18)
        add_activity(
            live_id,
            live_contract,
            f"SEC:{line}:HX1_HX2:EB",
            f"SEC:{line}:HX1_HX2:EB",
            1,
            (16 if line == "LHX" else 17,),
        )
        local_id = f"V{marker}PM"
        local_contract = f"K{local_id}"
        add_project(local_contract, "PM", "Non-live (Others)", 18)
        add_activity(local_id, local_contract, corridor_one, corridor_one, 1, (18,), live_id)

    write(output / "01_LINES.csv", ("line_code", "line_name"), [
        {"line_code": code, "line_name": name} for code, name in lines
    ])
    write(output / "02_STATIONS.csv", ("station_id", "line_code", "seq", "is_interchange"), [
        {"station_id": station, "line_code": line, "seq": seq, "is_interchange": interchange}
        for line, values in stations.items()
        for station, seq, interchange in values
    ])
    write(output / "03_SECTORS.csv", ("sector_id", "line_code", "from_station_id", "to_station_id", "seq", "is_shared"), sectors)
    write(output / "04_LOCATION_SUPPLY.csv", ("location_id", "location_kind", "line_code", "bound", "supply_capacity"), locations)
    write(output / "05_BUFFER_LOCATION.csv", ("nature_of_works", "up_to_buffer_sectors", "opposite_bound_required"), [
        {"nature_of_works": "Live", "up_to_buffer_sectors": 2, "opposite_bound_required": 1},
        {"nature_of_works": "Non-live (Consist)", "up_to_buffer_sectors": 1, "opposite_bound_required": 0},
        {"nature_of_works": "Non-live (Others)", "up_to_buffer_sectors": 0, "opposite_bound_required": 0},
    ])
    write(output / "06_PARAMETERS.csv", ("key", "value"), [
        {"key": "horizon_start", "value": horizon_start.isoformat()},
        {"key": "horizon_weeks", "value": 24},
    ])
    write(output / "07_PROJECT_DETAILS.csv", (
        "contract_number", "contract_description", "contract_award_date", "activity_type",
        "nature_of_activity", "contract_priority", "contract_completion_date",
        "planned_completion_date", "number_of_workfronts", "access_type",
        "number_of_maximum_access_per_week",
    ), projects)
    write(output / "08_ACTIVITY_DETAILS.csv", (
        "activity_id", "contract_number", "activity_type", "start_location_id",
        "end_location_id", "total_accesses", "planned_start_date",
        "predecessor_activity_id", "activity_priority",
    ), activities)

    sector_by_id = {str(row["sector_id"]): row for row in sectors}

    def footprint(start_location: str, end_location: str) -> list[str]:
        start_parts = start_location.split(":")
        end_parts = end_location.split(":")
        line, bound = start_parts[1], start_parts[3]
        low, high = sorted(
            (
                int(sector_by_id[":".join(start_parts[:3])]["seq"]),
                int(sector_by_id[":".join(end_parts[:3])]["seq"]),
            )
        )
        corridor = sorted(
            (row for row in sectors if row["line_code"] == line and low <= int(row["seq"]) <= high),
            key=lambda row: int(row["seq"]),
        )
        station_ids = [str(corridor[0]["from_station_id"]), *[str(row["to_station_id"]) for row in corridor]]
        return sorted(
            [f"{row['sector_id']}:{bound}" for row in corridor]
            + [f"PLAT:{line}:{station}:{bound}" for station in station_ids]
        )

    access_rows: list[dict[str, object]] = []
    occupancy_rows: list[dict[str, object]] = []
    for activity in activities:
        activity_id = str(activity["activity_id"])
        start, end = endpoints[activity_id]
        for sequence, week in enumerate(oracle_weeks[activity_id], start=1):
            access_rows.append(
                {"activity_id": activity_id, "access_seq": sequence, "week": week, "eclo": 0, "access_night": 1}
            )
            batch_key = activity_id[:-1] if activity_id.endswith("P") else activity_id[:-2] if activity_id.endswith(("C1", "C2", "C3")) else activity_id
            group = f"{batch_key}W{week}"
            for location_id in footprint(start, end):
                occupancy_rows.append(
                    {"activity_id": activity_id, "week": week, "location_id": location_id, "co_share_group": group}
                )
    write(oracle / "SCHEDULE_ACCESS.csv", ("activity_id", "access_seq", "week", "eclo", "access_night"), access_rows)
    write(oracle / "SCHEDULE_OCCUPANCY.csv", ("activity_id", "week", "location_id", "co_share_group"), occupancy_rows)

    activities_by_contract: dict[str, list[str]] = {}
    for activity in activities:
        activities_by_contract.setdefault(str(activity["contract_number"]), []).append(str(activity["activity_id"]))
    project_by_contract = {str(project["contract_number"]): project for project in projects}
    result_rows = []
    for contract in sorted(project_by_contract):
        completion_week = max(max(oracle_weeks[activity_id]) for activity_id in activities_by_contract[contract])
        completion_date = horizon_start + timedelta(days=7 * completion_week - 1)
        planned = date.fromisoformat(str(project_by_contract[contract]["planned_completion_date"]))
        result_rows.append(
            {
                "scenario": "A",
                "contract_number": contract,
                "simulated_completion_date": completion_date.isoformat(),
                "overrun_days": max(0, (completion_date - planned).days),
            }
        )
    write(oracle / "RESULTS.csv", ("scenario", "contract_number", "simulated_completion_date", "overrun_days"), result_rows)


if __name__ == "__main__":
    main()
