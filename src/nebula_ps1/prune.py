from __future__ import annotations

import csv
import json
import tempfile
from dataclasses import asdict, dataclass, replace
from pathlib import Path

from .closure import screen_closures
from .evaluate import AccessRow, Evaluation, OccupancyRow, evaluate_submission, load_submission
from .instance import Instance


SUBMISSION_FILES = ("SCHEDULE_ACCESS.csv", "SCHEDULE_OCCUPANCY.csv", "RESULTS.csv")


@dataclass(frozen=True)
class PruneReport:
    scenario: str
    initial_score: float
    final_score: float
    initial_access_rows: int
    final_access_rows: int
    removed_accesses: tuple[tuple[str, int], ...]
    initial_submission_hash: str
    final_submission_hash: str
    reference_validator_confirmed: bool = False
    strict_buffer_overlap_checked: bool = False

    def as_json(self) -> str:
        return json.dumps(asdict(self), indent=2, sort_keys=True)


def _resequence(rows: list[AccessRow]) -> list[AccessRow]:
    by_activity: dict[str, list[AccessRow]] = {}
    for row in rows:
        by_activity.setdefault(row.activity_id, []).append(row)
    result: list[AccessRow] = []
    for activity_id in sorted(by_activity):
        ordered = sorted(by_activity[activity_id], key=lambda row: row.week)
        result.extend(replace(row, access_seq=index) for index, row in enumerate(ordered, 1))
    return result


def _write_submission(
    instance: Instance,
    output: Path,
    scenario: str,
    access_rows: list[AccessRow],
    occupancy_rows: list[OccupancyRow],
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    with (output / "SCHEDULE_ACCESS.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(("activity_id", "access_seq", "week", "eclo", "access_night"))
        writer.writerows(
            (row.activity_id, row.access_seq, row.week, row.eclo, row.access_night)
            for row in access_rows
        )
    with (output / "SCHEDULE_OCCUPANCY.csv").open(
        "w", newline="", encoding="utf-8"
    ) as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(("activity_id", "week", "location_id", "co_share_group"))
        writer.writerows(
            (row.activity_id, row.week, row.location_id, row.co_share_group)
            for row in sorted(
                occupancy_rows,
                key=lambda row: (row.activity_id, row.week, row.location_id),
            )
        )

    completion_by_activity = {
        activity_id: max(row.week for row in access_rows if row.activity_id == activity_id)
        for activity_id in sorted(instance.activities)
    }
    activities_by_contract: dict[str, list[str]] = {}
    for activity_id, activity in sorted(instance.activities.items()):
        activities_by_contract.setdefault(activity.contract_number, []).append(activity_id)
    with (output / "RESULTS.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(
            ("scenario", "contract_number", "simulated_completion_date", "overrun_days")
        )
        for contract_number in sorted(instance.projects):
            project = instance.projects[contract_number]
            completion_week = max(
                completion_by_activity[activity_id]
                for activity_id in activities_by_contract[contract_number]
            )
            completion_date = instance.completion_date(completion_week)
            writer.writerow(
                (
                    scenario,
                    contract_number,
                    completion_date.isoformat(),
                    max(0, (completion_date - project.planned_completion_date).days),
                )
            )


def prune_submission(
    instance: Instance,
    source_dir: str | Path,
    output_dir: str | Path,
    scenario: str,
    *,
    report_path: str | Path | None = None,
    forbid_buffer_overlap: bool = False,
) -> PruneReport:
    """Remove score-neutral or score-improving access rows behind a full-check gate."""

    if scenario not in {"A", "B", "C"}:
        raise ValueError("scenario must be A, B, or C")
    source = Path(source_dir)
    output = Path(output_dir)
    access_rows, occupancy_rows, _ = load_submission(source)
    initial = evaluate_submission(instance, source, scenario)
    if not initial.internally_feasible:
        raise ValueError("cannot prune an infeasible submission")
    if forbid_buffer_overlap and screen_closures(
        instance,
        access_rows,
        occupancy_rows,
        forbid_buffer_overlap=True,
    ):
        raise ValueError("cannot strict-prune a submission with buffer-overlap conflicts")

    current_access = _resequence(list(access_rows))
    current_occupancy = list(occupancy_rows)
    current_evaluation: Evaluation = initial
    removed: list[tuple[str, int]] = []

    with tempfile.TemporaryDirectory(prefix="nebula-prune-") as temp_dir:
        trial_dir = Path(temp_dir)
        while True:
            supplied_half_units: dict[str, int] = {}
            for row in current_access:
                supplied_half_units[row.activity_id] = supplied_half_units.get(row.activity_id, 0) + (
                    3 if row.eclo else 2
                )
            candidates = sorted(
                current_access,
                key=lambda row: (
                    -row.eclo,
                    -row.week,
                    row.activity_id,
                ),
            )
            accepted = False
            for row in candidates:
                required = 2 * instance.activities[row.activity_id].total_accesses
                row_yield = 3 if row.eclo else 2
                if supplied_half_units[row.activity_id] - row_yield < required:
                    continue
                candidate_access = _resequence(
                    [
                        candidate
                        for candidate in current_access
                        if not (
                            candidate.activity_id == row.activity_id
                            and candidate.week == row.week
                        )
                    ]
                )
                candidate_occupancy = [
                    candidate
                    for candidate in current_occupancy
                    if not (
                        candidate.activity_id == row.activity_id
                        and candidate.week == row.week
                    )
                ]
                _write_submission(
                    instance, trial_dir, scenario, candidate_access, candidate_occupancy
                )
                evaluation = evaluate_submission(instance, trial_dir, scenario)
                strict_conflicts = (
                    screen_closures(
                        instance,
                        candidate_access,
                        candidate_occupancy,
                        forbid_buffer_overlap=True,
                    )
                    if forbid_buffer_overlap
                    else ()
                )
                if (
                    evaluation.internally_feasible
                    and evaluation.objective_score <= current_evaluation.objective_score
                    and not strict_conflicts
                ):
                    current_access = candidate_access
                    current_occupancy = candidate_occupancy
                    current_evaluation = evaluation
                    removed.append((row.activity_id, row.week))
                    accepted = True
                    break
            if not accepted:
                break

    _write_submission(instance, output, scenario, current_access, current_occupancy)
    final = evaluate_submission(instance, output, scenario)
    final_strict_conflicts = (
        screen_closures(
            instance,
            current_access,
            current_occupancy,
            forbid_buffer_overlap=True,
        )
        if forbid_buffer_overlap
        else ()
    )
    if (
        not final.internally_feasible
        or final.objective_score > initial.objective_score
        or final_strict_conflicts
    ):
        raise RuntimeError("pruned submission failed final feasibility/score gate")
    if sorted(path.name for path in output.iterdir()) != sorted(SUBMISSION_FILES):
        raise RuntimeError("pruned submission directory contains files beyond the three CSVs")
    report = PruneReport(
        scenario=scenario,
        initial_score=initial.objective_score,
        final_score=final.objective_score,
        initial_access_rows=len(access_rows),
        final_access_rows=len(current_access),
        removed_accesses=tuple(removed),
        initial_submission_hash=initial.submission_hash,
        final_submission_hash=final.submission_hash,
        strict_buffer_overlap_checked=forbid_buffer_overlap,
    )
    if report_path is not None:
        Path(report_path).write_text(report.as_json() + "\n", encoding="utf-8")
    return report
