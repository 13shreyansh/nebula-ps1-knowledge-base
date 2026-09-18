from __future__ import annotations

import csv
import hashlib
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Iterable


class InputError(ValueError):
    """Raised when an input pack violates the published schema."""


@dataclass(frozen=True)
class Station:
    station_id: str
    line_code: str
    seq: int
    is_interchange: bool


@dataclass(frozen=True)
class Sector:
    sector_id: str
    line_code: str
    from_station_id: str
    to_station_id: str
    seq: int
    is_shared: bool


@dataclass(frozen=True)
class LocationSupply:
    location_id: str
    location_kind: str
    line_code: str
    bound: str
    supply_capacity: int


@dataclass(frozen=True)
class BufferRule:
    nature_of_works: str
    up_to_buffer_sectors: int
    opposite_bound_required: bool


@dataclass(frozen=True)
class Project:
    contract_number: str
    activity_type: str
    nature_of_activity: str
    contract_priority: int
    contract_completion_date: date
    planned_completion_date: date
    number_of_workfronts: int
    access_type: str
    number_of_maximum_access_per_week: int


@dataclass(frozen=True)
class Activity:
    activity_id: str
    contract_number: str
    activity_type: str
    start_location_id: str
    end_location_id: str
    total_accesses: int
    planned_start_date: date
    predecessor_activity_id: str | None
    activity_priority: int


@dataclass(frozen=True)
class Instance:
    root: Path
    dataset_hash: str
    lines: tuple[str, ...]
    stations: dict[tuple[str, str], Station]
    sectors: dict[str, Sector]
    locations: dict[str, LocationSupply]
    buffers: dict[str, BufferRule]
    projects: dict[str, Project]
    activities: dict[str, Activity]
    horizon_start: date
    horizon_weeks: int

    def week_for_date(self, value: date) -> int:
        return ((value - self.horizon_start).days // 7) + 1

    def completion_date(self, week: int) -> date:
        return self.horizon_start + timedelta(days=7 * week - 1)

    def last_week_completing_by(self, value: date) -> int:
        """Return the final week whose Sunday completion does not exceed value."""

        return max(0, ((value - self.horizon_start).days + 1) // 7)


FILES = {
    "lines": "01_LINES.csv",
    "stations": "02_STATIONS.csv",
    "sectors": "03_SECTORS.csv",
    "locations": "04_LOCATION_SUPPLY.csv",
    "buffers": "05_BUFFER_LOCATION.csv",
    "parameters": "06_PARAMETERS.csv",
    "projects": "07_PROJECT_DETAILS.csv",
    "activities": "08_ACTIVITY_DETAILS.csv",
}


def _rows(path: Path, required: Iterable[str]) -> list[dict[str, str]]:
    try:
        with path.open(newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle)
            missing = set(required) - set(reader.fieldnames or ())
            if missing:
                raise InputError(f"{path.name}: missing columns {sorted(missing)}")
            rows = list(reader)
    except FileNotFoundError as exc:
        raise InputError(f"missing required file: {path}") from exc
    if not rows:
        raise InputError(f"{path.name}: file has no data rows")
    return rows


def _unique(items: Iterable[object], key_name: str, label: str) -> dict[str, object]:
    result: dict[str, object] = {}
    for item in items:
        key = str(getattr(item, key_name))
        if key in result:
            raise InputError(f"duplicate {label}: {key}")
        result[key] = item
    return result


def _as_int(row: dict[str, str], field: str, source: str, minimum: int | None = None) -> int:
    try:
        value = int(row[field])
    except (KeyError, ValueError) as exc:
        raise InputError(f"{source}: {field} must be an integer") from exc
    if minimum is not None and value < minimum:
        raise InputError(f"{source}: {field} must be >= {minimum}")
    return value


def _as_date(row: dict[str, str], field: str, source: str) -> date:
    try:
        return date.fromisoformat(row[field])
    except (KeyError, ValueError) as exc:
        raise InputError(f"{source}: {field} must be an ISO date") from exc


def _dataset_hash(data_dir: Path) -> str:
    digest = hashlib.sha256()
    for name in FILES.values():
        path = data_dir / name
        digest.update(name.encode())
        digest.update(b"\0")
        try:
            digest.update(path.read_bytes())
        except FileNotFoundError as exc:
            raise InputError(f"missing required file: {path}") from exc
        digest.update(b"\0")
    return digest.hexdigest()


def load_instance(data_dir: str | Path) -> Instance:
    root = Path(data_dir).resolve()

    line_rows = _rows(root / FILES["lines"], ["line_code", "line_name"])
    lines = tuple(row["line_code"].strip() for row in line_rows)
    if len(set(lines)) != len(lines):
        raise InputError("01_LINES.csv: duplicate line_code")

    station_rows = _rows(
        root / FILES["stations"], ["station_id", "line_code", "seq", "is_interchange"]
    )
    stations: dict[tuple[str, str], Station] = {}
    station_sequences: set[tuple[str, int]] = set()
    for row in station_rows:
        station = Station(
            row["station_id"].strip(),
            row["line_code"].strip(),
            _as_int(row, "seq", FILES["stations"], 1),
            bool(_as_int(row, "is_interchange", FILES["stations"], 0)),
        )
        key = (station.line_code, station.station_id)
        if key in stations:
            raise InputError(f"duplicate station key: {key}")
        seq_key = (station.line_code, station.seq)
        if seq_key in station_sequences:
            raise InputError(f"duplicate station sequence: {seq_key}")
        if station.line_code not in lines:
            raise InputError(f"station {station.station_id}: unknown line {station.line_code}")
        stations[key] = station
        station_sequences.add(seq_key)

    sector_rows = _rows(
        root / FILES["sectors"],
        ["sector_id", "line_code", "from_station_id", "to_station_id", "seq", "is_shared"],
    )
    sector_objects: list[Sector] = []
    sector_sequences: set[tuple[str, int]] = set()
    for row in sector_rows:
        sector = Sector(
            row["sector_id"].strip(),
            row["line_code"].strip(),
            row["from_station_id"].strip(),
            row["to_station_id"].strip(),
            _as_int(row, "seq", FILES["sectors"], 1),
            bool(_as_int(row, "is_shared", FILES["sectors"], 0)),
        )
        if (sector.line_code, sector.from_station_id) not in stations or (
            sector.line_code,
            sector.to_station_id,
        ) not in stations:
            raise InputError(f"sector {sector.sector_id}: unknown endpoint")
        seq_key = (sector.line_code, sector.seq)
        if seq_key in sector_sequences:
            raise InputError(f"duplicate sector sequence: {seq_key}")
        sector_sequences.add(seq_key)
        sector_objects.append(sector)
    sectors = _unique(sector_objects, "sector_id", "sector_id")

    location_rows = _rows(
        root / FILES["locations"],
        ["location_id", "location_kind", "line_code", "bound", "supply_capacity"],
    )
    locations = _unique(
        (
            LocationSupply(
                row["location_id"].strip(),
                row["location_kind"].strip(),
                row["line_code"].strip(),
                row["bound"].strip(),
                _as_int(row, "supply_capacity", FILES["locations"], 0),
            )
            for row in location_rows
        ),
        "location_id",
        "location_id",
    )

    buffer_rows = _rows(
        root / FILES["buffers"],
        ["nature_of_works", "up_to_buffer_sectors", "opposite_bound_required"],
    )
    buffers = _unique(
        (
            BufferRule(
                row["nature_of_works"].strip(),
                _as_int(row, "up_to_buffer_sectors", FILES["buffers"], 0),
                bool(_as_int(row, "opposite_bound_required", FILES["buffers"], 0)),
            )
            for row in buffer_rows
        ),
        "nature_of_works",
        "nature_of_works",
    )

    parameter_rows = _rows(root / FILES["parameters"], ["key", "value"])
    parameters = {row["key"].strip(): row["value"].strip() for row in parameter_rows}
    try:
        horizon_start = date.fromisoformat(parameters["horizon_start"])
        horizon_weeks = int(parameters["horizon_weeks"])
    except (KeyError, ValueError) as exc:
        raise InputError("06_PARAMETERS.csv: invalid horizon_start or horizon_weeks") from exc
    if horizon_weeks < 1:
        raise InputError("06_PARAMETERS.csv: horizon_weeks must be positive")

    project_rows = _rows(
        root / FILES["projects"],
        [
            "contract_number",
            "activity_type",
            "nature_of_activity",
            "contract_priority",
            "contract_completion_date",
            "planned_completion_date",
            "number_of_workfronts",
            "access_type",
            "number_of_maximum_access_per_week",
        ],
    )
    projects = _unique(
        (
            Project(
                row["contract_number"].strip(),
                row["activity_type"].strip(),
                row["nature_of_activity"].strip(),
                _as_int(row, "contract_priority", FILES["projects"], 1),
                _as_date(row, "contract_completion_date", FILES["projects"]),
                _as_date(row, "planned_completion_date", FILES["projects"]),
                _as_int(row, "number_of_workfronts", FILES["projects"], 1),
                row["access_type"].strip(),
                _as_int(row, "number_of_maximum_access_per_week", FILES["projects"], 1),
            )
            for row in project_rows
        ),
        "contract_number",
        "contract_number",
    )

    activity_rows = _rows(
        root / FILES["activities"],
        [
            "activity_id",
            "contract_number",
            "activity_type",
            "start_location_id",
            "end_location_id",
            "total_accesses",
            "planned_start_date",
            "predecessor_activity_id",
            "activity_priority",
        ],
    )
    activities = _unique(
        (
            Activity(
                row["activity_id"].strip(),
                row["contract_number"].strip(),
                row["activity_type"].strip(),
                row["start_location_id"].strip(),
                row["end_location_id"].strip(),
                _as_int(row, "total_accesses", FILES["activities"], 1),
                _as_date(row, "planned_start_date", FILES["activities"]),
                row["predecessor_activity_id"].strip() or None,
                _as_int(row, "activity_priority", FILES["activities"], 1),
            )
            for row in activity_rows
        ),
        "activity_id",
        "activity_id",
    )

    for activity in activities.values():
        if activity.contract_number not in projects:
            raise InputError(f"activity {activity.activity_id}: unknown contract")
        project = projects[activity.contract_number]
        if activity.activity_type != project.activity_type:
            raise InputError(f"activity {activity.activity_id}: activity_type disagrees with contract")
        if activity.start_location_id not in locations or activity.end_location_id not in locations:
            raise InputError(f"activity {activity.activity_id}: unknown endpoint location")
        if activity.predecessor_activity_id and activity.predecessor_activity_id not in activities:
            raise InputError(f"activity {activity.activity_id}: unknown predecessor")
        if project.nature_of_activity not in buffers:
            raise InputError(f"contract {project.contract_number}: no buffer rule")

    return Instance(
        root=root,
        dataset_hash=_dataset_hash(root),
        lines=lines,
        stations=stations,
        sectors=sectors,
        locations=locations,
        buffers=buffers,
        projects=projects,
        activities=activities,
        horizon_start=horizon_start,
        horizon_weeks=horizon_weeks,
    )
