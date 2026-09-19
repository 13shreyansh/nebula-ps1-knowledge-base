from __future__ import annotations

import json
import tempfile
import time
from pathlib import Path

from build_benchmark_matrix import CASES, ROOT
from nebula_ps1.closure import screen_closures
from nebula_ps1.eclo_compact import best_serialized_eclo_compaction_sequence
from nebula_ps1.evaluate import evaluate_submission, load_submission
from nebula_ps1.idle_compact import best_idle_week_compaction_sequence
from nebula_ps1.independent_score import independently_score
from nebula_ps1.instance import load_instance


DATA = ROOT / "fixtures" / "independent_idle_week_v1"
SOURCE = ROOT / "fixtures" / "independent_idle_week_v1_source_c"
UNLOCK_DATA = ROOT / "fixtures" / "independent_idle_unlock_v1"
UNLOCK_SOURCE = ROOT / "fixtures" / "independent_idle_unlock_v1_source_c"


def main() -> None:
    instance = load_instance(DATA)
    source = evaluate_submission(instance, SOURCE, "C")
    started = time.perf_counter()
    with tempfile.TemporaryDirectory() as temp_dir:
        scratch = Path(temp_dir)
        idle_dir, idle, idle_report = best_idle_week_compaction_sequence(
            instance,
            SOURCE,
            scratch / "idle",
            forbid_buffer_overlap=True,
        )
        if idle_dir is None or idle is None:
            raise RuntimeError("idle-week audit produced no first-stage selection")
        final_dir, final, eclo_report = best_serialized_eclo_compaction_sequence(
            instance,
            idle_dir,
            scratch / "eclo",
            forbid_buffer_overlap=True,
        )
        if final_dir is None or final is None:
            raise RuntimeError("idle-week audit produced no ECLO selection")
        independent = independently_score(DATA, final_dir)
        access, occupancy, _ = load_submission(final_dir)
        strict_conflicts = screen_closures(
            instance,
            access,
            occupancy,
            forbid_buffer_overlap=True,
        )

        retained: list[dict[str, object]] = []
        for index, case in enumerate(CASES):
            name, data_rel, submission_rel, scenario, *_ = case
            if scenario != "C":
                continue
            case_instance = load_instance(ROOT / data_rel)
            _, selected, report = best_idle_week_compaction_sequence(
                case_instance,
                ROOT / submission_rel,
                scratch / f"retained_{index:02d}",
                forbid_buffer_overlap=True,
            )
            retained.append(
                {
                    "case": name,
                    "source_score": report["source_score"],
                    "promotions": report["promotions"],
                    "selected_score": selected.objective_score if selected else None,
                    "candidates_checked": report["candidates_checked"],
                    "initial_gap_count": report["rounds"][0]["gap_count"],
                    "score_prediction_mismatches": report[
                        "score_prediction_mismatches"
                    ],
                }
            )

        unlock_instance = load_instance(UNLOCK_DATA)
        unlock_idle_dir, unlock_idle, unlock_idle_report = (
            best_idle_week_compaction_sequence(
                unlock_instance,
                UNLOCK_SOURCE,
                scratch / "unlock_idle",
                forbid_buffer_overlap=True,
                allow_equal=True,
            )
        )
        if unlock_idle_dir is None or unlock_idle is None:
            raise RuntimeError("equal-score idle normalization was not retained")
        unlock_final_dir, unlock_final, unlock_eclo_report = (
            best_serialized_eclo_compaction_sequence(
                unlock_instance,
                unlock_idle_dir,
                scratch / "unlock_eclo",
                forbid_buffer_overlap=True,
            )
        )
        if unlock_final_dir is None or unlock_final is None:
            raise RuntimeError("equal-score normalization did not unlock ECLO")
        unlock_access, unlock_occupancy, _ = load_submission(unlock_final_dir)
        unlock_strict_conflicts = screen_closures(
            unlock_instance,
            unlock_access,
            unlock_occupancy,
            forbid_buffer_overlap=True,
        )
        unlock_independent_score = independently_score(
            UNLOCK_DATA, unlock_final_dir
        ).objective_score
    payload = {
        "dataset_hash": instance.dataset_hash,
        "source_score": source.objective_score,
        "source_independent_score": independently_score(DATA, SOURCE).objective_score,
        "source_submission_hash": source.submission_hash,
        "idle_score": idle.objective_score,
        "idle_submission_hash": idle.submission_hash,
        "idle_report": idle_report,
        "final_score": final.objective_score,
        "final_submission_hash": final.submission_hash,
        "final_independent_score": independent.objective_score,
        "final_strict_conflicts": len(strict_conflicts),
        "eclo_promotions": eclo_report["promotions"],
        "elapsed_seconds": round(time.perf_counter() - started, 6),
        "retained_case_count": len(retained),
        "retained_promoted_count": sum(
            int(record["promotions"] > 0) for record in retained
        ),
        "retained_total_initial_gaps": sum(
            int(record["initial_gap_count"]) for record in retained
        ),
        "retained_total_candidates_checked": sum(
            int(record["candidates_checked"]) for record in retained
        ),
        "retained_cases": retained,
        "equal_score_unlock": {
            "dataset_hash": unlock_instance.dataset_hash,
            "source_score": evaluate_submission(
                unlock_instance, UNLOCK_SOURCE, "C"
            ).objective_score,
            "idle_score": unlock_idle.objective_score,
            "idle_submission_hash": unlock_idle.submission_hash,
            "idle_report": unlock_idle_report,
            "final_score": unlock_final.objective_score,
            "final_submission_hash": unlock_final.submission_hash,
            "final_independent_score": unlock_independent_score,
            "final_strict_conflicts": len(unlock_strict_conflicts),
            "eclo_promotions": unlock_eclo_report["promotions"],
        },
    }
    output = ROOT / "runs" / "idle_week_compaction_audit.json"
    output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
