from __future__ import annotations

import csv
from datetime import date, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "fixtures" / "independent_multi_bridge_v1"
ORACLE = ROOT / "fixtures" / "independent_multi_bridge_v1_oracle_a"


def write(name: str, fields: tuple[str, ...], rows: list[dict[str, object]]) -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    with (DATA / name).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_oracle(
    name: str, fields: tuple[str, ...], rows: list[dict[str, object]]
) -> None:
    ORACLE.mkdir(parents=True, exist_ok=True)
    with (ORACLE / name).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def footprint(line: str, left: str, right: str, bound: str) -> tuple[str, ...]:
    stations = ("X1", "X2", "X3", "N4" if line == "LNX" else "S4")
    lo, hi = sorted((stations.index(left), stations.index(right)))
    locations = [f"PLAT:{line}:{station}:{bound}" for station in stations[lo : hi + 1]]
    locations.extend(
        f"SEC:{line}:{stations[index]}_{stations[index + 1]}:{bound}"
        for index in range(lo, hi)
    )
    return tuple(locations)


def main() -> None:
    lines = [("LNX", "Synthetic North"), ("LNY", "Synthetic South")]
    write(
        "01_LINES.csv",
        ("line_code", "line_name"),
        [{"line_code": code, "line_name": name} for code, name in lines],
    )

    stations_by_line = {
        "LNX": ("X1", "X2", "X3", "N4"),
        "LNY": ("X1", "X2", "X3", "S4"),
    }
    station_rows = []
    sector_rows = []
    supply_rows = []
    for line, stations in stations_by_line.items():
        for seq, station in enumerate(stations, 1):
            station_rows.append(
                {
                    "station_id": station,
                    "line_code": line,
                    "seq": seq,
                    "is_interchange": int(station.startswith("X")),
                }
            )
            for bound in ("EB", "WB"):
                supply_rows.append(
                    {
                        "location_id": f"PLAT:{line}:{station}:{bound}",
                        "location_kind": "platform",
                        "line_code": line,
                        "bound": bound,
                        "supply_capacity": 1,
                    }
                )
        for seq, (left, right) in enumerate(zip(stations, stations[1:]), 1):
            sector_id = f"SEC:{line}:{left}_{right}"
            sector_rows.append(
                {
                    "sector_id": sector_id,
                    "line_code": line,
                    "from_station_id": left,
                    "to_station_id": right,
                    "seq": seq,
                    "is_shared": int(left.startswith("X") and right.startswith("X")),
                }
            )
            for bound in ("EB", "WB"):
                supply_rows.append(
                    {
                        "location_id": f"{sector_id}:{bound}",
                        "location_kind": "tunnel sector",
                        "line_code": line,
                        "bound": bound,
                        "supply_capacity": 1,
                    }
                )
    write(
        "02_STATIONS.csv",
        ("station_id", "line_code", "seq", "is_interchange"),
        station_rows,
    )
    write(
        "03_SECTORS.csv",
        (
            "sector_id",
            "line_code",
            "from_station_id",
            "to_station_id",
            "seq",
            "is_shared",
        ),
        sector_rows,
    )
    write(
        "04_LOCATION_SUPPLY.csv",
        ("location_id", "location_kind", "line_code", "bound", "supply_capacity"),
        supply_rows,
    )
    write(
        "05_BUFFER_LOCATION.csv",
        ("nature_of_works", "up_to_buffer_sectors", "opposite_bound_required"),
        [
            {"nature_of_works": "Live", "up_to_buffer_sectors": 2, "opposite_bound_required": 1},
            {"nature_of_works": "Non-live (Consist)", "up_to_buffer_sectors": 1, "opposite_bound_required": 0},
            {"nature_of_works": "Non-live (Others)", "up_to_buffer_sectors": 0, "opposite_bound_required": 0},
        ],
    )
    write(
        "06_PARAMETERS.csv",
        ("key", "value"),
        [{"key": "horizon_start", "value": "2031-01-06"}, {"key": "horizon_weeks", "value": 8}],
    )

    projects = [
        ("K201", "Live", 1, "PM", "2031-01-12"),
        ("K202", "Non-live (Others)", 3, "C", "2031-01-19"),
        ("K203", "Live", 1, "PM", "2031-01-26"),
        ("K204", "Non-live (Others)", 3, "C", "2031-02-02"),
    ]
    project_rows = [
        {
            "contract_number": contract,
            "contract_description": f"Independent multi-bridge {contract}",
            "contract_award_date": "2030-06-01",
            "activity_type": "Synthetic",
            "nature_of_activity": nature,
            "contract_priority": priority,
            "contract_completion_date": "2031-02-23",
            "planned_completion_date": planned,
            "number_of_workfronts": 1,
            "access_type": access_type,
            "number_of_maximum_access_per_week": 1 if nature == "Live" else 2,
        }
        for contract, nature, priority, access_type, planned in projects
    ]
    write(
        "07_PROJECT_DETAILS.csv",
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
        project_rows,
    )

    activities = [
        ("M001", "K201", "LNX", "X1", "X3", "EB", "2031-01-06"),
        ("M002", "K202", "LNY", "X1", "X2", "WB", "2031-01-06"),
        ("M003", "K203", "LNY", "X2", "X3", "EB", "2031-01-20"),
        ("M004", "K204", "LNX", "X2", "X3", "WB", "2031-01-20"),
    ]
    activity_rows = [
        {
            "activity_id": activity,
            "contract_number": contract,
            "activity_type": "Synthetic",
            "start_location_id": f"SEC:{line}:{left}_{stations_by_line[line][stations_by_line[line].index(left)+1]}:{bound}",
            "end_location_id": f"SEC:{line}:{stations_by_line[line][stations_by_line[line].index(right)-1]}_{right}:{bound}",
            "total_accesses": 1,
            "planned_start_date": start,
            "predecessor_activity_id": "",
            "activity_priority": 3,
        }
        for activity, contract, line, left, right, bound, start in activities
    ]
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
        activity_rows,
    )

    weeks = {"M001": 1, "M002": 2, "M003": 3, "M004": 4}
    access_rows = []
    occupancy_rows = []
    for activity, _, line, left, right, bound, _ in activities:
        week = weeks[activity]
        access_rows.append(
            {"activity_id": activity, "access_seq": 1, "week": week, "eclo": 0, "access_night": 1}
        )
        occupancy_rows.extend(
            {
                "activity_id": activity,
                "week": week,
                "location_id": location,
                "co_share_group": f"G{week}",
            }
            for location in footprint(line, left, right, bound)
        )
    result_rows = []
    start = date(2031, 1, 6)
    for contract, activity in zip((p[0] for p in projects), weeks, strict=True):
        completion = start + timedelta(days=7 * weeks[activity] - 1)
        result_rows.append(
            {
                "scenario": "A",
                "contract_number": contract,
                "simulated_completion_date": completion.isoformat(),
                "overrun_days": 0,
            }
        )
    write_oracle(
        "SCHEDULE_ACCESS.csv",
        ("activity_id", "access_seq", "week", "eclo", "access_night"),
        access_rows,
    )
    write_oracle(
        "SCHEDULE_OCCUPANCY.csv",
        ("activity_id", "week", "location_id", "co_share_group"),
        occupancy_rows,
    )
    write_oracle(
        "RESULTS.csv",
        ("scenario", "contract_number", "simulated_completion_date", "overrun_days"),
        result_rows,
    )


if __name__ == "__main__":
    main()
