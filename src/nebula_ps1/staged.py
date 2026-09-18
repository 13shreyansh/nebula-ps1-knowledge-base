from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from .closure import screen_closures
from .evaluate import Evaluation, evaluate_submission, load_submission
from .flexible_solver import solve_flexible_supply_relaxation
from .instance import Instance
from .portfolio import SUBMISSION_FILES, _candidate_is_better, _copy_submission
from .prune import prune_submission


def solve_staged_scenario(
    instance: Instance,
    output_dir: str | Path,
    scenario: str,
    *,
    audit_output_dir: str | Path | None = None,
    heuristic_time_limit_seconds: float = 120.0,
    verification_time_limit_seconds: float = 120.0,
    workers: int = 8,
    seed: int = 1,
    heuristic_attempts: int = 3,
    closure_round_limit: int = 500,
    forbid_buffer_overlap: bool = False,
) -> dict[str, object]:
    """Generate quickly, then protect and improve with the sound separator."""

    if scenario not in {"A", "B", "C"}:
        raise ValueError("scenario must be A, B, or C")
    if heuristic_attempts < 1:
        raise ValueError("heuristic_attempts must be positive")
    output = Path(output_dir)
    audit_output = (
        Path(audit_output_dir)
        if audit_output_dir is not None
        else output.with_name(f"{output.name}_audit")
    )
    if output.exists() and any(output.iterdir()):
        raise ValueError(f"staged output directory must be empty: {output}")
    if audit_output.exists() and any(audit_output.iterdir()):
        raise ValueError(f"staged audit directory must be empty: {audit_output}")
    output.mkdir(parents=True, exist_ok=True)
    audit_output.mkdir(parents=True, exist_ok=True)

    heuristic_raw: Path | None = None
    heuristic_pruned = audit_output / "heuristic_pruned"
    verification_raw = audit_output / "verification_raw"
    verification_pruned = audit_output / "verification_pruned"
    attempt_telemetry: list[dict[str, object]] = []
    heuristic = None
    for attempt in range(heuristic_attempts):
        attempt_seed = seed + attempt
        attempt_output = audit_output / f"heuristic_attempt_{attempt + 1}_raw"
        attempt_result = solve_flexible_supply_relaxation(
            instance,
            attempt_output,
            scenario,
            time_limit_seconds=heuristic_time_limit_seconds,
            workers=workers,
            seed=attempt_seed,
            closure_round_limit=closure_round_limit,
            forbid_buffer_overlap=forbid_buffer_overlap,
            separator_mode="direct_heuristic",
        )
        attempt_telemetry.append(asdict(attempt_result))
        if (
            attempt_result.objective_score is not None
            and attempt_result.remaining_closure_conflicts == 0
        ):
            heuristic = attempt_result
            heuristic_raw = attempt_output
            break
    if heuristic is None or heuristic_raw is None:
        (audit_output / "STAGED_FAILURES.json").write_text(
            json.dumps(attempt_telemetry, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        raise RuntimeError("direct heuristic did not produce a checked safe incumbent")
    heuristic_prune = prune_submission(
        instance,
        heuristic_raw,
        heuristic_pruned,
        scenario,
        report_path=audit_output / "HEURISTIC_PRUNE.json",
        forbid_buffer_overlap=forbid_buffer_overlap,
    )
    incumbent = evaluate_submission(instance, heuristic_pruned, scenario)

    verification = solve_flexible_supply_relaxation(
        instance,
        verification_raw,
        scenario,
        time_limit_seconds=verification_time_limit_seconds,
        workers=workers,
        seed=seed,
        closure_round_limit=closure_round_limit,
        sample_hint_dir=heuristic_pruned,
        forbid_buffer_overlap=forbid_buffer_overlap,
        separator_mode="bridge_safe",
    )
    verification_prune = prune_submission(
        instance,
        verification_raw,
        verification_pruned,
        scenario,
        report_path=audit_output / "VERIFICATION_PRUNE.json",
        forbid_buffer_overlap=forbid_buffer_overlap,
    )
    verified = evaluate_submission(instance, verification_pruned, scenario)

    selected_stage = "heuristic_incumbent"
    selected_dir = heuristic_pruned
    selected: Evaluation = incumbent
    if _candidate_is_better(verified, incumbent):
        selected_stage = "bridge_safe_improvement"
        selected_dir = verification_pruned
        selected = verified
    _copy_submission(selected_dir, output)

    final = evaluate_submission(instance, output, scenario)
    access, occupancy, _ = load_submission(output)
    strict_conflicts = (
        screen_closures(
            instance,
            access,
            occupancy,
            forbid_buffer_overlap=True,
        )
        if forbid_buffer_overlap
        else ()
    )
    if (
        not final.internally_feasible
        or strict_conflicts
        or final.submission_hash != selected.submission_hash
    ):
        raise RuntimeError("staged final-copy verification failed")
    if sorted(path.name for path in output.iterdir()) != sorted(SUBMISSION_FILES):
        raise RuntimeError("staged submission directory contains files beyond the three CSVs")

    report: dict[str, object] = {
        "scenario": scenario,
        "selected_stage": selected_stage,
        "selected_objective_score": final.objective_score,
        "selected_submission_hash": final.submission_hash,
        "strict_buffer_overlap_checked": forbid_buffer_overlap,
        "reference_validator_confirmed": False,
        "submission_files": list(SUBMISSION_FILES),
        "selection_rule": "strictly lower fully checked objective; otherwise preserve incumbent",
        "heuristic_telemetry": asdict(heuristic),
        "heuristic_attempts": attempt_telemetry,
        "heuristic_prune": asdict(heuristic_prune),
        "verification_telemetry": asdict(verification),
        "verification_prune": asdict(verification_prune),
    }
    (audit_output / "STAGED.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return report
