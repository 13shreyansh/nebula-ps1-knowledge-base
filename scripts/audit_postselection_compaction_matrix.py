from __future__ import annotations

import json
import tempfile
import time
from pathlib import Path

from build_benchmark_matrix import CASES, ROOT
from nebula_ps1.closure import screen_closures
from nebula_ps1.evaluate import evaluate_submission, load_submission
from nebula_ps1.independent_score import independently_score
from nebula_ps1.instance import load_instance
from nebula_ps1.postprocess import best_checked_c_postprocessing_sequence


def main() -> None:
    records: list[dict[str, object]] = []
    started_all = time.perf_counter()
    with tempfile.TemporaryDirectory() as temporary:
        scratch = Path(temporary)
        for index, case in enumerate(CASES):
            name, data_rel, submission_rel, scenario, *_ = case
            if scenario != "C":
                continue
            data = ROOT / data_rel
            source_dir = ROOT / submission_rel
            instance = load_instance(data)
            source = evaluate_submission(instance, source_dir, "C")
            source_access, source_occupancy, _ = load_submission(source_dir)
            source_strict_conflicts = screen_closures(
                instance,
                source_access,
                source_occupancy,
                forbid_buffer_overlap=True,
            )
            started = time.perf_counter()
            selected_dir, selected, report = best_checked_c_postprocessing_sequence(
                instance,
                source_dir,
                scratch / f"case_{index:03d}",
                forbid_buffer_overlap=True,
            )
            independent = independently_score(data, selected_dir)
            access, occupancy, _ = load_submission(selected_dir)
            strict_conflicts = screen_closures(
                instance,
                access,
                occupancy,
                forbid_buffer_overlap=True,
            )
            if selected.objective_score != independent.objective_score:
                raise RuntimeError(f"{name}: independent score mismatch")
            if selected.objective_score > source.objective_score:
                raise RuntimeError(f"{name}: post-processing worsened the source")
            if not selected.internally_feasible:
                raise RuntimeError(f"{name}: post-processing selected an unsafe result")
            if report["strict_improvement"] and strict_conflicts:
                raise RuntimeError(f"{name}: promoted result has strict conflicts")
            if not report["strict_improvement"] and (
                selected.submission_hash != source.submission_hash
            ):
                raise RuntimeError(f"{name}: no-op changed the source hash")
            records.append(
                {
                    "case": name,
                    "source_score": source.objective_score,
                    "source_submission_hash": source.submission_hash,
                    "selected_score": selected.objective_score,
                    "selected_submission_hash": selected.submission_hash,
                    "independent_score": independent.objective_score,
                    "source_strict_conflicts": len(source_strict_conflicts),
                    "strict_conflicts": len(strict_conflicts),
                    "promoted": bool(report["strict_improvement"]),
                    "score_change": selected.objective_score - source.objective_score,
                    "hash_changed": selected.submission_hash != source.submission_hash,
                    "idle_candidates_checked": report["idle_week_compaction"][
                        "candidates_checked"
                    ],
                    "eclo_candidates_checked": report["eclo_compaction"][
                        "candidates_checked"
                    ],
                    "elapsed_seconds": round(time.perf_counter() - started, 6),
                }
            )
    payload = {
        "scope": "retained Scenario C benchmark incumbents",
        "strict_buffer_overlap_required": True,
        "case_count": len(records),
        "promoted_count": sum(int(record["promoted"]) for record in records),
        "hash_changed_count": sum(int(record["hash_changed"]) for record in records),
        "total_idle_candidates_checked": sum(
            int(record["idle_candidates_checked"]) for record in records
        ),
        "total_eclo_candidates_checked": sum(
            int(record["eclo_candidates_checked"]) for record in records
        ),
        "total_elapsed_seconds": round(time.perf_counter() - started_all, 6),
        "max_case_elapsed_seconds": max(
            float(record["elapsed_seconds"]) for record in records
        ),
        "cases": records,
    }
    output = ROOT / "runs" / "postselection_compaction_retained_c_audit.json"
    output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
