from __future__ import annotations

import argparse
import csv
import shutil
from datetime import date, timedelta
from pathlib import Path


COPIED = (
    "01_LINES.csv",
    "02_STATIONS.csv",
    "03_SECTORS.csv",
    "04_LOCATION_SUPPLY.csv",
    "05_BUFFER_LOCATION.csv",
    "06_PARAMETERS.csv",
)


def read(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or ()), list(reader)


def write(path: Path, fields: list[str], rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a cross-contract predecessor repair fixture."
    )
    parser.add_argument("--base-data", required=True)
    parser.add_argument("--base-oracle", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--oracle-output", required=True)
    parser.add_argument("--delayed-output", required=True)
    args = parser.parse_args()
    base_data = Path(args.base_data)
    base_oracle = Path(args.base_oracle)
    output = Path(args.output)
    oracle = Path(args.oracle_output)
    delayed = Path(args.delayed_output)
    for path in (output, oracle, delayed):
        if path.exists() and any(path.iterdir()):
            raise ValueError(f"output directory must be empty: {path}")
        path.mkdir(parents=True, exist_ok=True)

    for name in COPIED:
        shutil.copyfile(base_data / name, output / name)
    parameters = {row["key"]: row["value"] for row in read(base_data / "06_PARAMETERS.csv")[1]}
    horizon_start = date.fromisoformat(parameters["horizon_start"])
    horizon_weeks = int(parameters["horizon_weeks"])
    completion_limit = horizon_start + timedelta(days=7 * horizon_weeks - 1)

    project_fields, _ = read(base_data / "07_PROJECT_DETAILS.csv")
    projects = [
        {
            "contract_number": "KPRE",
            "contract_description": "On-time predecessor",
            "contract_award_date": "2030-06-01",
            "activity_type": "PredecessorTradeoff",
            "nature_of_activity": "Non-live (Others)",
            "contract_priority": "1",
            "contract_completion_date": completion_limit.isoformat(),
            "planned_completion_date": (
                horizon_start + timedelta(days=7 * 10 - 1)
            ).isoformat(),
            "number_of_workfronts": "1",
            "access_type": "C",
            "number_of_maximum_access_per_week": "1",
        },
        {
            "contract_number": "KLATE",
            "contract_description": "Priority successor",
            "contract_award_date": "2030-06-01",
            "activity_type": "PredecessorTradeoff",
            "nature_of_activity": "Non-live (Others)",
            "contract_priority": "3",
            "contract_completion_date": completion_limit.isoformat(),
            "planned_completion_date": (
                horizon_start + timedelta(days=7 * 3 - 1)
            ).isoformat(),
            "number_of_workfronts": "1",
            "access_type": "C",
            "number_of_maximum_access_per_week": "1",
        },
    ]
    write(output / "07_PROJECT_DETAILS.csv", project_fields, projects)

    activity_fields, base_activities = read(base_data / "08_ACTIVITY_DETAILS.csv")
    by_id = {row["activity_id"]: row for row in base_activities}
    activities = [
        {
            **by_id["Q001"],
            "activity_id": "PRED",
            "contract_number": "KPRE",
            "activity_type": "PredecessorTradeoff",
            "total_accesses": "1",
            "planned_start_date": horizon_start.isoformat(),
            "predecessor_activity_id": "",
            "activity_priority": "1",
        },
        {
            **by_id["Q004"],
            "activity_id": "SUCC",
            "contract_number": "KLATE",
            "activity_type": "PredecessorTradeoff",
            "total_accesses": "1",
            "planned_start_date": horizon_start.isoformat(),
            "predecessor_activity_id": "PRED",
            "activity_priority": "3",
        },
    ]
    write(output / "08_ACTIVITY_DETAILS.csv", activity_fields, activities)

    access_fields, _ = read(base_oracle / "SCHEDULE_ACCESS.csv")
    occupancy_fields, base_occupancy = read(base_oracle / "SCHEDULE_OCCUPANCY.csv")
    result_fields, _ = read(base_oracle / "RESULTS.csv")
    footprints = {
        "PRED": sorted(
            {row["location_id"] for row in base_occupancy if row["activity_id"] == "Q001"}
        ),
        "SUCC": sorted(
            {row["location_id"] for row in base_occupancy if row["activity_id"] == "Q004"}
        ),
    }

    def emit(target: Path, pred_week: int, succ_week: int) -> None:
        access_rows = [
            {
                "activity_id": activity_id,
                "access_seq": 1,
                "week": week,
                "eclo": 0,
                "access_night": 1,
            }
            for activity_id, week in (("PRED", pred_week), ("SUCC", succ_week))
        ]
        occupancy_rows = [
            {
                "activity_id": activity_id,
                "week": week,
                "location_id": location_id,
                "co_share_group": f"{activity_id}_W{week:02d}",
            }
            for activity_id, week in (("PRED", pred_week), ("SUCC", succ_week))
            for location_id in footprints[activity_id]
        ]
        result_rows = []
        for contract_number, week, planned_week in (
            ("KPRE", pred_week, 10),
            ("KLATE", succ_week, 3),
        ):
            completion = horizon_start + timedelta(days=7 * week - 1)
            planned = horizon_start + timedelta(days=7 * planned_week - 1)
            result_rows.append(
                {
                    "scenario": "C",
                    "contract_number": contract_number,
                    "simulated_completion_date": completion.isoformat(),
                    "overrun_days": max(0, (completion - planned).days),
                }
            )
        write(target / "SCHEDULE_ACCESS.csv", access_fields, access_rows)
        write(target / "SCHEDULE_OCCUPANCY.csv", occupancy_fields, occupancy_rows)
        write(target / "RESULTS.csv", result_fields, result_rows)

    emit(oracle, 1, 2)
    emit(delayed, 3, 4)


if __name__ == "__main__":
    main()
