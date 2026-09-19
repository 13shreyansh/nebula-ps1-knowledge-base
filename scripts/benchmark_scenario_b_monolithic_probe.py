from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from nebula_ps1.candidate_portfolio import _externally_gate_candidate
from nebula_ps1.decomposed import _primary_proof_telemetry
from nebula_ps1.instance import load_instance
from nebula_ps1.staged import solve_staged_scenario


CASES = (
    (
        "independent_irregular_coupled_b_v1",
        "2ceb2a7c769ea594e36d5b42a622626e9e512b03b5dea87179e6b77ab2a422da",
        31,
    ),
    (
        "independent_scaled_m8",
        "4f28846aabe8ba18a9f2c146e441929641782b50a2728789c7cae459937defc2",
        31,
    ),
    (
        "independent_heterogeneous_b_v1",
        "9f457c848f337da76b54d88887b2c9eaef8d718a79f41fc08e606fe281770be4",
        1,
    ),
    (
        "independent_heterogeneous_b_v1_permuted_s23",
        "2aad7853acbd3dfc945d8b8600bcf3d44e7776c95b7c760f9e949080e6dc71f5",
        31,
    ),
)

POLICY = {
    "heuristic_time_limit_seconds": 0.1,
    "local_repair_time_limit_seconds": 0.1,
    "fallback_time_limit_seconds": 0.5,
    "verification_time_limit_seconds": 0.2,
    "workers": 1,
    "heuristic_attempts": 1,
    "fallback_attempts": 1,
    "closure_round_limit": 1000,
    "forbid_buffer_overlap": True,
}


def _write(path: Path, report: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Benchmark a bounded Scenario B monolithic proof probe."
    )
    parser.add_argument("--fixtures", default="fixtures")
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--summary", required=True)
    args = parser.parse_args()
    fixture_root = Path(args.fixtures)
    output_root = Path(args.output_root)
    summary = Path(args.summary)
    if summary.exists():
        raise ValueError(f"summary already exists: {summary}")
    report: dict[str, object] = {
        "protocol": (
            "four preselected multi-component B cases; strict closure; 0.1/0.1/"
            "0.5/0.2-second stages; one worker; fixed per-case seeds"
        ),
        "policy": POLICY,
        "cases": [],
        "portal_used": False,
        "status": "running",
    }
    for fixture, dataset_hash, seed in CASES:
        data = fixture_root / fixture
        instance = load_instance(data)
        if instance.dataset_hash != dataset_hash:
            raise RuntimeError(f"dataset hash drift for {data}")
        output = output_root / f"{fixture}_b_probe_seed{seed}_w1"
        audit = output.with_name(f"{output.name}_audit")
        if output.exists() or audit.exists():
            raise ValueError(f"probe output already exists for {fixture}")
        started = time.perf_counter()
        try:
            staged = solve_staged_scenario(
                instance,
                output,
                "B",
                audit_output_dir=audit,
                seed=seed,
                **POLICY,
            )
            evaluation = _externally_gate_candidate(
                instance,
                data,
                output,
                "B",
                forbid_buffer_overlap=True,
            )
            proved = _primary_proof_telemetry(staged) is not None
            result = {
                "status": "accepted",
                "wall_time_seconds": time.perf_counter() - started,
                "objective_score": evaluation.objective_score,
                "submission_hash": evaluation.submission_hash,
                "global_optimality_proved": proved,
            }
        except (RuntimeError, ValueError) as error:
            result = {
                "status": "failed",
                "wall_time_seconds": time.perf_counter() - started,
                "error_type": type(error).__name__,
                "error": str(error),
            }
        report["cases"].append(
            {
                "fixture": fixture,
                "dataset_hash": dataset_hash,
                "seed": seed,
                "result": result,
                "output": str(output),
                "audit": str(audit),
            }
        )
        _write(summary, report)
    report["status"] = "complete"
    _write(summary, report)
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
