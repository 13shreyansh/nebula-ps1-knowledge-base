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
from .staged import _scenario_b_cost_contributing_activities, solve_staged_scenario
from .submission import relabel_submission_scenario


def solve_staged_c_portfolio(
    instance: Instance,
    output_dir: str | Path,
    *,
    audit_output_dir: str | Path | None = None,
    a_heuristic_time_limit_seconds: float = 120.0,
    a_local_repair_time_limit_seconds: float = 30.0,
    a_fallback_time_limit_seconds: float = 120.0,
    a_verification_time_limit_seconds: float = 120.0,
    c_heuristic_time_limit_seconds: float = 120.0,
    c_verification_time_limit_seconds: float = 120.0,
    workers: int = 8,
    seed: int = 1,
    a_heuristic_attempts: int = 3,
    a_fallback_attempts: int = 2,
    c_heuristic_attempts: int = 3,
    closure_round_limit: int = 500,
    forbid_buffer_overlap: bool = False,
) -> dict[str, object]:
    """Construct A safely, then generate and soundly verify a lower C score."""

    if c_heuristic_attempts < 1:
        raise ValueError("c_heuristic_attempts must be positive")

    output = Path(output_dir)
    audit_output = (
        Path(audit_output_dir)
        if audit_output_dir is not None
        else output.with_name(f"{output.name}_audit")
    )
    if output.exists() and any(output.iterdir()):
        raise ValueError(f"staged C output directory must be empty: {output}")
    if audit_output.exists() and any(audit_output.iterdir()):
        raise ValueError(f"staged C audit directory must be empty: {audit_output}")
    output.mkdir(parents=True, exist_ok=True)
    audit_output.mkdir(parents=True, exist_ok=True)

    stages = audit_output / "stages"
    a_stage = stages / "scenario_a"
    a_audit = stages / "scenario_a_audit"
    fallback_raw = stages / "scenario_c_fallback_raw"
    fallback_pruned = stages / "scenario_c_fallback_pruned"
    verification_raw = stages / "scenario_c_verification_raw"
    verification_pruned = stages / "scenario_c_verification_pruned"

    try:
        a_report = solve_staged_scenario(
            instance,
            a_stage,
            "A",
            audit_output_dir=a_audit,
            heuristic_time_limit_seconds=a_heuristic_time_limit_seconds,
            local_repair_time_limit_seconds=a_local_repair_time_limit_seconds,
            fallback_time_limit_seconds=a_fallback_time_limit_seconds,
            verification_time_limit_seconds=a_verification_time_limit_seconds,
            workers=workers,
            seed=seed,
            heuristic_attempts=a_heuristic_attempts,
            fallback_attempts=a_fallback_attempts,
            closure_round_limit=closure_round_limit,
            forbid_buffer_overlap=forbid_buffer_overlap,
        )
    except RuntimeError as error:
        if str(error) != (
            "neither direct heuristic nor bridge-safe fallback produced a checked safe incumbent"
        ):
            raise
        direct_report = solve_staged_scenario(
            instance,
            output,
            "C",
            audit_output_dir=stages / "scenario_c_direct_after_a_failure_audit",
            heuristic_time_limit_seconds=c_heuristic_time_limit_seconds,
            local_repair_time_limit_seconds=a_local_repair_time_limit_seconds,
            fallback_time_limit_seconds=a_fallback_time_limit_seconds,
            verification_time_limit_seconds=c_verification_time_limit_seconds,
            workers=workers,
            seed=seed,
            heuristic_attempts=c_heuristic_attempts,
            fallback_attempts=a_fallback_attempts,
            closure_round_limit=closure_round_limit,
            forbid_buffer_overlap=forbid_buffer_overlap,
        )
        report: dict[str, object] = {
            "scenario": "C",
            "selected_stage": "scenario_c_direct_after_a_failure",
            "selected_objective_score": direct_report["selected_objective_score"],
            "selected_submission_hash": direct_report["selected_submission_hash"],
            "selection_rule": "use checked direct C only when guarded A construction fails",
            "strict_buffer_overlap_checked": forbid_buffer_overlap,
            "reference_validator_confirmed": False,
            "submission_files": list(SUBMISSION_FILES),
            "scenario_a_failure": str(error),
            "direct_c_staged_report": direct_report,
        }
        (audit_output / "STAGED_C.json").write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return report
    relabel_submission_scenario(instance, a_stage, fallback_raw, "C")
    fallback_prune = prune_submission(
        instance,
        fallback_raw,
        fallback_pruned,
        "C",
        report_path=audit_output / "FALLBACK_PRUNE.json",
        forbid_buffer_overlap=forbid_buffer_overlap,
    )
    fallback = evaluate_submission(instance, fallback_pruned, "C")
    if not fallback.internally_feasible:
        raise RuntimeError("staged A output did not produce a valid Scenario C fallback")

    heuristic_attempt_records: list[dict[str, object]] = []
    heuristic_best: Evaluation = fallback
    heuristic_best_dir = fallback_pruned
    selected_heuristic_attempt: int | None = None
    for attempt in range(c_heuristic_attempts):
        attempt_number = attempt + 1
        attempt_raw = stages / f"scenario_c_heuristic_attempt_{attempt_number}_raw"
        attempt_pruned = stages / f"scenario_c_heuristic_attempt_{attempt_number}_pruned"
        attempt_telemetry = solve_flexible_supply_relaxation(
            instance,
            attempt_raw,
            "C",
            time_limit_seconds=c_heuristic_time_limit_seconds,
            workers=workers,
            seed=seed + attempt,
            closure_round_limit=closure_round_limit,
            # The first challenger must be independent of the A-derived
            # fallback. Otherwise a feasible but poor A schedule can suppress
            # the structural C construction that handles ECLO/excess tradeoffs.
            sample_hint_dir=None if attempt == 0 else fallback_pruned,
            forbid_buffer_overlap=forbid_buffer_overlap,
            separator_mode="direct_heuristic",
            use_structural_hints=attempt == 0,
        )
        attempt_record: dict[str, object] = {
            "attempt": attempt_number,
            "telemetry": asdict(attempt_telemetry),
        }
        if (
            attempt_telemetry.objective_score is not None
            and attempt_telemetry.remaining_closure_conflicts == 0
        ):
            prune_report = prune_submission(
                instance,
                attempt_raw,
                attempt_pruned,
                "C",
                report_path=audit_output / f"C_HEURISTIC_ATTEMPT_{attempt_number}_PRUNE.json",
                forbid_buffer_overlap=forbid_buffer_overlap,
            )
            candidate = evaluate_submission(instance, attempt_pruned, "C")
            attempt_record["prune"] = asdict(prune_report)
            if _candidate_is_better(candidate, heuristic_best):
                heuristic_best = candidate
                heuristic_best_dir = attempt_pruned
                selected_heuristic_attempt = attempt_number
        heuristic_attempt_records.append(attempt_record)

    verification_telemetry = solve_flexible_supply_relaxation(
        instance,
        verification_raw,
        "C",
        time_limit_seconds=c_verification_time_limit_seconds,
        workers=workers,
        seed=seed,
        closure_round_limit=closure_round_limit,
        sample_hint_dir=heuristic_best_dir,
        forbid_buffer_overlap=forbid_buffer_overlap,
        separator_mode="bridge_safe",
    )
    verification_prune = prune_submission(
        instance,
        verification_raw,
        verification_pruned,
        "C",
        report_path=audit_output / "C_VERIFICATION_PRUNE.json",
        forbid_buffer_overlap=forbid_buffer_overlap,
    )
    verified = evaluate_submission(instance, verification_pruned, "C")

    selected_stage = "scenario_c_fallback"
    selected_dir = fallback_pruned
    selected = fallback
    if _candidate_is_better(heuristic_best, selected):
        selected_stage = "scenario_c_heuristic"
        selected_dir = heuristic_best_dir
        selected = heuristic_best
    if _candidate_is_better(verified, selected):
        selected_stage = "scenario_c_bridge_safe_improvement"
        selected_dir = verification_pruned
        selected = verified

    cost_repair = None
    cost_repair_prune = None
    cost_repair_activities: list[str] = []
    if a_local_repair_time_limit_seconds > 0:
        cost_repair_activities = _scenario_b_cost_contributing_activities(
            instance,
            selected_dir,
            expand_footprints=True,
            expand_contracts=True,
            expand_precedence=True,
            revisit_precedence_after_footprints=True,
            include_delays=True,
        )
        if cost_repair_activities:
            cost_repair_raw = stages / "scenario_c_cost_repair_raw"
            cost_repair_pruned = stages / "scenario_c_cost_repair_pruned"
            cost_repair = solve_flexible_supply_relaxation(
                instance,
                cost_repair_raw,
                "C",
                time_limit_seconds=a_local_repair_time_limit_seconds,
                workers=workers,
                seed=seed,
                closure_round_limit=closure_round_limit,
                sample_hint_dir=selected_dir,
                round_time_limit_seconds=5.0,
                forbid_buffer_overlap=forbid_buffer_overlap,
                freeze_access_hint=True,
                freeze_access_except=set(cost_repair_activities),
                separator_mode="bridge_safe",
            )
            if (
                cost_repair.objective_score is not None
                and cost_repair.remaining_closure_conflicts == 0
            ):
                cost_repair_prune = prune_submission(
                    instance,
                    cost_repair_raw,
                    cost_repair_pruned,
                    "C",
                    report_path=audit_output / "C_COST_REPAIR_PRUNE.json",
                    forbid_buffer_overlap=forbid_buffer_overlap,
                )
                repaired = evaluate_submission(instance, cost_repair_pruned, "C")
                if _candidate_is_better(repaired, selected):
                    selected_stage = "scenario_c_cost_repair"
                    selected_dir = cost_repair_pruned
                    selected = repaired
    _copy_submission(selected_dir, output)

    final = evaluate_submission(instance, output, "C")
    access, occupancy, _ = load_submission(output)
    strict_conflicts = (
        screen_closures(instance, access, occupancy, forbid_buffer_overlap=True)
        if forbid_buffer_overlap
        else ()
    )
    if (
        not final.internally_feasible
        or strict_conflicts
        or final.submission_hash != selected.submission_hash
    ):
        raise RuntimeError("staged C final-copy verification failed")
    if sorted(path.name for path in output.iterdir()) != sorted(SUBMISSION_FILES):
        raise RuntimeError("staged C submission directory contains files beyond the three CSVs")

    report: dict[str, object] = {
        "scenario": "C",
        "selected_stage": selected_stage,
        "selected_objective_score": final.objective_score,
        "selected_submission_hash": final.submission_hash,
        "fallback_objective_score": fallback.objective_score,
        "heuristic_best_objective_score": heuristic_best.objective_score,
        "verified_objective_score": verified.objective_score,
        "selection_rule": "strictly lower fully checked C objective; otherwise preserve the checked incumbent",
        "strict_buffer_overlap_checked": forbid_buffer_overlap,
        "reference_validator_confirmed": False,
        "submission_files": list(SUBMISSION_FILES),
        "scenario_a_staged_report": a_report,
        "fallback_prune": asdict(fallback_prune),
        "scenario_c_heuristic_attempts": heuristic_attempt_records,
        "scenario_c_heuristic_selected_attempt": selected_heuristic_attempt,
        "scenario_c_verification_telemetry": asdict(verification_telemetry),
        "scenario_c_verification_prune": asdict(verification_prune),
        "scenario_c_cost_repair_activities": cost_repair_activities,
        "scenario_c_cost_repair_telemetry": (
            asdict(cost_repair) if cost_repair is not None else None
        ),
        "scenario_c_cost_repair_prune": (
            asdict(cost_repair_prune) if cost_repair_prune is not None else None
        ),
    }
    (audit_output / "STAGED_C.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return report
