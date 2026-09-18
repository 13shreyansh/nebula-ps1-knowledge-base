from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

from nebula_ps1.closure import screen_closures
from nebula_ps1.evaluate import evaluate_submission, load_submission
from nebula_ps1.independent_score import independently_score
from nebula_ps1.instance import load_instance
from nebula_ps1.staged import solve_staged_scenario
from nebula_ps1.staged_c import solve_staged_c_portfolio


def _write_summary(path: Path, payload: dict[str, object]) -> None:
    temporary = path.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    os.replace(temporary, path)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run an unfiltered fixed-budget seed distribution."
    )
    parser.add_argument("--data", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--scenarios", nargs="+", choices=("A", "B", "C"), required=True)
    parser.add_argument("--seeds", nargs="+", type=int, required=True)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--heuristic-time-limit", type=float, default=30.0)
    parser.add_argument("--local-repair-time-limit", type=float, default=10.0)
    parser.add_argument("--fallback-time-limit", type=float, default=30.0)
    parser.add_argument("--verification-time-limit", type=float, default=10.0)
    parser.add_argument("--heuristic-attempts", type=int, default=1)
    parser.add_argument("--fallback-attempts", type=int, default=1)
    parser.add_argument("--closure-rounds", type=int, default=500)
    parser.add_argument(
        "--production-c",
        action="store_true",
        help="route C through the guarded A-as-C production controller",
    )
    args = parser.parse_args()

    output = Path(args.output)
    if output.exists() and any(output.iterdir()):
        raise ValueError(f"output directory must be empty: {output}")
    output.mkdir(parents=True, exist_ok=True)
    instance = load_instance(args.data)
    records: list[dict[str, object]] = []
    summary: dict[str, object] = {
        "schema_version": 1,
        "dataset_hash": instance.dataset_hash,
        "data": str(Path(args.data)),
        "policy": {
            "workers": args.workers,
            "heuristic_time_limit_seconds": args.heuristic_time_limit,
            "local_repair_time_limit_seconds": args.local_repair_time_limit,
            "fallback_time_limit_seconds": args.fallback_time_limit,
            "verification_time_limit_seconds": args.verification_time_limit,
            "heuristic_attempts": args.heuristic_attempts,
            "fallback_attempts": args.fallback_attempts,
            "closure_round_limit": args.closure_rounds,
            "forbid_buffer_overlap": False,
            "production_c": args.production_c,
        },
        "requested_scenarios": args.scenarios,
        "requested_seeds": args.seeds,
        "runs": records,
    }
    summary_path = output / "SEED_MATRIX.json"
    _write_summary(summary_path, summary)

    for scenario in args.scenarios:
        for seed in args.seeds:
            run_name = f"{scenario.lower()}_seed_{seed}"
            submission = output / run_name
            audit = output / f"{run_name}_audit"
            started = time.perf_counter()
            record: dict[str, object] = {
                "scenario": scenario,
                "seed": seed,
                "status": "RUNNING",
            }
            records.append(record)
            _write_summary(summary_path, summary)
            try:
                if scenario == "C" and args.production_c:
                    report = solve_staged_c_portfolio(
                        instance,
                        submission,
                        audit_output_dir=audit,
                        a_heuristic_time_limit_seconds=args.heuristic_time_limit,
                        a_local_repair_time_limit_seconds=args.local_repair_time_limit,
                        a_fallback_time_limit_seconds=args.fallback_time_limit,
                        a_verification_time_limit_seconds=args.verification_time_limit,
                        c_heuristic_time_limit_seconds=args.heuristic_time_limit,
                        c_verification_time_limit_seconds=args.verification_time_limit,
                        workers=args.workers,
                        seed=seed,
                        a_heuristic_attempts=args.heuristic_attempts,
                        a_fallback_attempts=args.fallback_attempts,
                        c_heuristic_attempts=args.heuristic_attempts,
                        closure_round_limit=args.closure_rounds,
                        forbid_buffer_overlap=False,
                    )
                else:
                    report = solve_staged_scenario(
                        instance,
                        submission,
                        scenario,
                        audit_output_dir=audit,
                        heuristic_time_limit_seconds=args.heuristic_time_limit,
                        local_repair_time_limit_seconds=args.local_repair_time_limit,
                        fallback_time_limit_seconds=args.fallback_time_limit,
                        verification_time_limit_seconds=args.verification_time_limit,
                        workers=args.workers,
                        seed=seed,
                        heuristic_attempts=args.heuristic_attempts,
                        fallback_attempts=args.fallback_attempts,
                        closure_round_limit=args.closure_rounds,
                        forbid_buffer_overlap=False,
                    )
                evaluation = evaluate_submission(instance, submission, scenario)
                independent = independently_score(args.data, submission)
                access, occupancy, _ = load_submission(submission)
                strict_conflicts = screen_closures(
                    instance, access, occupancy, forbid_buffer_overlap=True
                )
                if evaluation.hard_violations:
                    raise RuntimeError(f"hard violations: {evaluation.hard_violations}")
                if evaluation.objective_score != independent.objective_score:
                    raise RuntimeError(
                        "scorer mismatch: "
                        f"{evaluation.objective_score} != {independent.objective_score}"
                    )
                record.update(
                    {
                        "status": "SUCCESS",
                        "wall_seconds": time.perf_counter() - started,
                        "score": evaluation.objective_score,
                        "submission_hash": evaluation.submission_hash,
                        "strict_conflicts": len(strict_conflicts),
                        "selected_stage": report["selected_stage"],
                        "reference_validator_confirmed": False,
                    }
                )
            except Exception as exc:  # benchmark failures are recorded, never filtered
                record.update(
                    {
                        "status": "FAILURE",
                        "wall_seconds": time.perf_counter() - started,
                        "error_type": type(exc).__name__,
                        "error": str(exc),
                    }
                )
            _write_summary(summary_path, summary)

    successes = [row for row in records if row["status"] == "SUCCESS"]
    summary["successes"] = len(successes)
    summary["failures"] = len(records) - len(successes)
    summary["success_rate"] = len(successes) / len(records) if records else 0.0
    _write_summary(summary_path, summary)


if __name__ == "__main__":
    main()
