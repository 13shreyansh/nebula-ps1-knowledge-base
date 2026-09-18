from __future__ import annotations

import argparse
import csv
import random
import shutil
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path


INSTANCE_FILES = (
    "01_LINES.csv",
    "02_STATIONS.csv",
    "03_SECTORS.csv",
    "04_LOCATION_SUPPLY.csv",
    "05_BUFFER_LOCATION.csv",
    "06_PARAMETERS.csv",
    "07_PROJECT_DETAILS.csv",
    "08_ACTIVITY_DETAILS.csv",
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
    parser.add_argument("--oracle-submission", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--seed", type=int, default=20260919)
    parser.add_argument(
        "--mutate-demand",
        action="store_true",
        help="reduce selected workloads, advance starts, and add oracle-safe predecessors",
    )
    args = parser.parse_args()

    source = Path(args.source)
    oracle = Path(args.oracle_submission)
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)

    _, access = read_rows(oracle / "SCHEDULE_ACCESS.csv")
    _, occupancy = read_rows(oracle / "SCHEDULE_OCCUPANCY.csv")
    activity_weeks: dict[str, list[int]] = defaultdict(list)
    for row in access:
        activity_weeks[row["activity_id"]].append(int(row["week"]))
    groups: dict[tuple[str, int], set[str]] = defaultdict(set)
    for row in occupancy:
        groups[(row["location_id"], int(row["week"]))].add(row["co_share_group"])
    required_capacity: dict[str, int] = defaultdict(int)
    for (location_id, _), labels in groups.items():
        required_capacity[location_id] = max(required_capacity[location_id], len(labels))

    for name in INSTANCE_FILES:
        if name not in {"04_LOCATION_SUPPLY.csv", "07_PROJECT_DETAILS.csv", "08_ACTIVITY_DETAILS.csv"}:
            shutil.copy2(source / name, output / name)

    supply_fields, supply_rows = read_rows(source / "04_LOCATION_SUPPLY.csv")
    for row in supply_rows:
        original = int(row["supply_capacity"])
        oracle_need = max(1, required_capacity.get(row["location_id"], 1))
        row["supply_capacity"] = str(min(original, oracle_need))
    random.Random(f"{args.seed}:supply-rows").shuffle(supply_rows)
    write_rows(output / "04_LOCATION_SUPPLY.csv", supply_fields, supply_rows)

    project_fields, project_rows = read_rows(source / "07_PROJECT_DETAILS.csv")
    project_priorities = [row["contract_priority"] for row in project_rows]
    random.Random(f"{args.seed}:contract-priority").shuffle(project_priorities)
    for row, priority in zip(project_rows, project_priorities, strict=True):
        row["contract_priority"] = priority
    random.Random(f"{args.seed}:project-rows").shuffle(project_rows)
    write_rows(output / "07_PROJECT_DETAILS.csv", project_fields, project_rows)

    activity_fields, activity_rows = read_rows(source / "08_ACTIVITY_DETAILS.csv")
    activity_priorities = [row["activity_priority"] for row in activity_rows]
    random.Random(f"{args.seed}:activity-priority").shuffle(activity_priorities)
    for row, priority in zip(activity_rows, activity_priorities, strict=True):
        row["activity_priority"] = priority
    if args.mutate_demand:
        demand_rng = random.Random(f"{args.seed}:demand")
        chronological = sorted(
            activity_weeks,
            key=lambda activity_id: (
                min(activity_weeks[activity_id]),
                max(activity_weeks[activity_id]),
                activity_id,
            ),
        )
        added_predecessors = 0
        for row in sorted(activity_rows, key=lambda item: item["activity_id"]):
            activity_id = row["activity_id"]
            if int(row["total_accesses"]) > 1 and demand_rng.random() < 0.35:
                row["total_accesses"] = str(int(row["total_accesses"]) - 1)
            start = date.fromisoformat(row["planned_start_date"])
            row["planned_start_date"] = (
                start - timedelta(days=7 * demand_rng.randint(0, 2))
            ).isoformat()
            if row["predecessor_activity_id"] or added_predecessors >= 10:
                continue
            successor_start = min(activity_weeks[activity_id])
            candidates = [
                candidate
                for candidate in chronological
                if candidate != activity_id
                and max(activity_weeks[candidate]) < successor_start
            ]
            if candidates and demand_rng.random() < 0.5:
                row["predecessor_activity_id"] = demand_rng.choice(candidates)
                added_predecessors += 1
    random.Random(f"{args.seed}:activity-rows").shuffle(activity_rows)
    write_rows(output / "08_ACTIVITY_DETAILS.csv", activity_fields, activity_rows)


if __name__ == "__main__":
    main()
