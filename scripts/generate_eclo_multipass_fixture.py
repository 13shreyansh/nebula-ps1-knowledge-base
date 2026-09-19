from __future__ import annotations

import csv
from datetime import date, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "fixtures" / "independent_eclo_multipass_v1"
SOURCE = ROOT / "fixtures" / "independent_eclo_multipass_v1_source_c"
HORIZON_START = date(2035, 1, 1)


def _write(path: Path, fields: tuple[str, ...], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _date_for_week(week: int) -> date:
    return HORIZON_START + timedelta(days=7 * week - 1)


def main() -> None:
    lines = ("MPX", "MPY")
    _write(
        DATA / "01_LINES.csv",
        ("line_code", "line_name"),
        [
            {"line_code": line, "line_name": f"Multipass {line}"}
            for line in lines
        ],
    )
    stations = [
        {
            "station_id": f"{line}{index}",
            "line_code": line,
            "seq": index,
            "is_interchange": 0,
        }
        for line in lines
        for index in (1, 2)
    ]
    _write(
        DATA / "02_STATIONS.csv",
        ("station_id", "line_code", "seq", "is_interchange"),
        stations,
    )
    _write(
        DATA / "03_SECTORS.csv",
        (
            "sector_id",
            "line_code",
            "from_station_id",
            "to_station_id",
            "seq",
            "is_shared",
        ),
        [
            {
                "sector_id": f"SEC:{line}:{line}1_{line}2",
                "line_code": line,
                "from_station_id": f"{line}1",
                "to_station_id": f"{line}2",
                "seq": 1,
                "is_shared": 0,
            }
            for line in lines
        ],
    )
    locations = [
        {
            "location_id": f"PLAT:{line}:{line}{index}:{bound}",
            "location_kind": "platform",
            "line_code": line,
            "bound": bound,
            "supply_capacity": 1,
        }
        for line in lines
        for index in (1, 2)
        for bound in ("EB", "WB")
    ] + [
        {
            "location_id": f"SEC:{line}:{line}1_{line}2:{bound}",
            "location_kind": "tunnel sector",
            "line_code": line,
            "bound": bound,
            "supply_capacity": 1,
        }
        for line in lines
        for bound in ("EB", "WB")
    ]
    _write(
        DATA / "04_LOCATION_SUPPLY.csv",
        ("location_id", "location_kind", "line_code", "bound", "supply_capacity"),
        locations,
    )
    _write(
        DATA / "05_BUFFER_LOCATION.csv",
        ("nature_of_works", "up_to_buffer_sectors", "opposite_bound_required"),
        [
            {
                "nature_of_works": "Non-live (Others)",
                "up_to_buffer_sectors": 0,
                "opposite_bound_required": 0,
            }
        ],
    )
    _write(
        DATA / "06_PARAMETERS.csv",
        ("key", "value"),
        [
            {"key": "horizon_start", "value": HORIZON_START.isoformat()},
            {"key": "horizon_weeks", "value": 12},
        ],
    )

    specs = (
        ("MX1", "MPX", 3),
        ("MX2", "MPX", 6),
        ("MY1", "MPY", 9),
        ("MY2", "MPY", 12),
    )
    projects = [
        {
            "contract_number": f"K{activity}",
            "contract_description": f"Multipass contract {activity}",
            "contract_award_date": "2034-06-01",
            "activity_type": "Synthetic",
            "nature_of_activity": "Non-live (Others)",
            "contract_priority": 1,
            "contract_completion_date": _date_for_week(12).isoformat(),
            "planned_completion_date": _date_for_week(1).isoformat(),
            "number_of_workfronts": 1,
            "access_type": "PM",
            "number_of_maximum_access_per_week": 1,
        }
        for activity, _, _ in specs
    ]
    activities = [
        {
            "activity_id": activity,
            "contract_number": f"K{activity}",
            "activity_type": "Synthetic",
            "start_location_id": f"SEC:{line}:{line}1_{line}2:EB",
            "end_location_id": f"SEC:{line}:{line}1_{line}2:EB",
            "total_accesses": 3,
            "planned_start_date": HORIZON_START.isoformat(),
            "predecessor_activity_id": "",
            "activity_priority": 1,
        }
        for activity, line, _ in specs
    ]
    _write(
        DATA / "07_PROJECT_DETAILS.csv",
        (
            "contract_number",
            "contract_description",
            "contract_award_date",
            "activity_type",
            "nature_of_activity",
            "contract_priority",
            "contract_completion_date",
            "planned_completion_date",
            "number_of_workfronts",
            "access_type",
            "number_of_maximum_access_per_week",
        ),
        projects,
    )
    _write(
        DATA / "08_ACTIVITY_DETAILS.csv",
        (
            "activity_id",
            "contract_number",
            "activity_type",
            "start_location_id",
            "end_location_id",
            "total_accesses",
            "planned_start_date",
            "predecessor_activity_id",
            "activity_priority",
        ),
        activities,
    )

    access: list[dict[str, object]] = []
    occupancy: list[dict[str, object]] = []
    results: list[dict[str, object]] = []
    for activity, line, completion_week in specs:
        for sequence, week in enumerate(
            range(completion_week - 2, completion_week + 1), 1
        ):
            access.append(
                {
                    "activity_id": activity,
                    "access_seq": sequence,
                    "week": week,
                    "eclo": 0,
                    "access_night": 1,
                }
            )
            for location in (
                f"PLAT:{line}:{line}1:EB",
                f"PLAT:{line}:{line}2:EB",
                f"SEC:{line}:{line}1_{line}2:EB",
            ):
                occupancy.append(
                    {
                        "activity_id": activity,
                        "week": week,
                        "location_id": location,
                        "co_share_group": "g1",
                    }
                )
        completion = _date_for_week(completion_week)
        planned = _date_for_week(1)
        results.append(
            {
                "scenario": "C",
                "contract_number": f"K{activity}",
                "simulated_completion_date": completion.isoformat(),
                "overrun_days": (completion - planned).days,
            }
        )
    _write(
        SOURCE / "SCHEDULE_ACCESS.csv",
        ("activity_id", "access_seq", "week", "eclo", "access_night"),
        access,
    )
    _write(
        SOURCE / "SCHEDULE_OCCUPANCY.csv",
        ("activity_id", "week", "location_id", "co_share_group"),
        occupancy,
    )
    _write(
        SOURCE / "RESULTS.csv",
        ("scenario", "contract_number", "simulated_completion_date", "overrun_days"),
        results,
    )


if __name__ == "__main__":
    main()
