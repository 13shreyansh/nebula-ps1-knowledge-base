from __future__ import annotations

import argparse
import csv
import shutil
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
        description="Generate a cross-module, cross-line Scenario C trade-off."
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
    horizon_weeks = int(parameters["horizon_weeks"])

    selected = {"R0103", "R0206", "R0303", "R0406", "R0503"}
    empty_contracts = {"Z0103", "Z0205", "Z0303", "Z0405", "Z0503"}
    planned_week = 13
    planned = horizon_start + timedelta(days=7 * planned_week - 1)

    project_fields, projects = tables["07_PROJECT_DETAILS.csv"]
    projects = [
        row for row in projects if row["contract_number"] not in empty_contracts
    ]
    projects.append(
        {
            "contract_number": "KMM",
            "contract_description": "Cross-module workfront trade-off",
            "contract_award_date": "2030-06-01",
            "activity_type": "MultimoduleTradeoff",
            "nature_of_activity": "Non-live (Others)",
            "contract_priority": "3",
            "contract_completion_date": (
                horizon_start + timedelta(days=7 * horizon_weeks - 1)
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
            row["contract_number"] = "KMM"
            row["activity_type"] = "MultimoduleTradeoff"
            row["total_accesses"] = "3"
            row["planned_start_date"] = horizon_start.isoformat()
            row["predecessor_activity_id"] = ""
            row["activity_priority"] = "3"

    for name, (fields, rows) in tables.items():
        if name == "07_PROJECT_DETAILS.csv":
            write(output / name, project_fields, projects)
        elif name == "08_ACTIVITY_DETAILS.csv":
            write(output / name, activity_fields, activities)
        else:
            shutil.copyfile(base_data / name, output / name)

    access_fields, base_access = read(base_oracle / "SCHEDULE_ACCESS.csv")
    occupancy_fields, base_occupancy = read(base_oracle / "SCHEDULE_OCCUPANCY.csv")
    result_fields, base_results = read(base_oracle / "RESULTS.csv")

    footprint_by_activity = {
        activity_id: sorted(
            {
                row["location_id"]
                for row in base_occupancy
                if row["activity_id"] == activity_id
            }
        )
        for activity_id in selected
    }
    access_rows: list[dict[str, object]] = [
        row for row in base_access if row["activity_id"] not in selected
    ]
    occupancy_rows: list[dict[str, object]] = [
        row for row in base_occupancy if row["activity_id"] not in selected
    ]

    schedule = {
        "R0103": ((1, 1), (2, 1)),
        "R0206": ((4, 1), (5, 1)),
        "R0303": ((3, 0), (6, 0), (7, 0)),
        "R0503": ((8, 0), (9, 0), (12, 0)),
        "R0406": ((10, 0), (11, 0), (13, 0)),
    }
    for activity_id, placements in schedule.items():
        for access_seq, (week, eclo) in enumerate(placements, start=1):
            access_rows.append(
                {
                    "activity_id": activity_id,
                    "access_seq": access_seq,
                    "week": week,
                    "eclo": eclo,
                    "access_night": 1,
                }
            )
            existing_groups = {
                row["location_id"]: row["co_share_group"]
                for row in occupancy_rows
                if int(row["week"]) == week
                and row["location_id"] in footprint_by_activity[activity_id]
            }
            occupancy_rows.extend(
                {
                    "activity_id": activity_id,
                    "week": week,
                    "location_id": location_id,
                    "co_share_group": existing_groups.get(
                        location_id, f"KMM_{activity_id}_W{week:02d}"
                    ),
                }
                for location_id in footprint_by_activity[activity_id]
            )

    result_rows: list[dict[str, object]] = []
    for row in base_results:
        if row["contract_number"] in empty_contracts:
            continue
        copied = dict(row)
        copied["scenario"] = "C"
        result_rows.append(copied)
    result_rows.append(
        {
            "scenario": "C",
            "contract_number": "KMM",
            "simulated_completion_date": planned.isoformat(),
            "overrun_days": "0",
        }
    )

    write(oracle / "SCHEDULE_ACCESS.csv", access_fields, access_rows)
    write(oracle / "SCHEDULE_OCCUPANCY.csv", occupancy_fields, occupancy_rows)
    write(oracle / "RESULTS.csv", result_fields, result_rows)


if __name__ == "__main__":
    main()
