from __future__ import annotations

from pathlib import Path

from .eclo_compact import best_serialized_eclo_compaction_sequence
from .evaluate import Evaluation, evaluate_submission
from .idle_compact import best_idle_week_compaction_sequence
from .instance import Instance


def best_checked_c_postprocessing_sequence(
    instance: Instance,
    source_dir: str | Path,
    candidates_dir: str | Path,
    *,
    forbid_buffer_overlap: bool = False,
) -> tuple[Path, Evaluation, dict[str, object]]:
    """Run checked idle normalization and ECLO compaction on a final C candidate."""

    source = Path(source_dir)
    root = Path(candidates_dir)
    source_evaluation = evaluate_submission(instance, source, "C")
    selected_dir = source
    selected = source_evaluation

    idle_dir, idle, idle_report = best_idle_week_compaction_sequence(
        instance,
        source,
        root / "idle_week_candidates",
        forbid_buffer_overlap=forbid_buffer_overlap,
        allow_equal=True,
    )
    compaction_source_dir = source
    idle_used_as_seed = False
    idle_promoted = False
    if (
        idle_dir is not None
        and idle is not None
        and idle.internally_feasible
        and idle.objective_score <= source_evaluation.objective_score
    ):
        compaction_source_dir = idle_dir
        idle_used_as_seed = True
        if idle.objective_score < selected.objective_score:
            selected_dir = idle_dir
            selected = idle
            idle_promoted = True

    eclo_dir, eclo, eclo_report = best_serialized_eclo_compaction_sequence(
        instance,
        compaction_source_dir,
        root / "eclo_candidates",
        forbid_buffer_overlap=forbid_buffer_overlap,
    )
    eclo_promoted = False
    if (
        eclo_dir is not None
        and eclo is not None
        and eclo.internally_feasible
        and eclo.objective_score < selected.objective_score
    ):
        selected_dir = eclo_dir
        selected = eclo
        eclo_promoted = True

    report: dict[str, object] = {
        "source_score": source_evaluation.objective_score,
        "idle_week_compaction": idle_report,
        "idle_week_compaction_used_as_seed": idle_used_as_seed,
        "idle_week_compaction_promoted": idle_promoted,
        "eclo_compaction": eclo_report,
        "eclo_compaction_promoted": eclo_promoted,
        "selected_score": selected.objective_score,
        "selected_submission_hash": selected.submission_hash,
        "strict_improvement": (
            selected.objective_score < source_evaluation.objective_score
        ),
        "selected_stage": (
            "eclo_compaction"
            if eclo_promoted
            else "idle_week_compaction"
            if idle_promoted
            else None
        ),
    }
    return selected_dir, selected, report
