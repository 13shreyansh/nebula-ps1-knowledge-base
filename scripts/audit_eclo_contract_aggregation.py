from __future__ import annotations

import json
import tempfile
import time
from pathlib import Path

from nebula_ps1.closure import screen_closures
from nebula_ps1.eclo_compact import best_single_lane_eclo_compaction
from nebula_ps1.evaluate import evaluate_submission, load_submission
from nebula_ps1.independent_score import independently_score
from nebula_ps1.instance import load_instance


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "fixtures" / "independent_eclo_contract_aggregation_v1"
SOURCE = ROOT / "fixtures" / "independent_eclo_contract_aggregation_v1_source_c"


def _run(instance, *, exhaustive: bool) -> dict[str, object]:
    started = time.perf_counter()
    with tempfile.TemporaryDirectory() as temp_dir:
        selected_dir, selected, report = best_single_lane_eclo_compaction(
            instance,
            SOURCE,
            Path(temp_dir) / "candidates",
            forbid_buffer_overlap=True,
            exhaustive=exhaustive,
        )
        if selected_dir is None or selected is None:
            raise RuntimeError("contract-aggregation audit produced no selection")
        independent = independently_score(DATA, selected_dir)
        access, occupancy, _ = load_submission(selected_dir)
        strict_conflicts = screen_closures(
            instance,
            access,
            occupancy,
            forbid_buffer_overlap=True,
        )
    return {
        "exhaustive": exhaustive,
        "selected_score": selected.objective_score,
        "selected_submission_hash": selected.submission_hash,
        "independent_score": independent.objective_score,
        "strict_conflicts": len(strict_conflicts),
        "candidates_checked": report["candidates_checked"],
        "duplicate_candidates_skipped": report["duplicate_candidates_skipped"],
        "unique_candidates_ranked": report["unique_candidates_ranked"],
        "candidates_pruned_by_exact_score_order": report[
            "candidates_pruned_by_exact_score_order"
        ],
        "score_prediction_mismatches": report["score_prediction_mismatches"],
        "candidate_scores": [
            {
                "activity_id": candidate["activity_id"],
                "removed_week": candidate["removed_week"],
                "predicted_score": candidate["predicted_score"],
                "serialized_score": candidate["score"],
                "matches": candidate["score_prediction_matches"],
            }
            for candidate in report["candidates"]
        ],
        "elapsed_seconds": round(time.perf_counter() - started, 6),
    }


def main() -> None:
    instance = load_instance(DATA)
    source = evaluate_submission(instance, SOURCE, "C")
    source_independent = independently_score(DATA, SOURCE)
    access, occupancy, _ = load_submission(SOURCE)
    payload = {
        "dataset_hash": instance.dataset_hash,
        "contract_count": len(instance.projects),
        "activity_count": len(instance.activities),
        "source_score": source.objective_score,
        "source_independent_score": source_independent.objective_score,
        "source_submission_hash": source.submission_hash,
        "source_hard_violations": list(source.hard_violations),
        "source_strict_conflicts": len(
            screen_closures(
                instance,
                access,
                occupancy,
                forbid_buffer_overlap=True,
            )
        ),
        "ranked": _run(instance, exhaustive=False),
        "exhaustive": _run(instance, exhaustive=True),
    }
    output = ROOT / "runs" / "eclo_contract_aggregation_audit.json"
    output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
