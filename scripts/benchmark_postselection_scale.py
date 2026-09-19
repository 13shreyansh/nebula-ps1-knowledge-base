from __future__ import annotations

import json
import tempfile
import time
from pathlib import Path

from nebula_ps1.closure import screen_closures
from nebula_ps1.evaluate import evaluate_submission, load_submission
from nebula_ps1.independent_score import independently_score
from nebula_ps1.instance import load_instance
from nebula_ps1.postprocess import best_checked_c_postprocessing_sequence


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "fixtures" / "independent_eclo_compaction_scale_v1"
SOURCE = ROOT / "fixtures" / "independent_eclo_compaction_scale_v1_source_c"
REVERSE_SOURCE = (
    ROOT / "fixtures" / "independent_eclo_compaction_scale_v1_reverse_source_c"
)


def _run_case(instance, name: str, source: Path) -> dict[str, object]:
    source_evaluation = evaluate_submission(instance, source, "C")
    started = time.perf_counter()
    with tempfile.TemporaryDirectory() as temporary:
        selected_dir, selected, report = best_checked_c_postprocessing_sequence(
            instance,
            source,
            Path(temporary) / "candidates",
            forbid_buffer_overlap=True,
        )
        elapsed_seconds = time.perf_counter() - started
        independent = independently_score(DATA, selected_dir)
        access, occupancy, _ = load_submission(selected_dir)
        strict_conflicts = screen_closures(
            instance,
            access,
            occupancy,
            forbid_buffer_overlap=True,
        )
    if selected.objective_score != independent.objective_score:
        raise RuntimeError(f"{name}: independent score mismatch")
    if selected.objective_score > source_evaluation.objective_score:
        raise RuntimeError(f"{name}: final postprocessing worsened the source")
    if not selected.internally_feasible or strict_conflicts:
        raise RuntimeError(f"{name}: final postprocessing selected an unsafe result")
    return {
        "case": name,
        "source": str(source.relative_to(ROOT)),
        "source_score": source_evaluation.objective_score,
        "selected_score": selected.objective_score,
        "independent_score": independent.objective_score,
        "score_change": selected.objective_score - source_evaluation.objective_score,
        "strict_improvement": report["strict_improvement"],
        "selected_stage": report["selected_stage"],
        "source_submission_hash": source_evaluation.submission_hash,
        "selected_submission_hash": selected.submission_hash,
        "hash_changed": (
            selected.submission_hash != source_evaluation.submission_hash
        ),
        "strict_conflicts": len(strict_conflicts),
        "idle_candidates_checked": report["idle_week_compaction"][
            "candidates_checked"
        ],
        "eclo_candidates_checked": report["eclo_compaction"][
            "candidates_checked"
        ],
        "eclo_candidates_pruned_by_exact_score_order": report["eclo_compaction"][
            "candidates_pruned_by_exact_score_order"
        ],
        "elapsed_seconds": round(elapsed_seconds, 6),
    }


def main() -> None:
    instance = load_instance(DATA)
    cases = [
        _run_case(instance, "zero_score_floor", SOURCE),
        _run_case(instance, "reverse_positive_score", REVERSE_SOURCE),
    ]
    payload = {
        "dataset_hash": instance.dataset_hash,
        "activity_count": len(instance.activities),
        "horizon_weeks": instance.horizon_weeks,
        "strict_buffer_overlap_required": True,
        "cases": cases,
        "total_elapsed_seconds": round(
            sum(float(case["elapsed_seconds"]) for case in cases), 6
        ),
    }
    output = ROOT / "runs" / "postselection_compaction_scale_benchmark.json"
    output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
