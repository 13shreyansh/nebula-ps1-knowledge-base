from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from nebula_ps1.closure import screen_closures
from nebula_ps1.evaluate import evaluate_submission, load_submission
from nebula_ps1.flexible_solver import solve_flexible_supply_relaxation
from nebula_ps1.independent_score import independently_score
from nebula_ps1.instance import load_instance
from nebula_ps1.portfolio import _candidate_is_better, _copy_submission
from nebula_ps1.prune import prune_submission
from nebula_ps1.staged import _scenario_b_cost_contributing_activities


def checked_record(data: Path, instance, submission: Path) -> dict[str, object]:
    evaluation = evaluate_submission(instance, submission, "C")
    independent = independently_score(data, submission)
    access, occupancy, _ = load_submission(submission)
    standard_conflicts = screen_closures(instance, access, occupancy)
    strict_conflicts = screen_closures(
        instance,
        access,
        occupancy,
        forbid_buffer_overlap=True,
    )
    if evaluation.hard_violations or standard_conflicts:
        raise RuntimeError(
            f"unsafe candidate {submission}: violations={evaluation.hard_violations}, "
            f"conflicts={standard_conflicts}"
        )
    if evaluation.objective_score != independent.objective_score:
        raise RuntimeError(
            f"scorer disagreement {submission}: {evaluation.objective_score} != "
            f"{independent.objective_score}"
        )
    return {
        "score": evaluation.objective_score,
        "submission_hash": evaluation.submission_hash,
        "standard_conflicts": len(standard_conflicts),
        "strict_conflicts": len(strict_conflicts),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Benchmark the protected narrow-plus-expanded Scenario C repair portfolio."
    )
    parser.add_argument("--data", required=True)
    parser.add_argument("--source", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--seeds", default="1,2,3,4,5")
    parser.add_argument("--narrow-time", type=float, default=30.0)
    parser.add_argument("--expanded-time", type=float, default=10.0)
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()
    data = Path(args.data)
    source = Path(args.source)
    output = Path(args.output)
    if output.exists() and any(output.iterdir()):
        raise ValueError(f"output directory must be empty: {output}")
    output.mkdir(parents=True, exist_ok=True)
    seeds = [int(value) for value in args.seeds.split(",")]
    instance = load_instance(data)
    source_record = checked_record(data, instance, source)
    records: list[dict[str, object]] = []

    for seed in seeds:
        seed_root = output / f"seed_{seed}"
        seed_root.mkdir()
        selected_dir = source
        selected = evaluate_submission(instance, source, "C")
        narrow_activities = _scenario_b_cost_contributing_activities(
            instance,
            selected_dir,
            expand_footprints=True,
            expand_contracts=True,
            expand_precedence=True,
            include_delays=True,
        )
        narrow_raw = seed_root / "narrow_raw"
        narrow_pruned = seed_root / "narrow_pruned"
        narrow = solve_flexible_supply_relaxation(
            instance,
            narrow_raw,
            "C",
            time_limit_seconds=args.narrow_time,
            workers=args.workers,
            seed=seed,
            closure_round_limit=500,
            sample_hint_dir=selected_dir,
            round_time_limit_seconds=5.0,
            freeze_access_hint=True,
            freeze_access_except=set(narrow_activities),
            separator_mode="bridge_safe",
        )
        narrow_prune = prune_submission(
            instance,
            narrow_raw,
            narrow_pruned,
            "C",
            report_path=seed_root / "NARROW_PRUNE.json",
        )
        narrow_evaluation = evaluate_submission(instance, narrow_pruned, "C")
        if _candidate_is_better(narrow_evaluation, selected):
            selected_dir = narrow_pruned
            selected = narrow_evaluation

        current_narrow = _scenario_b_cost_contributing_activities(
            instance,
            selected_dir,
            expand_footprints=True,
            expand_contracts=True,
            expand_precedence=True,
            include_delays=True,
        )
        expanded_activities = _scenario_b_cost_contributing_activities(
            instance,
            selected_dir,
            expand_footprints=True,
            expand_contracts=True,
            expand_precedence=True,
            revisit_precedence_after_footprints=True,
            revisit_contracts_after_precedence=True,
            include_delays=True,
        )
        expanded = None
        expanded_prune = None
        expanded_record = None
        if set(expanded_activities) != set(current_narrow):
            expanded_raw = seed_root / "expanded_raw"
            expanded_pruned = seed_root / "expanded_pruned"
            expanded = solve_flexible_supply_relaxation(
                instance,
                expanded_raw,
                "C",
                time_limit_seconds=args.expanded_time,
                workers=args.workers,
                seed=seed + 1,
                closure_round_limit=500,
                sample_hint_dir=selected_dir,
                round_time_limit_seconds=5.0,
                freeze_access_hint=True,
                freeze_access_except=set(expanded_activities),
                separator_mode="bridge_safe",
            )
            expanded_prune = prune_submission(
                instance,
                expanded_raw,
                expanded_pruned,
                "C",
                report_path=seed_root / "EXPANDED_PRUNE.json",
            )
            expanded_evaluation = evaluate_submission(instance, expanded_pruned, "C")
            expanded_record = checked_record(data, instance, expanded_pruned)
            if _candidate_is_better(expanded_evaluation, selected):
                selected_dir = expanded_pruned
                selected = expanded_evaluation

        final_dir = seed_root / "final"
        _copy_submission(selected_dir, final_dir)
        final_record = checked_record(data, instance, final_dir)
        record = {
            "seed": seed,
            "source": source_record,
            "narrow_activity_count": len(narrow_activities),
            "narrow_telemetry": asdict(narrow),
            "narrow_prune": asdict(narrow_prune),
            "narrow": checked_record(data, instance, narrow_pruned),
            "expanded_activity_count": len(expanded_activities),
            "expanded_telemetry": asdict(expanded) if expanded else None,
            "expanded_prune": asdict(expanded_prune) if expanded_prune else None,
            "expanded": expanded_record,
            "final": final_record,
        }
        records.append(record)
        print(
            json.dumps(
                {
                    "seed": seed,
                    "narrow_score": record["narrow"]["score"],
                    "expanded_score": (
                        record["expanded"]["score"] if record["expanded"] else None
                    ),
                    "final_score": final_record["score"],
                },
                sort_keys=True,
            ),
            flush=True,
        )

    summary = {
        "data": str(data),
        "source": str(source),
        "narrow_time_limit_seconds": args.narrow_time,
        "expanded_time_limit_seconds": args.expanded_time,
        "workers": args.workers,
        "records": records,
    }
    (output / "REPAIR_MATRIX.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
