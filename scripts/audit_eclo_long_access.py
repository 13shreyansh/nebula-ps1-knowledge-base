from __future__ import annotations

import json
import tempfile
import time
from pathlib import Path

from nebula_ps1.closure import screen_closures
from nebula_ps1.eclo_compact import best_serialized_eclo_compaction_sequence
from nebula_ps1.evaluate import evaluate_submission, load_submission
from nebula_ps1.independent_score import independently_score
from nebula_ps1.instance import load_instance


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "fixtures" / "independent_eclo_long_access_v1"
SOURCE = ROOT / "fixtures" / "independent_eclo_long_access_v1_source_c"


def _run(instance, *, exhaustive: bool) -> dict[str, object]:
    started = time.perf_counter()
    with tempfile.TemporaryDirectory() as temp_dir:
        selected_dir, selected, report = best_serialized_eclo_compaction_sequence(
            instance,
            SOURCE,
            Path(temp_dir) / "candidates",
            forbid_buffer_overlap=True,
            exhaustive=exhaustive,
        )
        if selected_dir is None or selected is None:
            raise RuntimeError("long-access audit produced no selection")
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
        "source_score": report["source_score"],
        "selected_score": selected.objective_score,
        "selected_submission_hash": selected.submission_hash,
        "independent_score": independent.objective_score,
        "strict_conflicts": len(strict_conflicts),
        "promotions": report["promotions"],
        "round_count": len(report["rounds"]),
        "round_scores": [item["selected_score"] for item in report["rounds"]],
        "candidates_checked": report["candidates_checked"],
        "duplicate_candidates_skipped": report["duplicate_candidates_skipped"],
        "candidates_skipped_existing_eclo_window": report[
            "candidates_skipped_existing_eclo_window"
        ],
        "candidates_pruned_by_exact_score_order": report[
            "candidates_pruned_by_exact_score_order"
        ],
        "score_prediction_mismatches": report["score_prediction_mismatches"],
        "elapsed_seconds": round(time.perf_counter() - started, 6),
    }


def main() -> None:
    instance = load_instance(DATA)
    source = evaluate_submission(instance, SOURCE, "C")
    source_independent = independently_score(DATA, SOURCE)
    payload = {
        "dataset_hash": instance.dataset_hash,
        "line_count": len(instance.lines),
        "activity_count": len(instance.activities),
        "total_accesses_per_activity": sorted(
            {activity.total_accesses for activity in instance.activities.values()}
        ),
        "source_score": source.objective_score,
        "source_independent_score": source_independent.objective_score,
        "source_submission_hash": source.submission_hash,
        "source_hard_violations": list(source.hard_violations),
        "ranked": _run(instance, exhaustive=False),
        "exhaustive": _run(instance, exhaustive=True),
    }
    output = ROOT / "runs" / "eclo_long_access_audit.json"
    output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
