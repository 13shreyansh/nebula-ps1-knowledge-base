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
        description="Generate a dense trade-off coupled through C's ECLO window."
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
    removed_activities = {f"VXE{batch:02d}C3" for batch in range(1, 7)}
    removed_contracts = {f"K{activity_id}" for activity_id in removed_activities}

    project_fields, projects = tables["07_PROJECT_DETAILS.csv"]
    projects = [
        row for row in projects if row["contract_number"] not in removed_contracts
    ]
    activity_fields, activities = tables["08_ACTIVITY_DETAILS.csv"]
    activities = [
        row for row in activities if row["activity_id"] not in removed_activities
    ]

    tight_specs = (
        ("WCOUPLED1", "KWCOUPLED1", 1, 2, (1, 2, 3)),
        ("WCOUPLED2", "KWCOUPLED2", 5, 6, (5, 6, 7)),
    )
    for activity_id, contract, start_week, target_week, _ in tight_specs:
        planned_completion = horizon_start + timedelta(days=7 * target_week - 1)
        projects.append(
            {
                "contract_number": contract,
                "contract_description": f"Coupled ECLO-window trade-off {activity_id}",
                "contract_award_date": "2031-06-01",
                "activity_type": "CoupledTradeoff",
                "nature_of_activity": "Non-live (Others)",
                "contract_priority": "1",
                "contract_completion_date": (planned_completion + timedelta(days=35)).isoformat(),
                "planned_completion_date": planned_completion.isoformat(),
                "number_of_workfronts": "1",
                "access_type": "C",
                "number_of_maximum_access_per_week": "3",
            }
        )
        activities.append(
            {
                "activity_id": activity_id,
                "contract_number": contract,
                "activity_type": "CoupledTradeoff",
                "start_location_id": "SEC:LHX:HN3_HN4:EB",
                "end_location_id": "SEC:LHX:HN3_HN4:EB",
                "total_accesses": "3",
                "planned_start_date": (
                    horizon_start + timedelta(days=7 * (start_week - 1))
                ).isoformat(),
                "predecessor_activity_id": "",
                "activity_priority": "1",
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
    access_rows = [row for row in access_rows if row["activity_id"] not in removed_activities]
    occupancy_rows = [
        row for row in occupancy_rows if row["activity_id"] not in removed_activities
    ]
    result_rows = [
        row for row in result_rows if row["contract_number"] not in removed_contracts
    ]
    group_lookup: dict[tuple[int, str], str] = {}
    for row in occupancy_rows:
        if row["location_id"] in {
            "SEC:LHX:HN3_HN4:EB",
            "PLAT:LHX:HN3:EB",
            "PLAT:LHX:HN4:EB",
        }:
            group_lookup[(int(row["week"]), row["location_id"])] = row[
                "co_share_group"
            ]

    footprint = (
        "SEC:LHX:HN3_HN4:EB",
        "PLAT:LHX:HN3:EB",
        "PLAT:LHX:HN4:EB",
    )
    for activity_id, contract, _, target_week, weeks in tight_specs:
        for sequence, week in enumerate(weeks, start=1):
            access_rows.append(
                {
                    "activity_id": activity_id,
                    "access_seq": str(sequence),
                    "week": str(week),
                    "eclo": "0",
                    "access_night": "1",
                }
            )
            for location_id in footprint:
                occupancy_rows.append(
                    {
                        "activity_id": activity_id,
                        "week": str(week),
                        "location_id": location_id,
                        "co_share_group": group_lookup[(week, location_id)],
                    }
                )
        completion = horizon_start + timedelta(days=7 * max(weeks) - 1)
        target = horizon_start + timedelta(days=7 * target_week - 1)
        result_rows.append(
            {
                "scenario": "A",
                "contract_number": contract,
                "simulated_completion_date": completion.isoformat(),
                "overrun_days": str((completion - target).days),
            }
        )

    write(oracle / "SCHEDULE_ACCESS.csv", access_fields, access_rows)
    write(oracle / "SCHEDULE_OCCUPANCY.csv", occupancy_fields, occupancy_rows)
    write(oracle / "RESULTS.csv", result_fields, result_rows)


if __name__ == "__main__":
    main()
