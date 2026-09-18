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
        description="Generate a contract dependency introduced after precedence expansion."
    )
    parser.add_argument("--base-data", required=True)
    parser.add_argument("--base-oracle", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--oracle-output", required=True)
    parser.add_argument("--incumbent-output", required=True)
    args = parser.parse_args()
    base_data = Path(args.base_data)
    base_oracle = Path(args.base_oracle)
    output = Path(args.output)
    oracle = Path(args.oracle_output)
    incumbent = Path(args.incumbent_output)
    for path in (output, oracle, incumbent):
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

    def project(
        contract: str,
        description: str,
        priority: int,
        planned_week: int,
        access_type: str,
    ) -> dict[str, object]:
        return {
            "contract_number": contract,
            "contract_description": description,
            "contract_award_date": "2030-06-01",
            "activity_type": "PostPrecedenceContractTradeoff",
            "nature_of_activity": "Non-live (Others)",
            "contract_priority": priority,
            "contract_completion_date": completion_limit.isoformat(),
            "planned_completion_date": (
                horizon_start + timedelta(days=7 * planned_week - 1)
            ).isoformat(),
            "number_of_workfronts": 1,
            "access_type": access_type,
            "number_of_maximum_access_per_week": 1,
        }

    write(
        output / "07_PROJECT_DETAILS.csv",
        project_fields,
        [
            project("KDIRECT", "ECLO cost contributor", 1, 4, "PM"),
            project("KCOMP", "Footprint competitor", 3, 10, "C"),
            project("KCHAIN", "Successor and contract peer", 1, 6, "C"),
        ],
    )

    activity_fields, base_activities = read(base_data / "08_ACTIVITY_DETAILS.csv")
    by_id = {row["activity_id"]: row for row in base_activities}

    def activity(
        template: str,
        activity_id: str,
        contract: str,
        total_accesses: int,
        start_week: int,
        predecessor: str = "",
    ) -> dict[str, object]:
        return {
            **by_id[template],
            "activity_id": activity_id,
            "contract_number": contract,
            "activity_type": "PostPrecedenceContractTradeoff",
            "total_accesses": total_accesses,
            "planned_start_date": (
                horizon_start + timedelta(days=7 * (start_week - 1))
            ).isoformat(),
            "predecessor_activity_id": predecessor,
            "activity_priority": 1,
        }

    activities = [
        activity("Q001", "DIRECT", "KDIRECT", 3, 2),
        activity("Q001", "COMP", "KCOMP", 1, 2),
        activity("Q004", "FOLLOW", "KCHAIN", 1, 1, "COMP"),
        activity("Q008", "PEER", "KCHAIN", 1, 1),
    ]
    write(output / "08_ACTIVITY_DETAILS.csv", activity_fields, activities)

    access_fields, _ = read(base_oracle / "SCHEDULE_ACCESS.csv")
    occupancy_fields, base_occupancy = read(base_oracle / "SCHEDULE_OCCUPANCY.csv")
    result_fields, _ = read(base_oracle / "RESULTS.csv")
    template_by_activity = {
        "DIRECT": "Q001",
        "COMP": "Q001",
        "FOLLOW": "Q004",
        "PEER": "Q008",
    }
    footprints = {
        activity_id: sorted(
            {
                row["location_id"]
                for row in base_occupancy
                if row["activity_id"] == template
            }
        )
        for activity_id, template in template_by_activity.items()
    }

    def emit(target: Path, schedule: dict[str, list[tuple[int, int]]]) -> None:
        access_rows = [
            {
                "activity_id": activity_id,
                "access_seq": sequence,
                "week": week,
                "eclo": eclo,
                "access_night": 1,
            }
            for activity_id, rows in schedule.items()
            for sequence, (week, eclo) in enumerate(rows, start=1)
        ]
        occupancy_rows = [
            {
                "activity_id": activity_id,
                "week": week,
                "location_id": location_id,
                "co_share_group": f"{activity_id}_W{week:02d}",
            }
            for activity_id, rows in schedule.items()
            for week, _ in rows
            for location_id in footprints[activity_id]
        ]
        activities_by_contract = {
            "KDIRECT": ("DIRECT",),
            "KCOMP": ("COMP",),
            "KCHAIN": ("FOLLOW", "PEER"),
        }
        planned_weeks = {"KDIRECT": 4, "KCOMP": 10, "KCHAIN": 6}
        result_rows = []
        for contract, activity_ids in activities_by_contract.items():
            completion_week = max(
                week
                for activity_id in activity_ids
                for week, _ in schedule[activity_id]
            )
            completion = horizon_start + timedelta(days=7 * completion_week - 1)
            planned = horizon_start + timedelta(days=7 * planned_weeks[contract] - 1)
            result_rows.append(
                {
                    "scenario": "C",
                    "contract_number": contract,
                    "simulated_completion_date": completion.isoformat(),
                    "overrun_days": max(0, (completion - planned).days),
                }
            )
        write(target / "SCHEDULE_ACCESS.csv", access_fields, access_rows)
        write(target / "SCHEDULE_OCCUPANCY.csv", occupancy_fields, occupancy_rows)
        write(target / "RESULTS.csv", result_fields, result_rows)

    emit(
        oracle,
        {
            "DIRECT": [(2, 0), (3, 0), (4, 0)],
            "COMP": [(5, 0)],
            "FOLLOW": [(6, 0)],
            "PEER": [(4, 0)],
        },
    )
    emit(
        incumbent,
        {
            "DIRECT": [(3, 1), (4, 1)],
            "COMP": [(2, 0)],
            "FOLLOW": [(3, 0)],
            "PEER": [(6, 0)],
        },
    )


if __name__ == "__main__":
    main()
