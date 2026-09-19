from __future__ import annotations

import csv
import itertools
import json
import shutil
import tempfile
from datetime import date, timedelta
from pathlib import Path

from audit_idle_gap_search import _best_composed, _exhaustive_normalizations, _write
from audit_multiline_idle_branching import ACTIVITIES, BASE_DATA, _write_source
from build_benchmark_matrix import ROOT
from nebula_ps1.eclo_compact import best_serialized_eclo_compaction_sequence
from nebula_ps1.evaluate import evaluate_submission
from nebula_ps1.idle_compact import best_idle_week_compaction_sequence
from nebula_ps1.independent_score import independently_score
from nebula_ps1.instance import load_instance


HORIZON_START = date(2035, 1, 1)
VARIANTS = {
    "staggered_starts": {
        "start_weeks": (1, 5, 9, 13),
        "predecessors": ("", "", "", ""),
    },
    "precedence_chain": {
        "start_weeks": (1, 1, 1, 1),
        "predecessors": ("", "MX1", "MX2", "MY1"),
    },
    "staggered_chain": {
        "start_weeks": (1, 5, 9, 13),
        "predecessors": ("", "MX1", "MX2", "MY1"),
    },
}


def _read(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _prepare_data(
    output_dir: Path,
    *,
    start_weeks: tuple[int, ...],
    predecessors: tuple[str, ...],
) -> None:
    shutil.copytree(BASE_DATA, output_dir)
    _write(
        output_dir / "06_PARAMETERS.csv",
        ("key", "value"),
        [
            {"key": "horizon_start", "value": HORIZON_START.isoformat()},
            {"key": "horizon_weeks", "value": 16},
        ],
    )
    activity_rows = _read(output_dir / "08_ACTIVITY_DETAILS.csv")
    settings = {
        activity_id: (start_week, predecessor)
        for activity_id, start_week, predecessor in zip(
            ACTIVITIES, start_weeks, predecessors, strict=True
        )
    }
    for row in activity_rows:
        start_week, predecessor = settings[row["activity_id"]]
        row["planned_start_date"] = (
            HORIZON_START + timedelta(days=7 * (start_week - 1))
        ).isoformat()
        row["predecessor_activity_id"] = predecessor
    _write(
        output_dir / "08_ACTIVITY_DETAILS.csv",
        tuple(activity_rows[0]),
        activity_rows,
    )


def main() -> None:
    variant_records: list[dict[str, object]] = []
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        for variant_name, settings in VARIANTS.items():
            data_dir = root / variant_name / "data"
            _prepare_data(data_dir, **settings)
            instance = load_instance(data_dir)
            mismatch_examples: list[dict[str, object]] = []
            case_count = 0
            score_match_count = 0
            max_states = 0
            for case_index, omitted in enumerate(
                itertools.product(range(4), repeat=4)
            ):
                case_root = root / variant_name / f"case_{case_index:03d}"
                source_dir = case_root / "source"
                _write_source(instance, source_dir, omitted)
                source = evaluate_submission(instance, source_dir, "C")
                if not source.internally_feasible:
                    raise RuntimeError(
                        f"{variant_name}: invalid generated source {omitted}"
                    )
                idle_dir, idle, _ = best_idle_week_compaction_sequence(
                    instance,
                    source_dir,
                    case_root / "greedy_idle",
                    forbid_buffer_overlap=True,
                    allow_equal=True,
                )
                greedy_seed = idle_dir if idle_dir is not None else source_dir
                greedy_seed_score = (
                    idle.objective_score
                    if idle is not None
                    else source.objective_score
                )
                greedy_dir, greedy, _ = best_serialized_eclo_compaction_sequence(
                    instance,
                    greedy_seed,
                    case_root / "greedy_eclo",
                    forbid_buffer_overlap=True,
                    exhaustive=True,
                )
                greedy_final = (
                    greedy_dir if greedy_dir is not None else greedy_seed
                )
                greedy_score = (
                    greedy.objective_score
                    if greedy is not None
                    else greedy_seed_score
                )
                states = _exhaustive_normalizations(
                    instance,
                    source_dir,
                    case_root / "exhaustive_idle",
                )
                max_states = max(max_states, len(states))
                exhaustive = _best_composed(
                    instance,
                    data_dir,
                    states,
                    case_root / "exhaustive_eclo",
                )
                independent = independently_score(
                    data_dir, greedy_final
                ).objective_score
                if independent != greedy_score:
                    raise RuntimeError(
                        f"{variant_name} {omitted}: independent score mismatch"
                    )
                score_matches = greedy_score == exhaustive["score"]
                case_count += 1
                score_match_count += int(score_matches)
                if not score_matches and len(mismatch_examples) < 10:
                    mismatch_examples.append(
                        {
                            "omitted_offsets": list(omitted),
                            "source_score": source.objective_score,
                            "greedy_score": greedy_score,
                            "exhaustive_score": exhaustive["score"],
                            "reachable_normalization_states": len(states),
                        }
                    )
            variant_records.append(
                {
                    "variant": variant_name,
                    "dataset_hash": instance.dataset_hash,
                    "case_count": case_count,
                    "score_match_count": score_match_count,
                    "mismatch_count": case_count - score_match_count,
                    "max_reachable_normalization_states": max_states,
                    "mismatch_examples": mismatch_examples,
                }
            )
    payload = {
        "variant_count": len(variant_records),
        "case_count": sum(int(row["case_count"]) for row in variant_records),
        "score_match_count": sum(
            int(row["score_match_count"]) for row in variant_records
        ),
        "mismatch_count": sum(
            int(row["mismatch_count"]) for row in variant_records
        ),
        "variants": variant_records,
    }
    output = ROOT / "runs" / "constrained_idle_branching_audit.json"
    output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
