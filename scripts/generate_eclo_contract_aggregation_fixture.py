from __future__ import annotations

import csv
from datetime import date, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "fixtures" / "independent_eclo_contract_aggregation_v1"
SOURCE = ROOT / "fixtures" / "independent_eclo_contract_aggregation_v1_source_c"
HORIZON_START = date(2034, 1, 2)


def _write(path: Path, fields: tuple[str, ...], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _date_for_week(week: int) -> date:
    return HORIZON_START + timedelta(days=7 * week - 1)


def main() -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    SOURCE.mkdir(parents=True, exist_ok=True)
    _write(
        DATA / "01_LINES.csv",
        ("line_code", "line_name"),
        [{"line_code": "LCZ", "line_name": "Contract Aggregation Line"}],
    )
    _write(
        DATA / "02_STATIONS.csv",
        ("station_id", "line_code", "seq", "is_interchange"),
        [
            {"station_id": station, "line_code": "LCZ", "seq": seq, "is_interchange": 0}
            for seq, station in enumerate(("V1", "V2", "V3"), 1)
        ],
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
                "sector_id": f"SEC:LCZ:V{seq}_V{seq + 1}",
                "line_code": "LCZ",
                "from_station_id": f"V{seq}",
                "to_station_id": f"V{seq + 1}",
                "seq": seq,
                "is_shared": 0,
            }
            for seq in (1, 2)
        ],
    )
    locations = [
        {
            "location_id": f"PLAT:LCZ:{station}:{bound}",
            "location_kind": "platform",
            "line_code": "LCZ",
            "bound": bound,
            "supply_capacity": 1,
        }
        for station in ("V1", "V2", "V3")
        for bound in ("EB", "WB")
    ] + [
        {
            "location_id": f"SEC:LCZ:V{seq}_V{seq + 1}:{bound}",
            "location_kind": "tunnel sector",
            "line_code": "LCZ",
            "bound": bound,
            "supply_capacity": 1,
        }
        for seq in (1, 2)
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
            {"key": "horizon_weeks", "value": 18},
        ],
    )

    project_specs = (
        ("KC1", 1, 4),
        ("KC2", 2, 8),
        ("KC3", 3, 12),
    )
    projects = [
        {
            "contract_number": contract,
            "contract_description": f"Aggregation contract {contract}",
            "contract_award_date": "2033-06-01",
            "activity_type": "Synthetic",
            "nature_of_activity": "Non-live (Others)",
            "contract_priority": priority,
            "contract_completion_date": _date_for_week(18).isoformat(),
            "planned_completion_date": _date_for_week(due_week).isoformat(),
            "number_of_workfronts": 1,
            "access_type": "PM",
            "number_of_maximum_access_per_week": 1,
        }
        for contract, priority, due_week in project_specs
    ]
    activity_specs = (
        ("TC11", "KC1", 1),
        ("TC12", "KC1", 3),
        ("TC21", "KC2", 2),
        ("TC22", "KC2", 1),
        ("TC31", "KC3", 3),
        ("TC32", "KC3", 2),
    )
    activities = [
        {
            "activity_id": activity,
            "contract_number": contract,
            "activity_type": "Synthetic",
            "start_location_id": "SEC:LCZ:V1_V2:EB",
            "end_location_id": "SEC:LCZ:V2_V3:EB",
            "total_accesses": 3,
            "planned_start_date": HORIZON_START.isoformat(),
            "predecessor_activity_id": "",
            "activity_priority": priority,
        }
        for activity, contract, priority in activity_specs
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

    schedule_order = ("TC11", "TC21", "TC31", "TC32", "TC22", "TC12")
    footprint = (
        "PLAT:LCZ:V1:EB",
        "PLAT:LCZ:V2:EB",
        "PLAT:LCZ:V3:EB",
        "SEC:LCZ:V1_V2:EB",
        "SEC:LCZ:V2_V3:EB",
    )
    access: list[dict[str, object]] = []
    occupancy: list[dict[str, object]] = []
    completion_by_activity: dict[str, int] = {}
    for position, activity in enumerate(schedule_order, 1):
        completion_week = 3 * position
        completion_by_activity[activity] = completion_week
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
            occupancy.extend(
                {
                    "activity_id": activity,
                    "week": week,
                    "location_id": location,
                    "co_share_group": "g1",
                }
                for location in footprint
            )
    due_by_contract = {contract: due for contract, _, due in project_specs}
    activities_by_contract: dict[str, list[str]] = {
        contract: [
            activity
            for activity, activity_contract, _ in activity_specs
            if activity_contract == contract
        ]
        for contract, _, _ in project_specs
    }
    results = []
    for contract, _, _ in project_specs:
        completion_week = max(
            completion_by_activity[activity]
            for activity in activities_by_contract[contract]
        )
        completion = _date_for_week(completion_week)
        planned = _date_for_week(due_by_contract[contract])
        results.append(
            {
                "scenario": "C",
                "contract_number": contract,
                "simulated_completion_date": completion.isoformat(),
                "overrun_days": max(0, (completion - planned).days),
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
