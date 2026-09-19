from __future__ import annotations

import argparse
import itertools
import json
from collections import Counter
from pathlib import Path

from nebula_ps1.closure import _blocked_locations, _buffer_locations
from nebula_ps1.decomposed import (
    DECOMPOSITION_COUPLING_INVENTORY,
    DECOMPOSITION_COUPLING_INVENTORY_VERSION,
    _activity_interaction_reasons,
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


def _component_count(
    activity_ids: list[str],
    edges: list[tuple[str, str, tuple[str, ...]]],
    *,
    include_reasons: set[str],
) -> int:
    parent = {activity_id: activity_id for activity_id in activity_ids}

    def find(activity_id: str) -> str:
        while parent[activity_id] != activity_id:
            parent[activity_id] = parent[parent[activity_id]]
            activity_id = parent[activity_id]
        return activity_id

    def union(first: str, second: str) -> None:
        first_root, second_root = find(first), find(second)
        if first_root != second_root:
            parent[second_root] = first_root

    for first, second, reasons in edges:
        if include_reasons.intersection(reasons):
            union(first, second)
    return len({find(activity_id) for activity_id in activity_ids})


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Quantify conservative overlap in decomposition graph reasons."
    )
    parser.add_argument("--fixtures", default="fixtures")
    parser.add_argument("--public-data")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    datasets = _input_directories(Path(args.fixtures))
    if args.public_data:
        datasets.append(Path(args.public_data))
    declared_reasons = set(DECOMPOSITION_COUPLING_INVENTORY)
    reason_edges: Counter[str] = Counter()
    exclusive_edges: Counter[str] = Counter()
    signature_counts: Counter[str] = Counter()
    cardinality_counts: Counter[str] = Counter()
    per_reason = {
        reason: {
            "standalone_component_reduction": 0,
            "marginal_component_increase_when_removed": 0,
            "policy_cases_with_marginal_effect": 0,
        }
        for reason in sorted(declared_reasons)
    }
    policy_case_count = 0
    pair_checks = 0
    activity_slots = 0
    full_components_total = 0

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
        for scenario in ("A", "B", "C"):
            for strict in (False, True):
                policy_case_count += 1
                activity_slots += len(activity_ids)
                edges: list[tuple[str, str, tuple[str, ...]]] = []
                for first, second in itertools.combinations(activity_ids, 2):
                    pair_checks += 1
                    reasons = _activity_interaction_reasons(
                        instance,
                        scenario,
                        first,
                        second,
                        forbid_buffer_overlap=strict,
                        work=work,
                        blocked=blocked,
                        buffers=buffers,
                        lines=lines,
                        crossover=crossover,
                    )
                    unknown = set(reasons) - declared_reasons
                    if unknown:
                        raise RuntimeError(
                            f"undeclared graph reasons for {data}: {sorted(unknown)}"
                        )
                    if not reasons:
                        cardinality_counts["0"] += 1
                        continue
                    edges.append((first, second, reasons))
                    cardinality_counts[str(len(reasons))] += 1
                    signature_counts["+".join(sorted(reasons))] += 1
                    reason_edges.update(reasons)
                    if len(reasons) == 1:
                        exclusive_edges[reasons[0]] += 1

                full_components = _component_count(
                    activity_ids,
                    edges,
                    include_reasons=declared_reasons,
                )
                full_components_total += full_components
                for reason in sorted(declared_reasons):
                    standalone_components = _component_count(
                        activity_ids,
                        edges,
                        include_reasons={reason},
                    )
                    without_components = _component_count(
                        activity_ids,
                        edges,
                        include_reasons=declared_reasons - {reason},
                    )
                    per_reason[reason]["standalone_component_reduction"] += (
                        len(activity_ids) - standalone_components
                    )
                    marginal_increase = without_components - full_components
                    per_reason[reason][
                        "marginal_component_increase_when_removed"
                    ] += marginal_increase
                    if marginal_increase:
                        per_reason[reason]["policy_cases_with_marginal_effect"] += 1

    for reason in sorted(declared_reasons):
        per_reason[reason]["edge_occurrences"] = reason_edges[reason]
        per_reason[reason]["exclusive_edge_occurrences"] = exclusive_edges[reason]

    report = {
        "scope": (
            "encoded local graph-conservatism diagnostic; counts do not prove an "
            "edge safe to remove"
        ),
        "coupling_inventory_version": DECOMPOSITION_COUPLING_INVENTORY_VERSION,
        "dataset_count": len(datasets),
        "policy_case_count": policy_case_count,
        "activity_pair_checks_with_repetition": pair_checks,
        "activity_slots_across_policy_cases": activity_slots,
        "full_graph_components_total": full_components_total,
        "full_graph_component_reduction": activity_slots - full_components_total,
        "pair_reason_cardinality_counts": dict(sorted(cardinality_counts.items())),
        "reason_signature_counts": dict(sorted(signature_counts.items())),
        "per_reason": per_reason,
        "portal_used": False,
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
