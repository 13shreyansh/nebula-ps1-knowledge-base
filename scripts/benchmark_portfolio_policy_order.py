from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from nebula_ps1.candidate_portfolio import _externally_gate_candidate
from nebula_ps1.decomposed import (
    _primary_proof_telemetry,
    independent_activity_components,
    solve_decomposed_scenario,
)
from nebula_ps1.instance import load_instance
from nebula_ps1.staged import solve_staged_scenario


CASES = (
    {
        "scenario": "A",
        "fixture": "independent_multimodule_tradeoff_v1",
        "dataset_hash": "3220b2c715aaf57df46d10570ed0de9b6b79a1900e26d6df9c342e760ab9a293",
        "activities": 72,
        "component_sizes": [45, 9, 9, 9],
    },
    {
        "scenario": "A",
        "fixture": "independent_scaled_m8",
        "dataset_hash": "4f28846aabe8ba18a9f2c146e441929641782b50a2728789c7cae459937defc2",
        "activities": 72,
        "component_sizes": [9, 9, 9, 9, 9, 9, 9, 9],
    },
    {
        "scenario": "B",
        "fixture": "independent_irregular_coupled_b_v1",
        "dataset_hash": "2ceb2a7c769ea594e36d5b42a622626e9e512b03b5dea87179e6b77ab2a422da",
        "activities": 8,
        "component_sizes": [7, 1],
    },
    {
        "scenario": "B",
        "fixture": "independent_heterogeneous_b_v1_permuted_s23",
        "dataset_hash": "2aad7853acbd3dfc945d8b8600bcf3d44e7776c95b7c760f9e949080e6dc71f5",
        "activities": 42,
        "component_sizes": [13, 7, 7, 5, 3, 2, 2, 2, 1],
    },
    {
        "scenario": "C",
        "fixture": "independent_eclo_long_access_v1",
        "dataset_hash": "06660e467be28c897c74d57088ed5360fcb3471aa2d847b6950174f536b9a1cb",
        "activities": 4,
        "component_sizes": [2, 2],
    },
    {
        "scenario": "C",
        "fixture": "independent_heterogeneous_b_v1_permuted_s23",
        "dataset_hash": "2aad7853acbd3dfc945d8b8600bcf3d44e7776c95b7c760f9e949080e6dc71f5",
        "activities": 42,
        "component_sizes": [13, 8, 7, 5, 5, 4],
    },
)

POLICY = {
    "heuristic_time_limit_seconds": 3.0,
    "local_repair_time_limit_seconds": 2.0,
    "fallback_time_limit_seconds": 5.0,
    "verification_time_limit_seconds": 10.0,
    "workers": 1,
    "seed": 31,
    "heuristic_attempts": 1,
    "fallback_attempts": 1,
    "closure_round_limit": 1000,
    "forbid_buffer_overlap": True,
}


def _write_summary(path: Path, report: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _run_policy(
    policy: str,
    data: Path,
    output_root: Path,
    scenario: str,
) -> dict[str, object]:
    destination = output_root / f"{data.name}_{scenario.lower()}_{policy}_seed31_w1"
    audit = destination.with_name(f"{destination.name}_audit")
    for path in (destination, audit):
        if path.exists():
            raise ValueError(f"benchmark path already exists: {path}")
    instance = load_instance(data)
    started = time.perf_counter()
    try:
        if policy == "monolithic":
            solver_report = solve_staged_scenario(
                instance,
                destination,
                scenario,
                audit_output_dir=audit,
                **POLICY,
            )
            proved = _primary_proof_telemetry(solver_report) is not None
        elif policy == "decomposed":
            solver_report = solve_decomposed_scenario(
                data,
                destination,
                scenario,
                audit_output_dir=audit,
                **POLICY,
            )
            proved = bool(solver_report["global_optimality_proved_by_additivity"])
        else:
            raise AssertionError(policy)
        evaluation = _externally_gate_candidate(
            instance,
            data,
            destination,
            scenario,
            forbid_buffer_overlap=True,
        )
        return {
            "policy": policy,
            "status": "accepted",
            "wall_time_seconds": time.perf_counter() - started,
            "objective_score": evaluation.objective_score,
            "submission_hash": evaluation.submission_hash,
            "global_optimality_proved": proved,
            "output": str(destination),
            "audit": str(audit),
        }
    except (RuntimeError, ValueError) as error:
        return {
            "policy": policy,
            "status": "failed",
            "wall_time_seconds": time.perf_counter() - started,
            "error_type": type(error).__name__,
            "error": str(error),
            "output": str(destination),
            "audit": str(audit),
        }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compare fixed monolithic/decomposed policy order evidence."
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
            "six structure-selected cases; both policies; fixed 3/2/5/10-second "
            "stage limits; one worker; seed 31; strict closure; no portal"
        ),
        "policy": POLICY,
        "cases": [],
        "portal_used": False,
        "status": "running",
    }
    for specification in CASES:
        data = fixture_root / str(specification["fixture"])
        scenario = str(specification["scenario"])
        instance = load_instance(data)
        component_sizes = sorted(
            (
                len(component)
                for component in independent_activity_components(
                    instance,
                    scenario,
                    forbid_buffer_overlap=True,
                )
            ),
            reverse=True,
        )
        if instance.dataset_hash != specification["dataset_hash"]:
            raise RuntimeError(f"dataset hash drift for {data}")
        if len(instance.activities) != specification["activities"]:
            raise RuntimeError(f"activity count drift for {data}")
        if component_sizes != specification["component_sizes"]:
            raise RuntimeError(f"component structure drift for {data}")
        case = dict(specification)
        case["attempts"] = [
            _run_policy("monolithic", data, output_root, scenario),
            _run_policy("decomposed", data, output_root, scenario),
        ]
        report["cases"].append(case)
        _write_summary(summary, report)
    report["status"] = "complete"
    _write_summary(summary, report)
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
