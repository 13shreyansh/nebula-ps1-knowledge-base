from __future__ import annotations

import argparse
import csv
import shutil
from datetime import date, timedelta
from pathlib import Path


INPUT_FILES = (
    "01_LINES.csv",
    "02_STATIONS.csv",
    "03_SECTORS.csv",
    "04_LOCATION_SUPPLY.csv",
    "05_BUFFER_LOCATION.csv",
    "06_PARAMETERS.csv",
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
        description="Add a cross-contract predecessor to a post-expansion contract peer."
    )
    parser.add_argument("--base-data", required=True)
    parser.add_argument("--base-oracle", required=True)
    parser.add_argument("--base-incumbent", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--oracle-output", required=True)
    parser.add_argument("--incumbent-output", required=True)
    args = parser.parse_args()
    base_data = Path(args.base_data)
    base_oracle = Path(args.base_oracle)
    base_incumbent = Path(args.base_incumbent)
    output = Path(args.output)
    oracle = Path(args.oracle_output)
    incumbent = Path(args.incumbent_output)
    for path in (output, oracle, incumbent):
        if path.exists() and any(path.iterdir()):
            raise ValueError(f"output directory must be empty: {path}")
        path.mkdir(parents=True, exist_ok=True)

    for name in INPUT_FILES:
        shutil.copyfile(base_data / name, output / name)
    parameters = {row["key"]: row["value"] for row in read(base_data / "06_PARAMETERS.csv")[1]}
    horizon_start = date.fromisoformat(parameters["horizon_start"])
    horizon_weeks = int(parameters["horizon_weeks"])
    completion_limit = horizon_start + timedelta(days=7 * horizon_weeks - 1)

    project_fields, projects = read(base_data / "07_PROJECT_DETAILS.csv")
    template_project = next(row for row in projects if row["contract_number"] == "KCOMP")
    projects.append(
        {
            **template_project,
            "contract_number": "KPREPEER",
            "contract_description": "Predecessor of final contract peer",
            "contract_priority": "3",
            "contract_completion_date": completion_limit.isoformat(),
            "planned_completion_date": (
                horizon_start + timedelta(days=7 * 10 - 1)
            ).isoformat(),
            "number_of_workfronts": "1",
            "access_type": "C",
            "number_of_maximum_access_per_week": "1",
        }
    )
    write(output / "07_PROJECT_DETAILS.csv", project_fields, projects)

    activity_fields, activities = read(base_data / "08_ACTIVITY_DETAILS.csv")
    follow = next(row for row in activities if row["activity_id"] == "FOLLOW")
    for row in activities:
        if row["activity_id"] == "PEER":
            row["predecessor_activity_id"] = "PREPEER"
    activities.append(
        {
            **follow,
            "activity_id": "PREPEER",
            "contract_number": "KPREPEER",
            "total_accesses": "1",
            "planned_start_date": horizon_start.isoformat(),
            "predecessor_activity_id": "",
            "activity_priority": "1",
        }
    )
    write(output / "08_ACTIVITY_DETAILS.csv", activity_fields, activities)

    def extend_submission(source: Path, target: Path, predecessor_week: int) -> None:
        access_fields, access_rows = read(source / "SCHEDULE_ACCESS.csv")
        occupancy_fields, occupancy_rows = read(source / "SCHEDULE_OCCUPANCY.csv")
        result_fields, result_rows = read(source / "RESULTS.csv")
        access_rows.append(
            {
                "activity_id": "PREPEER",
                "access_seq": "1",
                "week": str(predecessor_week),
                "eclo": "0",
                "access_night": "1",
            }
        )
        follow_locations = sorted(
            {
                row["location_id"]
                for row in occupancy_rows
                if row["activity_id"] == "FOLLOW"
            }
        )
        occupancy_rows.extend(
            {
                "activity_id": "PREPEER",
                "week": str(predecessor_week),
                "location_id": location_id,
                "co_share_group": f"PREPEER_W{predecessor_week:02d}",
            }
            for location_id in follow_locations
        )
        completion = horizon_start + timedelta(days=7 * predecessor_week - 1)
        planned = horizon_start + timedelta(days=7 * 10 - 1)
        result_rows.append(
            {
                "scenario": "C",
                "contract_number": "KPREPEER",
                "simulated_completion_date": completion.isoformat(),
                "overrun_days": str(max(0, (completion - planned).days)),
            }
        )
        write(target / "SCHEDULE_ACCESS.csv", access_fields, access_rows)
        write(target / "SCHEDULE_OCCUPANCY.csv", occupancy_fields, occupancy_rows)
        write(target / "RESULTS.csv", result_fields, result_rows)

    extend_submission(base_oracle, oracle, 3)
    extend_submission(base_incumbent, incumbent, 5)


if __name__ == "__main__":
    main()
