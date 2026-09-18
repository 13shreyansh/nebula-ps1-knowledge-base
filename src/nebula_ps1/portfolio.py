from __future__ import annotations

import json
import shutil
from dataclasses import asdict
from pathlib import Path

from .evaluate import Evaluation, evaluate_submission
from .flexible_solver import solve_flexible_supply_relaxation
from .instance import Instance
from .prune import prune_submission
from .submission import relabel_submission_scenario


SUBMISSION_FILES = ("SCHEDULE_ACCESS.csv", "SCHEDULE_OCCUPANCY.csv", "RESULTS.csv")


def _copy_submission(source: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    for name in SUBMISSION_FILES:
        shutil.copy2(source / name, destination / name)


def _candidate_is_better(candidate: Evaluation, incumbent: Evaluation) -> bool:
    return candidate.internally_feasible and (
        not incumbent.internally_feasible
        or candidate.objective_score < incumbent.objective_score
    )


def solve_scenario_c_portfolio(
    instance: Instance,
    output_dir: str | Path,
    *,
    audit_output_dir: str | Path | None = None,
    a_time_limit_seconds: float = 120.0,
    c_time_limit_seconds: float = 120.0,
    workers: int = 8,
    seed: int = 1,
    closure_round_limit: int = 500,
    a_round_time_limit_seconds: float = 1.0,
    c_round_time_limit_seconds: float = 3.0,
    forbid_buffer_overlap: bool = False,
) -> dict[str, object]:
    """Protect a checked A-as-C fallback before attempting a lower-scoring C solve.

    Scenario A is constructed from the current input without an external schedule.
    Its output is mechanically relabelled and checked under C, then used only as a
    search hint. A C candidate replaces the fallback only after the implemented
    checker accepts it at a strictly lower penalty.
    """

    output = Path(output_dir)
    audit_output = (
        Path(audit_output_dir)
        if audit_output_dir is not None
        else output.with_name(f"{output.name}_audit")
    )
    if output.exists() and any(output.iterdir()):
        raise ValueError(f"portfolio output directory must be empty: {output}")
    if audit_output.exists() and any(audit_output.iterdir()):
        raise ValueError(f"portfolio audit directory must be empty: {audit_output}")
    output.mkdir(parents=True, exist_ok=True)
    audit_output.mkdir(parents=True, exist_ok=True)
    stages = audit_output / "stages"
    a_stage = stages / "scenario_a"
    fallback_raw_stage = stages / "scenario_c_fallback_raw"
    fallback_stage = stages / "scenario_c_fallback_pruned"
    candidate_raw_stage = stages / "scenario_c_candidate_raw"
    candidate_stage = stages / "scenario_c_candidate_pruned"

    a_telemetry = solve_flexible_supply_relaxation(
        instance,
        a_stage,
        "A",
        time_limit_seconds=a_time_limit_seconds,
        workers=workers,
        seed=seed,
        closure_round_limit=closure_round_limit,
        round_time_limit_seconds=a_round_time_limit_seconds,
        forbid_buffer_overlap=forbid_buffer_overlap,
    )
    if a_telemetry.objective_score is None or a_telemetry.remaining_closure_conflicts:
        raise RuntimeError("Scenario A stage did not produce a closure-safe fallback")

    relabel_submission_scenario(instance, a_stage, fallback_raw_stage, "C")
    fallback_prune = prune_submission(
        instance,
        fallback_raw_stage,
        fallback_stage,
        "C",
        report_path=audit_output / "FALLBACK_PRUNE.json",
        forbid_buffer_overlap=forbid_buffer_overlap,
    )
    fallback = evaluate_submission(instance, fallback_stage, "C")
    if not fallback.internally_feasible:
        raise RuntimeError(
            "Scenario A output was not a valid Scenario C fallback: "
            + "; ".join(fallback.hard_violations)
        )

    c_telemetry = solve_flexible_supply_relaxation(
        instance,
        candidate_raw_stage,
        "C",
        time_limit_seconds=c_time_limit_seconds,
        workers=workers,
        seed=seed,
        closure_round_limit=closure_round_limit,
        sample_hint_dir=fallback_stage,
        round_time_limit_seconds=c_round_time_limit_seconds,
        forbid_buffer_overlap=forbid_buffer_overlap,
    )
    candidate: Evaluation | None = None
    candidate_prune: dict[str, object] | None = None
    if all((candidate_raw_stage / name).is_file() for name in SUBMISSION_FILES):
        prune_report = prune_submission(
            instance,
            candidate_raw_stage,
            candidate_stage,
            "C",
            report_path=audit_output / "CANDIDATE_PRUNE.json",
            forbid_buffer_overlap=forbid_buffer_overlap,
        )
        candidate_prune = asdict(prune_report)
        candidate = evaluate_submission(instance, candidate_stage, "C")

    selected_name = "scenario_c_fallback"
    selected_dir = fallback_stage
    selected = fallback
    if candidate is not None and _candidate_is_better(candidate, fallback):
        selected_name = "scenario_c_candidate"
        selected_dir = candidate_stage
        selected = candidate
    _copy_submission(selected_dir, output)

    final = evaluate_submission(instance, output, "C")
    if not final.internally_feasible or final.submission_hash != selected.submission_hash:
        raise RuntimeError("portfolio final-copy verification failed")

    report: dict[str, object] = {
        "scenario": "C",
        "selection_rule": "strictly lower internally checked objective; otherwise preserve fallback",
        "selected_stage": selected_name,
        "selected_objective_score": final.objective_score,
        "selected_submission_hash": final.submission_hash,
        "reference_validator_confirmed": False,
        "strict_buffer_overlap_checked": forbid_buffer_overlap,
        "submission_files": list(SUBMISSION_FILES),
        "scenario_a_telemetry": asdict(a_telemetry),
        "scenario_c_telemetry": asdict(c_telemetry),
        "fallback_objective_score": fallback.objective_score,
        "fallback_prune": asdict(fallback_prune),
        "candidate_objective_score": (
            candidate.objective_score if candidate is not None else None
        ),
        "candidate_internally_feasible": (
            candidate.internally_feasible if candidate is not None else False
        ),
        "candidate_hard_violations": (
            list(candidate.hard_violations) if candidate is not None else ["no candidate output"]
        ),
        "candidate_prune": candidate_prune,
    }
    (audit_output / "PORTFOLIO.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    if sorted(path.name for path in output.iterdir()) != sorted(SUBMISSION_FILES):
        raise RuntimeError("portfolio submission directory contains files beyond the three CSVs")
    return report
