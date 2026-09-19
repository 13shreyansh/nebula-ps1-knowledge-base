from __future__ import annotations

import argparse
import csv
import random
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


def read(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or ()), list(reader)


def write(path: Path, fields: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Replicate the frozen Live-interchange input into disjoint components."
    )
    parser.add_argument("--source", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--copies", type=int, default=8)
    parser.add_argument("--seed", type=int, default=20260919)
    args = parser.parse_args()
    if args.copies < 1:
        raise ValueError("copies must be positive")
    source = Path(args.source)
    output = Path(args.output)
    if output.exists() and any(output.iterdir()):
        raise ValueError(f"output directory must be empty: {output}")
    output.mkdir(parents=True, exist_ok=True)

    tables = {name: read(source / name) for name in FILES}
    replicated: dict[str, list[dict[str, str]]] = {
        name: [] for name in FILES
    }
    replicated["05_BUFFER_LOCATION.csv"] = [
        dict(row) for row in tables["05_BUFFER_LOCATION.csv"][1]
    ]
    replicated["06_PARAMETERS.csv"] = [
        dict(row) for row in tables["06_PARAMETERS.csv"][1]
    ]

    for copy_index in range(1, args.copies + 1):
        prefix = f"R{copy_index:02d}"
        line_map = {
            row["line_code"]: f"{prefix}{row['line_code']}"
            for row in tables["01_LINES.csv"][1]
        }
        station_ids = {
            row["station_id"] for row in tables["02_STATIONS.csv"][1]
        }
        station_map = {station: f"{prefix}{station}" for station in station_ids}
        contract_map = {
            row["contract_number"]: f"{prefix}{row['contract_number']}"
            for row in tables["07_PROJECT_DETAILS.csv"][1]
        }
        activity_map = {
            row["activity_id"]: f"{prefix}{row['activity_id']}"
            for row in tables["08_ACTIVITY_DETAILS.csv"][1]
        }
        sector_map = {
            row["sector_id"]: (
                f"SEC:{line_map[row['line_code']]}:"
                f"{station_map[row['from_station_id']]}_"
                f"{station_map[row['to_station_id']]}"
            )
            for row in tables["03_SECTORS.csv"][1]
        }

        def location(value: str) -> str:
            kind, line, body, bound = value.split(":")
            if kind == "SEC":
                return f"{sector_map[f'SEC:{line}:{body}']}:{bound}"
            return f"PLAT:{line_map[line]}:{station_map[body]}:{bound}"

        for row in tables["01_LINES.csv"][1]:
            copied = dict(row)
            copied["line_code"] = line_map[row["line_code"]]
            copied["line_name"] = f"{prefix} {row['line_name']}"
            replicated["01_LINES.csv"].append(copied)
        for row in tables["02_STATIONS.csv"][1]:
            copied = dict(row)
            copied["station_id"] = station_map[row["station_id"]]
            copied["line_code"] = line_map[row["line_code"]]
            replicated["02_STATIONS.csv"].append(copied)
        for row in tables["03_SECTORS.csv"][1]:
            copied = dict(row)
            copied["sector_id"] = sector_map[row["sector_id"]]
            copied["line_code"] = line_map[row["line_code"]]
            copied["from_station_id"] = station_map[row["from_station_id"]]
            copied["to_station_id"] = station_map[row["to_station_id"]]
            replicated["03_SECTORS.csv"].append(copied)
        for row in tables["04_LOCATION_SUPPLY.csv"][1]:
            copied = dict(row)
            copied["location_id"] = location(row["location_id"])
            copied["line_code"] = line_map[row["line_code"]]
            replicated["04_LOCATION_SUPPLY.csv"].append(copied)
        for row in tables["07_PROJECT_DETAILS.csv"][1]:
            copied = dict(row)
            copied["contract_number"] = contract_map[row["contract_number"]]
            copied["contract_description"] = f"{prefix} {row['contract_description']}"
            replicated["07_PROJECT_DETAILS.csv"].append(copied)
        for row in tables["08_ACTIVITY_DETAILS.csv"][1]:
            copied = dict(row)
            copied["activity_id"] = activity_map[row["activity_id"]]
            copied["contract_number"] = contract_map[row["contract_number"]]
            copied["start_location_id"] = location(row["start_location_id"])
            copied["end_location_id"] = location(row["end_location_id"])
            if row["predecessor_activity_id"]:
                copied["predecessor_activity_id"] = activity_map[
                    row["predecessor_activity_id"]
                ]
            replicated["08_ACTIVITY_DETAILS.csv"].append(copied)

    for name in FILES:
        fields = tables[name][0]
        rows = replicated[name]
        random.Random(f"{args.seed}:{name}").shuffle(rows)
        write(output / name, fields, rows)


if __name__ == "__main__":
    main()
