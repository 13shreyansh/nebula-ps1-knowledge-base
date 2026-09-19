"""Portable local PS1 validator interface; standard-library-only runtime.

Feasibility uses the tested local evaluator, not the optimiser. A separate raw-CSV
score calculation cross-checks every locally feasible result. This reproduces
observed portal examples, but it is not the organiser's source code.
"""
from __future__ import annotations

import argparse
import csv
import json
import stat
import sys
import tempfile
import zipfile
from collections import defaultdict
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from .closure import screen_closures
from .evaluate import evaluate_submission, load_submission
from .independent_score import independently_score
from .instance import FILES, InputError, Instance, load_instance
from .objective import ACTIVITY_NUDGE, CONTRACT_WEIGHT
from .topology import activity_footprint

VERSION = "1.0.0"
FORMULA_VERSION = "local-contract-completion-v1"
SUBMISSION_SCHEMAS = {
    "SCHEDULE_ACCESS.csv": ("activity_id", "access_seq", "week", "eclo", "access_night"),
    "SCHEDULE_OCCUPANCY.csv": ("activity_id", "week", "location_id", "co_share_group"),
    "RESULTS.csv": ("scenario", "contract_number", "simulated_completion_date", "overrun_days"),
}
INPUT_SCHEMAS = {
    FILES["lines"]: ("line_code", "line_name"),
    FILES["stations"]: ("station_id", "line_code", "seq", "is_interchange"),
    FILES["sectors"]: ("sector_id", "line_code", "from_station_id", "to_station_id", "seq", "is_shared"),
    FILES["locations"]: ("location_id", "location_kind", "line_code", "bound", "supply_capacity"),
    FILES["buffers"]: ("nature_of_works", "up_to_buffer_sectors", "opposite_bound_required"),
    FILES["parameters"]: ("key", "value"),
    FILES["projects"]: ("contract_number", "activity_type", "nature_of_activity", "contract_priority", "contract_completion_date", "planned_completion_date", "number_of_workfronts", "access_type", "number_of_maximum_access_per_week"),
    FILES["activities"]: ("activity_id", "contract_number", "activity_type", "start_location_id", "end_location_id", "total_accesses", "planned_start_date", "predecessor_activity_id", "activity_priority"),
}
MAX_MEMBER_BYTES = 64 * 1024 * 1024
MAX_PACK_BYTES = 256 * 1024 * 1024


class PackError(InputError):
    """The container cannot safely represent the required CSV files."""


@contextmanager
def _materialize(path: Path, names: set[str], *, exact: bool) -> Iterator[Path]:
    if path.is_dir():
        observed = {p.name for p in path.iterdir()}
        missing = names - observed
        extra = observed - names if exact else set()
        if missing or extra:
            raise PackError(f"{path.name}: missing={sorted(missing)}, unexpected={sorted(extra)}")
        if any(not (path / name).is_file() for name in names):
            raise PackError("Required CSV members must be regular files")
        yield path
        return
    if not path.is_file():
        raise PackError(f"Path does not exist or is not a file/directory: {path}")
    try:
        with zipfile.ZipFile(path) as archive:
            members = archive.infolist()
            observed = [m.filename for m in members]
            # No arbitrary extraction: accepted names are fixed root CSV names.
            if len(observed) != len(set(observed)):
                raise PackError("ZIP contains duplicate member names")
            if set(observed) != names:
                raise PackError(f"ZIP must contain exactly the required root CSV files: missing={sorted(names - set(observed))}, unexpected={sorted(set(observed) - names)}")
            if sum(m.file_size for m in members) > MAX_PACK_BYTES:
                raise PackError("ZIP exceeds local uncompressed-size limit of 256 MiB")
            for member in members:
                if member.flag_bits & 1:
                    raise PackError("Encrypted ZIP members are not supported")
                if member.is_dir() or stat.S_ISLNK(member.external_attr >> 16):
                    raise PackError("ZIP members must be regular CSV files")
                if member.file_size > MAX_MEMBER_BYTES:
                    raise PackError("ZIP member exceeds local size limit of 64 MiB")
            with tempfile.TemporaryDirectory(prefix="nebula-validator-") as temporary:
                root = Path(temporary)
                for member in members:
                    (root / member.filename).write_bytes(archive.read(member))
                yield root
    except (zipfile.BadZipFile, NotImplementedError, RuntimeError) as exc:
        raise PackError(f"Cannot read ZIP: {exc}") from exc


def _csv_rows(path: Path, required: tuple[str, ...]) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle, strict=True)
        fields = reader.fieldnames or []
        if not fields or any(not field for field in fields) or len(set(fields)) != len(fields):
            raise InputError(f"{path.name}: empty or duplicate CSV headers")
        missing = set(required) - set(fields)
        if missing:
            raise InputError(f"{path.name}: missing columns {sorted(missing)}")
        result = []
        for row in reader:
            if None in row or any(value is None for value in row.values()):
                raise InputError(f"{path.name} row {reader.line_num}: column count does not match header")
            result.append(row)
        return result


def _check_instance(root: Path) -> Instance:
    raw = {name: _csv_rows(root / name, schema) for name, schema in INPUT_SCHEMAS.items()}
    for name, fields in (
        (FILES["stations"], ("is_interchange",)),
        (FILES["sectors"], ("is_shared",)),
        (FILES["buffers"], ("opposite_bound_required",)),
    ):
        for row in raw[name]:
            for field in fields:
                if row[field].strip() not in {"0", "1"}:
                    raise InputError(f"{name}: {field} must be 0 or 1")
    keys = [row["key"].strip() for row in raw[FILES["parameters"]]]
    if len(keys) != len(set(keys)):
        raise InputError("06_PARAMETERS.csv: duplicate parameter key")
    instance = load_instance(root)
    # Check enums/references before the scorer indexes priority dictionaries.
    if any(not line for line in instance.lines):
        raise InputError("01_LINES.csv: empty line identifier")
    instance.completion_date(instance.horizon_weeks)  # reject date overflow
    for location in instance.locations.values():
        if location.line_code not in instance.lines or location.bound not in {"EB", "WB"}:
            raise InputError(f"location {location.location_id}: invalid line or bound")
        parts = location.location_id.split(":")
        if len(parts) != 4 or parts[1] != location.line_code or parts[3] != location.bound:
            raise InputError(f"location {location.location_id}: identifier disagrees with line/bound")
        if parts[0] == "SEC":
            if ":".join(parts[:3]) not in instance.sectors:
                raise InputError(f"location {location.location_id}: undefined sector")
        elif parts[0] == "PLAT":
            if (parts[1], parts[2]) not in instance.stations:
                raise InputError(f"location {location.location_id}: undefined station")
        else:
            raise InputError(f"location {location.location_id}: expected SEC or PLAT")
    for line in instance.lines:
        ordered = sorted((s for s in instance.sectors.values() if s.line_code == line), key=lambda s: s.seq)
        for left, right in zip(ordered, ordered[1:]):
            if left.to_station_id != right.from_station_id:
                raise InputError(f"line {line}: disconnected ordered sectors {left.sector_id}, {right.sector_id}")
    contract_activity_counts: dict[str, int] = defaultdict(int)
    for project in instance.projects.values():
        if not project.contract_number or project.contract_priority not in {1, 2, 3}:
            raise InputError(f"contract {project.contract_number}: invalid identifier or priority")
        if project.access_type not in {"PM", "PC", "C"}:
            raise InputError(f"contract {project.contract_number}: invalid access_type")
        if project.nature_of_activity not in {"Live", "Non-live (Consist)", "Non-live (Others)"}:
            raise InputError(f"contract {project.contract_number}: unsupported nature_of_activity")
    resolved: set[str] = set()
    for activity in instance.activities.values():
        if not activity.activity_id or activity.activity_priority not in {1, 2, 3}:
            raise InputError(f"activity {activity.activity_id}: invalid identifier or priority")
        activity_footprint(instance, activity)
        contract_activity_counts[activity.contract_number] += 1
        path: set[str] = set()
        current: str | None = activity.activity_id
        while current and current not in resolved:
            if current in path:
                raise InputError(f"predecessor cycle involving {current}")
            path.add(current)
            current = instance.activities[current].predecessor_activity_id
        resolved.update(path)
    if set(contract_activity_counts) != set(instance.projects):
        raise InputError("Every input contract must contain at least one activity")
    return instance


def _rule(detail: str) -> str:
    """Classify the existing evaluator's diagnostics without changing its rules."""
    text = detail.lower()
    for token, rule in (
        ("closure conflict", "closure"),
        ("buffer overlap", "closure"),
        ("capacity exceeded", "capacity"),
        ("planned completion exceeded", "planned_date"),
        ("eclo", "eclo"),
        ("workfront", "workfront"),
        ("access_night", "weekly_allocation"),
        ("weekly allocation", "weekly_allocation"),
        ("predecessor", "predecessor"),
        ("outside horizon", "horizon"),
        ("starts in week", "planned_start"),
        ("workload", "workload"),
        ("no scheduled access", "workload"),
        ("access_seq", "access_sequence"),
        ("more than one access", "access_sequence"),
        ("illegal mix", "legal_mix"),
        ("occupancy", "occupancy"),
        ("co_share_group", "occupancy"),
        ("results", "results"),
        ("scenario", "scenario"),
    ):
        if token in text:
            return rule
    return "schema"


def _violation(rule: str, detail: str) -> dict[str, str]:
    return {"rule": rule, "severity": "hard", "detail": detail}


def _base_report(scenario: str | None, strict_buffers: bool) -> dict:
    return {
        "validator": {"name": "nebula-ps1-local-validator", "version": VERSION, "origin": "local feasibility engine with independent raw-CSV score cross-check; not organiser source", "reference_validator_confirmed": False, "closure_policy": "strict_buffer_overlap" if strict_buffers else "observed_standard", "known_evidence": ["A-001: five closure violations", "A-002: feasible, 137.9", "B-001: feasible, 30.0", "C-001: feasible, 62.7"]},
        "scenario": scenario,
        "feasible": False,
        "hard_violations": [],
        "soft_scores": {},
        "detail": {},
        "warnings": ["Local validation does not establish official acceptance or complete equivalence on hidden instances."],
    }


def validate(data: str | Path, submission: str | Path, scenario: str | None = None,
             *, strict_buffers: bool = False) -> dict:
    """Validate an eight-CSV instance and a three-CSV submission (folder or ZIP).

    Returns a JSON-serializable report. An objective is included only for a
    locally feasible submission. Strict buffer findings are advisory by default.
    """
    report = _base_report(scenario, strict_buffers)
    phase = "instance"
    try:
        if scenario is not None and scenario not in {"A", "B", "C"}:
            report["hard_violations"] = [_violation("scenario", f"Unknown scenario: {scenario!r}")]
            return report
        with _materialize(Path(data), set(INPUT_SCHEMAS), exact=False) as data_root:
            instance = _check_instance(data_root)
            report["dataset_hash"] = instance.dataset_hash
            phase = "submission"
            with _materialize(Path(submission), set(SUBMISSION_SCHEMAS), exact=True) as submission_root:
                raw = {name: _csv_rows(submission_root / name, schema) for name, schema in SUBMISSION_SCHEMAS.items()}
                scenarios = {r["scenario"].strip() for r in raw["RESULTS.csv"]}
                if len(scenarios) != 1 or not scenarios <= {"A", "B", "C"}:
                    report["hard_violations"] = [_violation("scenario", f"RESULTS.csv must contain exactly one valid scenario; found {sorted(scenarios)}")]
                    return report
                selected = next(iter(scenarios))
                report["scenario"] = scenario or selected
                if scenario is not None and selected != scenario:
                    report["hard_violations"] = [_violation("scenario", f"RESULTS.csv scenario {selected} disagrees with requested {scenario}")]
                    return report
                access, occupancy, _ = load_submission(submission_root)
                # Out-of-domain weeks must never reach datetime arithmetic.
                outside = [r for r in access if not 1 <= r.week <= instance.horizon_weeks]
                if outside:
                    report["hard_violations"] = [_violation("horizon", f"{r.activity_id}: week {r.week} outside 1..{instance.horizon_weeks}") for r in outside]
                    return report
                evaluation = evaluate_submission(instance, submission_root, selected)
                violations = [_violation(_rule(v), v) for v in evaluation.hard_violations]
                valid_access = [r for r in access if r.activity_id in instance.activities]
                valid_keys = {(r.activity_id, r.week) for r in valid_access}
                valid_occupancy = [r for r in occupancy if r.activity_id in instance.activities and r.location_id in instance.locations and (r.activity_id, r.week) in valid_keys]
                standard = screen_closures(instance, valid_access, valid_occupancy)
                strict = screen_closures(instance, valid_access, valid_occupancy, forbid_buffer_overlap=True)
                additional = sorted({c.describe() for c in strict} - {c.describe() for c in standard})
                if strict_buffers:
                    violations.extend(_violation("closure", v) for v in additional)
                report["hard_violations"] = violations
                report["feasible"] = not violations
                report["submission_hash"] = evaluation.submission_hash
                report["checked_rules"] = list(evaluation.checked_rules)
                if additional and not strict_buffers:
                    report["warnings"].append(f"Extra strict buffer-overlap screen found {len(additional)} advisory conflicts; these do not alter standard feasibility.")
                completion = defaultdict(int)
                for row in valid_access:
                    completion[row.activity_id] = max(completion[row.activity_id], row.week)
                contracts = []
                for key, project in instance.projects.items():
                    jobs = [a for a in instance.activities.values() if a.contract_number == key]
                    if not all(a.activity_id in completion for a in jobs):
                        contracts.append({"contract_number": key, "complete_schedule": False})
                        continue
                    finish = instance.completion_date(max(completion[a.activity_id] for a in jobs))
                    late = max(0, (finish - project.planned_completion_date).days)
                    weight = CONTRACT_WEIGHT[project.contract_priority] * sum(1 + ACTIVITY_NUDGE[a.activity_priority] for a in jobs)
                    contracts.append({"contract_number": key, "complete_schedule": True, "simulated_completion_date": finish.isoformat(), "overrun_days": late, "earliness_days": max(0, (project.planned_completion_date - finish).days), "delay_penalty": round(late * weight, 10)})
                scores = {
                    "scenario": selected,
                    "overrun_days_total": sum(c.get("overrun_days", 0) for c in contracts),
                    "contracts_overrunning": sum(c.get("overrun_days", 0) > 0 for c in contracts),
                    "earliness_days_total": sum(c.get("earliness_days", 0) for c in contracts),
                    "excess_access_nights_total": evaluation.excess_access_nights_total,
                    "eclo_nights_total": evaluation.eclo_nights_total,
                    "priority_overrun": {str(k): v for k, v in evaluation.priority_overrun.items()},
                    "priority_weighted_score": evaluation.priority_weighted_score,
                }
                if report["feasible"]:
                    independent = independently_score(data_root, submission_root)
                    score_mismatches = []
                    for label, first, second in (
                        (
                            "objective_score",
                            evaluation.objective_score,
                            independent.objective_score,
                        ),
                        (
                            "priority_weighted_score",
                            evaluation.priority_weighted_score,
                            independent.priority_weighted_delay,
                        ),
                        (
                            "excess_access_nights_total",
                            evaluation.excess_access_nights_total,
                            independent.excess_access_nights,
                        ),
                        (
                            "eclo_nights_total",
                            evaluation.eclo_nights_total,
                            independent.eclo_nights,
                        ),
                    ):
                        if abs(first - second) > 1e-9:
                            score_mismatches.append(
                                f"{label}: evaluator={first}, independent={second}"
                            )
                    if score_mismatches:
                        violations.append(
                            _violation(
                                "internal_consistency",
                                "score cross-check disagrees: "
                                + "; ".join(score_mismatches),
                            )
                        )
                        report["feasible"] = False
                    else:
                        scores.update(
                            objective_score=evaluation.objective_score,
                            formula_version=FORMULA_VERSION,
                            independent_score_matches=True,
                        )
                groups = defaultdict(set)
                for row in valid_occupancy:
                    groups[row.location_id, row.week].add(row.co_share_group)
                hotspots = []
                for (location, week), group_set in sorted(groups.items()):
                    capacity = instance.locations[location].supply_capacity
                    if len(group_set) > capacity:
                        hotspots.append({"location_id": location, "week": week, "possessions": len(group_set), "nominal_capacity": capacity, "excess": max(0, len(group_set) - capacity)})
                report["soft_scores"] = scores
                report["detail"] = {"contracts": contracts, "capacity_hotspots": hotspots, "access_rows_scheduled": len(access), "occupancy_rows": len(occupancy), "eclo_nights": evaluation.eclo_nights_total, "strict_buffer_overlap": {"enforced": strict_buffers, "additional_conflicts": additional}}
    except PackError as exc:
        report["hard_violations"] = [_violation("packaging", f"{phase}: {exc}")]
    except (InputError, OSError, UnicodeError, csv.Error, ValueError, KeyError, TypeError, OverflowError) as exc:
        report["hard_violations"] = [_violation("input" if phase == "instance" else "schema", f"{phase}: {exc}")]
    # Any caught parsing/diagnostic error must fail closed and suppress scoring.
    if report["hard_violations"]:
        report["feasible"] = False
        report["soft_scores"].pop("objective_score", None)
        report["soft_scores"].pop("formula_version", None)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Portable local PS1 validator (not the organiser's validator).")
    parser.add_argument("--data", required=True, help="Folder or ZIP containing the eight instance CSVs")
    parser.add_argument("--submission", required=True, help="Folder or ZIP containing exactly three submission CSVs")
    parser.add_argument("--scenario", choices=("A", "B", "C"), help="Optional expected scenario; otherwise inferred from RESULTS.csv")
    parser.add_argument("--strict-buffers", action="store_true", help="Enforce the additional conservative buffer-overlap screen")
    parser.add_argument("--output", help="Also save the JSON report to this path")
    parser.add_argument("--version", action="version", version=f"nebula-ps1-local-validator {VERSION}")
    args = parser.parse_args(argv)
    report = validate(args.data, args.submission, args.scenario, strict_buffers=args.strict_buffers)
    text = json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n"
    if args.output:
        try:
            Path(args.output).write_text(text, encoding="utf-8")
        except OSError as exc:
            print(f"Cannot write report: {exc}", file=sys.stderr)
            return 2
    print(text, end="")
    return 0 if report["feasible"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
