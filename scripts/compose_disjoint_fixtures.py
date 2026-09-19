from __future__ import annotations

import argparse
import csv
import random
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
        description=(
            "Compose schema-compatible fixtures as identifier-disjoint subinstances. "
            "Each source is PREFIX=PATH."
        )
    )
    parser.add_argument("--source", action="append", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--horizon-start", default="2040-01-02")
    parser.add_argument("--seed", type=int, default=20260919)
    args = parser.parse_args()
    target_start = date.fromisoformat(args.horizon_start)
    output = Path(args.output)
    if output.exists() and any(output.iterdir()):
        raise ValueError(f"output directory must be empty: {output}")
    output.mkdir(parents=True, exist_ok=True)

    sources: list[tuple[str, Path]] = []
    for value in args.source:
        if "=" not in value:
            raise ValueError("each --source must be PREFIX=PATH")
        prefix, raw_path = value.split("=", 1)
        if not prefix or not prefix.isalnum():
            raise ValueError(f"source prefix must be alphanumeric: {prefix!r}")
        sources.append((prefix, Path(raw_path)))
    if len({prefix for prefix, _ in sources}) != len(sources):
        raise ValueError("source prefixes must be unique")

    first_tables = {name: read(sources[0][1] / name) for name in FILES}
    fields = {name: table[0] for name, table in first_tables.items()}
    combined = {name: [] for name in FILES}
    maximum_horizon_weeks = 0

    for prefix, source in sources:
        tables = {name: read(source / name) for name in FILES}
        for name in FILES:
            if tables[name][0] != fields[name]:
                raise ValueError(f"schema mismatch for {name}: {source}")
        parameters = {
            row["key"]: row["value"] for row in tables["06_PARAMETERS.csv"][1]
        }
        source_start = date.fromisoformat(parameters["horizon_start"])
        maximum_horizon_weeks = max(
            maximum_horizon_weeks,
            int(parameters["horizon_weeks"]),
        )

        line_map = {
            row["line_code"]: f"{prefix}{row['line_code']}"
            for row in tables["01_LINES.csv"][1]
        }
        station_map = {
            row["station_id"]: f"{prefix}{row['station_id']}"
            for row in tables["02_STATIONS.csv"][1]
        }
        contract_map = {
            row["contract_number"]: f"{prefix}{row['contract_number']}"
            for row in tables["07_PROJECT_DETAILS.csv"][1]
        }
        activity_map = {
            row["activity_id"]: f"{prefix}{row['activity_id']}"
            for row in tables["08_ACTIVITY_DETAILS.csv"][1]
        }
        nature_map = {
            row["nature_of_works"]: f"{prefix} {row['nature_of_works']}"
            for row in tables["05_BUFFER_LOCATION.csv"][1]
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
            if kind == "PLAT":
                return f"PLAT:{line_map[line]}:{station_map[body]}:{bound}"
            raise ValueError(f"unsupported location kind: {value}")

        def shifted(value: str) -> str:
            original = date.fromisoformat(value)
            return (target_start + timedelta(days=(original - source_start).days)).isoformat()

        for row in tables["01_LINES.csv"][1]:
            copied = dict(row)
            copied["line_code"] = line_map[row["line_code"]]
            copied["line_name"] = f"{prefix} {row['line_name']}"
            combined["01_LINES.csv"].append(copied)
        for row in tables["02_STATIONS.csv"][1]:
            copied = dict(row)
            copied["station_id"] = station_map[row["station_id"]]
            copied["line_code"] = line_map[row["line_code"]]
            combined["02_STATIONS.csv"].append(copied)
        for row in tables["03_SECTORS.csv"][1]:
            copied = dict(row)
            copied["sector_id"] = sector_map[row["sector_id"]]
            copied["line_code"] = line_map[row["line_code"]]
            copied["from_station_id"] = station_map[row["from_station_id"]]
            copied["to_station_id"] = station_map[row["to_station_id"]]
            combined["03_SECTORS.csv"].append(copied)
        for row in tables["04_LOCATION_SUPPLY.csv"][1]:
            copied = dict(row)
            copied["location_id"] = location(row["location_id"])
            copied["line_code"] = line_map[row["line_code"]]
            combined["04_LOCATION_SUPPLY.csv"].append(copied)
        for row in tables["05_BUFFER_LOCATION.csv"][1]:
            copied = dict(row)
            copied["nature_of_works"] = nature_map[row["nature_of_works"]]
            combined["05_BUFFER_LOCATION.csv"].append(copied)
        for row in tables["07_PROJECT_DETAILS.csv"][1]:
            copied = dict(row)
            copied["contract_number"] = contract_map[row["contract_number"]]
            copied["contract_description"] = f"{prefix} {row['contract_description']}"
            copied["nature_of_activity"] = nature_map[row["nature_of_activity"]]
            for key in (
                "contract_award_date",
                "contract_completion_date",
                "planned_completion_date",
            ):
                copied[key] = shifted(row[key])
            combined["07_PROJECT_DETAILS.csv"].append(copied)
        for row in tables["08_ACTIVITY_DETAILS.csv"][1]:
            copied = dict(row)
            copied["activity_id"] = activity_map[row["activity_id"]]
            copied["contract_number"] = contract_map[row["contract_number"]]
            copied["start_location_id"] = location(row["start_location_id"])
            copied["end_location_id"] = location(row["end_location_id"])
            copied["planned_start_date"] = shifted(row["planned_start_date"])
            if row["predecessor_activity_id"]:
                copied["predecessor_activity_id"] = activity_map[
                    row["predecessor_activity_id"]
                ]
            combined["08_ACTIVITY_DETAILS.csv"].append(copied)

    combined["06_PARAMETERS.csv"] = [
        {"key": "horizon_start", "value": target_start.isoformat()},
        {"key": "horizon_weeks", "value": str(maximum_horizon_weeks)},
    ]
    for name in FILES:
        rows = combined[name]
        random.Random(f"{args.seed}:{name}").shuffle(rows)
        write(output / name, fields[name], rows)


if __name__ == "__main__":
    main()
