from __future__ import annotations

import argparse
import csv
import shutil
from pathlib import Path


COPIED_FILES = (
    "01_LINES.csv",
    "02_STATIONS.csv",
    "03_SECTORS.csv",
    "04_LOCATION_SUPPLY.csv",
    "05_BUFFER_LOCATION.csv",
    "06_PARAMETERS.csv",
)


def read_rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or ()), list(reader)


def write_rows(path: Path, fields: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument(
        "--activities",
        required=True,
        help="comma-separated activity IDs; predecessor closure is included automatically",
    )
    args = parser.parse_args()

    source = Path(args.source)
    output = Path(args.output)
    requested = {item.strip() for item in args.activities.split(",") if item.strip()}
    if not requested:
        raise ValueError("at least one activity ID is required")

    activity_fields, activity_rows = read_rows(source / "08_ACTIVITY_DETAILS.csv")
    activities = {row["activity_id"]: row for row in activity_rows}
    unknown = sorted(requested - set(activities))
    if unknown:
        raise ValueError(f"unknown activities: {unknown}")

    selected = set(requested)
    pending = list(requested)
    while pending:
        predecessor = activities[pending.pop()]["predecessor_activity_id"]
        if predecessor and predecessor not in selected:
            selected.add(predecessor)
            pending.append(predecessor)

    project_fields, project_rows = read_rows(source / "07_PROJECT_DETAILS.csv")
    selected_contracts = {activities[activity_id]["contract_number"] for activity_id in selected}
    chosen_projects = sorted(
        (row for row in project_rows if row["contract_number"] in selected_contracts),
        key=lambda row: row["contract_number"],
    )
    chosen_activities = [activities[activity_id] for activity_id in sorted(selected)]

    output.mkdir(parents=True, exist_ok=True)
    for name in COPIED_FILES:
        shutil.copy2(source / name, output / name)
    write_rows(output / "07_PROJECT_DETAILS.csv", project_fields, chosen_projects)
    write_rows(output / "08_ACTIVITY_DETAILS.csv", activity_fields, chosen_activities)


if __name__ == "__main__":
    main()
