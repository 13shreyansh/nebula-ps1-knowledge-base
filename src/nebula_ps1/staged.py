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
from .solver import SolveTelemetry


def solve_staged_scenario(
    instance: Instance,
    output_dir: str | Path,
    scenario: str,
    *,
    audit_output_dir: str | Path | None = None,
    heuristic_time_limit_seconds: float = 120.0,
    fallback_time_limit_seconds: float = 120.0,
    verification_time_limit_seconds: float = 120.0,
    workers: int = 8,
    seed: int = 1,
    heuristic_attempts: int = 3,
    fallback_attempts: int = 2,
    closure_round_limit: int = 500,
    forbid_buffer_overlap: bool = False,
) -> dict[str, object]:
    """Generate quickly, then protect and improve with the sound separator."""

    if scenario not in {"A", "B", "C"}:
        raise ValueError("scenario must be A, B, or C")
    if heuristic_attempts < 1:
        raise ValueError("heuristic_attempts must be positive")
    if fallback_attempts < 1:
        raise ValueError("fallback_attempts must be positive")
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
    heuristic: SolveTelemetry | None = None
    repair_hint: Path | None = None
    repair_hint_attempt: int | None = None
    repair_hint_rank: tuple[int, float] | None = None
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
        if attempt_result.objective_score is not None and all(
            (attempt_output / name).exists() for name in SUBMISSION_FILES
        ):
            rank = (
                attempt_result.remaining_closure_conflicts,
                attempt_result.objective_score,
            )
            if repair_hint_rank is None or rank < repair_hint_rank:
                repair_hint = attempt_output
                repair_hint_attempt = attempt + 1
                repair_hint_rank = rank
    fallback: SolveTelemetry | None = None
    heuristic_prune = None
    fallback_prune = None
    fallback_attempt_telemetry: list[dict[str, object]] = []
    selected_fallback_attempt: int | None = None
    if heuristic is not None and heuristic_raw is not None:
        heuristic_prune = prune_submission(
            instance,
            heuristic_raw,
            heuristic_pruned,
            scenario,
            report_path=audit_output / "HEURISTIC_PRUNE.json",
            forbid_buffer_overlap=forbid_buffer_overlap,
        )
        incumbent_stage = "heuristic_incumbent"
        improvement_stage = "bridge_safe_improvement"
        incumbent_dir = heuristic_pruned
    else:
        best_fallback_evaluation: Evaluation | None = None
        best_fallback_dir: Path | None = None
        for fallback_attempt in range(fallback_attempts):
            attempt_number = fallback_attempt + 1
            attempt_seed = seed + fallback_attempt
            attempt_hint = repair_hint if fallback_attempt == 0 else None
            attempt_raw = audit_output / f"bridge_safe_fallback_attempt_{attempt_number}_raw"
            attempt_pruned = audit_output / f"bridge_safe_fallback_attempt_{attempt_number}_pruned"
            attempt_result = solve_flexible_supply_relaxation(
                instance,
                attempt_raw,
                scenario,
                time_limit_seconds=fallback_time_limit_seconds,
                workers=workers,
                seed=attempt_seed,
                closure_round_limit=closure_round_limit,
                sample_hint_dir=attempt_hint,
                forbid_buffer_overlap=forbid_buffer_overlap,
                separator_mode="bridge_safe",
            )
            attempt_record: dict[str, object] = {
                "attempt": attempt_number,
                "repair_hint_heuristic_attempt": (
                    repair_hint_attempt if attempt_hint is not None else None
                ),
                "telemetry": asdict(attempt_result),
            }
            if (
                attempt_result.objective_score is not None
                and attempt_result.remaining_closure_conflicts == 0
            ):
                attempt_prune = prune_submission(
                    instance,
                    attempt_raw,
                    attempt_pruned,
                    scenario,
                    report_path=audit_output / f"FALLBACK_ATTEMPT_{attempt_number}_PRUNE.json",
                    forbid_buffer_overlap=forbid_buffer_overlap,
                )
                candidate = evaluate_submission(instance, attempt_pruned, scenario)
                attempt_record["prune"] = asdict(attempt_prune)
                if best_fallback_evaluation is None or _candidate_is_better(
                    candidate, best_fallback_evaluation
                ):
                    fallback = attempt_result
                    fallback_prune = attempt_prune
                    best_fallback_evaluation = candidate
                    best_fallback_dir = attempt_pruned
                    selected_fallback_attempt = attempt_number
            fallback_attempt_telemetry.append(attempt_record)
        if fallback is None or best_fallback_dir is None:
            (audit_output / "STAGED_FAILURES.json").write_text(
                json.dumps(
                    {
                        "heuristic_attempts": attempt_telemetry,
                        "bridge_safe_repair_hint_source_attempt": repair_hint_attempt,
                        "bridge_safe_fallback_attempts": fallback_attempt_telemetry,
                    },
                    indent=2,
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )
            raise RuntimeError(
                "neither direct heuristic nor bridge-safe fallback produced a checked safe incumbent"
            )
        incumbent_stage = "bridge_safe_fallback"
        improvement_stage = "bridge_safe_fallback_improvement"
        incumbent_dir = best_fallback_dir

    incumbent = evaluate_submission(instance, incumbent_dir, scenario)
    verification = solve_flexible_supply_relaxation(
        instance,
        verification_raw,
        scenario,
        time_limit_seconds=verification_time_limit_seconds,
        workers=workers,
        seed=seed,
        closure_round_limit=closure_round_limit,
        sample_hint_dir=incumbent_dir,
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

    selected_stage = incumbent_stage
    selected_dir = incumbent_dir
    selected: Evaluation = incumbent
    if _candidate_is_better(verified, incumbent):
        selected_stage = improvement_stage
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
        "heuristic_telemetry": asdict(heuristic) if heuristic is not None else None,
        "heuristic_attempts": attempt_telemetry,
        "heuristic_prune": asdict(heuristic_prune) if heuristic_prune is not None else None,
        "bridge_safe_fallback_telemetry": asdict(fallback) if fallback is not None else None,
        "bridge_safe_repair_hint_source_attempt": repair_hint_attempt,
        "bridge_safe_fallback_attempts": fallback_attempt_telemetry,
        "bridge_safe_fallback_selected_attempt": selected_fallback_attempt,
        "bridge_safe_fallback_prune": asdict(fallback_prune) if fallback_prune is not None else None,
        "verification_telemetry": asdict(verification) if verification is not None else None,
        "verification_prune": asdict(verification_prune) if verification_prune is not None else None,
    }
    (audit_output / "STAGED.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return report
