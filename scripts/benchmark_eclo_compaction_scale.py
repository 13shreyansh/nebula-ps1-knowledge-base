from __future__ import annotations

import json
import tempfile
import time
from pathlib import Path

from nebula_ps1.eclo_compact import best_single_lane_eclo_compaction
from nebula_ps1.instance import load_instance


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "fixtures" / "independent_eclo_compaction_scale_v1"
SOURCE = ROOT / "fixtures" / "independent_eclo_compaction_scale_v1_source_c"
REVERSE_SOURCE = (
    ROOT / "fixtures" / "independent_eclo_compaction_scale_v1_reverse_source_c"
)


def _run_case(
    instance, name: str, source: Path, *, exhaustive: bool = False
) -> dict[str, object]:
    started = time.perf_counter()
    with tempfile.TemporaryDirectory() as temp_dir:
        selected_dir, selected, report = best_single_lane_eclo_compaction(
            instance,
            source,
            Path(temp_dir) / "candidates",
            forbid_buffer_overlap=True,
            exhaustive=exhaustive,
        )
        candidates = report.get("candidates", [])
        candidate_scores = [float(candidate["score"]) for candidate in candidates]
        candidate_hashes = {
            str(candidate["submission_hash"]) for candidate in candidates
        }
    return {
        "case": name,
        "source": str(source.relative_to(ROOT)),
        "source_score": report["source_score"],
        "exhaustive": exhaustive,
        "applicable": report["applicable"],
        "reason": report["reason"],
        "candidates_checked": report["candidates_checked"],
        "duplicate_candidates_skipped": report["duplicate_candidates_skipped"],
        "unique_candidates_ranked": report["unique_candidates_ranked"],
        "candidates_pruned_by_exact_score_order": report[
            "candidates_pruned_by_exact_score_order"
        ],
        "score_prediction_mismatches": report["score_prediction_mismatches"],
        "unique_candidate_hashes": len(candidate_hashes),
        "feasible_candidates": report["feasible_candidates"],
        "improving_candidates": report["improving_candidates"],
        "minimum_candidate_score": min(candidate_scores, default=None),
        "maximum_candidate_score": max(candidate_scores, default=None),
        "selected": selected_dir is not None,
        "selected_score": selected.objective_score if selected else None,
        "elapsed_seconds": round(time.perf_counter() - started, 6),
    }


def main() -> None:
    instance = load_instance(DATA)
    cases = [
        _run_case(instance, "zero_score_floor", SOURCE),
        _run_case(instance, "reverse_positive_score", REVERSE_SOURCE),
        _run_case(
            instance,
            "reverse_positive_score_exhaustive",
            REVERSE_SOURCE,
            exhaustive=True,
        ),
    ]
    payload = {
        "dataset_hash": instance.dataset_hash,
        "activity_count": len(instance.activities),
        "horizon_weeks": instance.horizon_weeks,
        "strict_buffer_overlap_required": True,
        "cases": cases,
    }
    output = ROOT / "runs" / "eclo_compaction_scale_benchmark.json"
    output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
