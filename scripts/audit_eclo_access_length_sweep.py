from __future__ import annotations

import csv
import json
import shutil
import tempfile
import time
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

from nebula_ps1.closure import screen_closures
from nebula_ps1.eclo_compact import best_serialized_eclo_compaction_sequence
from nebula_ps1.evaluate import evaluate_submission, load_submission
from nebula_ps1.independent_score import independently_score
from nebula_ps1.instance import load_instance


ROOT = Path(__file__).resolve().parents[1]
BASE_DATA = ROOT / "fixtures" / "independent_eclo_multipass_v1"
BASE_SOURCE = ROOT / "fixtures" / "independent_eclo_multipass_v1_source_c"
HORIZON_START = date(2035, 1, 1)


def _read(path: Path) -> tuple[tuple[str, ...], list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return tuple(reader.fieldnames or ()), list(reader)


def _write(path: Path, fields: tuple[str, ...], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _date_for_week(week: int) -> date:
    return HORIZON_START + timedelta(days=7 * week - 1)


def _build_case(root: Path, access_count: int) -> tuple[Path, Path]:
    data = root / f"data_{access_count}"
    source = root / f"source_{access_count}"
    data.mkdir(parents=True)
    for name in (
        "01_LINES.csv",
        "02_STATIONS.csv",
        "03_SECTORS.csv",
        "04_LOCATION_SUPPLY.csv",
        "05_BUFFER_LOCATION.csv",
    ):
        shutil.copy2(BASE_DATA / name, data / name)
    horizon_weeks = 4 * access_count
    _write(
        data / "06_PARAMETERS.csv",
        ("key", "value"),
        [
            {"key": "horizon_start", "value": HORIZON_START.isoformat()},
            {"key": "horizon_weeks", "value": horizon_weeks},
        ],
    )
    project_fields, projects = _read(BASE_DATA / "07_PROJECT_DETAILS.csv")
    for project in projects:
        project["contract_completion_date"] = _date_for_week(
            horizon_weeks
        ).isoformat()
    _write(data / "07_PROJECT_DETAILS.csv", project_fields, projects)
    activity_fields, activities = _read(BASE_DATA / "08_ACTIVITY_DETAILS.csv")
    for activity in activities:
        activity["total_accesses"] = str(access_count)
    _write(data / "08_ACTIVITY_DETAILS.csv", activity_fields, activities)

    _, base_occupancy = _read(BASE_SOURCE / "SCHEDULE_OCCUPANCY.csv")
    locations_by_activity: dict[str, set[str]] = defaultdict(set)
    for row in base_occupancy:
        locations_by_activity[row["activity_id"]].add(row["location_id"])
    contract_by_activity = {
        activity["activity_id"]: activity["contract_number"]
        for activity in activities
    }
    project_by_contract = {
        project["contract_number"]: project for project in projects
    }
    access: list[dict[str, object]] = []
    occupancy: list[dict[str, object]] = []
    results: list[dict[str, object]] = []
    for position, activity_id in enumerate(("MX1", "MX2", "MY1", "MY2"), 1):
        completion_week = access_count * position
        for sequence, week in enumerate(
            range(completion_week - access_count + 1, completion_week + 1), 1
        ):
            access.append(
                {
                    "activity_id": activity_id,
                    "access_seq": sequence,
                    "week": week,
                    "eclo": 0,
                    "access_night": 1,
                }
            )
            occupancy.extend(
                {
                    "activity_id": activity_id,
                    "week": week,
                    "location_id": location_id,
                    "co_share_group": "g1",
                }
                for location_id in sorted(locations_by_activity[activity_id])
            )
        contract = contract_by_activity[activity_id]
        planned = date.fromisoformat(
            project_by_contract[contract]["planned_completion_date"]
        )
        completion = _date_for_week(completion_week)
        results.append(
            {
                "scenario": "C",
                "contract_number": contract,
                "simulated_completion_date": completion.isoformat(),
                "overrun_days": max(0, (completion - planned).days),
            }
        )
    _write(
        source / "SCHEDULE_ACCESS.csv",
        ("activity_id", "access_seq", "week", "eclo", "access_night"),
        access,
    )
    _write(
        source / "SCHEDULE_OCCUPANCY.csv",
        ("activity_id", "week", "location_id", "co_share_group"),
        occupancy,
    )
    _write(
        source / "RESULTS.csv",
        ("scenario", "contract_number", "simulated_completion_date", "overrun_days"),
        sorted(results, key=lambda row: str(row["contract_number"])),
    )
    return data, source


def _run(data: Path, source: Path, *, exhaustive: bool) -> dict[str, object]:
    instance = load_instance(data)
    started = time.perf_counter()
    with tempfile.TemporaryDirectory() as temp_dir:
        selected_dir, selected, report = best_serialized_eclo_compaction_sequence(
            instance,
            source,
            Path(temp_dir) / "candidates",
            forbid_buffer_overlap=True,
            exhaustive=exhaustive,
        )
        if selected_dir is None or selected is None:
            raise RuntimeError("access-length sweep produced no selection")
        independent = independently_score(data, selected_dir)
        access, occupancy, _ = load_submission(selected_dir)
        strict_conflicts = screen_closures(
            instance,
            access,
            occupancy,
            forbid_buffer_overlap=True,
        )
    return {
        "exhaustive": exhaustive,
        "selected_score": selected.objective_score,
        "selected_submission_hash": selected.submission_hash,
        "independent_score": independent.objective_score,
        "strict_conflicts": len(strict_conflicts),
        "promotions": report["promotions"],
        "candidates_checked": report["candidates_checked"],
        "duplicate_candidates_skipped": report["duplicate_candidates_skipped"],
        "candidates_pruned_by_exact_score_order": report[
            "candidates_pruned_by_exact_score_order"
        ],
        "score_prediction_mismatches": report["score_prediction_mismatches"],
        "elapsed_seconds": round(time.perf_counter() - started, 6),
    }


def main() -> None:
    cases: list[dict[str, object]] = []
    with tempfile.TemporaryDirectory() as temp_dir:
        scratch = Path(temp_dir)
        for access_count in range(3, 8):
            data, source = _build_case(scratch, access_count)
            instance = load_instance(data)
            source_evaluation = evaluate_submission(instance, source, "C")
            source_independent = independently_score(data, source)
            ranked = _run(data, source, exhaustive=False)
            exhaustive = _run(data, source, exhaustive=True)
            cases.append(
                {
                    "access_count": access_count,
                    "dataset_hash": instance.dataset_hash,
                    "source_score": source_evaluation.objective_score,
                    "source_independent_score": source_independent.objective_score,
                    "ranked": ranked,
                    "exhaustive": exhaustive,
                    "selected_scores_match": ranked["selected_score"]
                    == exhaustive["selected_score"],
                    "selected_hashes_match": ranked["selected_submission_hash"]
                    == exhaustive["selected_submission_hash"],
                }
            )
    payload = {
        "access_counts": [case["access_count"] for case in cases],
        "all_scores_match": all(case["selected_scores_match"] for case in cases),
        "all_hashes_match": all(case["selected_hashes_match"] for case in cases),
        "total_prediction_mismatches": sum(
            int(case["exhaustive"]["score_prediction_mismatches"])
            for case in cases
        ),
        "cases": cases,
    }
    output = ROOT / "runs" / "eclo_access_length_sweep.json"
    output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
