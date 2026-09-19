from __future__ import annotations

import itertools
import json
import shutil
import tempfile
from collections import defaultdict
from pathlib import Path

from audit_idle_gap_search import (
    _best_composed,
    _exhaustive_normalizations,
    _write,
)
from build_benchmark_matrix import ROOT
from nebula_ps1.eclo_compact import best_serialized_eclo_compaction_sequence
from nebula_ps1.evaluate import evaluate_submission, load_submission
from nebula_ps1.idle_compact import best_idle_week_compaction_sequence
from nebula_ps1.independent_score import independently_score
from nebula_ps1.instance import Instance, load_instance


BASE_DATA = ROOT / "fixtures" / "independent_eclo_multipass_v1"
BASE_SOURCE = ROOT / "fixtures" / "independent_eclo_multipass_v1_source_c"
ACTIVITIES = ("MX1", "MX2", "MY1", "MY2")


def _prepare_data(output_dir: Path) -> None:
    shutil.copytree(BASE_DATA, output_dir)
    _write(
        output_dir / "06_PARAMETERS.csv",
        ("key", "value"),
        [
            {"key": "horizon_start", "value": "2035-01-01"},
            {"key": "horizon_weeks", "value": 16},
        ],
    )


def _write_source(
    instance: Instance,
    output_dir: Path,
    omitted_offsets: tuple[int, ...],
) -> None:
    base_access, base_occupancy, _ = load_submission(BASE_SOURCE)
    weeks_by_activity = {
        activity_id: tuple(
            week
            for week in range(4 * index + 1, 4 * index + 5)
            if week != 4 * index + 1 + omitted_offsets[index]
        )
        for index, activity_id in enumerate(ACTIVITIES)
    }
    old_to_new: dict[tuple[str, int], int] = {}
    access_rows: list[dict[str, object]] = []
    for activity_id in ACTIVITIES:
        old_rows = sorted(
            (row for row in base_access if row.activity_id == activity_id),
            key=lambda row: row.access_seq,
        )
        for row, week in zip(
            old_rows, weeks_by_activity[activity_id], strict=True
        ):
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
        for row in base_occupancy
    ]
    completion_by_contract: dict[str, int] = defaultdict(int)
    for activity_id, weeks in weeks_by_activity.items():
        completion_by_contract[
            instance.activities[activity_id].contract_number
        ] = max(weeks)
    result_rows = []
    for contract in sorted(instance.projects):
        project = instance.projects[contract]
        completion = instance.completion_date(completion_by_contract[contract])
        result_rows.append(
            {
                "scenario": "C",
                "contract_number": contract,
                "simulated_completion_date": completion.isoformat(),
                "overrun_days": max(
                    0, (completion - project.planned_completion_date).days
                ),
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


def main() -> None:
    records: list[dict[str, object]] = []
    max_states = 0
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        data_dir = root / "data"
        _prepare_data(data_dir)
        instance = load_instance(data_dir)
        for case_index, omitted in enumerate(itertools.product(range(4), repeat=4)):
            case_root = root / f"case_{case_index:03d}"
            source_dir = case_root / "source"
            _write_source(instance, source_dir, omitted)
            source = evaluate_submission(instance, source_dir, "C")
            if not source.internally_feasible:
                raise RuntimeError(f"invalid generated source {omitted}")
            idle_dir, idle, idle_report = best_idle_week_compaction_sequence(
                instance,
                source_dir,
                case_root / "greedy_idle",
                forbid_buffer_overlap=True,
                allow_equal=True,
            )
            greedy_seed = idle_dir if idle_dir is not None else source_dir
            greedy_seed_score = (
                idle.objective_score if idle is not None else source.objective_score
            )
            greedy_dir, greedy, _ = best_serialized_eclo_compaction_sequence(
                instance,
                greedy_seed,
                case_root / "greedy_eclo",
                forbid_buffer_overlap=True,
                exhaustive=True,
            )
            greedy_final = greedy_dir if greedy_dir is not None else greedy_seed
            greedy_score = (
                greedy.objective_score if greedy is not None else greedy_seed_score
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
            greedy_independent = independently_score(
                data_dir, greedy_final
            ).objective_score
            records.append(
                {
                    "omitted_offsets": list(omitted),
                    "source_score": source.objective_score,
                    "greedy_idle_path": [
                        round_record["selected_gap_week"]
                        for round_record in idle_report["rounds"]
                        if round_record["selected_gap_week"] is not None
                    ],
                    "reachable_normalization_states": len(states),
                    "greedy_score": greedy_score,
                    "greedy_independent_score": greedy_independent,
                    "exhaustive_score": exhaustive["score"],
                    "score_matches": greedy_score == exhaustive["score"],
                }
            )
    mismatches = [record for record in records if not record["score_matches"]]
    payload = {
        "dataset_hash": instance.dataset_hash,
        "case_count": len(records),
        "score_match_count": len(records) - len(mismatches),
        "mismatch_count": len(mismatches),
        "max_reachable_normalization_states": max_states,
        "mismatches": mismatches,
    }
    output = ROOT / "runs" / "multiline_idle_branching_audit.json"
    output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
