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
        description="Add a provable nonzero A/B/C trade-off to the dense holdout."
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

    tables: dict[str, tuple[list[str], list[dict[str, str]]]] = {
        name: read(base_data / name) for name in DATA_FILES
    }
    parameter_rows = tables["06_PARAMETERS.csv"][1]
    parameters = {row["key"]: row["value"] for row in parameter_rows}
    horizon_start = date.fromisoformat(parameters["horizon_start"])
    planned_completion = horizon_start + timedelta(days=7 * 2 - 1)

    project_fields, projects = tables["07_PROJECT_DETAILS.csv"]
    projects.append(
        {
            "contract_number": "KWTIGHT",
            "contract_description": "Held-out nonzero trade-off",
            "contract_award_date": "2031-06-01",
            "activity_type": "HeldoutTradeoff",
            "nature_of_activity": "Non-live (Others)",
            "contract_priority": "3",
            "contract_completion_date": (planned_completion + timedelta(days=35)).isoformat(),
            "planned_completion_date": planned_completion.isoformat(),
            "number_of_workfronts": "1",
            "access_type": "C",
            "number_of_maximum_access_per_week": "3",
        }
    )
    activity_fields, activities = tables["08_ACTIVITY_DETAILS.csv"]
    activities.append(
        {
            "activity_id": "WTIGHT",
            "contract_number": "KWTIGHT",
            "activity_type": "HeldoutTradeoff",
            "start_location_id": "SEC:LHX:HN5_HN6:EB",
            "end_location_id": "SEC:LHX:HN5_HN6:EB",
            "total_accesses": "3",
            "planned_start_date": horizon_start.isoformat(),
            "predecessor_activity_id": "",
            "activity_priority": "3",
        }
    )
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
    for sequence, week in enumerate((1, 2, 3), start=1):
        access_rows.append(
            {
                "activity_id": "WTIGHT",
                "access_seq": str(sequence),
                "week": str(week),
                "eclo": "0",
                "access_night": "1",
            }
        )
        for location_id in (
            "SEC:LHX:HN5_HN6:EB",
            "PLAT:LHX:HN5:EB",
            "PLAT:LHX:HN6:EB",
        ):
            occupancy_rows.append(
                {
                    "activity_id": "WTIGHT",
                    "week": str(week),
                    "location_id": location_id,
                    "co_share_group": f"WT{week}",
                }
            )
    completion = horizon_start + timedelta(days=7 * 3 - 1)
    result_rows.append(
        {
            "scenario": "A",
            "contract_number": "KWTIGHT",
            "simulated_completion_date": completion.isoformat(),
            "overrun_days": "7",
        }
    )
    write(oracle / "SCHEDULE_ACCESS.csv", access_fields, access_rows)
    write(oracle / "SCHEDULE_OCCUPANCY.csv", occupancy_fields, occupancy_rows)
    write(oracle / "RESULTS.csv", result_fields, result_rows)


if __name__ == "__main__":
    main()
