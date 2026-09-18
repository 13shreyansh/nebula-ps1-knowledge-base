from __future__ import annotations

import argparse
import csv
from datetime import date, timedelta
from pathlib import Path


DATA_FILES = (
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
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or ()), list(reader)


def write(path: Path, fields: list[str], rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate an independent multi-activity partial-hint trade-off."
    )
    parser.add_argument("--base-data", required=True)
    parser.add_argument("--base-oracle", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--oracle-output", required=True)
    args = parser.parse_args()
    base_data = Path(args.base_data)
    base_oracle = Path(args.base_oracle)
    output = Path(args.output)
    oracle = Path(args.oracle_output)
    if output.exists() and any(output.iterdir()):
        raise ValueError(f"output directory must be empty: {output}")
    if oracle.exists() and any(oracle.iterdir()):
        raise ValueError(f"oracle directory must be empty: {oracle}")
    output.mkdir(parents=True, exist_ok=True)
    oracle.mkdir(parents=True, exist_ok=True)

    tables = {name: read(base_data / name) for name in DATA_FILES}
    parameters = {row["key"]: row["value"] for row in tables["06_PARAMETERS.csv"][1]}
    horizon_start = date.fromisoformat(parameters["horizon_start"])
    selected = {f"VXE{batch:02d}C3" for batch in range(1, 6)}
    three_access = {f"VXE{batch:02d}C3" for batch in range(1, 4)}
    removed_contracts = {f"K{activity_id}" for activity_id in selected}

    project_fields, projects = tables["07_PROJECT_DETAILS.csv"]
    projects = [
        row for row in projects if row["contract_number"] not in removed_contracts
    ]
    planned_week = 12
    planned = horizon_start + timedelta(days=7 * planned_week - 1)
    projects.append(
        {
            "contract_number": "KIRR",
            "contract_description": "Irregular workfront-coupled trade-off",
            "contract_award_date": "2031-06-01",
            "activity_type": "IrregularTradeoff",
            "nature_of_activity": "Non-live (Others)",
            "contract_priority": "3",
            "contract_completion_date": (
                horizon_start + timedelta(days=7 * 24 - 1)
            ).isoformat(),
            "planned_completion_date": planned.isoformat(),
            "number_of_workfronts": "1",
            "access_type": "C",
            "number_of_maximum_access_per_week": "1",
        }
    )

    activity_fields, activities = tables["08_ACTIVITY_DETAILS.csv"]
    for row in activities:
        if row["activity_id"] in selected:
            row["contract_number"] = "KIRR"
            row["activity_type"] = "IrregularTradeoff"
            row["activity_priority"] = "3"
            if row["activity_id"] in three_access:
                row["total_accesses"] = "3"

    for name, (fields, rows) in tables.items():
        if name == "07_PROJECT_DETAILS.csv":
            write(output / name, project_fields, projects)
        elif name == "08_ACTIVITY_DETAILS.csv":
            write(output / name, activity_fields, activities)
        else:
            write(output / name, fields, rows)

    access_fields, access_rows = read(base_oracle / "SCHEDULE_ACCESS.csv")
    occupancy_fields, occupancy_rows = read(base_oracle / "SCHEDULE_OCCUPANCY.csv")
    result_fields, result_rows = read(base_oracle / "RESULTS.csv")
    result_rows = [
        row for row in result_rows if row["contract_number"] not in removed_contracts
    ]

    footprint = (
        "SEC:LHX:HN3_HN4:EB",
        "PLAT:LHX:HN3:EB",
        "PLAT:LHX:HN4:EB",
    )
    added_weeks = {"VXE01C3": 13, "VXE02C3": 14, "VXE03C3": 15}
    for activity_id, week in added_weeks.items():
        group_by_location = {
            row["location_id"]: row["co_share_group"]
            for row in occupancy_rows
            if int(row["week"]) == week and row["location_id"] in footprint
        }
        if not group_by_location:
            group_by_location = {
                location_id: f"KIRR_W{week}" for location_id in footprint
            }
        elif set(group_by_location) != set(footprint):
            raise ValueError(f"base oracle has a partial week-{week} corridor group")
        access_rows.append(
            {
                "activity_id": activity_id,
                "access_seq": "3",
                "week": str(week),
                "eclo": "0",
                "access_night": "1",
            }
        )
        occupancy_rows.extend(
            {
                "activity_id": activity_id,
                "week": str(week),
                "location_id": location_id,
                "co_share_group": group_by_location[location_id],
            }
            for location_id in footprint
        )
    week = max(added_weeks.values())
    completion = horizon_start + timedelta(days=7 * week - 1)
    result_rows.append(
        {
            "scenario": "A",
            "contract_number": "KIRR",
            "simulated_completion_date": completion.isoformat(),
            "overrun_days": str((completion - planned).days),
        }
    )

    write(oracle / "SCHEDULE_ACCESS.csv", access_fields, access_rows)
    write(oracle / "SCHEDULE_OCCUPANCY.csv", occupancy_fields, occupancy_rows)
    write(oracle / "RESULTS.csv", result_fields, result_rows)


if __name__ == "__main__":
    main()
