from __future__ import annotations

import csv
from datetime import date, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "fixtures" / "independent_eclo_compaction_scale_v1"
SOURCE = ROOT / "fixtures" / "independent_eclo_compaction_scale_v1_source_c"
REVERSE_SOURCE = (
    ROOT / "fixtures" / "independent_eclo_compaction_scale_v1_reverse_source_c"
)
ACTIVITY_COUNT = 120
HORIZON_START = date(2033, 1, 3)


def _write(path: Path, fields: tuple[str, ...], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _completion_date(week: int) -> str:
    return (HORIZON_START + timedelta(days=7 * week - 1)).isoformat()


def main() -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    SOURCE.mkdir(parents=True, exist_ok=True)
    REVERSE_SOURCE.mkdir(parents=True, exist_ok=True)
    horizon_weeks = 3 * ACTIVITY_COUNT
    _write(
        DATA / "01_LINES.csv",
        ("line_code", "line_name"),
        [{"line_code": "LSZ", "line_name": "Synthetic Serial Line"}],
    )
    _write(
        DATA / "02_STATIONS.csv",
        ("station_id", "line_code", "seq", "is_interchange"),
        [
            {"station_id": station, "line_code": "LSZ", "seq": seq, "is_interchange": 0}
            for seq, station in enumerate(("U1", "U2", "U3"), 1)
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
                "sector_id": f"SEC:LSZ:U{seq}_U{seq + 1}",
                "line_code": "LSZ",
                "from_station_id": f"U{seq}",
                "to_station_id": f"U{seq + 1}",
                "seq": seq,
                "is_shared": 0,
            }
            for seq in (1, 2)
        ],
    )
    locations = [
        {
            "location_id": f"PLAT:LSZ:{station}:{bound}",
            "location_kind": "platform",
            "line_code": "LSZ",
            "bound": bound,
            "supply_capacity": 1,
        }
        for station in ("U1", "U2", "U3")
        for bound in ("EB", "WB")
    ] + [
        {
            "location_id": f"SEC:LSZ:U{seq}_U{seq + 1}:{bound}",
            "location_kind": "tunnel sector",
            "line_code": "LSZ",
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
            {"key": "horizon_weeks", "value": horizon_weeks},
        ],
    )

    projects: list[dict[str, object]] = []
    activities: list[dict[str, object]] = []
    access: list[dict[str, object]] = []
    occupancy: list[dict[str, object]] = []
    results: list[dict[str, object]] = []
    footprint = (
        "PLAT:LSZ:U1:EB",
        "PLAT:LSZ:U2:EB",
        "PLAT:LSZ:U3:EB",
        "SEC:LSZ:U1_U2:EB",
        "SEC:LSZ:U2_U3:EB",
    )
    for index in range(1, ACTIVITY_COUNT + 1):
        contract = f"KS{index:03d}"
        activity = f"TS{index:03d}"
        completion_week = 3 * index
        completion_date = _completion_date(completion_week)
        projects.append(
            {
                "contract_number": contract,
                "contract_description": f"Serial scale job {index}",
                "contract_award_date": "2032-06-01",
                "activity_type": "Synthetic",
                "nature_of_activity": "Non-live (Others)",
                "contract_priority": 1 + ((index - 1) % 3),
                "contract_completion_date": completion_date,
                "planned_completion_date": completion_date,
                "number_of_workfronts": 1,
                "access_type": "PM",
                "number_of_maximum_access_per_week": 1,
            }
        )
        activities.append(
            {
                "activity_id": activity,
                "contract_number": contract,
                "activity_type": "Synthetic",
                "start_location_id": "SEC:LSZ:U1_U2:EB",
                "end_location_id": "SEC:LSZ:U2_U3:EB",
                "total_accesses": 3,
                "planned_start_date": HORIZON_START.isoformat(),
                "predecessor_activity_id": "",
                "activity_priority": 3,
            }
        )
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
        results.append(
            {
                "scenario": "C",
                "contract_number": contract,
                "simulated_completion_date": completion_date,
                "overrun_days": 0,
            }
        )

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

    reverse_access: list[dict[str, object]] = []
    reverse_occupancy: list[dict[str, object]] = []
    reverse_results: list[dict[str, object]] = []
    completion_by_index: dict[int, int] = {}
    for position, index in enumerate(range(ACTIVITY_COUNT, 0, -1), 1):
        activity = f"TS{index:03d}"
        completion_week = 3 * position
        completion_by_index[index] = completion_week
        for sequence, week in enumerate(
            range(completion_week - 2, completion_week + 1), 1
        ):
            reverse_access.append(
                {
                    "activity_id": activity,
                    "access_seq": sequence,
                    "week": week,
                    "eclo": 0,
                    "access_night": 1,
                }
            )
            reverse_occupancy.extend(
                {
                    "activity_id": activity,
                    "week": week,
                    "location_id": location,
                    "co_share_group": "g1",
                }
                for location in footprint
            )
    for index in range(1, ACTIVITY_COUNT + 1):
        completion = HORIZON_START + timedelta(
            days=7 * completion_by_index[index] - 1
        )
        planned = HORIZON_START + timedelta(days=7 * (3 * index) - 1)
        reverse_results.append(
            {
                "scenario": "C",
                "contract_number": f"KS{index:03d}",
                "simulated_completion_date": completion.isoformat(),
                "overrun_days": max(0, (completion - planned).days),
            }
        )
    _write(
        REVERSE_SOURCE / "SCHEDULE_ACCESS.csv",
        ("activity_id", "access_seq", "week", "eclo", "access_night"),
        reverse_access,
    )
    _write(
        REVERSE_SOURCE / "SCHEDULE_OCCUPANCY.csv",
        ("activity_id", "week", "location_id", "co_share_group"),
        reverse_occupancy,
    )
    _write(
        REVERSE_SOURCE / "RESULTS.csv",
        ("scenario", "contract_number", "simulated_completion_date", "overrun_days"),
        reverse_results,
    )


if __name__ == "__main__":
    main()
