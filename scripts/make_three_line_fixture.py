from __future__ import annotations

import argparse
import csv
from datetime import date, timedelta
from pathlib import Path


FILES = (
    "01_LINES.csv",
    "02_STATIONS.csv",
    "03_SECTORS.csv",
    "04_LOCATION_SUPPLY.csv",
    "05_BUFFER_LOCATION.csv",
    "06_PARAMETERS.csv",
    "07_PROJECT_DETAILS.csv",
    "08_ACTIVITY_DETAILS.csv",
)


def read_table(root: Path, name: str) -> tuple[list[str], list[dict[str, str]]]:
    with (root / name).open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or ()), list(reader)


def write_table(
    root: Path, name: str, fields: list[str], rows: list[dict[str, object]]
) -> None:
    with (root / name).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--source-oracle", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--oracle-output", required=True, type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    args.oracle_output.mkdir(parents=True, exist_ok=True)

    tables = {name: read_table(args.source, name) for name in FILES}
    tables["01_LINES.csv"][1].append(
        {"line_code": "LNZ", "line_name": "Synthetic East"}
    )
    third_stations = (("X1", 1, 1), ("X2", 2, 1), ("Z3", 3, 0), ("Z4", 4, 0))
    tables["02_STATIONS.csv"][1].extend(
        {
            "station_id": station,
            "line_code": "LNZ",
            "seq": str(seq),
            "is_interchange": str(interchange),
        }
        for station, seq, interchange in third_stations
    )
    third_sectors: list[dict[str, object]] = []
    for seq, (left, _, _), (right, _, _) in zip(
        range(1, len(third_stations)),
        third_stations[:-1],
        third_stations[1:],
        strict=True,
    ):
        third_sectors.append(
            {
                "sector_id": f"SEC:LNZ:{left}_{right}",
                "line_code": "LNZ",
                "from_station_id": left,
                "to_station_id": right,
                "seq": seq,
                "is_shared": int(seq == 1),
            }
        )
    tables["03_SECTORS.csv"][1].extend(third_sectors)
    for sector in third_sectors:
        for bound in ("EB", "WB"):
            tables["04_LOCATION_SUPPLY.csv"][1].append(
                {
                    "location_id": f"{sector['sector_id']}:{bound}",
                    "location_kind": "tunnel sector",
                    "line_code": "LNZ",
                    "bound": bound,
                    "supply_capacity": 1,
                }
            )
    for station, _, _ in third_stations:
        for bound in ("EB", "WB"):
            tables["04_LOCATION_SUPPLY.csv"][1].append(
                {
                    "location_id": f"PLAT:LNZ:{station}:{bound}",
                    "location_kind": "platform",
                    "line_code": "LNZ",
                    "bound": bound,
                    "supply_capacity": 1,
                }
            )
    tables["07_PROJECT_DETAILS.csv"][1].append(
        {
            "contract_number": "K109",
            "contract_description": "Independent third-line extension",
            "contract_award_date": "2030-06-01",
            "activity_type": "Synthetic",
            "nature_of_activity": "Non-live (Others)",
            "contract_priority": 2,
            "contract_completion_date": "2031-06-22",
            "planned_completion_date": "2031-04-20",
            "number_of_workfronts": 1,
            "access_type": "C",
            "number_of_maximum_access_per_week": 2,
        }
    )
    tables["08_ACTIVITY_DETAILS.csv"][1].append(
        {
            "activity_id": "Q010",
            "contract_number": "K109",
            "activity_type": "Synthetic",
            "start_location_id": "SEC:LNZ:Z3_Z4:EB",
            "end_location_id": "SEC:LNZ:Z3_Z4:EB",
            "total_accesses": 1,
            "planned_start_date": "2031-04-14",
            "predecessor_activity_id": "",
            "activity_priority": 2,
        }
    )
    for name in FILES:
        fields, rows = tables[name]
        write_table(args.output, name, fields, rows)

    access_fields, access_rows = read_table(args.source_oracle, "SCHEDULE_ACCESS.csv")
    occupancy_fields, occupancy_rows = read_table(
        args.source_oracle, "SCHEDULE_OCCUPANCY.csv"
    )
    result_fields, result_rows = read_table(args.source_oracle, "RESULTS.csv")
    access_rows.append(
        {
            "activity_id": "Q010",
            "access_seq": "1",
            "week": "15",
            "eclo": "0",
            "access_night": "1",
        }
    )
    for location_id in (
        "SEC:LNZ:Z3_Z4:EB",
        "PLAT:LNZ:Z3:EB",
        "PLAT:LNZ:Z4:EB",
    ):
        occupancy_rows.append(
            {
                "activity_id": "Q010",
                "week": "15",
                "location_id": location_id,
                "co_share_group": "G15",
            }
        )
    horizon_start = date.fromisoformat("2031-01-06")
    completion_date = horizon_start + timedelta(days=7 * 15 - 1)
    result_rows.append(
        {
            "scenario": "A",
            "contract_number": "K109",
            "simulated_completion_date": completion_date.isoformat(),
            "overrun_days": "0",
        }
    )
    write_table(args.oracle_output, "SCHEDULE_ACCESS.csv", access_fields, access_rows)
    write_table(
        args.oracle_output,
        "SCHEDULE_OCCUPANCY.csv",
        occupancy_fields,
        occupancy_rows,
    )
    write_table(args.oracle_output, "RESULTS.csv", result_fields, result_rows)


if __name__ == "__main__":
    main()
