from __future__ import annotations

import argparse
import json
from pathlib import Path

from nebula_ps1.evaluate import load_submission
from nebula_ps1.instance import Instance, load_instance
from nebula_ps1.staged import _scenario_b_cost_contributing_activities


def dependency_frontier(
    instance: Instance,
    submission_dir: str | Path,
    selected: set[str],
) -> dict[str, list[str]]:
    _, occupancy, _ = load_submission(submission_dir)
    contracts = {
        instance.activities[activity_id].contract_number for activity_id in selected
    }
    contract = {
        activity_id
        for activity_id, activity in instance.activities.items()
        if activity.contract_number in contracts and activity_id not in selected
    }
    precedence: set[str] = set()
    for activity_id, activity in instance.activities.items():
        predecessor = activity.predecessor_activity_id
        if predecessor and ((activity_id in selected) != (predecessor in selected)):
            precedence.add(activity_id if activity_id not in selected else predecessor)
    locations = {
        row.location_id for row in occupancy if row.activity_id in selected
    }
    footprint = {
        row.activity_id
        for row in occupancy
        if row.location_id in locations and row.activity_id not in selected
    }
    return {
        "contract": sorted(contract),
        "precedence": sorted(precedence),
        "footprint": sorted(footprint),
        "union": sorted(contract | precedence | footprint),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Measure dependencies outside the bounded Scenario C repair set."
    )
    parser.add_argument("data_dir", type=Path)
    parser.add_argument("submission_dir", type=Path)
    args = parser.parse_args()

    instance = load_instance(args.data_dir)
    expanded = set(
        _scenario_b_cost_contributing_activities(
            instance,
            args.submission_dir,
            expand_footprints=True,
            expand_contracts=True,
            expand_precedence=True,
            revisit_precedence_after_footprints=True,
            revisit_contracts_after_precedence=True,
            revisit_precedence_after_contracts=True,
            include_delays=True,
        )
    )
    frontier = dependency_frontier(instance, args.submission_dir, expanded)
    print(
        json.dumps(
            {
                "dataset_hash": instance.dataset_hash,
                "activity_count": len(instance.activities),
                "expanded_repair_count": len(expanded),
                "expanded_repair_activities": sorted(expanded),
                "frontier_counts": {
                    relation: len(activities)
                    for relation, activities in frontier.items()
                },
                "frontier_activities": frontier,
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
