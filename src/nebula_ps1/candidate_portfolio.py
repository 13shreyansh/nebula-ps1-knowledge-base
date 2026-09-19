from __future__ import annotations

import json
import time
from pathlib import Path

from .closure import screen_closures
from .decomposed import (
    _primary_proof_telemetry,
    _publish_submission_atomically,
    independent_activity_components,
    solve_decomposed_scenario,
)
from .evaluate import Evaluation, evaluate_submission, load_submission
from .independent_score import independently_score
from .instance import Instance, load_instance
from .portfolio import SUBMISSION_FILES
from .staged import solve_staged_scenario


def _externally_gate_candidate(
    instance: Instance,
    data_root: Path,
    candidate: Path,
    scenario: str,
    *,
    forbid_buffer_overlap: bool,
) -> Evaluation:
    if sorted(path.name for path in candidate.iterdir()) != sorted(SUBMISSION_FILES):
        raise RuntimeError("candidate does not contain exactly the three submission CSVs")
    evaluation = evaluate_submission(instance, candidate, scenario)
    access, occupancy, _ = load_submission(candidate)
    conflicts = screen_closures(
        instance,
        access,
        occupancy,
        forbid_buffer_overlap=forbid_buffer_overlap,
    )
    if not evaluation.internally_feasible or conflicts:
        details = list(evaluation.hard_violations)
        details.extend(conflict.describe() for conflict in conflicts)
        raise RuntimeError("candidate failed full feasibility: " + "; ".join(details))
    independent = independently_score(data_root, candidate)
    comparisons = {
        "scenario": (evaluation.scenario, independent.scenario),
        "objective_score": (evaluation.objective_score, independent.objective_score),
        "priority_weighted_score": (
            evaluation.priority_weighted_score,
            independent.priority_weighted_delay,
        ),
        "excess_access_nights_total": (
            evaluation.excess_access_nights_total,
            independent.excess_access_nights,
        ),
        "eclo_nights_total": (
            evaluation.eclo_nights_total,
            independent.eclo_nights,
        ),
        "access_rows": (evaluation.access_rows, independent.access_rows),
        "occupancy_rows": (evaluation.occupancy_rows, independent.occupancy_rows),
    }
    mismatches = [
        f"{field} primary={primary!r} independent={second!r}"
        for field, (primary, second) in comparisons.items()
        if primary != second
    ]
    if mismatches:
        raise RuntimeError("candidate failed independent score agreement: " + "; ".join(mismatches))
    return evaluation


def solve_candidate_portfolio(
    data_dir: str | Path,
    output_dir: str | Path,
    scenario: str,
    *,
    audit_output_dir: str | Path | None = None,
    initial_submission_dir: str | Path | None = None,
    heuristic_time_limit_seconds: float = 3.0,
    local_repair_time_limit_seconds: float = 2.0,
    fallback_time_limit_seconds: float = 5.0,
    verification_time_limit_seconds: float = 10.0,
    workers: int = 1,
    seed: int = 1,
    heuristic_attempts: int = 1,
    fallback_attempts: int = 1,
    closure_round_limit: int = 1000,
    forbid_buffer_overlap: bool = False,
) -> dict[str, object]:
    """Run independent safe policies and publish only the best fully gated candidate."""

    if scenario not in {"A", "B", "C"}:
        raise ValueError("scenario must be A, B, or C")
    data_root = Path(data_dir).resolve()
    output = Path(output_dir)
    audit = (
        Path(audit_output_dir)
        if audit_output_dir is not None
        else output.with_name(f"{output.name}_audit")
    )
    for label, path in (("output", output), ("audit", audit)):
        if path.exists() and (not path.is_dir() or any(path.iterdir())):
            raise ValueError(f"portfolio {label} directory must be empty: {path}")
    audit.mkdir(parents=True, exist_ok=True)
    instance = load_instance(data_root)
    components = independent_activity_components(
        instance,
        scenario,
        forbid_buffer_overlap=forbid_buffer_overlap,
    )
    common = {
        "heuristic_time_limit_seconds": heuristic_time_limit_seconds,
        "local_repair_time_limit_seconds": local_repair_time_limit_seconds,
        "fallback_time_limit_seconds": fallback_time_limit_seconds,
        "verification_time_limit_seconds": verification_time_limit_seconds,
        "workers": workers,
        "seed": seed,
        "heuristic_attempts": heuristic_attempts,
        "fallback_attempts": fallback_attempts,
        "closure_round_limit": closure_round_limit,
        "forbid_buffer_overlap": forbid_buffer_overlap,
    }
    attempts: list[dict[str, object]] = []
    candidates: list[tuple[int, str, Path, Evaluation, bool]] = []

    if initial_submission_dir is not None:
        initial = Path(initial_submission_dir)
        evaluation = _externally_gate_candidate(
            instance,
            data_root,
            initial,
            scenario,
            forbid_buffer_overlap=forbid_buffer_overlap,
        )
        candidates.append((0, "initial_incumbent", initial, evaluation, False))
        attempts.append(
            {
                "policy": "initial_incumbent",
                "status": "accepted",
                "objective_score": evaluation.objective_score,
                "submission_hash": evaluation.submission_hash,
                "global_optimality_proved": False,
            }
        )

    def assert_proof_consistent(policy: str, proved_score: float) -> None:
        contradictory = [
            (candidate_policy, evaluation.objective_score)
            for _, candidate_policy, _, evaluation, _ in candidates
            if evaluation.objective_score < proved_score
        ]
        if contradictory:
            raise RuntimeError(
                f"{policy} full-instance proof contradicts a lower fully gated "
                f"candidate: proof={proved_score!r}, "
                f"lower_candidates={contradictory!r}"
            )

    def run_monolithic() -> float | None:
        monolithic_output = audit / "monolithic_submission"
        started = time.perf_counter()
        try:
            monolithic_report = solve_staged_scenario(
                instance,
                monolithic_output,
                scenario,
                audit_output_dir=audit / "monolithic_audit",
                initial_submission_dir=initial_submission_dir,
                initial_score_data_dir=data_root if initial_submission_dir else None,
                **common,
            )
            evaluation = _externally_gate_candidate(
                instance,
                data_root,
                monolithic_output,
                scenario,
                forbid_buffer_overlap=forbid_buffer_overlap,
            )
            proved = _primary_proof_telemetry(monolithic_report) is not None
            candidates.append(
                (1, "monolithic", monolithic_output, evaluation, proved)
            )
            attempts.append(
                {
                    "policy": "monolithic",
                    "status": "accepted",
                    "outer_wall_time_seconds": time.perf_counter() - started,
                    "objective_score": evaluation.objective_score,
                    "submission_hash": evaluation.submission_hash,
                    "global_optimality_proved": proved,
                }
            )
        except (RuntimeError, ValueError) as error:
            attempts.append(
                {
                    "policy": "monolithic",
                    "status": "failed",
                    "outer_wall_time_seconds": time.perf_counter() - started,
                    "error_type": type(error).__name__,
                    "error": str(error),
                }
            )
            return None
        if proved:
            assert_proof_consistent("monolithic", evaluation.objective_score)
            return evaluation.objective_score
        return None

    def run_decomposed() -> float | None:
        decomposed_output = audit / "decomposed_submission"
        started = time.perf_counter()
        try:
            decomposed_report = solve_decomposed_scenario(
                data_root,
                decomposed_output,
                scenario,
                audit_output_dir=audit / "decomposed_audit",
                **common,
            )
            evaluation = _externally_gate_candidate(
                instance,
                data_root,
                decomposed_output,
                scenario,
                forbid_buffer_overlap=forbid_buffer_overlap,
            )
            proved = bool(
                decomposed_report["global_optimality_proved_by_additivity"]
            )
            candidates.append(
                (2, "decomposed", decomposed_output, evaluation, proved)
            )
            attempts.append(
                {
                    "policy": "decomposed",
                    "status": "accepted",
                    "outer_wall_time_seconds": time.perf_counter() - started,
                    "objective_score": evaluation.objective_score,
                    "submission_hash": evaluation.submission_hash,
                    "global_optimality_proved": proved,
                }
            )
        except (RuntimeError, ValueError) as error:
            attempts.append(
                {
                    "policy": "decomposed",
                    "status": "failed",
                    "outer_wall_time_seconds": time.perf_counter() - started,
                    "error_type": type(error).__name__,
                    "error": str(error),
                }
            )
            return None
        if proved:
            assert_proof_consistent("decomposed", evaluation.objective_score)
            return evaluation.objective_score
        return None

    if len(components) > 1:
        decomposed_proved_score = run_decomposed()
        if decomposed_proved_score is None:
            run_monolithic()
        else:
            attempts.append(
                {
                    "policy": "monolithic",
                    "status": "skipped",
                    "reason": (
                        "decomposed full-instance additive proof leaves no lower "
                        "primary objective for monolithic search to find"
                    ),
                    "proof_policy": "decomposed",
                    "proved_objective_score": decomposed_proved_score,
                }
            )
    else:
        run_monolithic()
        attempts.append(
            {
                "policy": "decomposed",
                "status": "skipped",
                "reason": "one component; identical staged policy adds no search diversity",
            }
        )

    if not candidates:
        failure_report = {
            "scenario": scenario,
            "dataset_hash": instance.dataset_hash,
            "component_count": len(components),
            "attempts": attempts,
            "publication_status": "not_published",
        }
        (audit / "CANDIDATE_PORTFOLIO_FAILURE.json").write_text(
            json.dumps(failure_report, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        raise RuntimeError("candidate portfolio produced no fully gated submission")

    priority, selected_policy, selected_dir, selected, selected_proved = min(
        candidates,
        key=lambda item: (item[3].objective_score, item[0]),
    )
    del priority
    selected_optimality_proof_policies = [
        policy
        for _, policy, _, evaluation, proved in candidates
        if proved and evaluation.objective_score == selected.objective_score
    ]
    selected_proved = bool(selected_optimality_proof_policies)
    report: dict[str, object] = {
        "scenario": scenario,
        "dataset_hash": instance.dataset_hash,
        "component_count": len(components),
        "execution_order": [
            attempt["policy"]
            for attempt in attempts
            if attempt["policy"] != "initial_incumbent"
        ],
        "selection_rule": (
            "lowest fully gated objective; exact ties preserve initial incumbent, "
            "then monolithic, then decomposed"
        ),
        "attempts": attempts,
        "selected_policy": selected_policy,
        "selected_objective_score": selected.objective_score,
        "selected_submission_hash": selected.submission_hash,
        "selected_global_optimality_proved": selected_proved,
        "selected_optimality_proof_policies": selected_optimality_proof_policies,
        "reference_validator_confirmed": False,
        "publication_status": "staged",
    }
    report_path = audit / "CANDIDATE_PORTFOLIO.json"
    report_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    _publish_submission_atomically(selected_dir, output)
    final = _externally_gate_candidate(
        instance,
        data_root,
        output,
        scenario,
        forbid_buffer_overlap=forbid_buffer_overlap,
    )
    if final.submission_hash != selected.submission_hash:
        raise RuntimeError("portfolio atomic publication changed the selected candidate")
    report["publication_status"] = "published"
    temporary_report = audit / ".CANDIDATE_PORTFOLIO.json.tmp"
    temporary_report.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary_report.replace(report_path)
    return report
