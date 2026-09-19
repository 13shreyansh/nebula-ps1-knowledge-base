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
DATA = ROOT / "fixtures" / "independent_idle_compaction_scale_v1"
SOURCE = ROOT / "fixtures" / "independent_idle_compaction_scale_v1_source_c"


def main() -> None:
    instance = load_instance(DATA)
    source = evaluate_submission(instance, SOURCE, "C")
    started = time.perf_counter()
    with tempfile.TemporaryDirectory() as temporary:
        selected_dir, selected, report = best_checked_c_postprocessing_sequence(
            instance,
            SOURCE,
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
        raise RuntimeError("independent score mismatch")
    if not selected.internally_feasible or strict_conflicts:
        raise RuntimeError("unsafe scale-audit selection")
    payload = {
        "dataset_hash": instance.dataset_hash,
        "activity_count": len(instance.activities),
        "horizon_weeks": instance.horizon_weeks,
        "source_score": source.objective_score,
        "selected_score": selected.objective_score,
        "independent_score": independent.objective_score,
        "score_change": selected.objective_score - source.objective_score,
        "source_submission_hash": source.submission_hash,
        "selected_submission_hash": selected.submission_hash,
        "strict_conflicts": len(strict_conflicts),
        "initial_gap_count": report["idle_week_compaction"]["rounds"][0][
            "gap_count"
        ],
        "idle_promotions": report["idle_week_compaction"]["promotions"],
        "idle_candidates_checked": report["idle_week_compaction"][
            "candidates_checked"
        ],
        "idle_prediction_mismatches": report["idle_week_compaction"][
            "score_prediction_mismatches"
        ],
        "eclo_promotions": report["eclo_compaction"]["promotions"],
        "eclo_candidates_checked": report["eclo_compaction"][
            "candidates_checked"
        ],
        "selected_stage": report["selected_stage"],
        "elapsed_seconds": round(elapsed_seconds, 6),
    }
    output = ROOT / "runs" / "idle_compaction_scale_benchmark.json"
    output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
