from __future__ import annotations

import csv
import json
import shutil
import tempfile
from pathlib import Path

from .closure import _blocked_locations, _buffer_locations, screen_closures
from .evaluate import evaluate_submission, load_submission
from .flexible_solver import _scenario_b_workload_deadline_deficits
from .independent_score import independently_score
from .instance import FILES, Instance, load_instance
from .portfolio import SUBMISSION_FILES
from .staged import solve_staged_scenario
from .topology import (
    activity_footprint,
    affects_interchange_cross_line,
    split_sector_location,
)


DECOMPOSITION_COUPLING_INVENTORY_VERSION = "2026-09-19.v1"
DECOMPOSITION_COUPLING_INVENTORY: dict[str, tuple[str, ...]] = {
    "same_contract": (
        "contract_completion_delay_objective",
        "contract_week_access_night_allocation",
        "contract_week_night_workfront_cap",
    ),
    "predecessor": ("activity_precedence",),
    "scenario_c_same_line_window": ("scenario_c_line_eclo_two_week_window",),
    "scenario_c_live_all_line_window": (
        "scenario_c_live_interchange_all_line_eclo_window",
    ),
    "resource_or_closure": (
        "location_week_group_membership_and_legal_mix",
        "location_week_supply_and_excess_objective",
        "directional_work_versus_blocked_closure",
    ),
    "strict_buffer_overlap": ("strict_buffer_to_buffer_closure_hedge",),
}


def independent_activity_components(
    instance: Instance,
    scenario: str,
    *,
    forbid_buffer_overlap: bool = False,
) -> tuple[tuple[str, ...], ...]:
    """Conservatively partition activities whose constraints cannot interact."""

    if scenario not in {"A", "B", "C"}:
        raise ValueError("scenario must be A, B, or C")
    activity_ids = sorted(instance.activities)
    parent = {activity_id: activity_id for activity_id in activity_ids}

    def find(activity_id: str) -> str:
        while parent[activity_id] != activity_id:
            parent[activity_id] = parent[parent[activity_id]]
            activity_id = parent[activity_id]
        return activity_id

    def union(first: str, second: str) -> None:
        first_root, second_root = find(first), find(second)
        if first_root != second_root:
            parent[second_root] = first_root

    work: dict[str, set[str]] = {}
    blocked: dict[str, set[str]] = {}
    buffers: dict[str, set[str]] = {}
    lines: dict[str, str] = {}
    crossover: dict[str, bool] = {}
    for activity_id in activity_ids:
        activity = instance.activities[activity_id]
        line, _, _ = split_sector_location(activity.start_location_id)
        lines[activity_id] = line
        crossover[activity_id] = affects_interchange_cross_line(instance, activity)
        work[activity_id] = set(activity_footprint(instance, activity))
        blocked[activity_id] = _blocked_locations(instance, {activity_id})
        buffers[activity_id] = _buffer_locations(instance, {activity_id})

    for first_index, first in enumerate(activity_ids):
        for second in activity_ids[first_index + 1 :]:
            if _activity_interaction_reasons(
                instance,
                scenario,
                first,
                second,
                forbid_buffer_overlap=forbid_buffer_overlap,
                work=work,
                blocked=blocked,
                buffers=buffers,
                lines=lines,
                crossover=crossover,
            ):
                union(first, second)

    components: dict[str, list[str]] = {}
    for activity_id in activity_ids:
        components.setdefault(find(activity_id), []).append(activity_id)
    return tuple(
        sorted(
            (tuple(sorted(component)) for component in components.values()),
            key=lambda component: component,
        )
    )


def _activity_interaction_reasons(
    instance: Instance,
    scenario: str,
    first: str,
    second: str,
    *,
    forbid_buffer_overlap: bool = False,
    work: dict[str, set[str]] | None = None,
    blocked: dict[str, set[str]] | None = None,
    buffers: dict[str, set[str]] | None = None,
    lines: dict[str, str] | None = None,
    crossover: dict[str, bool] | None = None,
) -> tuple[str, ...]:
    """Explain every modeled constraint family that couples two activities."""

    first_activity = instance.activities[first]
    second_activity = instance.activities[second]
    reasons: list[str] = []
    if first_activity.contract_number == second_activity.contract_number:
        reasons.append("same_contract")
    if (
        first_activity.predecessor_activity_id == second
        or second_activity.predecessor_activity_id == first
    ):
        reasons.append("predecessor")
    first_line = (
        lines[first]
        if lines is not None
        else split_sector_location(first_activity.start_location_id)[0]
    )
    second_line = (
        lines[second]
        if lines is not None
        else split_sector_location(second_activity.start_location_id)[0]
    )
    if scenario == "C" and first_line == second_line:
        reasons.append("scenario_c_same_line_window")
    first_crossover = (
        crossover[first]
        if crossover is not None
        else affects_interchange_cross_line(instance, first_activity)
    )
    second_crossover = (
        crossover[second]
        if crossover is not None
        else affects_interchange_cross_line(instance, second_activity)
    )
    if scenario == "C" and (first_crossover or second_crossover):
        reasons.append("scenario_c_live_all_line_window")
    first_work = (
        work[first]
        if work is not None
        else set(activity_footprint(instance, first_activity))
    )
    second_work = (
        work[second]
        if work is not None
        else set(activity_footprint(instance, second_activity))
    )
    first_blocked = (
        blocked[first]
        if blocked is not None
        else _blocked_locations(instance, {first})
    )
    second_blocked = (
        blocked[second]
        if blocked is not None
        else _blocked_locations(instance, {second})
    )
    if first_work & second_blocked or second_work & first_blocked:
        reasons.append("resource_or_closure")
    if forbid_buffer_overlap:
        first_buffer = (
            buffers[first]
            if buffers is not None
            else _buffer_locations(instance, {first})
        )
        second_buffer = (
            buffers[second]
            if buffers is not None
            else _buffer_locations(instance, {second})
        )
        if first_buffer & second_buffer:
            reasons.append("strict_buffer_overlap")
    return tuple(reasons)


def _read(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or ()), list(reader)


def _write(path: Path, fields: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _write_component_data(
    data_root: Path,
    output: Path,
    activity_ids: tuple[str, ...],
) -> None:
    output.mkdir(parents=True, exist_ok=False)
    for key in ("lines", "stations", "sectors", "locations", "buffers", "parameters"):
        name = FILES[key]
        shutil.copy2(data_root / name, output / name)
    activity_fields, activity_rows = _read(data_root / FILES["activities"])
    selected_activities = [
        row for row in activity_rows if row["activity_id"] in set(activity_ids)
    ]
    selected_contracts = {row["contract_number"] for row in selected_activities}
    project_fields, project_rows = _read(data_root / FILES["projects"])
    selected_projects = [
        row for row in project_rows if row["contract_number"] in selected_contracts
    ]
    _write(output / FILES["projects"], project_fields, selected_projects)
    _write(output / FILES["activities"], activity_fields, selected_activities)


def _merge_submissions(sources: list[Path], output: Path) -> None:
    output.mkdir(parents=True, exist_ok=False)
    for name in SUBMISSION_FILES:
        fields: list[str] | None = None
        rows: list[dict[str, str]] = []
        for source in sources:
            source_fields, source_rows = _read(source / name)
            if fields is None:
                fields = source_fields
            elif source_fields != fields:
                raise RuntimeError(f"component output schema mismatch for {name}")
            rows.extend(source_rows)
        assert fields is not None
        _write(output / name, fields, rows)


def _publish_submission_atomically(source: Path, destination: Path) -> None:
    """Copy a checked candidate off-path, then expose all three files at once."""

    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(
        tempfile.mkdtemp(
            prefix=f".{destination.name}.publishing-",
            dir=destination.parent,
        )
    )
    try:
        for name in SUBMISSION_FILES:
            shutil.copy2(source / name, temporary / name)
        if sorted(path.name for path in temporary.iterdir()) != sorted(SUBMISSION_FILES):
            raise RuntimeError("atomic publication staging has unexpected files")
        for name in SUBMISSION_FILES:
            if (source / name).read_bytes() != (temporary / name).read_bytes():
                raise RuntimeError(f"atomic publication byte mismatch for {name}")
        if destination.exists():
            destination.rmdir()
        temporary.replace(destination)
    except BaseException:
        shutil.rmtree(temporary, ignore_errors=True)
        raise


def _primary_proof_telemetry(
    staged_report: dict[str, object],
) -> dict[str, object] | None:
    """Return the telemetry that proves the selected primary score, if any."""

    if staged_report.get("verification_skipped_primary_proven") is True:
        telemetry = staged_report.get("heuristic_telemetry")
    else:
        telemetry = staged_report.get("verification_telemetry")
    if not isinstance(telemetry, dict):
        return None
    selected_score = staged_report.get("selected_objective_score")
    scope = telemetry.get("primary_bound_scope")
    formulation = telemetry.get("formulation")
    scope_matches_formulation = (
        scope == "full_instance"
        or (
            scope == "full_instance_nonnegative_floor"
            and formulation
            in {
                "scenario_a_checked_zero_floor_incumbent",
                "scenario_b_checked_zero_floor_incumbent",
                "scenario_c_checked_zero_floor_incumbent",
                "scenario_a_checked_structural_zero_floor_candidate",
                "scenario_c_checked_structural_zero_floor_candidate",
            }
        )
        or (
            scope == "full_instance_workload_eclo_lower_bound"
            and formulation
            in {
                "scenario_b_checked_workload_lower_bound_incumbent",
                "scenario_b_checked_structural_workload_lower_bound_candidate",
            }
        )
    )
    if (
        telemetry.get("primary_score_proven_optimal") is not True
        or not scope_matches_formulation
        or telemetry.get("best_bound") != selected_score
        or telemetry.get("objective_score") != selected_score
    ):
        return None
    return telemetry


def solve_decomposed_scenario(
    data_dir: str | Path,
    output_dir: str | Path,
    scenario: str,
    *,
    audit_output_dir: str | Path | None = None,
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
    """Solve conservative independent components, then fail closed on the merge."""

    data_root = Path(data_dir).resolve()
    output = Path(output_dir)
    audit = (
        Path(audit_output_dir)
        if audit_output_dir is not None
        else output.with_name(f"{output.name}_audit")
    )
    if output.exists():
        if not output.is_dir() or any(output.iterdir()):
            raise ValueError(f"decomposed output directory must be empty: {output}")
    if audit.exists():
        if not audit.is_dir() or any(audit.iterdir()):
            raise ValueError(f"decomposed audit directory must be empty: {audit}")
    instance = load_instance(data_root)
    if scenario == "B":
        workload_deficits = _scenario_b_workload_deadline_deficits(instance)
        if workload_deficits:
            details = "; ".join(
                f"{item['activity_id']} max={item['maximum_half_units']}/2 "
                f"required={item['required_half_units']}/2"
                for item in workload_deficits
            )
            raise ValueError(
                "Scenario B workload cannot fit before planned completion: "
                + details
            )
    audit.mkdir(parents=True, exist_ok=True)

    components = independent_activity_components(
        instance,
        scenario,
        forbid_buffer_overlap=forbid_buffer_overlap,
    )
    component_reports: list[dict[str, object]] = []
    component_outputs: list[Path] = []
    for index, activity_ids in enumerate(components, start=1):
        component_root = audit / f"component_{index:03d}"
        component_data = component_root / "data"
        component_output = component_root / "submission"
        component_audit = component_root / "audit"
        component_root.mkdir(parents=True, exist_ok=False)
        _write_component_data(data_root, component_data, activity_ids)
        component_instance = load_instance(component_data)
        staged_report = solve_staged_scenario(
            component_instance,
            component_output,
            scenario,
            audit_output_dir=component_audit,
            heuristic_time_limit_seconds=heuristic_time_limit_seconds,
            local_repair_time_limit_seconds=local_repair_time_limit_seconds,
            fallback_time_limit_seconds=fallback_time_limit_seconds,
            verification_time_limit_seconds=verification_time_limit_seconds,
            workers=workers,
            seed=seed + index - 1,
            heuristic_attempts=heuristic_attempts,
            fallback_attempts=fallback_attempts,
            closure_round_limit=closure_round_limit,
            forbid_buffer_overlap=forbid_buffer_overlap,
        )
        component_reports.append(
            {
                "index": index,
                "activities": list(activity_ids),
                "dataset_hash": component_instance.dataset_hash,
                "selected_objective_score": staged_report["selected_objective_score"],
                "selected_submission_hash": staged_report["selected_submission_hash"],
                "selected_stage": staged_report["selected_stage"],
                "verification_telemetry": staged_report["verification_telemetry"],
                "primary_proof_telemetry": _primary_proof_telemetry(staged_report),
            }
        )
        component_outputs.append(component_output)

    merged_candidate = audit / "merged_candidate"
    _merge_submissions(component_outputs, merged_candidate)
    evaluation = evaluate_submission(instance, merged_candidate, scenario)
    independent = independently_score(data_root, merged_candidate)
    access, occupancy, _ = load_submission(merged_candidate)
    conflicts = screen_closures(
        instance,
        access,
        occupancy,
        forbid_buffer_overlap=forbid_buffer_overlap,
    )
    if not evaluation.internally_feasible or conflicts:
        details = list(evaluation.hard_violations)
        details.extend(conflict.describe() for conflict in conflicts)
        raise RuntimeError("decomposed merge failed full feasibility: " + "; ".join(details))
    comparisons = (
        (evaluation.scenario, independent.scenario),
        (evaluation.objective_score, independent.objective_score),
        (evaluation.priority_weighted_score, independent.priority_weighted_delay),
        (evaluation.excess_access_nights_total, independent.excess_access_nights),
        (evaluation.eclo_nights_total, independent.eclo_nights),
        (evaluation.access_rows, independent.access_rows),
        (evaluation.occupancy_rows, independent.occupancy_rows),
    )
    if any(primary != second for primary, second in comparisons):
        raise RuntimeError("decomposed merge failed independent score agreement")
    component_score = round(
        sum(float(report["selected_objective_score"]) for report in component_reports),
        10,
    )
    if component_score != evaluation.objective_score:
        raise RuntimeError(
            "decomposed objective is not additive: "
            f"components={component_score} merged={evaluation.objective_score}"
        )
    globally_proven = all(
        report["primary_proof_telemetry"] is not None
        for report in component_reports
    )
    report: dict[str, object] = {
        "scenario": scenario,
        "dataset_hash": instance.dataset_hash,
        "component_count": len(components),
        "components": component_reports,
        "selected_objective_score": evaluation.objective_score,
        "selected_submission_hash": evaluation.submission_hash,
        "independent_objective_score": independent.objective_score,
        "strict_buffer_overlap_checked": forbid_buffer_overlap,
        "selected_policy_conflicts": len(conflicts),
        "global_optimality_proved_by_additivity": globally_proven,
        "coupling_inventory_version": DECOMPOSITION_COUPLING_INVENTORY_VERSION,
        "coupling_edge_reasons": sorted(DECOMPOSITION_COUPLING_INVENTORY),
        "reference_validator_confirmed": False,
        "publication_status": "staged",
    }
    (audit / "DECOMPOSED.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    _publish_submission_atomically(merged_candidate, output)
    if sorted(path.name for path in output.iterdir()) != sorted(SUBMISSION_FILES):
        raise RuntimeError(
            "decomposed published submission contains files beyond the three CSVs"
        )
    report["publication_status"] = "published"
    report_temporary = audit / ".DECOMPOSED.json.tmp"
    report_temporary.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    report_temporary.replace(audit / "DECOMPOSED.json")
    return report
