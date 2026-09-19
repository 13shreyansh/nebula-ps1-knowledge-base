from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path

from .closure import screen_closures
from .evaluate import Evaluation, evaluate_submission, load_submission
from .instance import Instance


def _write(
    path: Path, fields: tuple[str, ...], rows: list[dict[str, object]]
) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _completion_by_contract(instance: Instance, access_rows) -> dict[str, int]:
    completion_by_activity: dict[str, int] = defaultdict(int)
    for row in access_rows:
        activity_id = str(row["activity_id"] if isinstance(row, dict) else row.activity_id)
        week = int(row["week"] if isinstance(row, dict) else row.week)
        completion_by_activity[activity_id] = max(completion_by_activity[activity_id], week)
    completion_by_contract: dict[str, int] = defaultdict(int)
    for activity_id, week in completion_by_activity.items():
        contract = instance.activities[activity_id].contract_number
        completion_by_contract[contract] = max(completion_by_contract[contract], week)
    return completion_by_contract


def _write_shifted_candidate(
    instance: Instance,
    source_dir: Path,
    output_dir: Path,
    gap_week: int,
) -> None:
    access, occupancy, _ = load_submission(source_dir)
    output_access = [
        {
            "activity_id": row.activity_id,
            "access_seq": row.access_seq,
            "week": row.week - int(row.week > gap_week),
            "eclo": row.eclo,
            "access_night": row.access_night,
        }
        for row in access
    ]
    output_occupancy = [
        {
            "activity_id": row.activity_id,
            "week": row.week - int(row.week > gap_week),
            "location_id": row.location_id,
            "co_share_group": row.co_share_group,
        }
        for row in occupancy
    ]
    completion_by_contract = _completion_by_contract(instance, output_access)
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


def _predicted_objective(
    instance: Instance,
    access,
    gap_week: int,
    *,
    excess_total: int,
    eclo_total: int,
) -> float:
    shifted = [
        {
            "activity_id": row.activity_id,
            "week": row.week - int(row.week > gap_week),
        }
        for row in access
    ]
    completion_by_contract = _completion_by_contract(instance, shifted)
    contract_weight = {1: 100.0, 2: 10.0, 3: 1.0}
    activity_nudge = {1: 0.3, 2: 0.2, 3: 0.0}
    delay_score = 0.0
    for contract, project in instance.projects.items():
        completion = instance.completion_date(completion_by_contract[contract])
        delay_days = max(0, (completion - project.planned_completion_date).days)
        for activity in instance.activities.values():
            if activity.contract_number == contract:
                delay_score += (
                    delay_days
                    * contract_weight[project.contract_priority]
                    * (1.0 + activity_nudge[activity.activity_priority])
                )
    return round(delay_score + 20.0 * excess_total + 5.0 * eclo_total, 10)


def best_idle_week_compaction_sequence(
    instance: Instance,
    source_dir: str | Path,
    candidates_dir: str | Path,
    *,
    forbid_buffer_overlap: bool = False,
    allow_equal: bool = False,
) -> tuple[Path | None, Evaluation | None, dict[str, object]]:
    """Delete globally idle weeks before the last occupied week through checks."""

    source = Path(source_dir)
    root = Path(candidates_dir)
    source_evaluation = evaluate_submission(instance, source, "C")
    current_dir = source
    current = source_evaluation
    rounds: list[dict[str, object]] = []
    selected_dir: Path | None = None
    promotions = 0
    prediction_mismatches = 0
    prediction_untrusted = False
    candidates_checked = 0
    while True:
        access, _, _ = load_submission(current_dir)
        occupied = sorted({row.week for row in access})
        occupied_set = set(occupied)
        gaps = (
            [week for week in range(1, occupied[-1]) if week not in occupied_set]
            if occupied
            else []
        )
        ranked = sorted(
            (
                _predicted_objective(
                    instance,
                    access,
                    gap,
                    excess_total=current.excess_access_nights_total,
                    eclo_total=current.eclo_nights_total,
                ),
                gap,
            )
            for gap in gaps
        )
        round_record: dict[str, object] = {
            "source_score": current.objective_score,
            "gap_count": len(gaps),
            "candidates_checked": 0,
            "selected_gap_week": None,
            "selected_score": None,
            "reason": "",
        }
        round_best_dir: Path | None = None
        round_best: Evaluation | None = None
        for candidate_index, (predicted_score, gap_week) in enumerate(ranked):
            score_cannot_qualify = (
                predicted_score > current.objective_score
                if allow_equal
                else predicted_score >= current.objective_score
            )
            if (
                candidate_index > 0
                and not prediction_untrusted
                and score_cannot_qualify
            ):
                break
            candidate_dir = root / f"round_{promotions + 1:03d}_gap_{gap_week}"
            _write_shifted_candidate(instance, current_dir, candidate_dir, gap_week)
            candidate = evaluate_submission(instance, candidate_dir, "C")
            candidate_access, candidate_occupancy, _ = load_submission(candidate_dir)
            strict_conflicts = screen_closures(
                instance,
                candidate_access,
                candidate_occupancy,
                forbid_buffer_overlap=True,
            )
            candidates_checked += 1
            round_record["candidates_checked"] = (
                int(round_record["candidates_checked"]) + 1
            )
            if candidate.objective_score != predicted_score:
                prediction_mismatches += 1
                prediction_untrusted = True
            candidate_is_acceptable = (
                candidate.internally_feasible
                and not (forbid_buffer_overlap and strict_conflicts)
                and (
                    candidate.objective_score <= current.objective_score
                    if allow_equal
                    else candidate.objective_score < current.objective_score
                )
            )
            if candidate_is_acceptable and (
                round_best is None
                or candidate.objective_score < round_best.objective_score
                or (
                    candidate.objective_score == round_best.objective_score
                    and gap_week < int(round_record["selected_gap_week"])
                )
            ):
                round_best_dir, round_best = candidate_dir, candidate
                round_record["selected_gap_week"] = gap_week
                round_record["selected_score"] = candidate.objective_score
            if candidate_is_acceptable and not prediction_untrusted:
                break
            if (
                not prediction_untrusted
                and candidate.objective_score == predicted_score
                and score_cannot_qualify
            ):
                break
        if round_best_dir is None or round_best is None:
            round_record["reason"] = (
                "no removable idle week"
                if not gaps
                else "no checked idle-week shift improved the source"
            )
            rounds.append(round_record)
            break
        rounds.append(round_record)
        selected_dir = round_best_dir
        current_dir = round_best_dir
        current = round_best
        promotions += 1

    report: dict[str, object] = {
        "source_score": source_evaluation.objective_score,
        "allow_equal": allow_equal,
        "selected_score": current.objective_score if promotions else None,
        "selected_submission_hash": current.submission_hash if promotions else None,
        "promotions": promotions,
        "strict_improvement": current.objective_score < source_evaluation.objective_score,
        "rounds": rounds,
        "candidates_checked": candidates_checked,
        "score_prediction_mismatches": prediction_mismatches,
        "score_prediction_untrusted": prediction_untrusted,
        "reason": rounds[-1]["reason"],
    }
    return selected_dir, (current if promotions else None), report
