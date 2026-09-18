from __future__ import annotations

import argparse
import json

from .evaluate import evaluate_submission
from .flexible_solver import solve_flexible_supply_relaxation
from .independent_score import independently_score
from .instance import load_instance
from .portfolio import solve_scenario_c_portfolio
from .prune import prune_submission
from .solver import solve_scenario_a_relaxation
from .staged import solve_staged_scenario
from .submission import relabel_submission_scenario


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
    flexible_parser = subparsers.add_parser(
        "solve-flexible-relaxation",
        help="solve A, B, or C using the inferred closure separator",
    )
    flexible_parser.add_argument("--data", required=True)
    flexible_parser.add_argument("--output", required=True)
    flexible_parser.add_argument("--scenario", choices=("A", "B", "C"), required=True)
    flexible_parser.add_argument("--time-limit", type=float, default=120.0)
    flexible_parser.add_argument("--workers", type=int, default=8)
    flexible_parser.add_argument("--seed", type=int, default=1)
    flexible_parser.add_argument("--closure-rounds", type=int, default=50)
    flexible_parser.add_argument("--sample-hint")
    flexible_parser.add_argument(
        "--round-time-limit",
        type=float,
        help="per-solve cap; defaults to 1s for A/B and 3s for C",
    )
    flexible_parser.add_argument(
        "--strict-buffer-overlap",
        action="store_true",
        help="also forbid buffer-to-buffer overlap as a published-rule hedge",
    )
    flexible_parser.add_argument(
        "--freeze-access-hint",
        action="store_true",
        help="fix hinted access, ECLO, and local-night rows while repairing groups",
    )
    flexible_parser.add_argument(
        "--freeze-except",
        help="comma-separated activities left free when --freeze-access-hint is used",
    )
    flexible_parser.add_argument(
        "--separator",
        choices=("bridge_safe", "direct_heuristic"),
        default="bridge_safe",
        help="sound bridge-safe separation or faster over-restrictive candidate generation",
    )
    portfolio_parser = subparsers.add_parser(
        "solve-c-portfolio",
        help="protect a checked A-as-C fallback before attempting a better C solve",
    )
    portfolio_parser.add_argument("--data", required=True)
    portfolio_parser.add_argument("--output", required=True)
    portfolio_parser.add_argument("--audit-output")
    portfolio_parser.add_argument("--a-time-limit", type=float, default=120.0)
    portfolio_parser.add_argument("--c-time-limit", type=float, default=120.0)
    portfolio_parser.add_argument("--workers", type=int, default=8)
    portfolio_parser.add_argument("--seed", type=int, default=1)
    portfolio_parser.add_argument("--closure-rounds", type=int, default=500)
    portfolio_parser.add_argument("--a-round-time-limit", type=float, default=1.0)
    portfolio_parser.add_argument("--c-round-time-limit", type=float, default=3.0)
    portfolio_parser.add_argument(
        "--strict-buffer-overlap",
        action="store_true",
        help="preserve the published buffer-to-buffer hedge through all portfolio stages",
    )
    staged_parser = subparsers.add_parser(
        "solve-staged",
        help="generate with the fast heuristic, then verify/improve with sound cuts",
    )
    staged_parser.add_argument("--data", required=True)
    staged_parser.add_argument("--output", required=True)
    staged_parser.add_argument("--audit-output")
    staged_parser.add_argument("--scenario", choices=("A", "B", "C"), required=True)
    staged_parser.add_argument("--heuristic-time-limit", type=float, default=120.0)
    staged_parser.add_argument(
        "--fallback-time-limit",
        type=float,
        default=120.0,
        help="bridge-safe construction budget used only if every heuristic attempt fails",
    )
    staged_parser.add_argument(
        "--verification-time-limit",
        type=float,
        default=120.0,
        help="bridge-safe improvement and proof budget after a safe candidate is pruned",
    )
    staged_parser.add_argument("--workers", type=int, default=8)
    staged_parser.add_argument("--seed", type=int, default=1)
    staged_parser.add_argument("--heuristic-attempts", type=int, default=3)
    staged_parser.add_argument("--fallback-attempts", type=int, default=2)
    staged_parser.add_argument("--closure-rounds", type=int, default=500)
    staged_parser.add_argument("--strict-buffer-overlap", action="store_true")
    relabel_parser = subparsers.add_parser(
        "relabel-scenario",
        help="reuse a schedule unchanged and recompute result rows for another scenario",
    )
    relabel_parser.add_argument("--data", required=True)
    relabel_parser.add_argument("--source", required=True)
    relabel_parser.add_argument("--output", required=True)
    relabel_parser.add_argument("--scenario", choices=("A", "B", "C"), required=True)
    audit_parser = subparsers.add_parser(
        "audit-score",
        help="recompute score through the independent raw-CSV scorer",
    )
    audit_parser.add_argument("--data", required=True)
    audit_parser.add_argument("--submission", required=True)
    prune_parser = subparsers.add_parser(
        "prune-submission",
        help="remove redundant access rows only through the full feasibility/score gate",
    )
    prune_parser.add_argument("--data", required=True)
    prune_parser.add_argument("--source", required=True)
    prune_parser.add_argument("--output", required=True)
    prune_parser.add_argument("--scenario", choices=("A", "B", "C"), required=True)
    prune_parser.add_argument("--report")
    prune_parser.add_argument(
        "--strict-buffer-overlap",
        action="store_true",
        help="reject removals that introduce strict buffer-to-buffer conflicts",
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
        if telemetry.objective_score is None:
            raise SystemExit(3)
        raise SystemExit(0 if telemetry.remaining_closure_conflicts == 0 else 4)
    if args.command == "solve-flexible-relaxation":
        instance = load_instance(args.data)
        telemetry = solve_flexible_supply_relaxation(
            instance,
            args.output,
            args.scenario,
            time_limit_seconds=args.time_limit,
            workers=args.workers,
            seed=args.seed,
            closure_round_limit=args.closure_rounds,
            sample_hint_dir=args.sample_hint,
            round_time_limit_seconds=args.round_time_limit,
            forbid_buffer_overlap=args.strict_buffer_overlap,
            freeze_access_hint=args.freeze_access_hint,
            freeze_access_except=(
                {item.strip() for item in args.freeze_except.split(",") if item.strip()}
                if args.freeze_except
                else None
            ),
            separator_mode=args.separator,
        )
        print(telemetry.as_json())
        if telemetry.objective_score is None:
            raise SystemExit(3)
        raise SystemExit(0 if telemetry.remaining_closure_conflicts == 0 else 4)
    if args.command == "solve-c-portfolio":
        instance = load_instance(args.data)
        report = solve_scenario_c_portfolio(
            instance,
            args.output,
            audit_output_dir=args.audit_output,
            a_time_limit_seconds=args.a_time_limit,
            c_time_limit_seconds=args.c_time_limit,
            workers=args.workers,
            seed=args.seed,
            closure_round_limit=args.closure_rounds,
            a_round_time_limit_seconds=args.a_round_time_limit,
            c_round_time_limit_seconds=args.c_round_time_limit,
            forbid_buffer_overlap=args.strict_buffer_overlap,
        )
        print(json.dumps(report, indent=2, sort_keys=True))
        return
    if args.command == "solve-staged":
        instance = load_instance(args.data)
        report = solve_staged_scenario(
            instance,
            args.output,
            args.scenario,
            audit_output_dir=args.audit_output,
            heuristic_time_limit_seconds=args.heuristic_time_limit,
            fallback_time_limit_seconds=args.fallback_time_limit,
            verification_time_limit_seconds=args.verification_time_limit,
            workers=args.workers,
            seed=args.seed,
            heuristic_attempts=args.heuristic_attempts,
            fallback_attempts=args.fallback_attempts,
            closure_round_limit=args.closure_rounds,
            forbid_buffer_overlap=args.strict_buffer_overlap,
        )
        print(json.dumps(report, indent=2, sort_keys=True))
        return
    if args.command == "relabel-scenario":
        instance = load_instance(args.data)
        relabel_submission_scenario(instance, args.source, args.output, args.scenario)
        return
    if args.command == "audit-score":
        print(independently_score(args.data, args.submission).as_json())
        return
    if args.command == "prune-submission":
        instance = load_instance(args.data)
        report = prune_submission(
            instance,
            args.source,
            args.output,
            args.scenario,
            report_path=args.report,
            forbid_buffer_overlap=args.strict_buffer_overlap,
        )
        print(report.as_json())


if __name__ == "__main__":
    main()
