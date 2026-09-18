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


def read_rows(root: Path, name: str) -> tuple[list[str], list[dict[str, str]]]:
    with (root / name).open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or ()), list(reader)


def write_rows(root: Path, name: str, fields: list[str], rows: list[dict[str, str]]) -> None:
    with (root / name).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--seed", type=int, default=20260918)
    args = parser.parse_args()
    source = Path(args.source)
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)

    tables = {name: read_rows(source, name) for name in FILES}
    line_rows = tables["01_LINES.csv"][1]
    station_rows = tables["02_STATIONS.csv"][1]
    sector_rows = tables["03_SECTORS.csv"][1]
    project_rows = tables["07_PROJECT_DETAILS.csv"][1]
    activity_rows = tables["08_ACTIVITY_DETAILS.csv"][1]

    line_map = {
        row["line_code"]: f"L{index:02d}" for index, row in enumerate(line_rows, 1)
    }
    station_ids = sorted({row["station_id"] for row in station_rows})
    station_map = {station_id: f"N{index:03d}" for index, station_id in enumerate(station_ids, 1)}
    contract_map = {
        row["contract_number"]: f"K{index:03d}"
        for index, row in enumerate(project_rows, 501)
    }
    activity_map = {
        row["activity_id"]: f"Z{index:03d}"
        for index, row in enumerate(activity_rows, 501)
    }
    sector_map: dict[str, str] = {}
    for row in sector_rows:
        sector_map[row["sector_id"]] = (
            f"SEC:{line_map[row['line_code']]}:"
            f"{station_map[row['from_station_id']]}_{station_map[row['to_station_id']]}"
        )

    def location_id(value: str) -> str:
        kind, line, body, bound = value.split(":")
        if kind == "SEC":
            mapped = sector_map[f"SEC:{line}:{body}"]
            return f"{mapped}:{bound}"
        return f"PLAT:{line_map[line]}:{station_map[body]}:{bound}"

    transformed: dict[str, tuple[list[str], list[dict[str, str]]]] = {}
    for name, (fields, rows) in tables.items():
        copied = [dict(row) for row in rows]
        for original, row in zip(rows, copied, strict=True):
            if "line_code" in row:
                row["line_code"] = line_map[row["line_code"]]
            if name == "02_STATIONS.csv":
                row["station_id"] = station_map[row["station_id"]]
            elif name == "03_SECTORS.csv":
                row["sector_id"] = sector_map[original["sector_id"]]
                row["from_station_id"] = station_map[row["from_station_id"]]
                row["to_station_id"] = station_map[row["to_station_id"]]
            elif name == "04_LOCATION_SUPPLY.csv":
                row["location_id"] = location_id(original["location_id"])
            elif name == "07_PROJECT_DETAILS.csv":
                row["contract_number"] = contract_map[row["contract_number"]]
            elif name == "08_ACTIVITY_DETAILS.csv":
                row["activity_id"] = activity_map[row["activity_id"]]
                row["contract_number"] = contract_map[row["contract_number"]]
                row["start_location_id"] = location_id(row["start_location_id"])
                row["end_location_id"] = location_id(row["end_location_id"])
                if row["predecessor_activity_id"]:
                    row["predecessor_activity_id"] = activity_map[row["predecessor_activity_id"]]
        random.Random(f"{args.seed}:{name}").shuffle(copied)
        transformed[name] = fields, copied

    for name in FILES:
        fields, rows = transformed[name]
        write_rows(output, name, fields, rows)


if __name__ == "__main__":
    main()
