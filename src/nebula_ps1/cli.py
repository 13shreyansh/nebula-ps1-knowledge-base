from __future__ import annotations

import argparse

from .evaluate import evaluate_submission
from .instance import load_instance
from .solver import solve_scenario_a_relaxation


def main() -> None:
    parser = argparse.ArgumentParser(prog="nebula-ps1")
    subparsers = parser.add_subparsers(dest="command", required=True)
    inspect_parser = subparsers.add_parser("inspect", help="run the independent partial checker")
    inspect_parser.add_argument("--data", required=True)
    inspect_parser.add_argument("--submission", required=True)
    inspect_parser.add_argument("--scenario", choices=("A", "B", "C"))
    solve_parser = subparsers.add_parser(
        "solve-a-relaxation", help="solve Scenario A without unverified closure constraints"
    )
    solve_parser.add_argument("--data", required=True)
    solve_parser.add_argument("--output", required=True)
    solve_parser.add_argument("--sample-hint")
    solve_parser.add_argument("--time-limit", type=float, default=60.0)
    solve_parser.add_argument("--workers", type=int, default=8)
    solve_parser.add_argument("--seed", type=int, default=1)
    solve_parser.add_argument(
        "--freeze-except",
        help="comma-separated activities allowed to change; requires --sample-hint",
    )
    solve_parser.add_argument(
        "--repair-late-only",
        action="store_true",
        help="preserve each free activity's on-time sample accesses and move only late rows",
    )
    args = parser.parse_args()

    if args.command == "inspect":
        instance = load_instance(args.data)
        evaluation = evaluate_submission(instance, args.submission, args.scenario)
        print(evaluation.as_json())
        raise SystemExit(0 if evaluation.internally_feasible else 2)
    if args.command == "solve-a-relaxation":
        instance = load_instance(args.data)
        telemetry = solve_scenario_a_relaxation(
            instance,
            args.output,
            time_limit_seconds=args.time_limit,
            workers=args.workers,
            seed=args.seed,
            sample_hint_dir=args.sample_hint,
            freeze_except=(
                {item.strip() for item in args.freeze_except.split(",") if item.strip()}
                if args.freeze_except
                else None
            ),
            repair_late_only=args.repair_late_only,
        )
        print(telemetry.as_json())
        raise SystemExit(0 if telemetry.objective_score is not None else 3)


if __name__ == "__main__":
    main()
