from __future__ import annotations

import argparse
import csv
from datetime import date, timedelta
from pathlib import Path


def write(path: Path, fields: tuple[str, ...], rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Generate a fixed three-line interchange holdout without an answer key."
        )
    )
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    output = Path(args.output)
    if output.exists() and any(output.iterdir()):
        raise ValueError(f"output directory must be empty: {output}")
    output.mkdir(parents=True, exist_ok=True)

    horizon_start = date.fromisoformat("2037-01-05")

    def week_start(week: int) -> str:
        return (horizon_start + timedelta(days=7 * (week - 1))).isoformat()

    def week_end(week: int) -> str:
        return (horizon_start + timedelta(days=7 * week - 1)).isoformat()

    lines = ("LIA", "LIB", "LIC")
    outer = {"LIA": ("A1", "A4"), "LIB": ("B1", "B4"), "LIC": ("C1", "C4")}
    stations = {
        line: (left, "H1", "H2", right)
        for line, (left, right) in outer.items()
    }

    write(
        output / "01_LINES.csv",
        ("line_code", "line_name"),
        [
            {"line_code": line, "line_name": f"Interchange holdout {line}"}
            for line in lines
        ],
    )
    write(
        output / "02_STATIONS.csv",
        ("station_id", "line_code", "seq", "is_interchange"),
        [
            {
                "station_id": station,
                "line_code": line,
                "seq": sequence,
                "is_interchange": int(station in {"H1", "H2"}),
            }
            for line in lines
            for sequence, station in enumerate(stations[line], start=1)
        ],
    )

    sectors: list[dict[str, object]] = []
    locations: list[dict[str, object]] = []
    for line in lines:
        for sequence, (left, right) in enumerate(
            zip(stations[line][:-1], stations[line][1:], strict=True), start=1
        ):
            sector_id = f"SEC:{line}:{left}_{right}"
            sectors.append(
                {
                    "sector_id": sector_id,
                    "line_code": line,
                    "from_station_id": left,
                    "to_station_id": right,
                    "seq": sequence,
                    "is_shared": int({left, right} == {"H1", "H2"}),
                }
            )
            for bound in ("EB", "WB"):
                locations.append(
                    {
                        "location_id": f"{sector_id}:{bound}",
                        "location_kind": "tunnel sector",
                        "line_code": line,
                        "bound": bound,
                        "supply_capacity": 1 if sequence == 2 else 2,
                    }
                )
        for station in stations[line]:
            for bound in ("EB", "WB"):
                locations.append(
                    {
                        "location_id": f"PLAT:{line}:{station}:{bound}",
                        "location_kind": "platform",
                        "line_code": line,
                        "bound": bound,
                        "supply_capacity": 1 if station in {"H1", "H2"} else 2,
                    }
                )
    write(
        output / "03_SECTORS.csv",
        (
            "sector_id",
            "line_code",
            "from_station_id",
            "to_station_id",
            "seq",
            "is_shared",
        ),
        sectors,
    )
    write(
        output / "04_LOCATION_SUPPLY.csv",
        ("location_id", "location_kind", "line_code", "bound", "supply_capacity"),
        locations,
    )
    write(
        output / "05_BUFFER_LOCATION.csv",
        ("nature_of_works", "up_to_buffer_sectors", "opposite_bound_required"),
        [
            {
                "nature_of_works": "Live",
                "up_to_buffer_sectors": 1,
                "opposite_bound_required": 1,
            },
            {
                "nature_of_works": "Non-live (Consist)",
                "up_to_buffer_sectors": 0,
                "opposite_bound_required": 0,
            },
        ],
    )
    write(
        output / "06_PARAMETERS.csv",
        ("key", "value"),
        [
            {"key": "horizon_start", "value": horizon_start.isoformat()},
            {"key": "horizon_weeks", "value": 8},
        ],
    )

    project_specs = (
        ("KLA", "Live A bridge", "Live", 1, 2, "PC", 1),
        ("KLB", "Live B bridge", "Live", 2, 2, "C", 1),
        ("KLC", "Consist C bridge", "Non-live (Consist)", 3, 3, "C", 2),
        ("KPA", "A outer PM", "Non-live (Consist)", 2, 5, "PM", 1),
        ("KPB", "B outer PC", "Non-live (Consist)", 2, 4, "PC", 2),
        ("KCC", "C successor", "Non-live (Consist)", 3, 5, "C", 1),
    )
    write(
        output / "07_PROJECT_DETAILS.csv",
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
        [
            {
                "contract_number": contract,
                "contract_description": description,
                "contract_award_date": "2036-06-01",
                "activity_type": "InterchangeHoldout",
                "nature_of_activity": nature,
                "contract_priority": priority,
                "contract_completion_date": week_end(8),
                "planned_completion_date": week_end(deadline_week),
                "number_of_workfronts": 1,
                "access_type": access_type,
                "number_of_maximum_access_per_week": maximum,
            }
            for (
                contract,
                description,
                nature,
                priority,
                deadline_week,
                access_type,
                maximum,
            ) in project_specs
        ],
    )

    activity_specs = (
        ("HLA", "KLA", "SEC:LIA:H1_H2:EB", 3, 1, "", 1),
        ("HLB", "KLB", "SEC:LIB:H1_H2:WB", 1, 1, "", 2),
        ("HLC", "KLC", "SEC:LIC:H1_H2:EB", 2, 1, "", 3),
        ("OPA", "KPA", "SEC:LIA:A1_H1:WB", 2, 3, "", 2),
        ("OPB", "KPB", "SEC:LIB:H2_B4:EB", 2, 2, "", 1),
        ("SCC", "KCC", "SEC:LIC:H2_C4:WB", 1, 2, "HLC", 2),
    )
    write(
        output / "08_ACTIVITY_DETAILS.csv",
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
        [
            {
                "activity_id": activity,
                "contract_number": contract,
                "activity_type": "InterchangeHoldout",
                "start_location_id": location,
                "end_location_id": location,
                "total_accesses": accesses,
                "planned_start_date": week_start(release_week),
                "predecessor_activity_id": predecessor,
                "activity_priority": priority,
            }
            for (
                activity,
                contract,
                location,
                accesses,
                release_week,
                predecessor,
                priority,
            ) in activity_specs
        ],
    )


if __name__ == "__main__":
    main()
