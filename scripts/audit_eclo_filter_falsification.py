from __future__ import annotations

import csv
import itertools
import json
import tempfile
from collections import defaultdict
from pathlib import Path

from nebula_ps1.closure import screen_closures
from nebula_ps1.eclo_compact import (
    _affected_eclo_lines,
    _write_candidate,
    best_serialized_eclo_compaction_sequence,
)
from nebula_ps1.evaluate import Evaluation, evaluate_submission, load_submission
from nebula_ps1.instance import Instance, load_instance


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "fixtures" / "independent_eclo_multipass_v1"
SOURCE = ROOT / "fixtures" / "independent_eclo_multipass_v1_source_c"
LIVE_DATA = ROOT / "fixtures" / "independent_multi_bridge_scale_v1"
LIVE_SOURCE = ROOT / "runs" / "independent_multi_bridge_scale_v1_c_compaction_controller"


def _write(path: Path, fields: tuple[str, ...], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _permuted_source(instance: Instance, order: tuple[str, ...], output: Path) -> None:
    _, template_occupancy, _ = load_submission(SOURCE)
    locations_by_activity: dict[str, set[str]] = defaultdict(set)
    for row in template_occupancy:
        locations_by_activity[row.activity_id].add(row.location_id)
    access: list[dict[str, object]] = []
    occupancy: list[dict[str, object]] = []
    results: list[dict[str, object]] = []
    for position, activity_id in enumerate(order, 1):
        completion_week = 3 * position
        for sequence, week in enumerate(
            range(completion_week - 2, completion_week + 1), 1
        ):
            access.append(
                {
                    "activity_id": activity_id,
                    "access_seq": sequence,
                    "week": week,
                    "eclo": 0,
                    "access_night": 1,
                }
            )
            occupancy.extend(
                {
                    "activity_id": activity_id,
                    "week": week,
                    "location_id": location_id,
                    "co_share_group": "g1",
                }
                for location_id in sorted(locations_by_activity[activity_id])
            )
        contract = instance.activities[activity_id].contract_number
        project = instance.projects[contract]
        completion = instance.completion_date(completion_week)
        results.append(
            {
                "scenario": "C",
                "contract_number": contract,
                "simulated_completion_date": completion.isoformat(),
                "overrun_days": max(
                    0, (completion - project.planned_completion_date).days
                ),
            }
        )
    _write(
        output / "SCHEDULE_ACCESS.csv",
        ("activity_id", "access_seq", "week", "eclo", "access_night"),
        access,
    )
    _write(
        output / "SCHEDULE_OCCUPANCY.csv",
        ("activity_id", "week", "location_id", "co_share_group"),
        occupancy,
    )
    _write(
        output / "RESULTS.csv",
        ("scenario", "contract_number", "simulated_completion_date", "overrun_days"),
        sorted(results, key=lambda row: str(row["contract_number"])),
    )


def _unfiltered_children(
    instance: Instance,
    source: Path,
    root: Path,
    counter: list[int],
) -> tuple[list[tuple[Path, Evaluation]], int, int]:
    access, occupancy, _ = load_submission(source)
    source_evaluation = evaluate_submission(instance, source, "C")
    occupied_weeks = sorted({row.week for row in access})
    if occupied_weeks != list(range(occupied_weeks[0], occupied_weeks[-1] + 1)):
        return [], 0, 0
    by_activity = defaultdict(list)
    for row in access:
        by_activity[row.activity_id].append(row)
    existing_lines = {
        line
        for row in access
        if row.eclo == 1
        for line in _affected_eclo_lines(instance, row.activity_id)
    }
    children: list[tuple[Path, Evaluation]] = []
    seen_hashes: set[str] = set()
    filter_targets = 0
    feasible_filter_targets = 0
    for activity_id in sorted(by_activity):
        rows = sorted(by_activity[activity_id], key=lambda row: row.week)
        if len(rows) != 3 or any(row.eclo for row in rows):
            continue
        would_filter = bool(
            _affected_eclo_lines(instance, activity_id) & existing_lines
        )
        for removed in rows:
            retained = [
                row.week - int(row.week > removed.week)
                for row in rows
                if row.week != removed.week
            ]
            if max(retained) - min(retained) > 1:
                continue
            counter[0] += 1
            candidate_dir = root / f"candidate_{counter[0]:05d}"
            _write_candidate(
                instance,
                access,
                occupancy,
                candidate_dir,
                activity_id,
                removed.week,
            )
            evaluation = evaluate_submission(instance, candidate_dir, "C")
            if evaluation.submission_hash in seen_hashes:
                continue
            seen_hashes.add(evaluation.submission_hash)
            candidate_access, candidate_occupancy, _ = load_submission(candidate_dir)
            feasible = evaluation.internally_feasible and not screen_closures(
                instance,
                candidate_access,
                candidate_occupancy,
                forbid_buffer_overlap=True,
            )
            if would_filter:
                filter_targets += 1
                feasible_filter_targets += int(feasible)
            if feasible and evaluation.objective_score < source_evaluation.objective_score:
                children.append((candidate_dir, evaluation))
    return children, filter_targets, feasible_filter_targets


def _exhaustive_best(instance: Instance, source: Path, root: Path) -> dict[str, object]:
    incumbent = evaluate_submission(instance, source, "C")
    best = incumbent
    counter = [0]
    visited: set[str] = set()
    states = 0
    filter_targets = 0
    feasible_filter_targets = 0

    def visit(current_dir: Path, current: Evaluation) -> None:
        nonlocal best, states, filter_targets, feasible_filter_targets
        if current.submission_hash in visited:
            return
        visited.add(current.submission_hash)
        states += 1
        if current.objective_score < best.objective_score:
            best = current
        children, filtered, feasible_filtered = _unfiltered_children(
            instance, current_dir, root, counter
        )
        filter_targets += filtered
        feasible_filter_targets += feasible_filtered
        for candidate_dir, candidate in children:
            visit(candidate_dir, candidate)

    visit(source, incumbent)
    return {
        "best_score": best.objective_score,
        "best_submission_hash": best.submission_hash,
        "states_visited": states,
        "materialized_candidates": counter[0],
        "unique_candidates_filtered_by_window": filter_targets,
        "feasible_candidates_filtered_by_window": feasible_filter_targets,
    }


def main() -> None:
    instance = load_instance(DATA)
    activities = tuple(sorted(instance.activities))
    permutations: list[dict[str, object]] = []
    with tempfile.TemporaryDirectory() as temp_dir:
        scratch = Path(temp_dir)
        for index, order in enumerate(itertools.permutations(activities), 1):
            source = scratch / f"source_{index:02d}"
            _permuted_source(instance, order, source)
            source_evaluation = evaluate_submission(instance, source, "C")
            selected_dir, selected, report = best_serialized_eclo_compaction_sequence(
                instance,
                source,
                scratch / f"ranked_{index:02d}",
                forbid_buffer_overlap=True,
            )
            exhaustive = _exhaustive_best(
                instance,
                source,
                scratch / f"exhaustive_{index:02d}",
            )
            ranked_score = (
                selected.objective_score if selected is not None else source_evaluation.objective_score
            )
            permutations.append(
                {
                    "order": list(order),
                    "source_score": source_evaluation.objective_score,
                    "ranked_score": ranked_score,
                    "ranked_promotions": report["promotions"],
                    "ranked_hash": selected.submission_hash if selected else None,
                    "exhaustive_best_score": exhaustive["best_score"],
                    "score_matches_exhaustive": ranked_score
                    == exhaustive["best_score"],
                    "states_visited": exhaustive["states_visited"],
                    "materialized_candidates": exhaustive["materialized_candidates"],
                    "unique_candidates_filtered_by_window": exhaustive[
                        "unique_candidates_filtered_by_window"
                    ],
                    "feasible_candidates_filtered_by_window": exhaustive[
                        "feasible_candidates_filtered_by_window"
                    ],
                }
            )

        live_instance = load_instance(LIVE_DATA)
        live_exhaustive = _exhaustive_best(
            live_instance,
            LIVE_SOURCE,
            scratch / "live_exhaustive",
        )
    payload = {
        "dataset_hash": instance.dataset_hash,
        "permutation_count": len(permutations),
        "all_ranked_scores_match_exhaustive": all(
            record["score_matches_exhaustive"] for record in permutations
        ),
        "total_unique_candidates_filtered_by_window": sum(
            int(record["unique_candidates_filtered_by_window"])
            for record in permutations
        ),
        "total_feasible_candidates_filtered_by_window": sum(
            int(record["feasible_candidates_filtered_by_window"])
            for record in permutations
        ),
        "permutations": permutations,
        "live_cross_line_case": {
            "dataset_hash": live_instance.dataset_hash,
            "source_score": evaluate_submission(
                live_instance, LIVE_SOURCE, "C"
            ).objective_score,
            **live_exhaustive,
        },
    }
    output = ROOT / "runs" / "eclo_filter_falsification.json"
    output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
