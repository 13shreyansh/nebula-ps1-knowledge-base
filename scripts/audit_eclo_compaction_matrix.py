from __future__ import annotations

import json
import tempfile
import time
from pathlib import Path

from build_benchmark_matrix import CASES, ROOT
from nebula_ps1.eclo_compact import best_single_lane_eclo_compaction
from nebula_ps1.instance import load_instance


def main() -> None:
    records: list[dict[str, object]] = []
    with tempfile.TemporaryDirectory() as temp_dir:
        scratch = Path(temp_dir)
        for index, case in enumerate(CASES):
            name, data_rel, submission_rel, scenario, *_ = case
            if scenario != "C":
                continue
            instance = load_instance(ROOT / data_rel)
            started = time.perf_counter()
            _, selected, report = best_single_lane_eclo_compaction(
                instance,
                ROOT / submission_rel,
                scratch / f"case_{index}",
                forbid_buffer_overlap=True,
            )
            records.append(
                {
                    "case": name,
                    "source_score": report["source_score"],
                    "applicable": report["applicable"],
                    "reason": report["reason"],
                    "candidates_checked": report["candidates_checked"],
                    "duplicate_candidates_skipped": report[
                        "duplicate_candidates_skipped"
                    ],
                    "feasible_candidates": report["feasible_candidates"],
                    "improving_candidates": report["improving_candidates"],
                    "selected_score": selected.objective_score if selected else None,
                    "elapsed_seconds": round(time.perf_counter() - started, 6),
                }
            )
    payload = {
        "scope": "retained Scenario C benchmark incumbents",
        "strict_buffer_overlap_required": True,
        "case_count": len(records),
        "applicable_count": sum(bool(record["applicable"]) for record in records),
        "improved_count": sum(record["selected_score"] is not None for record in records),
        "total_candidates_checked": sum(
            int(record["candidates_checked"]) for record in records
        ),
        "total_duplicate_candidates_skipped": sum(
            int(record["duplicate_candidates_skipped"]) for record in records
        ),
        "cases": records,
    }
    output = ROOT / "runs" / "eclo_compaction_retained_c_audit.json"
    output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
