from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path

from nebula_ps1.evaluate import load_submission
from nebula_ps1.instance import load_instance


def write_rows(path: Path, fields: tuple[str, ...], rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True, type=Path)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--activity", required=True)
    args = parser.parse_args()

    instance = load_instance(args.data)
    access, occupancy, _ = load_submission(args.source)
    target = sorted(
        (row for row in access if row.activity_id == args.activity),
        key=lambda row: row.week,
    )
    if len(target) != 3 or any(row.eclo for row in target):
        raise ValueError("target must have exactly three standard accesses")

    activities_by_week: dict[int, set[str]] = defaultdict(set)
    for row in access:
        activities_by_week[row.week].add(row.activity_id)
    if any(len(activity_ids) != 1 for activity_ids in activities_by_week.values()):
        raise ValueError("candidate compactor requires one activity per occupied week")
    occupied_weeks = sorted(activities_by_week)
    if occupied_weeks != list(range(occupied_weeks[0], occupied_weeks[-1] + 1)):
        raise ValueError("candidate compactor requires a gap-free occupied horizon")

    removed_week = target[0].week
    retained_target_weeks = {row.week for row in target[1:]}
    retained_weeks = [week for week in occupied_weeks if week != removed_week]
    week_map = {
        old_week: new_week
        for new_week, old_week in enumerate(retained_weeks, occupied_weeks[0])
    }
    output_access = []
    by_activity: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in access:
        if row.activity_id == args.activity and row.week == removed_week:
            continue
        transformed = {
            "activity_id": row.activity_id,
            "access_seq": row.access_seq,
            "week": week_map[row.week],
            "eclo": int(
                row.activity_id == args.activity and row.week in retained_target_weeks
            ),
            "access_night": row.access_night,
        }
        by_activity[row.activity_id].append(transformed)
    for activity_id in sorted(by_activity):
        for access_seq, row in enumerate(
            sorted(by_activity[activity_id], key=lambda item: int(item["week"])), 1
        ):
            row["access_seq"] = access_seq
            output_access.append(row)

    output_occupancy = [
        {
            "activity_id": row.activity_id,
            "week": week_map[row.week],
            "location_id": row.location_id,
            "co_share_group": row.co_share_group,
        }
        for row in occupancy
        if not (row.activity_id == args.activity and row.week == removed_week)
    ]

    completion_week = {
        activity_id: max(int(row["week"]) for row in rows)
        for activity_id, rows in by_activity.items()
    }
    completion_by_contract: dict[str, int] = defaultdict(int)
    for activity_id, week in completion_week.items():
        contract = instance.activities[activity_id].contract_number
        completion_by_contract[contract] = max(completion_by_contract[contract], week)
    output_results = []
    for contract in sorted(instance.projects):
        project = instance.projects[contract]
        completion = instance.completion_date(completion_by_contract[contract])
        output_results.append(
            {
                "scenario": "C",
                "contract_number": contract,
                "simulated_completion_date": completion.isoformat(),
                "overrun_days": max(0, (completion - project.planned_completion_date).days),
            }
        )

    args.output.mkdir(parents=True, exist_ok=True)
    write_rows(
        args.output / "SCHEDULE_ACCESS.csv",
        ("activity_id", "access_seq", "week", "eclo", "access_night"),
        output_access,
    )
    write_rows(
        args.output / "SCHEDULE_OCCUPANCY.csv",
        ("activity_id", "week", "location_id", "co_share_group"),
        output_occupancy,
    )
    write_rows(
        args.output / "RESULTS.csv",
        ("scenario", "contract_number", "simulated_completion_date", "overrun_days"),
        output_results,
    )


if __name__ == "__main__":
    main()
