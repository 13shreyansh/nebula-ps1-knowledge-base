from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from nebula_ps1.decomposed import (
    _primary_proof_telemetry,
    independent_activity_components,
    solve_decomposed_scenario,
)
from nebula_ps1.instance import load_instance
from nebula_ps1.staged import solve_staged_scenario


def _attempt(label: str, function: object, **kwargs: object) -> dict[str, object]:
    started = time.perf_counter()
    try:
        report = function(**kwargs)  # type: ignore[operator]
    except Exception as error:
        return {
            "label": label,
            "succeeded": False,
            "outer_wall_time_seconds": time.perf_counter() - started,
            "error_type": type(error).__name__,
            "error": str(error),
        }
    return {
        "label": label,
        "succeeded": True,
        "outer_wall_time_seconds": time.perf_counter() - started,
        "selected_objective_score": report["selected_objective_score"],
        "selected_submission_hash": report["selected_submission_hash"],
        "global_optimality_proved": bool(
            report.get("global_optimality_proved_by_additivity")
            or _primary_proof_telemetry(report) is not None
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Compare monolithic and decomposed solving while dividing each "
            "decomposed stage allowance by the component count."
        )
    )
    parser.add_argument("--data", required=True)
    parser.add_argument("--scenario", choices=("A", "B", "C"), required=True)
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--heuristic-time-limit", type=float, default=3.0)
    parser.add_argument("--local-repair-time-limit", type=float, default=2.0)
    parser.add_argument("--fallback-time-limit", type=float, default=5.0)
    parser.add_argument("--verification-time-limit", type=float, default=10.0)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--strict-buffer-overlap", action="store_true")
    args = parser.parse_args()

    output_root = Path(args.output_root)
    if output_root.exists() and any(output_root.iterdir()):
        raise ValueError(f"output root must be empty: {output_root}")
    output_root.mkdir(parents=True, exist_ok=True)
    instance = load_instance(args.data)
    components = independent_activity_components(
        instance,
        args.scenario,
        forbid_buffer_overlap=args.strict_buffer_overlap,
    )
    count = len(components)
    common = {
        "heuristic_time_limit_seconds": args.heuristic_time_limit,
        "local_repair_time_limit_seconds": args.local_repair_time_limit,
        "fallback_time_limit_seconds": args.fallback_time_limit,
        "verification_time_limit_seconds": args.verification_time_limit,
        "workers": args.workers,
        "seed": args.seed,
        "heuristic_attempts": 1,
        "fallback_attempts": 1,
        "closure_round_limit": 1000,
        "forbid_buffer_overlap": args.strict_buffer_overlap,
    }
    monolithic = _attempt(
        "monolithic",
        solve_staged_scenario,
        instance=instance,
        output_dir=output_root / "monolithic",
        scenario=args.scenario,
        audit_output_dir=output_root / "monolithic_audit",
        **common,
    )
    divided = dict(common)
    for key in (
        "heuristic_time_limit_seconds",
        "local_repair_time_limit_seconds",
        "fallback_time_limit_seconds",
        "verification_time_limit_seconds",
    ):
        divided[key] = float(divided[key]) / count
    decomposed = _attempt(
        "decomposed_divided_allowance",
        solve_decomposed_scenario,
        data_dir=args.data,
        output_dir=output_root / "decomposed",
        scenario=args.scenario,
        audit_output_dir=output_root / "decomposed_audit",
        **divided,
    )
    result = {
        "dataset_hash": instance.dataset_hash,
        "scenario": args.scenario,
        "component_count": count,
        "component_sizes": sorted((len(item) for item in components), reverse=True),
        "workers": args.workers,
        "seed": args.seed,
        "strict_buffer_overlap": args.strict_buffer_overlap,
        "nominal_monolithic_stage_allowances_seconds": {
            key: common[key]
            for key in (
                "heuristic_time_limit_seconds",
                "local_repair_time_limit_seconds",
                "fallback_time_limit_seconds",
                "verification_time_limit_seconds",
            )
        },
        "nominal_decomposed_per_component_allowances_seconds": {
            key: divided[key]
            for key in (
                "heuristic_time_limit_seconds",
                "local_repair_time_limit_seconds",
                "fallback_time_limit_seconds",
                "verification_time_limit_seconds",
            )
        },
        "comparison_limit": (
            "Equal summed nominal stage allowances, not equal measured CPU time. "
            "Stages may exit early or be skipped, and model-construction overhead differs."
        ),
        "monolithic": monolithic,
        "decomposed": decomposed,
    }
    (output_root / "COMPARISON.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
