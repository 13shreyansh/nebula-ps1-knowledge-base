from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path

from .evaluate import load_submission
from .instance import Instance


def relabel_submission_scenario(
    instance: Instance,
    source_dir: str | Path,
    output_dir: str | Path,
    scenario: str,
) -> None:
    """Reuse an unchanged schedule and recompute its scenario result rows.

    This is a deterministic fallback operation, not a feasibility claim. The
    generated output must still pass the independent checker for the new scenario.
    """

    if scenario not in {"A", "B", "C"}:
        raise ValueError(f"unknown scenario: {scenario}")
    access_rows, occupancy_rows, _ = load_submission(source_dir)
    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)

    with (output_root / "SCHEDULE_ACCESS.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=("activity_id", "access_seq", "week", "eclo", "access_night")
        )
        writer.writeheader()
        writer.writerows(
            {
                "activity_id": row.activity_id,
                "access_seq": row.access_seq,
                "week": row.week,
                "eclo": row.eclo,
                "access_night": row.access_night,
            }
            for row in access_rows
        )

    with (output_root / "SCHEDULE_OCCUPANCY.csv").open(
        "w", newline="", encoding="utf-8"
    ) as handle:
        writer = csv.DictWriter(
            handle, fieldnames=("activity_id", "week", "location_id", "co_share_group")
        )
        writer.writeheader()
        writer.writerows(
            {
                "activity_id": row.activity_id,
                "week": row.week,
                "location_id": row.location_id,
                "co_share_group": row.co_share_group,
            }
            for row in occupancy_rows
        )

    completion_by_activity: dict[str, int] = defaultdict(int)
    for row in access_rows:
        completion_by_activity[row.activity_id] = max(
            completion_by_activity[row.activity_id], row.week
        )
    activities_by_contract: dict[str, list[str]] = defaultdict(list)
    for activity_id, activity in instance.activities.items():
        activities_by_contract[activity.contract_number].append(activity_id)

    with (output_root / "RESULTS.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=(
                "scenario",
                "contract_number",
                "simulated_completion_date",
                "overrun_days",
            ),
        )
        writer.writeheader()
        for contract_number in sorted(instance.projects):
            project = instance.projects[contract_number]
            completion_week = max(
                completion_by_activity[activity_id]
                for activity_id in activities_by_contract[contract_number]
            )
            completion_date = instance.completion_date(completion_week)
            writer.writerow(
                {
                    "scenario": scenario,
                    "contract_number": contract_number,
                    "simulated_completion_date": completion_date.isoformat(),
                    "overrun_days": max(
                        0, (completion_date - project.planned_completion_date).days
                    ),
                }
            )
