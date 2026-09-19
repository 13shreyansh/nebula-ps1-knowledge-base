from __future__ import annotations

import argparse
import itertools
import json
from collections import Counter
from pathlib import Path

from nebula_ps1.closure import _blocked_locations, _buffer_locations
from nebula_ps1.decomposed import (
    DECOMPOSITION_COUPLING_INVENTORY_VERSION,
    independent_activity_components,
)
from nebula_ps1.instance import FILES, load_instance
from nebula_ps1.topology import (
    activity_footprint,
    affects_interchange_cross_line,
    split_sector_location,
)


def _input_directories(root: Path) -> list[Path]:
    required = set(FILES.values())
    return sorted(
        path
        for path in root.iterdir()
        if path.is_dir() and required <= {child.name for child in path.iterdir()}
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Audit decomposition boundaries against encoded cross-activity rules."
    )
    parser.add_argument("--fixtures", default="fixtures")
    parser.add_argument("--public-data")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    fixture_root = Path(args.fixtures)
    datasets = _input_directories(fixture_root)
    if args.public_data:
        datasets.append(Path(args.public_data))
    family_counts: Counter[str] = Counter()
    dataset_reports: list[dict[str, object]] = []
    violations: list[dict[str, object]] = []
    total_policy_cases = 0
    total_pairs_checked = 0

    for data in datasets:
        instance = load_instance(data)
        activity_ids = sorted(instance.activities)
        work = {
            activity_id: set(
                activity_footprint(instance, instance.activities[activity_id])
            )
            for activity_id in activity_ids
        }
        blocked = {
            activity_id: _blocked_locations(instance, {activity_id})
            for activity_id in activity_ids
        }
        buffers = {
            activity_id: _buffer_locations(instance, {activity_id})
            for activity_id in activity_ids
        }
        lines = {
            activity_id: split_sector_location(
                instance.activities[activity_id].start_location_id
            )[0]
            for activity_id in activity_ids
        }
        crossover = {
            activity_id: affects_interchange_cross_line(
                instance, instance.activities[activity_id]
            )
            for activity_id in activity_ids
        }
        policy_components: dict[str, list[int]] = {}
        for scenario in ("A", "B", "C"):
            for strict in (False, True):
                total_policy_cases += 1
                components = independent_activity_components(
                    instance,
                    scenario,
                    forbid_buffer_overlap=strict,
                )
                policy_key = f"{scenario}/strict={str(strict).lower()}"
                policy_components[policy_key] = sorted(
                    (len(component) for component in components), reverse=True
                )
                component_of = {
                    activity_id: index
                    for index, component in enumerate(components)
                    for activity_id in component
                }
                for first, second in itertools.combinations(activity_ids, 2):
                    total_pairs_checked += 1
                    first_activity = instance.activities[first]
                    second_activity = instance.activities[second]
                    families: list[str] = []
                    if first_activity.contract_number == second_activity.contract_number:
                        families.append("same_contract")
                    if (
                        first_activity.predecessor_activity_id == second
                        or second_activity.predecessor_activity_id == first
                    ):
                        families.append("predecessor")
                    if work[first] & work[second]:
                        families.append("shared_location_group_supply")
                    if work[first] & blocked[second] or work[second] & blocked[first]:
                        families.append("directional_closure")
                    if strict and buffers[first] & buffers[second]:
                        families.append("strict_buffer_overlap")
                    if scenario == "C" and lines[first] == lines[second]:
                        families.append("scenario_c_same_line_window")
                    if scenario == "C" and (crossover[first] or crossover[second]):
                        families.append("scenario_c_live_all_line_window")
                    family_counts.update(families)
                    if families and component_of[first] != component_of[second]:
                        violations.append(
                            {
                                "dataset": str(data),
                                "scenario": scenario,
                                "strict_buffer_overlap": strict,
                                "first": first,
                                "second": second,
                                "families": families,
                            }
                        )
        dataset_reports.append(
            {
                "dataset": str(data),
                "dataset_hash": instance.dataset_hash,
                "activities": len(activity_ids),
                "policy_component_sizes": policy_components,
            }
        )

    report = {
        "scope": "encoded local coupling audit; not organizer-validator equivalence",
        "coupling_inventory_version": DECOMPOSITION_COUPLING_INVENTORY_VERSION,
        "dataset_count": len(datasets),
        "policy_case_count": total_policy_cases,
        "activity_pairs_checked_with_repetition": total_pairs_checked,
        "coupling_observation_counts": dict(sorted(family_counts.items())),
        "violation_count": len(violations),
        "violations": violations,
        "datasets": dataset_reports,
        "portal_used": False,
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({key: report[key] for key in report if key != "datasets"}, indent=2))
    if violations:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
