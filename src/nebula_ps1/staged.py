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


def _scenario_b_cost_contributing_activities(
    instance: Instance, submission_dir: str | Path
) -> list[str]:
    """Return activities that directly participate in B's ECLO or excess costs."""

    access, occupancy, _ = load_submission(submission_dir)
    contributors = {row.activity_id for row in access if row.eclo == 1}
    groups_by_location_week: dict[tuple[int, str], set[str]] = {}
    activities_by_location_week: dict[tuple[int, str], set[str]] = {}
    for row in occupancy:
        key = (row.week, row.location_id)
        groups_by_location_week.setdefault(key, set()).add(row.co_share_group)
        activities_by_location_week.setdefault(key, set()).add(row.activity_id)
    for key, groups in groups_by_location_week.items():
        location_id = key[1]
        if len(groups) > instance.locations[location_id].supply_capacity:
            contributors.update(activities_by_location_week[key])
    return sorted(contributors)


def solve_staged_scenario(
    instance: Instance,
    output_dir: str | Path,
    scenario: str,
    *,
    audit_output_dir: str | Path | None = None,
    heuristic_time_limit_seconds: float = 120.0,
    local_repair_time_limit_seconds: float = 30.0,
    fallback_time_limit_seconds: float = 120.0,
    verification_time_limit_seconds: float = 120.0,
    verification_round_time_limit_seconds: float | None = None,
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
    heuristic_pruned: Path | None = None
    verification_raw = audit_output / "verification_raw"
    verification_pruned = audit_output / "verification_pruned"
    attempt_telemetry: list[dict[str, object]] = []
    heuristic: SolveTelemetry | None = None
    selected_heuristic_attempt: int | None = None
    safe_heuristic_candidates: list[tuple[int, SolveTelemetry, Path]] = []
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
            safe_heuristic_candidates.append((attempt + 1, attempt_result, attempt_output))
            continue
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
    heuristic_prune = None
    best_heuristic_evaluation: Evaluation | None = None
    for attempt_number, attempt_result, attempt_output in safe_heuristic_candidates:
        attempt_pruned = audit_output / f"heuristic_attempt_{attempt_number}_pruned"
        attempt_prune = prune_submission(
            instance,
            attempt_output,
            attempt_pruned,
            scenario,
            report_path=audit_output / f"HEURISTIC_ATTEMPT_{attempt_number}_PRUNE.json",
            forbid_buffer_overlap=forbid_buffer_overlap,
        )
        attempt_evaluation = evaluate_submission(instance, attempt_pruned, scenario)
        if best_heuristic_evaluation is None or _candidate_is_better(
            attempt_evaluation, best_heuristic_evaluation
        ):
            heuristic = attempt_result
            heuristic_raw = attempt_output
            heuristic_pruned = attempt_pruned
            heuristic_prune = attempt_prune
            selected_heuristic_attempt = attempt_number
            best_heuristic_evaluation = attempt_evaluation

    fallback: SolveTelemetry | None = None
    local_repair: SolveTelemetry | None = None
    local_repair_prune = None
    local_repair_activities: list[str] = []
    fallback_prune = None
    fallback_attempt_telemetry: list[dict[str, object]] = []
    selected_fallback_attempt: int | None = None
    if heuristic is not None and heuristic_raw is not None and heuristic_pruned is not None:
        incumbent_stage = "heuristic_incumbent"
        improvement_stage = "bridge_safe_improvement"
        incumbent_dir = heuristic_pruned
    else:
        best_fallback_evaluation: Evaluation | None = None
        best_fallback_dir: Path | None = None
        if repair_hint is not None:
            hint_access, hint_occupancy, _ = load_submission(repair_hint)
            hint_conflicts = screen_closures(
                instance,
                hint_access,
                hint_occupancy,
                forbid_buffer_overlap=forbid_buffer_overlap,
            )
            local_repair_activities = sorted(
                {
                    activity_id
                    for conflict in hint_conflicts
                    for activity_id in (
                        *conflict.first_activities,
                        *conflict.second_activities,
                    )
                }
            )
            if local_repair_activities:
                local_raw = audit_output / "bridge_safe_local_repair_raw"
                local_pruned = audit_output / "bridge_safe_local_repair_pruned"
                local_repair = solve_flexible_supply_relaxation(
                    instance,
                    local_raw,
                    scenario,
                    time_limit_seconds=local_repair_time_limit_seconds,
                    workers=workers,
                    seed=seed,
                    closure_round_limit=closure_round_limit,
                    sample_hint_dir=repair_hint,
                    forbid_buffer_overlap=forbid_buffer_overlap,
                    freeze_access_hint=True,
                    freeze_access_except=set(local_repair_activities),
                    separator_mode="bridge_safe",
                )
                if (
                    local_repair.objective_score is not None
                    and local_repair.remaining_closure_conflicts == 0
                ):
                    local_repair_prune = prune_submission(
                        instance,
                        local_raw,
                        local_pruned,
                        scenario,
                        report_path=audit_output / "LOCAL_REPAIR_PRUNE.json",
                        forbid_buffer_overlap=forbid_buffer_overlap,
                    )
                    fallback = local_repair
                    fallback_prune = local_repair_prune
                    best_fallback_evaluation = evaluate_submission(
                        instance, local_pruned, scenario
                    )
                    best_fallback_dir = local_pruned

        for fallback_attempt in range(fallback_attempts if fallback is None else 0):
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
        incumbent_stage = (
            "bridge_safe_local_repair"
            if local_repair_prune is not None
            else "bridge_safe_fallback"
        )
        improvement_stage = f"{incumbent_stage}_improvement"
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
        round_time_limit_seconds=(
            verification_round_time_limit_seconds
            if verification_round_time_limit_seconds is not None
            else (5.0 if scenario == "B" else None)
        ),
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

    cost_repair: SolveTelemetry | None = None
    cost_repair_prune = None
    cost_repair_activities: list[str] = []
    if scenario == "B" and local_repair_time_limit_seconds > 0:
        cost_repair_activities = _scenario_b_cost_contributing_activities(
            instance, selected_dir
        )
        if cost_repair_activities:
            cost_repair_raw = audit_output / "bridge_safe_cost_repair_raw"
            cost_repair_pruned = audit_output / "bridge_safe_cost_repair_pruned"
            cost_repair = solve_flexible_supply_relaxation(
                instance,
                cost_repair_raw,
                scenario,
                time_limit_seconds=local_repair_time_limit_seconds,
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
                    scenario,
                    report_path=audit_output / "COST_REPAIR_PRUNE.json",
                    forbid_buffer_overlap=forbid_buffer_overlap,
                )
                cost_repaired = evaluate_submission(
                    instance, cost_repair_pruned, scenario
                )
                if _candidate_is_better(cost_repaired, selected):
                    selected_stage = "bridge_safe_cost_repair"
                    selected_dir = cost_repair_pruned
                    selected = cost_repaired
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
        "heuristic_selected_attempt": selected_heuristic_attempt,
        "heuristic_prune": asdict(heuristic_prune) if heuristic_prune is not None else None,
        "bridge_safe_fallback_telemetry": asdict(fallback) if fallback is not None else None,
        "bridge_safe_local_repair_activities": local_repair_activities,
        "bridge_safe_local_repair_telemetry": (
            asdict(local_repair) if local_repair is not None else None
        ),
        "bridge_safe_local_repair_prune": (
            asdict(local_repair_prune) if local_repair_prune is not None else None
        ),
        "bridge_safe_repair_hint_source_attempt": repair_hint_attempt,
        "bridge_safe_fallback_attempts": fallback_attempt_telemetry,
        "bridge_safe_fallback_selected_attempt": selected_fallback_attempt,
        "bridge_safe_fallback_prune": asdict(fallback_prune) if fallback_prune is not None else None,
        "verification_telemetry": asdict(verification) if verification is not None else None,
        "verification_round_time_limit_seconds": (
            verification_round_time_limit_seconds
            if verification_round_time_limit_seconds is not None
            else (5.0 if scenario == "B" else None)
        ),
        "verification_prune": asdict(verification_prune) if verification_prune is not None else None,
        "bridge_safe_cost_repair_activities": cost_repair_activities,
        "bridge_safe_cost_repair_telemetry": (
            asdict(cost_repair) if cost_repair is not None else None
        ),
        "bridge_safe_cost_repair_prune": (
            asdict(cost_repair_prune) if cost_repair_prune is not None else None
        ),
    }
    (audit_output / "STAGED.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return report
