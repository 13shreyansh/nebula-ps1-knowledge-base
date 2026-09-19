from __future__ import annotations

import csv
from collections import defaultdict
from dataclasses import asdict
from pathlib import Path

from .closure import screen_closures
from .evaluate import (
    AccessRow,
    Evaluation,
    OccupancyRow,
    evaluate_submission,
    load_submission,
)
from .instance import Instance
from .topology import affects_interchange_cross_line, split_sector_location


def _affected_eclo_lines(instance: Instance, activity_id: str) -> set[str]:
    activity = instance.activities[activity_id]
    line, _, _ = split_sector_location(activity.start_location_id)
    if affects_interchange_cross_line(instance, activity):
        return set(instance.lines)
    return {line}


def _write(
    path: Path, fields: tuple[str, ...], rows: list[dict[str, object]]
) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _write_candidate(
    instance: Instance,
    access: list[AccessRow],
    occupancy: list[OccupancyRow],
    output_dir: Path,
    activity_id: str,
    removed_week: int,
) -> None:
    occupied_weeks = sorted({row.week for row in access})
    week_map = {
        week: week - int(week > removed_week)
        for week in occupied_weeks
        if week != removed_week
    }
    target_weeks = {
        row.week
        for row in access
        if row.activity_id == activity_id and row.week != removed_week
    }

    by_activity: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in access:
        if row.activity_id == activity_id and row.week == removed_week:
            continue
        by_activity[row.activity_id].append(
            {
                "activity_id": row.activity_id,
                "access_seq": row.access_seq,
                "week": week_map[row.week],
                "eclo": (
                    int(row.week in target_weeks)
                    if row.activity_id == activity_id
                    else row.eclo
                ),
                "access_night": row.access_night,
            }
        )
    output_access: list[dict[str, object]] = []
    for current_activity in sorted(by_activity):
        for sequence, row in enumerate(
            sorted(by_activity[current_activity], key=lambda item: int(item["week"])),
            1,
        ):
            row["access_seq"] = sequence
            output_access.append(row)

    output_occupancy = [
        {
            "activity_id": row.activity_id,
            "week": week_map[row.week],
            "location_id": row.location_id,
            "co_share_group": row.co_share_group,
        }
        for row in occupancy
        if not (row.activity_id == activity_id and row.week == removed_week)
    ]
    completion_by_activity = {
        current_activity: max(int(row["week"]) for row in rows)
        for current_activity, rows in by_activity.items()
    }
    completion_by_contract: dict[str, int] = defaultdict(int)
    for current_activity, week in completion_by_activity.items():
        contract = instance.activities[current_activity].contract_number
        completion_by_contract[contract] = max(completion_by_contract[contract], week)
    output_results = []
    for contract in sorted(instance.projects):
        project = instance.projects[contract]
        completion = instance.completion_date(completion_by_contract[contract])
        output_results.append(
            {
                "scenario": "C",
                "contract_number": contract,
                "simulated_completion_date": completion.isoformat(),
                "overrun_days": max(0, (completion - project.planned_completion_date).days),
            }
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    _write(
        output_dir / "SCHEDULE_ACCESS.csv",
        ("activity_id", "access_seq", "week", "eclo", "access_night"),
        output_access,
    )
    _write(
        output_dir / "SCHEDULE_OCCUPANCY.csv",
        ("activity_id", "week", "location_id", "co_share_group"),
        output_occupancy,
    )
    _write(
        output_dir / "RESULTS.csv",
        ("scenario", "contract_number", "simulated_completion_date", "overrun_days"),
        output_results,
    )


def _candidate_signature(
    access: list[AccessRow],
    occupancy: list[OccupancyRow],
    activity_id: str,
    removed_week: int,
) -> tuple[tuple[object, ...], ...]:
    occupied_weeks = sorted({row.week for row in access})
    week_map = {
        week: week - int(week > removed_week)
        for week in occupied_weeks
        if week != removed_week
    }
    target_weeks = {
        row.week
        for row in access
        if row.activity_id == activity_id and row.week != removed_week
    }
    transformed_access = tuple(
        sorted(
            (
                "access",
                row.activity_id,
                week_map[row.week],
                (
                    int(row.week in target_weeks)
                    if row.activity_id == activity_id
                    else row.eclo
                ),
                row.access_night,
            )
            for row in access
            if not (row.activity_id == activity_id and row.week == removed_week)
        )
    )
    transformed_occupancy = tuple(
        sorted(
            (
                "occupancy",
                row.activity_id,
                week_map[row.week],
                row.location_id,
                row.co_share_group,
            )
            for row in occupancy
            if not (row.activity_id == activity_id and row.week == removed_week)
        )
    )
    return (*transformed_access, *transformed_occupancy)


def _predicted_objective(
    instance: Instance,
    access: list[AccessRow],
    activity_id: str,
    removed_week: int,
) -> float:
    """Return the exact C objective if this serialized transform is feasible."""

    occupied_weeks = sorted({row.week for row in access})
    week_map = {
        week: week - int(week > removed_week)
        for week in occupied_weeks
        if week != removed_week
    }
    completion_by_activity: dict[str, int] = defaultdict(int)
    eclo_total = 0
    for row in access:
        if row.activity_id == activity_id and row.week == removed_week:
            continue
        completion_by_activity[row.activity_id] = max(
            completion_by_activity[row.activity_id], week_map[row.week]
        )
        eclo_total += int(row.activity_id == activity_id or row.eclo == 1)

    completion_by_contract: dict[str, int] = defaultdict(int)
    for current_activity, week in completion_by_activity.items():
        contract = instance.activities[current_activity].contract_number
        completion_by_contract[contract] = max(completion_by_contract[contract], week)
    contract_weight = {1: 100.0, 2: 10.0, 3: 1.0}
    activity_nudge = {1: 0.3, 2: 0.2, 3: 0.0}
    delay_score = 0.0
    for contract, project in instance.projects.items():
        completion = instance.completion_date(completion_by_contract[contract])
        delay_days = max(0, (completion - project.planned_completion_date).days)
        for current_activity in instance.activities.values():
            if current_activity.contract_number != contract:
                continue
            delay_score += (
                delay_days
                * contract_weight[project.contract_priority]
                * (1.0 + activity_nudge[current_activity.activity_priority])
            )
    return round(delay_score + 5.0 * eclo_total, 10)


def best_single_lane_eclo_compaction(
    instance: Instance,
    source_dir: str | Path,
    candidates_dir: str | Path,
    *,
    forbid_buffer_overlap: bool = False,
    exhaustive: bool = False,
) -> tuple[Path | None, Evaluation | None, dict[str, object]]:
    """Try a checked two-week ECLO compression on a serialized single lane.

    The transformation is deliberately narrow and never constrains search. It
    applies only when the incumbent has one activity per occupied week and no
    gaps. It ranks legal three-standard-to-two-ECLO transformations by their
    exact serialized score, then fully checks the first potentially optimal
    candidate. The caller may promote only a strictly lower checked result;
    exhaustive mode evaluates every unique transformation for audits.
    """

    source = Path(source_dir)
    root = Path(candidates_dir)
    access, occupancy, _ = load_submission(source)
    source_evaluation = evaluate_submission(instance, source, "C")
    activities_by_week: dict[int, set[str]] = defaultdict(set)
    for row in access:
        activities_by_week[row.week].add(row.activity_id)
    occupied_weeks = sorted(activities_by_week)
    report: dict[str, object] = {
        "source_score": source_evaluation.objective_score,
        "strict_buffer_overlap_required": forbid_buffer_overlap,
        "exhaustive": exhaustive,
        "applicable": False,
        "reason": "",
        "candidates_checked": 0,
        "duplicate_candidates_skipped": 0,
        "candidates_skipped_existing_eclo_window": 0,
        "unique_candidates_ranked": 0,
        "candidates_pruned_by_exact_score_order": 0,
        "score_prediction_mismatches": 0,
        "feasible_candidates": 0,
        "improving_candidates": 0,
        "selected_activity": None,
        "selected_removed_week": None,
        "selected_score": None,
        "selected_submission_hash": None,
    }
    if not source_evaluation.internally_feasible:
        report["reason"] = "source is not internally feasible"
        return None, None, report
    if not occupied_weeks or any(
        len(activity_ids) != 1 for activity_ids in activities_by_week.values()
    ):
        report["reason"] = "source is not a one-activity-per-week serialization"
        return None, None, report
    if occupied_weeks != list(range(occupied_weeks[0], occupied_weeks[-1] + 1)):
        report["reason"] = "source occupied weeks are not contiguous"
        return None, None, report
    report["applicable"] = True
    if source_evaluation.objective_score <= 0:
        report["reason"] = "source already attains the nonnegative objective floor"
        return None, None, report

    by_activity: dict[str, list[AccessRow]] = defaultdict(list)
    for row in access:
        by_activity[row.activity_id].append(row)
    existing_eclo_lines = {
        line
        for row in access
        if row.eclo == 1
        for line in _affected_eclo_lines(instance, row.activity_id)
    }
    best_dir: Path | None = None
    best: Evaluation | None = None
    best_key: tuple[str, int] | None = None
    candidate_records: list[dict[str, object]] = []
    seen_signatures: set[tuple[tuple[object, ...], ...]] = set()
    duplicate_candidates_skipped = 0
    candidate_specs: list[tuple[float, str, int]] = []
    for activity_id in sorted(by_activity):
        rows = sorted(by_activity[activity_id], key=lambda row: row.week)
        if len(rows) != 3 or any(row.eclo for row in rows):
            continue
        if _affected_eclo_lines(instance, activity_id) & existing_eclo_lines:
            report["candidates_skipped_existing_eclo_window"] = (
                int(report["candidates_skipped_existing_eclo_window"]) + 1
            )
            continue
        for removed in rows:
            retained_weeks = [
                row.week - int(row.week > removed.week)
                for row in rows
                if row.week != removed.week
            ]
            if max(retained_weeks) - min(retained_weeks) > 1:
                continue
            signature = _candidate_signature(
                access,
                occupancy,
                activity_id,
                removed.week,
            )
            if signature in seen_signatures:
                duplicate_candidates_skipped += 1
                continue
            seen_signatures.add(signature)
            candidate_specs.append(
                (
                    _predicted_objective(
                        instance,
                        access,
                        activity_id,
                        removed.week,
                    ),
                    activity_id,
                    removed.week,
                )
            )
    candidate_specs.sort()
    report["duplicate_candidates_skipped"] = duplicate_candidates_skipped
    report["unique_candidates_ranked"] = len(candidate_specs)
    prediction_mismatch = False
    for candidate_index, (predicted_score, activity_id, removed_week) in enumerate(
        candidate_specs
    ):
        candidate_dir = root / f"{activity_id}_remove_week_{removed_week}"
        _write_candidate(
            instance,
            access,
            occupancy,
            candidate_dir,
            activity_id,
            removed_week,
        )
        evaluation = evaluate_submission(instance, candidate_dir, "C")
        candidate_access, candidate_occupancy, _ = load_submission(candidate_dir)
        strict_conflicts = screen_closures(
            instance,
            candidate_access,
            candidate_occupancy,
            forbid_buffer_overlap=True,
        )
        candidate_is_feasible = evaluation.internally_feasible and not (
            forbid_buffer_overlap and strict_conflicts
        )
        report["candidates_checked"] = int(report["candidates_checked"]) + 1
        if candidate_is_feasible:
            report["feasible_candidates"] = int(report["feasible_candidates"]) + 1
        if (
            candidate_is_feasible
            and evaluation.objective_score < source_evaluation.objective_score
        ):
            report["improving_candidates"] = int(report["improving_candidates"]) + 1
        candidate_records.append(
            {
                "activity_id": activity_id,
                "removed_week": removed_week,
                "predicted_score": predicted_score,
                "score": evaluation.objective_score,
                "score_prediction_matches": evaluation.objective_score
                == predicted_score,
                "hard_violations": list(evaluation.hard_violations),
                "strict_conflicts": [asdict(conflict) for conflict in strict_conflicts],
                "submission_hash": evaluation.submission_hash,
            }
        )
        if evaluation.objective_score != predicted_score:
            prediction_mismatch = True
            report["score_prediction_mismatches"] = (
                int(report["score_prediction_mismatches"]) + 1
            )
        candidate_key = (activity_id, removed_week)
        if (
            candidate_is_feasible
            and evaluation.objective_score < source_evaluation.objective_score
            and (
                best is None
                or evaluation.objective_score < best.objective_score
                or (
                    evaluation.objective_score == best.objective_score
                    and candidate_key < (best_key or candidate_key)
                )
            )
        ):
            best_dir = candidate_dir
            best = evaluation
            best_key = candidate_key
        if (
            not exhaustive
            and not prediction_mismatch
            and (
                best is not None
                or predicted_score >= source_evaluation.objective_score
            )
        ):
            report["candidates_pruned_by_exact_score_order"] = (
                len(candidate_specs) - candidate_index - 1
            )
            break
    report["candidates"] = candidate_records
    if best is not None and best_key is not None:
        report["selected_activity"] = best_key[0]
        report["selected_removed_week"] = best_key[1]
        report["selected_score"] = best.objective_score
        report["selected_submission_hash"] = best.submission_hash
    elif not candidate_records:
        report["reason"] = "no three-standard-access activity yielded a two-week window"
    else:
        report["reason"] = "no fully checked candidate improved the source"
    return best_dir, best, report


def best_serialized_eclo_compaction_sequence(
    instance: Instance,
    source_dir: str | Path,
    candidates_dir: str | Path,
    *,
    forbid_buffer_overlap: bool = False,
    exhaustive: bool = False,
) -> tuple[Path | None, Evaluation | None, dict[str, object]]:
    """Apply checked serialized compactions until no strict improvement remains."""

    source = Path(source_dir)
    root = Path(candidates_dir)
    source_evaluation = evaluate_submission(instance, source, "C")
    source_access, _, _ = load_submission(source)
    current_dir = source
    current = source_evaluation
    rounds: list[dict[str, object]] = []
    selected_dir: Path | None = None
    promotions = 0
    for round_number in range(1, len(source_access) + 1):
        candidate_dir, candidate, round_report = best_single_lane_eclo_compaction(
            instance,
            current_dir,
            root / f"round_{round_number:03d}",
            forbid_buffer_overlap=forbid_buffer_overlap,
            exhaustive=exhaustive,
        )
        rounds.append(round_report)
        if candidate_dir is None or candidate is None:
            break
        if candidate.objective_score >= current.objective_score:
            raise RuntimeError("ECLO compaction sequence accepted a non-improving round")
        selected_dir = candidate_dir
        current_dir = candidate_dir
        current = candidate
        promotions += 1
    else:
        raise RuntimeError("ECLO compaction sequence exceeded its access-row bound")

    report: dict[str, object] = {
        "source_score": source_evaluation.objective_score,
        "selected_score": current.objective_score if promotions else None,
        "selected_submission_hash": current.submission_hash if promotions else None,
        "promotions": promotions,
        "rounds": rounds,
        "candidates_checked": sum(int(item["candidates_checked"]) for item in rounds),
        "duplicate_candidates_skipped": sum(
            int(item["duplicate_candidates_skipped"]) for item in rounds
        ),
        "candidates_skipped_existing_eclo_window": sum(
            int(item["candidates_skipped_existing_eclo_window"]) for item in rounds
        ),
        "candidates_pruned_by_exact_score_order": sum(
            int(item["candidates_pruned_by_exact_score_order"]) for item in rounds
        ),
        "score_prediction_mismatches": sum(
            int(item["score_prediction_mismatches"]) for item in rounds
        ),
    }
    return selected_dir, (current if promotions else None), report
