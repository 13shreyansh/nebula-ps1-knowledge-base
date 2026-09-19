from __future__ import annotations

import csv
import itertools
import json
import tempfile
from collections import defaultdict
from pathlib import Path

from build_benchmark_matrix import ROOT
from nebula_ps1.closure import screen_closures
from nebula_ps1.eclo_compact import best_serialized_eclo_compaction_sequence
from nebula_ps1.evaluate import evaluate_submission, load_submission
from nebula_ps1.idle_compact import (
    _write_shifted_candidate,
    best_idle_week_compaction_sequence,
)
from nebula_ps1.independent_score import independently_score
from nebula_ps1.instance import Instance, load_instance


DATA = ROOT / "fixtures" / "independent_idle_tie_v1"
BASE_SOURCE = ROOT / "fixtures" / "independent_idle_tie_v1_source_c"


def _write(path: Path, fields: tuple[str, ...], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _write_source(
    instance: Instance,
    output_dir: Path,
    a_weeks: tuple[int, ...],
    b_weeks: tuple[int, ...],
) -> None:
    access, occupancy, _ = load_submission(BASE_SOURCE)
    target = {"TIEA": a_weeks, "TIEB": b_weeks}
    old_to_new: dict[tuple[str, int], int] = {}
    access_rows: list[dict[str, object]] = []
    for activity_id in sorted(target):
        old_rows = sorted(
            (row for row in access if row.activity_id == activity_id),
            key=lambda row: row.access_seq,
        )
        for row, week in zip(old_rows, target[activity_id], strict=True):
            old_to_new[(activity_id, row.week)] = week
            access_rows.append(
                {
                    "activity_id": activity_id,
                    "access_seq": row.access_seq,
                    "week": week,
                    "eclo": 0,
                    "access_night": row.access_night,
                }
            )
    occupancy_rows = [
        {
            "activity_id": row.activity_id,
            "week": old_to_new[(row.activity_id, row.week)],
            "location_id": row.location_id,
            "co_share_group": row.co_share_group,
        }
        for row in occupancy
    ]
    completion = {activity_id: max(weeks) for activity_id, weeks in target.items()}
    completion_by_contract: dict[str, int] = defaultdict(int)
    for activity_id, week in completion.items():
        contract = instance.activities[activity_id].contract_number
        completion_by_contract[contract] = max(completion_by_contract[contract], week)
    result_rows = []
    for contract in sorted(instance.projects):
        project = instance.projects[contract]
        date = instance.completion_date(completion_by_contract[contract])
        result_rows.append(
            {
                "scenario": "C",
                "contract_number": contract,
                "simulated_completion_date": date.isoformat(),
                "overrun_days": max(0, (date - project.planned_completion_date).days),
            }
        )
    _write(
        output_dir / "SCHEDULE_ACCESS.csv",
        ("activity_id", "access_seq", "week", "eclo", "access_night"),
        access_rows,
    )
    _write(
        output_dir / "SCHEDULE_OCCUPANCY.csv",
        ("activity_id", "week", "location_id", "co_share_group"),
        occupancy_rows,
    )
    _write(
        output_dir / "RESULTS.csv",
        ("scenario", "contract_number", "simulated_completion_date", "overrun_days"),
        result_rows,
    )


def _exhaustive_normalizations(
    instance: Instance,
    source_dir: Path,
    root: Path,
) -> list[tuple[Path, float, tuple[int, ...]]]:
    source = evaluate_submission(instance, source_dir, "C")
    pending = [(source_dir, source.objective_score, ())]
    states: list[tuple[Path, float, tuple[int, ...]]] = []
    seen = {source.submission_hash}
    while pending:
        current_dir, current_score, path = pending.pop()
        states.append((current_dir, current_score, path))
        access, _, _ = load_submission(current_dir)
        occupied = sorted({row.week for row in access})
        if not occupied:
            continue
        occupied_set = set(occupied)
        for gap in range(1, occupied[-1]):
            if gap in occupied_set:
                continue
            candidate_dir = root / f"state_{len(states):03d}_gap_{gap}"
            _write_shifted_candidate(instance, current_dir, candidate_dir, gap)
            candidate = evaluate_submission(instance, candidate_dir, "C")
            candidate_access, candidate_occupancy, _ = load_submission(candidate_dir)
            strict = screen_closures(
                instance,
                candidate_access,
                candidate_occupancy,
                forbid_buffer_overlap=True,
            )
            if (
                not candidate.internally_feasible
                or strict
                or candidate.objective_score > current_score
                or candidate.submission_hash in seen
            ):
                continue
            seen.add(candidate.submission_hash)
            pending.append(
                (candidate_dir, candidate.objective_score, (*path, gap))
            )
    return states


def _best_composed(
    instance: Instance,
    data_dir: Path,
    states: list[tuple[Path, float, tuple[int, ...]]],
    root: Path,
) -> dict[str, object]:
    best_dir, best_score, best_path = states[0]
    best_hash = evaluate_submission(instance, best_dir, "C").submission_hash
    for index, (state_dir, state_score, path) in enumerate(states):
        candidate_dir, candidate, _ = best_serialized_eclo_compaction_sequence(
            instance,
            state_dir,
            root / f"state_{index:03d}",
            forbid_buffer_overlap=True,
            exhaustive=True,
        )
        final_dir = candidate_dir if candidate_dir is not None else state_dir
        final_score = candidate.objective_score if candidate is not None else state_score
        final = evaluate_submission(instance, final_dir, "C")
        if (final_score, final.submission_hash) < (best_score, best_hash):
            best_dir = final_dir
            best_score = final_score
            best_path = path
            best_hash = final.submission_hash
    return {
        "score": best_score,
        "submission_hash": best_hash,
        "idle_path": list(best_path),
        "independent_score": independently_score(data_dir, best_dir).objective_score,
    }


def main() -> None:
    instance = load_instance(DATA)
    cases: list[dict[str, object]] = []
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        case_index = 0
        for a_weeks in itertools.combinations(range(1, 5), 3):
            for b_weeks in itertools.combinations(range(5, 9), 3):
                case_root = root / f"case_{case_index:03d}"
                source_dir = case_root / "source"
                _write_source(instance, source_dir, a_weeks, b_weeks)
                source = evaluate_submission(instance, source_dir, "C")
                if not source.internally_feasible:
                    raise RuntimeError(f"generated invalid source: {a_weeks}, {b_weeks}")
                idle_dir, idle, idle_report = best_idle_week_compaction_sequence(
                    instance,
                    source_dir,
                    case_root / "greedy_idle",
                    forbid_buffer_overlap=True,
                    allow_equal=True,
                )
                greedy_seed_dir = idle_dir if idle_dir is not None else source_dir
                greedy_seed_score = (
                    idle.objective_score if idle is not None else source.objective_score
                )
                greedy_dir, greedy, _ = best_serialized_eclo_compaction_sequence(
                    instance,
                    greedy_seed_dir,
                    case_root / "greedy_eclo",
                    forbid_buffer_overlap=True,
                    exhaustive=True,
                )
                greedy_final_dir = (
                    greedy_dir if greedy_dir is not None else greedy_seed_dir
                )
                greedy_score = (
                    greedy.objective_score if greedy is not None else greedy_seed_score
                )
                states = _exhaustive_normalizations(
                    instance,
                    source_dir,
                    case_root / "exhaustive_idle",
                )
                exhaustive = _best_composed(
                    instance,
                    DATA,
                    states,
                    case_root / "exhaustive_eclo",
                )
                cases.append(
                    {
                        "a_weeks": list(a_weeks),
                        "b_weeks": list(b_weeks),
                        "source_score": source.objective_score,
                        "greedy_idle_path": [
                            item["selected_gap_week"]
                            for item in idle_report["rounds"]
                            if item["selected_gap_week"] is not None
                        ],
                        "greedy_score": greedy_score,
                        "greedy_submission_hash": evaluate_submission(
                            instance, greedy_final_dir, "C"
                        ).submission_hash,
                        "greedy_independent_score": independently_score(
                            DATA, greedy_final_dir
                        ).objective_score,
                        "reachable_normalization_states": len(states),
                        "exhaustive": exhaustive,
                        "score_matches": greedy_score == exhaustive["score"],
                    }
                )
                case_index += 1
    payload = {
        "dataset_hash": instance.dataset_hash,
        "case_count": len(cases),
        "score_match_count": sum(int(case["score_matches"]) for case in cases),
        "mismatch_count": sum(int(not case["score_matches"]) for case in cases),
        "cases": cases,
    }
    output = ROOT / "runs" / "idle_gap_search_audit.json"
    output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
