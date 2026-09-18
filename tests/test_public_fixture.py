from __future__ import annotations

import unittest
import csv
import hashlib
import json
import shutil
import tempfile
import zipfile
from dataclasses import replace
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from nebula_ps1.cli import main as cli_main
from nebula_ps1.closure import _blocked_locations, _external_buffer_sectors, screen_closures
from nebula_ps1.evaluate import evaluate_submission, load_submission
from nebula_ps1.flexible_solver import solve_flexible_supply_relaxation
from nebula_ps1.independent_score import independently_score
from nebula_ps1.instance import load_instance
from nebula_ps1.portfolio import SUBMISSION_FILES, _candidate_is_better, _copy_submission
from nebula_ps1.prune import prune_submission
from nebula_ps1.solver import SolveTelemetry, _contract_costs
from nebula_ps1.staged import (
    _scenario_b_cost_contributing_activities,
    solve_staged_scenario,
)
from nebula_ps1.staged_c import solve_staged_c_portfolio
from nebula_ps1.submission import relabel_submission_scenario
from nebula_ps1.topology import (
    activity_footprint,
    interchange_cross_line_locations,
    split_sector_location,
)


ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "current-problem-statement" / "PS1"


class PublicFixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.instance = load_instance(PACK / "01_data")

    def test_instance_counts_are_loaded_from_schema(self) -> None:
        self.assertEqual(len(self.instance.lines), 2)

    def test_independent_synthetic_oracle_is_valid_without_public_identifiers(self) -> None:
        synthetic_root = ROOT / "fixtures" / "independent_synthetic_v1"
        oracle = ROOT / "fixtures" / "independent_synthetic_v1_oracle"
        instance = load_instance(synthetic_root)
        evaluation = evaluate_submission(instance, oracle, scenario="A")
        independent = independently_score(synthetic_root, oracle)
        self.assertEqual(set(instance.lines), {"LNX", "LNY"})
        self.assertTrue(all(activity_id.startswith("Q") for activity_id in instance.activities))
        self.assertEqual(evaluation.hard_violations, ())
        self.assertAlmostEqual(evaluation.objective_score, 7.0)
        self.assertAlmostEqual(independent.objective_score, 7.0)
        self.assertEqual(len(self.instance.projects), 14)
        self.assertEqual(len(self.instance.activities), 54)
        self.assertEqual(len(self.instance.locations), 76)
        self.assertEqual(self.instance.horizon_weeks, 30)

    def test_benchmark_matrix_matches_recomputed_scores_and_feasibility(self) -> None:
        matrix = json.loads((ROOT / "BENCHMARK_MATRIX.json").read_text(encoding="utf-8"))
        self.assertEqual(matrix["schema_version"], 1)
        self.assertEqual(len(matrix["cases"]), 32)
        for row in matrix["cases"]:
            if row["case"].startswith("public_"):
                data = PACK / "01_data"
                submission = ROOT / "deliverables" / "public" / row["scenario"]
            elif row["case"].startswith("prefix040_"):
                data = ROOT / "fixtures" / "prefix_040"
                run_name = {
                    "A": "a_prefix040_corrected_w1",
                    "B": "b_prefix040_portfolio_costrepair_w1",
                    "C": "c_prefix040_corrected_w1",
                }[row["scenario"]]
                submission = ROOT / "runs" / run_name
            elif row["case"].startswith("structural_demand_"):
                data = ROOT / "fixtures" / "structural_demand_seed_20260920"
                run_name = {
                    "A": "a_structural_demand_portfolio_w8",
                    "B": "b_structural_demand_portfolio_w8",
                    "C": "c_structural_demand_portfolio_w8",
                }[row["scenario"]]
                submission = ROOT / "runs" / run_name
            elif row["case"].startswith("independent_scaled_m20_"):
                data = ROOT / "fixtures" / "independent_scaled_m20"
                submission = (
                    ROOT
                    / "runs"
                    / "independent_scaled_m20_seed_matrix5_w1"
                    / f"{row['scenario'].lower()}_seed_1"
                )
            elif row["case"].startswith("independent_dense_"):
                if row["case"].startswith("independent_dense_holdout_"):
                    data = ROOT / "fixtures" / "independent_dense_holdout_v1"
                    run_root = "independent_dense_holdout_v1_production_matrix_w1"
                else:
                    data = ROOT / "fixtures" / "independent_dense_v1"
                    run_root = "independent_dense_v1_structural_matrix_w1"
                submission = ROOT / "runs" / run_root / f"{row['scenario'].lower()}_seed_1"
            elif row["case"].startswith("independent_tradeoff_holdout_"):
                data = ROOT / "fixtures" / "independent_tradeoff_holdout_v1"
                submission = (
                    ROOT
                    / "runs"
                    / "independent_tradeoff_holdout_v1_blind_w1"
                    / f"{row['scenario'].lower()}_seed_1"
                )
            elif row["case"].startswith("independent_coupled_tradeoff_"):
                data = ROOT / "fixtures" / "independent_coupled_tradeoff_v1"
                submission = (
                    ROOT
                    / "runs"
                    / "independent_coupled_tradeoff_v1_repair10_matrix_w1"
                    / f"{row['scenario'].lower()}_seed_1"
                )
            elif row["case"].startswith("independent_irregular_partial_"):
                data = ROOT / "fixtures" / "independent_irregular_partial_v1"
                submission = (
                    ROOT
                    / "runs"
                    / (
                        "independent_irregular_partial_v1_corrected_production_w8/b_seed_1"
                        if row["scenario"] == "B"
                        else "independent_irregular_partial_v1_guarded_independent_c120_costrepair_w8"
                    )
                )
            elif row["case"] == "independent_multimodule_tradeoff_C":
                data = ROOT / "fixtures" / "independent_multimodule_tradeoff_v1"
                submission = ROOT / "runs" / "postb651753_multimodule_c_seed1_w8"
            elif row["case"] == "independent_predecessor_tradeoff_C":
                data = ROOT / "fixtures" / "independent_predecessor_tradeoff_v1"
                submission = ROOT / "runs" / "postprecedenceexpand_delayed7_repair30"
            elif row["case"] == "independent_footprint_dependency_C":
                data = ROOT / "fixtures" / "independent_footprint_dependency_v1"
                submission = ROOT / "runs" / "c_footprint_dependency_postprecedence"
            else:
                self.assertTrue(row["case"].startswith("independent_"))
                data = ROOT / "fixtures" / "independent_synthetic_v1"
                run_name = {
                    "A": "a_independent_synthetic_v1",
                    "B": "b_independent_synthetic_v1",
                    "C": "c_independent_synthetic_v1",
                }[row["scenario"]]
                submission = ROOT / "runs" / run_name

            instance = load_instance(data)
            evaluation = evaluate_submission(instance, submission, row["scenario"])
            independent = independently_score(data, submission)
            self.assertEqual(evaluation.hard_violations, (), row["case"])
            self.assertEqual(evaluation.objective_score, row["score"], row["case"])
            self.assertEqual(independent.objective_score, row["score"], row["case"])
            self.assertTrue(row["proof_matches_score"], row["case"])
            self.assertIn(
                row["proof_scope"],
                {"full_instance", "frozen_access_neighborhood", "fixed_access_schedule"},
                row["case"],
            )

    def test_scaled_independent_oracle_is_valid_and_larger_than_public(self) -> None:
        data = ROOT / "fixtures" / "independent_scaled_m20"
        oracle = ROOT / "fixtures" / "independent_scaled_m20_oracle"
        instance = load_instance(data)
        evaluation = evaluate_submission(instance, oracle, scenario="A")
        independent = independently_score(data, oracle)
        self.assertEqual(set(instance.lines), {"LSX", "LSY"})
        self.assertEqual(len(instance.projects), 160)
        self.assertEqual(len(instance.activities), 180)
        self.assertGreater(len(instance.activities), len(self.instance.activities))
        self.assertEqual(evaluation.hard_violations, ())
        self.assertAlmostEqual(evaluation.objective_score, 140.0)
        self.assertAlmostEqual(independent.objective_score, 140.0)

    def test_dense_independent_b_constructs_zero_without_oracle_hint(self) -> None:
        data = ROOT / "fixtures" / "independent_dense_v1"
        instance = load_instance(data)
        self.assertEqual(len(instance.activities), 84)
        self.assertTrue(all(not activity_id.startswith("A") for activity_id in instance.activities))
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            report = solve_staged_scenario(
                instance,
                root / "submission",
                "B",
                audit_output_dir=root / "audit",
                heuristic_time_limit_seconds=2.0,
                local_repair_time_limit_seconds=1.0,
                fallback_time_limit_seconds=3.0,
                verification_time_limit_seconds=2.0,
                workers=1,
                seed=1,
                heuristic_attempts=1,
                fallback_attempts=1,
            )
            evaluation = evaluate_submission(instance, root / "submission", "B")
            independent = independently_score(data, root / "submission")
            self.assertEqual(report["selected_stage"], "heuristic_incumbent")
            self.assertTrue(report["heuristic_telemetry"]["structural_hints_used"])
            self.assertTrue(report["heuristic_telemetry"]["structural_hint_complete"])
            self.assertEqual(evaluation.hard_violations, ())
            self.assertEqual(evaluation.objective_score, 0.0)
            self.assertEqual(independent.objective_score, 0.0)

    def test_partial_public_structural_hint_is_dropped(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            telemetry = solve_flexible_supply_relaxation(
                self.instance,
                Path(temporary) / "candidate",
                "A",
                time_limit_seconds=0.05,
                workers=1,
                seed=1,
                closure_round_limit=1,
                separator_mode="direct_heuristic",
            )
        self.assertFalse(telemetry.structural_hints_used)
        self.assertFalse(telemetry.structural_hint_complete)
        self.assertEqual(telemetry.structural_hint_activity_count, 35)
        self.assertEqual(telemetry.structural_hint_access_count, 108)

    def test_partial_public_b_hint_is_retained_for_deadline_feasibility(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            telemetry = solve_flexible_supply_relaxation(
                self.instance,
                Path(temporary) / "candidate",
                "B",
                time_limit_seconds=0.05,
                workers=1,
                seed=1,
                closure_round_limit=1,
                separator_mode="direct_heuristic",
            )
        self.assertTrue(telemetry.structural_hints_used)
        self.assertFalse(telemetry.structural_hint_complete)
        self.assertEqual(telemetry.structural_hint_activity_count, 35)
        self.assertEqual(telemetry.structural_hint_access_count, 108)

    def test_tradeoff_holdout_recovers_nonzero_a_b_c_optima(self) -> None:
        data = ROOT / "fixtures" / "independent_tradeoff_holdout_v1"
        instance = load_instance(data)
        tight = instance.activities["WTIGHT"]
        self.assertEqual(tight.total_accesses, 3)
        self.assertEqual(instance.last_week_completing_by(
            instance.projects[tight.contract_number].planned_completion_date
        ), 2)
        expected = {"A": 7.0, "B": 10.0, "C": 7.0}
        for scenario, score in expected.items():
            submission = (
                ROOT
                / "runs"
                / "independent_tradeoff_holdout_v1_blind_w1"
                / f"{scenario.lower()}_seed_1"
            )
            evaluation = evaluate_submission(instance, submission, scenario)
            independent = independently_score(data, submission)
            self.assertEqual(evaluation.hard_violations, (), scenario)
            self.assertEqual(evaluation.objective_score, score, scenario)
            self.assertEqual(independent.objective_score, score, scenario)

    def test_coupled_tradeoff_recovers_window_bound(self) -> None:
        data = ROOT / "fixtures" / "independent_coupled_tradeoff_v1"
        instance = load_instance(data)
        for activity_id, target_week in (("WCOUPLED1", 2), ("WCOUPLED2", 6)):
            activity = instance.activities[activity_id]
            self.assertEqual(activity.total_accesses, 3)
            self.assertEqual(
                instance.last_week_completing_by(
                    instance.projects[activity.contract_number].planned_completion_date
                ),
                target_week,
            )
        expected = {"A": 1820.0, "B": 20.0, "C": 920.0}
        for scenario, score in expected.items():
            submission = (
                ROOT
                / "runs"
                / "independent_coupled_tradeoff_v1_repair10_matrix_w1"
                / f"{scenario.lower()}_seed_1"
            )
            evaluation = evaluate_submission(instance, submission, scenario)
            independent = independently_score(data, submission)
            self.assertEqual(evaluation.hard_violations, (), scenario)
            self.assertEqual(evaluation.objective_score, score, scenario)
            self.assertEqual(independent.objective_score, score, scenario)
        b_access, _, _ = load_submission(
            ROOT
            / "runs"
            / "independent_coupled_tradeoff_v1_repair10_matrix_w1"
            / "b_seed_1"
        )
        c_access, _, _ = load_submission(
            ROOT
            / "runs"
            / "independent_coupled_tradeoff_v1_repair10_matrix_w1"
            / "c_seed_1"
        )
        coupled = {"WCOUPLED1", "WCOUPLED2"}
        self.assertEqual(sum(row.eclo for row in b_access if row.activity_id in coupled), 4)
        self.assertEqual(sum(row.eclo for row in c_access if row.activity_id in coupled), 2)

    def test_multimodule_tradeoff_oracle_reaches_counting_bound(self) -> None:
        data = ROOT / "fixtures" / "independent_multimodule_tradeoff_v1"
        oracle = ROOT / "fixtures" / "independent_multimodule_tradeoff_v1_oracle"
        instance = load_instance(data)
        evaluation = evaluate_submission(instance, oracle, "C")
        independent = independently_score(data, oracle)
        access, occupancy, _ = load_submission(oracle)
        selected = {
            activity_id
            for activity_id, activity in instance.activities.items()
            if activity.contract_number == "KMM"
        }
        self.assertEqual(
            selected,
            {"R0103", "R0206", "R0303", "R0406", "R0503"},
        )
        self.assertEqual(sum(row.eclo for row in access if row.activity_id in selected), 4)
        self.assertEqual(evaluation.hard_violations, ())
        self.assertEqual(evaluation.objective_score, 76.0)
        self.assertEqual(independent.objective_score, 76.0)
        self.assertEqual(
            screen_closures(
                instance,
                access,
                occupancy,
                forbid_buffer_overlap=True,
            ),
            (),
        )

    def test_predecessor_tradeoff_oracle_and_delayed_incumbent(self) -> None:
        data = ROOT / "fixtures" / "independent_predecessor_tradeoff_v1"
        oracle = ROOT / "fixtures" / "independent_predecessor_tradeoff_v1_oracle"
        delayed = (
            ROOT / "fixtures" / "independent_predecessor_tradeoff_v1_delayed_incumbent"
        )
        instance = load_instance(data)
        oracle_evaluation = evaluate_submission(instance, oracle, "C")
        delayed_evaluation = evaluate_submission(instance, delayed, "C")
        self.assertEqual(oracle_evaluation.hard_violations, ())
        self.assertEqual(delayed_evaluation.hard_violations, ())
        self.assertEqual(oracle_evaluation.objective_score, 0.0)
        self.assertEqual(delayed_evaluation.objective_score, 7.0)
        self.assertEqual(independently_score(data, oracle).objective_score, 0.0)
        self.assertEqual(independently_score(data, delayed).objective_score, 7.0)

    def test_footprint_dependency_holdout_is_frozen_before_repair(self) -> None:
        data = ROOT / "fixtures" / "independent_footprint_dependency_v1"
        oracle = ROOT / "fixtures" / "independent_footprint_dependency_v1_oracle"
        incumbent = ROOT / "fixtures" / "independent_footprint_dependency_v1_incumbent"
        instance = load_instance(data)
        self.assertEqual(
            instance.dataset_hash,
            "bff7db75338331b9957deda68d00f8798fdff2f3799aca03611e3323c1fbab6f",
        )
        oracle_evaluation = evaluate_submission(instance, oracle, "C")
        incumbent_evaluation = evaluate_submission(instance, incumbent, "C")
        self.assertEqual(oracle_evaluation.hard_violations, ())
        self.assertEqual(incumbent_evaluation.hard_violations, ())
        self.assertEqual(oracle_evaluation.objective_score, 0.0)
        self.assertEqual(incumbent_evaluation.objective_score, 10.0)
        self.assertEqual(independently_score(data, oracle).objective_score, 0.0)
        self.assertEqual(independently_score(data, incumbent).objective_score, 10.0)
        access, occupancy, _ = load_submission(incumbent)
        self.assertEqual(screen_closures(instance, access, occupancy), ())
        self.assertEqual(
            screen_closures(
                instance,
                access,
                occupancy,
                forbid_buffer_overlap=True,
            ),
            (),
        )
        self.assertEqual(
            _scenario_b_cost_contributing_activities(
                instance,
                incumbent,
                expand_footprints=True,
                expand_contracts=True,
                expand_precedence=True,
                include_delays=True,
            ),
            ["COMP", "DIRECT"],
        )
        self.assertEqual(
            _scenario_b_cost_contributing_activities(
                instance,
                incumbent,
                expand_footprints=True,
                expand_contracts=True,
                expand_precedence=True,
                revisit_precedence_after_footprints=True,
                include_delays=True,
            ),
            ["COMP", "DIRECT", "FOLLOW"],
        )

    def test_post_footprint_precedence_repair_reaches_oracle(self) -> None:
        data = ROOT / "fixtures" / "independent_footprint_dependency_v1"
        source = ROOT / "fixtures" / "independent_footprint_dependency_v1_incumbent"
        instance = load_instance(data)
        free = _scenario_b_cost_contributing_activities(
            instance,
            source,
            expand_footprints=True,
            expand_contracts=True,
            expand_precedence=True,
            revisit_precedence_after_footprints=True,
            include_delays=True,
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            telemetry = solve_flexible_supply_relaxation(
                instance,
                temp_dir,
                "C",
                time_limit_seconds=1.0,
                workers=1,
                seed=1,
                sample_hint_dir=source,
                freeze_access_hint=True,
                freeze_access_except=set(free),
                separator_mode="bridge_safe",
            )
            evaluation = evaluate_submission(instance, temp_dir, "C")
            independent = independently_score(data, temp_dir)
        self.assertEqual(telemetry.primary_bound_scope, "frozen_access_neighborhood")
        self.assertTrue(telemetry.primary_score_proven_optimal)
        self.assertEqual(telemetry.best_bound, 0.0)
        self.assertEqual(evaluation.hard_violations, ())
        self.assertEqual(evaluation.objective_score, 0.0)
        self.assertEqual(independent.objective_score, 0.0)

    def test_post_precedence_contract_holdout_is_frozen_before_repair(self) -> None:
        data = ROOT / "fixtures" / "independent_post_precedence_contract_v1"
        oracle = ROOT / "fixtures" / "independent_post_precedence_contract_v1_oracle"
        incumbent = ROOT / "fixtures/independent_post_precedence_contract_v1_incumbent"
        instance = load_instance(data)
        self.assertEqual(
            instance.dataset_hash,
            "e5f513a65637232af1d6263763c5f4e437772dee505c7c611464ec188ed9d267",
        )
        oracle_evaluation = evaluate_submission(instance, oracle, "C")
        incumbent_evaluation = evaluate_submission(instance, incumbent, "C")
        self.assertEqual(oracle_evaluation.hard_violations, ())
        self.assertEqual(incumbent_evaluation.hard_violations, ())
        self.assertEqual(oracle_evaluation.objective_score, 0.0)
        self.assertEqual(incumbent_evaluation.objective_score, 10.0)
        self.assertEqual(independently_score(data, oracle).objective_score, 0.0)
        self.assertEqual(independently_score(data, incumbent).objective_score, 10.0)
        access, occupancy, _ = load_submission(incumbent)
        self.assertEqual(screen_closures(instance, access, occupancy), ())
        self.assertEqual(
            screen_closures(
                instance,
                access,
                occupancy,
                forbid_buffer_overlap=True,
            ),
            (),
        )
        self.assertEqual(
            _scenario_b_cost_contributing_activities(
                instance,
                incumbent,
                expand_footprints=True,
                expand_contracts=True,
                expand_precedence=True,
                revisit_precedence_after_footprints=True,
                include_delays=True,
            ),
            ["COMP", "DIRECT", "FOLLOW"],
        )

    def test_dense_holdout_production_c_preserves_zero_a_fallback(self) -> None:
        data = ROOT / "fixtures" / "independent_dense_holdout_v1"
        instance = load_instance(data)
        oracle = ROOT / "fixtures" / "independent_dense_holdout_v1_oracle"
        oracle_evaluation = evaluate_submission(instance, oracle, "A")
        self.assertEqual(len(instance.activities), 106)
        self.assertEqual(oracle_evaluation.hard_violations, ())
        self.assertEqual(oracle_evaluation.objective_score, 0.0)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            report = solve_staged_c_portfolio(
                instance,
                root / "submission",
                audit_output_dir=root / "audit",
                a_heuristic_time_limit_seconds=2.0,
                a_local_repair_time_limit_seconds=1.0,
                a_fallback_time_limit_seconds=3.0,
                a_verification_time_limit_seconds=2.0,
                c_heuristic_time_limit_seconds=2.0,
                c_verification_time_limit_seconds=2.0,
                workers=1,
                seed=1,
                a_heuristic_attempts=1,
                a_fallback_attempts=1,
                c_heuristic_attempts=1,
            )
            evaluation = evaluate_submission(instance, root / "submission", "C")
            independent = independently_score(data, root / "submission")
            self.assertEqual(report["selected_stage"], "scenario_c_fallback")
            self.assertEqual(evaluation.hard_violations, ())
            self.assertEqual(evaluation.objective_score, 0.0)
            self.assertEqual(independent.objective_score, 0.0)

    def test_hard_deadline_uses_last_completed_week_not_containing_week(self) -> None:
        midweek_deadline = date(2027, 1, 13)
        self.assertEqual(self.instance.week_for_date(midweek_deadline), 2)
        self.assertEqual(self.instance.last_week_completing_by(midweek_deadline), 1)
        self.assertLessEqual(self.instance.completion_date(1), midweek_deadline)
        self.assertGreater(self.instance.completion_date(2), midweek_deadline)
        self.assertEqual(
            self.instance.last_week_completing_by(date(2027, 1, 17)),
            2,
        )

    def test_a_137_9_lower_bound_critical_path_facts(self) -> None:
        a036 = self.instance.activities["A036"]
        a059 = self.instance.activities["A059"]
        a075 = self.instance.activities["A075"]
        self.assertEqual((a036.total_accesses, a059.total_accesses, a075.total_accesses), (7, 7, 1))
        self.assertEqual(self.instance.week_for_date(a036.planned_start_date), 22)
        self.assertEqual(self.instance.week_for_date(a059.planned_start_date), 14)
        self.assertEqual(self.instance.week_for_date(a075.planned_start_date), 24)
        self.assertEqual(
            self.instance.week_for_date(
                self.instance.projects[a036.contract_number].planned_completion_date
            ),
            26,
        )
        self.assertEqual(
            self.instance.week_for_date(
                self.instance.projects[a059.contract_number].planned_completion_date
            ),
            19,
        )
        self.assertEqual(
            self.instance.week_for_date(
                self.instance.projects[a075.contract_number].planned_completion_date
            ),
            28,
        )
        self.assertEqual(_contract_costs(self.instance, "C006")[27], 854)
        self.assertEqual(_contract_costs(self.instance, "C010")[19], 455)
        self.assertEqual(_contract_costs(self.instance, "C014")[28], 70)
        self.assertEqual(
            self.instance.projects[a075.contract_number].access_type,
            "PM",
        )
        self.assertFalse(
            set(activity_footprint(self.instance, a036))
            & set(activity_footprint(self.instance, a075))
        )
        self.assertTrue(
            set(activity_footprint(self.instance, a036))
            & _blocked_locations(self.instance, {"A075"})
        )

    def test_official_a002_contract_score_is_reproduced(self) -> None:
        candidate = ROOT / "runs" / "a_official_a001_local_repair_pruned"
        evaluation = evaluate_submission(self.instance, candidate, scenario="A")
        audit = independently_score(PACK / "01_data", candidate)
        self.assertEqual(evaluation.hard_violations, ())
        self.assertEqual(evaluation.priority_overrun, {1: 0, 2: 0, 3: 28})
        self.assertAlmostEqual(evaluation.objective_score, 137.9)
        self.assertAlmostEqual(audit.objective_score, 137.9)
        self.assertEqual(_contract_costs(self.instance, "C006")[29], 170.8 * 10)

    def test_generated_work_footprints_match_all_public_occupancy_keys(self) -> None:
        access, occupancy, _ = load_submission(PACK / "03_submission_sample")
        generated = {
            (row.activity_id, row.week, location_id)
            for row in access
            for location_id in activity_footprint(
                self.instance, self.instance.activities[row.activity_id]
            )
        }
        supplied = {(row.activity_id, row.week, row.location_id) for row in occupancy}
        self.assertEqual(len(generated), 928)
        self.assertEqual(generated, supplied)

    def test_interchange_crossover_is_derived_without_public_station_ids(self) -> None:
        def renamed(value: str) -> str:
            return value.replace("H01", "X91").replace("H02", "X92")

        stations = {
            (line, renamed(station_id)): replace(station, station_id=renamed(station_id))
            for (line, station_id), station in self.instance.stations.items()
        }
        sectors = {
            renamed(sector_id): replace(
                sector,
                sector_id=renamed(sector.sector_id),
                from_station_id=renamed(sector.from_station_id),
                to_station_id=renamed(sector.to_station_id),
            )
            for sector_id, sector in self.instance.sectors.items()
        }
        locations = {
            renamed(location_id): replace(location, location_id=renamed(location_id))
            for location_id, location in self.instance.locations.items()
        }
        activities = {
            activity_id: replace(
                activity,
                start_location_id=renamed(activity.start_location_id),
                end_location_id=renamed(activity.end_location_id),
            )
            for activity_id, activity in self.instance.activities.items()
        }
        renamed_instance = replace(
            self.instance,
            stations=stations,
            sectors=sectors,
            locations=locations,
            activities=activities,
        )
        affected = interchange_cross_line_locations(
            renamed_instance, renamed_instance.activities["A075"]
        )
        self.assertEqual(len(affected), 6)
        self.assertTrue(all("X91" in item or "X92" in item for item in affected))
        self.assertFalse(any("H01" in item or "H02" in item for item in affected))

    def test_public_scenario_a_fixture_passes_implemented_rules(self) -> None:
        evaluation = evaluate_submission(
            self.instance, PACK / "03_submission_sample", scenario="A"
        )
        self.assertEqual(evaluation.hard_violations, ())
        self.assertTrue(evaluation.internally_feasible)
        self.assertFalse(evaluation.reference_validator_confirmed)
        self.assertEqual(evaluation.access_rows, 192)
        self.assertEqual(evaluation.occupancy_rows, 928)
        self.assertEqual(evaluation.eclo_nights_total, 0)
        self.assertEqual(evaluation.excess_access_nights_total, 0)
        self.assertAlmostEqual(evaluation.priority_weighted_score, 137.9)
        self.assertAlmostEqual(evaluation.objective_score, 137.9)
        self.assertIn("closure", evaluation.warnings[0])

    def test_public_sample_contains_buffer_only_overlap(self) -> None:
        access, occupancy, _ = load_submission(PACK / "03_submission_sample")
        scheduled = {(row.activity_id, row.week) for row in access}
        self.assertIn(("A069", 12), scheduled)
        self.assertIn(("A046", 12), scheduled)

        first_work = set(
            activity_footprint(self.instance, self.instance.activities["A069"])
        )
        second_work = set(
            activity_footprint(self.instance, self.instance.activities["A046"])
        )
        first_buffer = _external_buffer_sectors(self.instance, "A069")
        second_buffer = _external_buffer_sectors(self.instance, "A046")

        self.assertFalse(first_work & second_work)
        self.assertFalse(first_buffer & second_work)
        self.assertFalse(second_buffer & first_work)
        self.assertEqual(
            first_buffer & second_buffer,
            {"SEC:ALP:H02_S05:WB"},
        )
        self.assertEqual(screen_closures(self.instance, access, occupancy), ())
        strict_conflicts = screen_closures(
            self.instance,
            access,
            occupancy,
            forbid_buffer_overlap=True,
        )
        self.assertEqual(len(strict_conflicts), 4)
        self.assertTrue(
            any(
                conflict.week == 12
                and set(conflict.first_activities + conflict.second_activities)
                == {"A046", "A069"}
                and conflict.locations == ("SEC:ALP:H02_S05:WB",)
                for conflict in strict_conflicts
            )
        )

    def test_public_sample_requires_transitive_possession_components(self) -> None:
        _, occupancy, _ = load_submission(PACK / "03_submission_sample")
        groups: dict[tuple[str, str], set[str]] = {}
        for row in occupancy:
            if row.week == 13:
                groups.setdefault((row.location_id, row.co_share_group), set()).add(
                    row.activity_id
                )
        self.assertTrue(
            {"A003", "A060"} <= groups[("PLAT:BET:S15:EB", "b1")]
        )
        self.assertTrue(
            {"A019", "A060"} <= groups[("PLAT:BET:S16:EB", "b2")]
        )

        shared_pairs = {
            tuple(sorted((first.activity_id, second.activity_id)))
            for first in occupancy
            for second in occupancy
            if first.week == second.week == 13
            and first.location_id == second.location_id
            and first.co_share_group == second.co_share_group
            and first.activity_id != second.activity_id
        }
        self.assertIn(("A003", "A060"), shared_pairs)
        self.assertIn(("A019", "A060"), shared_pairs)
        self.assertNotIn(("A003", "A019"), shared_pairs)

        direct_collision = (
            _blocked_locations(self.instance, {"A003"})
            & set(activity_footprint(self.instance, self.instance.activities["A019"]))
        ) | (
            _blocked_locations(self.instance, {"A019"})
            & set(activity_footprint(self.instance, self.instance.activities["A003"]))
        )
        self.assertEqual(
            direct_collision,
            {"PLAT:BET:S16:EB", "SEC:BET:S16_S17:EB"},
        )

    def test_official_a001_violation_oracle_is_reproduced_exactly(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            with zipfile.ZipFile(ROOT / "deliverables" / "validator" / "A.zip") as archive:
                archive.extractall(temp_dir)
            access, occupancy, _ = load_submission(temp_dir)
            conflicts = screen_closures(self.instance, access, occupancy)
        observed = [
            (
                conflict.week,
                conflict.first_activities,
                conflict.second_activities,
                conflict.locations,
            )
            for conflict in conflicts
        ]
        self.assertEqual(
            observed,
            [
                (
                    18,
                    ("A035",),
                    ("A058",),
                    (
                        "PLAT:ALP:S03:WB",
                        "PLAT:ALP:S04:WB",
                        "SEC:ALP:S03_S04:WB",
                    ),
                ),
                (
                    18,
                    ("A058",),
                    ("A035",),
                    (
                        "PLAT:ALP:S03:WB",
                        "PLAT:ALP:S04:WB",
                        "SEC:ALP:S03_S04:WB",
                    ),
                ),
                (
                    21,
                    ("A001",),
                    ("A074",),
                    (
                        "PLAT:BET:S15:EB",
                        "PLAT:BET:S16:EB",
                        "SEC:BET:S15_S16:EB",
                    ),
                ),
                (
                    21,
                    ("A011",),
                    ("A074",),
                    (
                        "PLAT:BET:S15:EB",
                        "PLAT:BET:S16:EB",
                        "SEC:BET:S15_S16:EB",
                    ),
                ),
                (
                    29,
                    ("A023",),
                    ("A075",),
                    (
                        "PLAT:ALP:S03:WB",
                        "PLAT:ALP:S04:WB",
                        "SEC:ALP:S03_S04:WB",
                    ),
                ),
            ],
        )

    def test_access_night_is_not_a_global_possession_identifier(self) -> None:
        access, occupancy, _ = load_submission(PACK / "03_submission_sample")
        nights = {(row.activity_id, row.week): row.access_night for row in access}
        self.assertEqual(nights[("A003", 16)], 3)
        self.assertEqual(nights[("A007", 16)], 1)
        self.assertEqual(
            self.instance.activities["A003"].contract_number,
            self.instance.activities["A007"].contract_number,
        )
        shared = {
            (row.activity_id, row.location_id, row.co_share_group)
            for row in occupancy
            if row.week == 16 and row.activity_id in {"A003", "A007"}
        }
        for location_id in (
            "PLAT:BET:H01:EB",
            "PLAT:BET:H02:EB",
            "SEC:BET:H01_H02:EB",
        ):
            self.assertIn(("A003", location_id, "b1"), shared)
            self.assertIn(("A007", location_id, "b1"), shared)

    def test_solve_a_cli_does_not_reference_an_undefined_audit_argument(self) -> None:
        telemetry = SimpleNamespace(
            objective_score=0.0,
            remaining_closure_conflicts=0,
            as_json=lambda: "{}",
        )
        argv = [
            "nebula-ps1",
            "solve-a-relaxation",
            "--data",
            str(PACK / "01_data"),
            "--output",
            "unused",
        ]
        with patch("sys.argv", argv), patch(
            "nebula_ps1.cli.solve_scenario_a_relaxation", return_value=telemetry
        ) as solve:
            with self.assertRaisesRegex(SystemExit, "0"):
                cli_main()
        self.assertNotIn("audit_output_dir", solve.call_args.kwargs)

    def test_flexible_cli_forwards_only_flexible_arguments(self) -> None:
        telemetry = SimpleNamespace(
            objective_score=0.0,
            remaining_closure_conflicts=0,
            as_json=lambda: "{}",
        )
        argv = [
            "nebula-ps1",
            "solve-flexible-relaxation",
            "--data",
            str(PACK / "01_data"),
            "--output",
            "unused",
            "--scenario",
            "B",
            "--max-deterministic-time-per-solve",
            "0.5",
            "--interleave-search",
        ]
        with patch("sys.argv", argv), patch(
            "nebula_ps1.cli.solve_flexible_supply_relaxation", return_value=telemetry
        ) as solve:
            with self.assertRaisesRegex(SystemExit, "0"):
                cli_main()
        self.assertNotIn("heuristic_attempts", solve.call_args.kwargs)
        self.assertEqual(solve.call_args.kwargs["separator_mode"], "bridge_safe")
        self.assertEqual(solve.call_args.kwargs["max_deterministic_time_per_solve"], 0.5)
        self.assertTrue(solve.call_args.kwargs["interleave_search"])

    def test_c_portfolio_cli_forwards_custom_audit_directory(self) -> None:
        argv = [
            "nebula-ps1",
            "solve-c-portfolio",
            "--data",
            str(PACK / "01_data"),
            "--output",
            "unused",
            "--audit-output",
            "custom-audit",
            "--strict-buffer-overlap",
        ]
        with patch("sys.argv", argv), patch(
            "nebula_ps1.cli.solve_scenario_c_portfolio", return_value={}
        ) as solve:
            cli_main()
        self.assertEqual(solve.call_args.kwargs["audit_output_dir"], "custom-audit")
        self.assertTrue(solve.call_args.kwargs["forbid_buffer_overlap"])

    def test_staged_cli_forwards_heuristic_attempt_count(self) -> None:
        argv = [
            "nebula-ps1",
            "solve-staged",
            "--data",
            str(PACK / "01_data"),
            "--output",
            "unused",
            "--scenario",
            "B",
            "--heuristic-attempts",
            "7",
            "--fallback-time-limit",
            "17",
            "--local-repair-time-limit",
            "16",
            "--fallback-attempts",
            "4",
            "--verification-round-time-limit",
            "6",
        ]
        with patch("sys.argv", argv), patch(
            "nebula_ps1.cli.solve_staged_scenario", return_value={}
        ) as solve:
            cli_main()
        self.assertEqual(solve.call_args.kwargs["heuristic_attempts"], 7)
        self.assertEqual(solve.call_args.kwargs["local_repair_time_limit_seconds"], 16.0)
        self.assertEqual(solve.call_args.kwargs["fallback_time_limit_seconds"], 17.0)
        self.assertEqual(solve.call_args.kwargs["fallback_attempts"], 4)
        self.assertEqual(
            solve.call_args.kwargs["verification_round_time_limit_seconds"], 6.0
        )

    def test_staged_c_cli_forwards_all_stage_budgets(self) -> None:
        argv = [
            "nebula-ps1",
            "solve-staged-c",
            "--data",
            str(PACK / "01_data"),
            "--output",
            "unused",
            "--audit-output",
            "custom-c-audit",
            "--a-heuristic-time-limit",
            "11",
            "--a-fallback-time-limit",
            "12",
            "--a-local-repair-time-limit",
            "10",
            "--a-verification-time-limit",
            "13",
            "--c-heuristic-time-limit",
            "14",
            "--c-verification-time-limit",
            "15",
            "--a-heuristic-attempts",
            "5",
            "--a-fallback-attempts",
            "6",
            "--c-heuristic-attempts",
            "7",
            "--strict-buffer-overlap",
        ]
        with patch("sys.argv", argv), patch(
            "nebula_ps1.cli.solve_staged_c_portfolio", return_value={}
        ) as solve:
            cli_main()
        kwargs = solve.call_args.kwargs
        self.assertEqual(kwargs["audit_output_dir"], "custom-c-audit")
        self.assertEqual(kwargs["a_heuristic_time_limit_seconds"], 11.0)
        self.assertEqual(kwargs["a_fallback_time_limit_seconds"], 12.0)
        self.assertEqual(kwargs["a_local_repair_time_limit_seconds"], 10.0)
        self.assertEqual(kwargs["a_verification_time_limit_seconds"], 13.0)
        self.assertEqual(kwargs["c_heuristic_time_limit_seconds"], 14.0)
        self.assertEqual(kwargs["c_verification_time_limit_seconds"], 15.0)
        self.assertEqual(kwargs["a_heuristic_attempts"], 5)
        self.assertEqual(kwargs["a_fallback_attempts"], 6)
        self.assertEqual(kwargs["c_heuristic_attempts"], 7)
        self.assertTrue(kwargs["forbid_buffer_overlap"])

    def test_official_a_incumbent_passes_corrected_closure_screen(self) -> None:
        candidate = ROOT / "deliverables" / "public" / "A"
        evaluation = evaluate_submission(self.instance, candidate, scenario="A")
        self.assertEqual(evaluation.hard_violations, ())
        self.assertAlmostEqual(evaluation.objective_score, 137.9)

    def test_official_scenario_a_incumbent_matches_portal_score(self) -> None:
        candidate = ROOT / "deliverables" / "public" / "A"
        evaluation = evaluate_submission(self.instance, candidate, scenario="A")
        self.assertEqual(evaluation.hard_violations, ())
        self.assertEqual(evaluation.eclo_nights_total, 0)
        self.assertEqual(evaluation.excess_access_nights_total, 0)
        self.assertAlmostEqual(evaluation.objective_score, 137.9)

    def test_scenario_b_incumbent_passes_all_implemented_rules(self) -> None:
        candidate = ROOT / "deliverables" / "public" / "B"
        evaluation = evaluate_submission(self.instance, candidate, scenario="B")
        self.assertEqual(evaluation.hard_violations, ())
        self.assertEqual(evaluation.eclo_nights_total, 6)
        self.assertEqual(evaluation.excess_access_nights_total, 0)
        self.assertAlmostEqual(evaluation.objective_score, 30.0)

    def test_scenario_b_cost_repair_targets_only_actual_cost_participants(self) -> None:
        contributors = _scenario_b_cost_contributing_activities(
            self.instance, ROOT / "deliverables" / "public" / "B"
        )
        self.assertEqual(contributors, ["A036", "A059"])

    def test_scenario_c_cost_repair_expands_to_footprint_competitors(self) -> None:
        direct = set(
            _scenario_b_cost_contributing_activities(
                self.instance, ROOT / "deliverables" / "public" / "C"
            )
        )
        expanded = set(
            _scenario_b_cost_contributing_activities(
                self.instance,
                ROOT / "deliverables" / "public" / "C",
                expand_footprints=True,
                expand_contracts=True,
                expand_precedence=True,
                revisit_precedence_after_footprints=True,
                include_delays=True,
            )
        )
        self.assertEqual(direct, {"A036", "A059"})
        self.assertGreater(len(expanded), len(direct))
        self.assertTrue(direct < expanded)

    def test_scenario_c_cost_repair_expands_direct_contributor_contracts(self) -> None:
        data = ROOT / "fixtures" / "independent_multimodule_tradeoff_v1"
        instance = load_instance(data)
        contributors = _scenario_b_cost_contributing_activities(
            instance,
            ROOT / "fixtures" / "independent_multimodule_tradeoff_v1_delayed_incumbent",
            expand_footprints=True,
            expand_contracts=True,
            expand_precedence=True,
            revisit_precedence_after_footprints=True,
            include_delays=True,
        )
        kmm = {
            activity_id
            for activity_id, activity in instance.activities.items()
            if activity.contract_number == "KMM"
        }
        self.assertTrue(kmm <= set(contributors))
        self.assertIn("R0101", contributors)

    def test_scenario_c_cost_repair_includes_delay_only_contracts(self) -> None:
        data = ROOT / "fixtures" / "independent_multimodule_tradeoff_v1"
        instance = load_instance(data)
        source = (
            ROOT / "fixtures" / "independent_multimodule_tradeoff_v1_delay_only_incumbent"
        )
        self.assertEqual(
            _scenario_b_cost_contributing_activities(
                instance,
                source,
                expand_footprints=True,
                expand_contracts=True,
            ),
            [],
        )
        contributors = _scenario_b_cost_contributing_activities(
            instance,
            source,
            expand_footprints=True,
            expand_contracts=True,
            expand_precedence=True,
            include_delays=True,
        )
        kmm = {
            activity_id
            for activity_id, activity in instance.activities.items()
            if activity.contract_number == "KMM"
        }
        self.assertTrue(kmm <= set(contributors))

    def test_scenario_c_cost_repair_expands_precedence_component(self) -> None:
        data = ROOT / "fixtures" / "independent_predecessor_tradeoff_v1"
        instance = load_instance(data)
        source = (
            ROOT / "fixtures" / "independent_predecessor_tradeoff_v1_delayed_incumbent"
        )
        without_predecessor = _scenario_b_cost_contributing_activities(
            instance,
            source,
            expand_footprints=True,
            expand_contracts=True,
            include_delays=True,
        )
        with_predecessor = _scenario_b_cost_contributing_activities(
            instance,
            source,
            expand_footprints=True,
            expand_contracts=True,
            expand_precedence=True,
            include_delays=True,
        )
        self.assertEqual(without_predecessor, ["SUCC"])
        self.assertEqual(with_predecessor, ["PRED", "SUCC"])

    def test_relabelled_a_incumbent_is_a_safe_scenario_c_fallback(self) -> None:
        source = ROOT / "deliverables" / "public" / "A"
        with tempfile.TemporaryDirectory() as temp_dir:
            relabel_submission_scenario(self.instance, source, temp_dir, "C")
            evaluation = evaluate_submission(self.instance, temp_dir, scenario="C")
            for name in SUBMISSION_FILES:
                self.assertNotIn(b"\r\n", (Path(temp_dir) / name).read_bytes())
        self.assertEqual(evaluation.hard_violations, ())
        self.assertEqual(evaluation.eclo_nights_total, 0)
        self.assertEqual(evaluation.excess_access_nights_total, 0)
        self.assertAlmostEqual(evaluation.objective_score, 137.9)

    def test_scenario_c_incumbent_passes_all_implemented_rules(self) -> None:
        candidate = ROOT / "deliverables" / "public" / "C"
        evaluation = evaluate_submission(self.instance, candidate, scenario="C")
        self.assertEqual(evaluation.hard_violations, ())
        self.assertEqual(evaluation.eclo_nights_total, 4)
        self.assertEqual(evaluation.excess_access_nights_total, 0)
        self.assertAlmostEqual(evaluation.priority_weighted_score, 42.7)
        self.assertAlmostEqual(evaluation.objective_score, 62.7)

    def test_scenario_c_rejects_discontinuous_eclo_window(self) -> None:
        source = ROOT / "deliverables" / "public" / "C"
        with tempfile.TemporaryDirectory() as temp_dir:
            copied = Path(temp_dir)
            for name in ("SCHEDULE_ACCESS.csv", "SCHEDULE_OCCUPANCY.csv", "RESULTS.csv"):
                shutil.copy(source / name, copied / name)
            access_path = copied / "SCHEDULE_ACCESS.csv"
            with access_path.open(newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
                fieldnames = list(rows[0])
            for row in rows:
                activity = self.instance.activities[row["activity_id"]]
                line, _, _ = split_sector_location(activity.start_location_id)
                if row["eclo"] == "0" and line == "BET" and int(row["week"]) < 20:
                    row["eclo"] = "1"
                    break
            else:
                self.fail("no suitable BET access row for ECLO-window mutation")
            with access_path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)
            evaluation = evaluate_submission(self.instance, copied, scenario="C")
        self.assertTrue(
            any("two-week window" in violation for violation in evaluation.hard_violations),
            evaluation.hard_violations,
        )

    def test_independent_raw_csv_scorer_matches_all_protected_incumbents(self) -> None:
        expected = {
            "A": ("A", 137.9, 137.9, 0, 0),
            "B": ("B", 30.0, 0.0, 0, 6),
            "C": ("C", 62.7, 42.7, 0, 4),
        }
        for scenario_name, components in expected.items():
            with self.subTest(scenario=scenario_name):
                candidate = ROOT / "deliverables" / "public" / scenario_name
                audit = independently_score(PACK / "01_data", candidate)
                scenario, objective, delay, excess, eclo = components
                self.assertEqual(audit.scenario, scenario)
                self.assertAlmostEqual(audit.objective_score, objective)
                self.assertAlmostEqual(audit.priority_weighted_delay, delay)
                self.assertEqual(audit.excess_access_nights, excess)
                self.assertEqual(audit.eclo_nights, eclo)

    def test_access_row_order_does_not_change_score(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            copied = Path(temp_dir)
            for name in ("SCHEDULE_ACCESS.csv", "SCHEDULE_OCCUPANCY.csv", "RESULTS.csv"):
                shutil.copy(PACK / "03_submission_sample" / name, copied / name)
            path = copied / "SCHEDULE_ACCESS.csv"
            with path.open(newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
                fieldnames = list(rows[0])
            with path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(reversed(rows))
            evaluation = evaluate_submission(self.instance, copied, scenario="A")
            self.assertEqual(evaluation.hard_violations, ())
            self.assertAlmostEqual(evaluation.objective_score, 137.9)

    def test_occupancy_order_and_group_labels_do_not_change_feasibility(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            copied = Path(temp_dir)
            for name in ("SCHEDULE_ACCESS.csv", "SCHEDULE_OCCUPANCY.csv", "RESULTS.csv"):
                shutil.copy(PACK / "03_submission_sample" / name, copied / name)
            path = copied / "SCHEDULE_OCCUPANCY.csv"
            with path.open(newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
                fieldnames = list(rows[0])
            label_map: dict[tuple[str, str, str], str] = {}
            for row in rows:
                key = (row["week"], row["location_id"], row["co_share_group"])
                if key not in label_map:
                    label_map[key] = f"renamed_group_{len(label_map) + 1}"
                row["co_share_group"] = label_map[key]
            with path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(reversed(rows))
            evaluation = evaluate_submission(self.instance, copied, scenario="A")
        self.assertEqual(evaluation.hard_violations, ())
        self.assertAlmostEqual(evaluation.objective_score, 137.9)

    def test_missing_access_is_rejected_instead_of_scoring_well(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            copied = Path(temp_dir)
            for name in ("SCHEDULE_ACCESS.csv", "SCHEDULE_OCCUPANCY.csv", "RESULTS.csv"):
                shutil.copy(PACK / "03_submission_sample" / name, copied / name)
            access_path = copied / "SCHEDULE_ACCESS.csv"
            with access_path.open(newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
                fieldnames = list(rows[0])
            removed = rows.pop()
            with access_path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)
            occupancy_path = copied / "SCHEDULE_OCCUPANCY.csv"
            with occupancy_path.open(newline="", encoding="utf-8") as handle:
                occupancy = list(csv.DictReader(handle))
                occupancy_fields = list(occupancy[0])
            occupancy = [
                row
                for row in occupancy
                if not (
                    row["activity_id"] == removed["activity_id"]
                    and row["week"] == removed["week"]
                )
            ]
            with occupancy_path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=occupancy_fields)
                writer.writeheader()
                writer.writerows(occupancy)
            evaluation = evaluate_submission(self.instance, copied, scenario="A")
            self.assertFalse(evaluation.internally_feasible)
            self.assertTrue(
                any(
                    "workload" in violation or "no scheduled access" in violation
                    for violation in evaluation.hard_violations
                ),
                evaluation.hard_violations,
            )

    def test_unknown_activity_is_rejected_without_crashing_closure_screen(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            copied = Path(temp_dir)
            for name in ("SCHEDULE_ACCESS.csv", "SCHEDULE_OCCUPANCY.csv", "RESULTS.csv"):
                shutil.copy(PACK / "03_submission_sample" / name, copied / name)
            access_path = copied / "SCHEDULE_ACCESS.csv"
            with access_path.open(newline="", encoding="utf-8") as handle:
                access_rows = list(csv.DictReader(handle))
                access_fields = list(access_rows[0])
            original_id = access_rows[0]["activity_id"]
            for row in access_rows:
                if row["activity_id"] == original_id:
                    row["activity_id"] = "UNKNOWN_ACTIVITY"
            with access_path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=access_fields)
                writer.writeheader()
                writer.writerows(access_rows)
            occupancy_path = copied / "SCHEDULE_OCCUPANCY.csv"
            with occupancy_path.open(newline="", encoding="utf-8") as handle:
                occupancy_rows = list(csv.DictReader(handle))
                occupancy_fields = list(occupancy_rows[0])
            for row in occupancy_rows:
                if row["activity_id"] == original_id:
                    row["activity_id"] = "UNKNOWN_ACTIVITY"
            with occupancy_path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=occupancy_fields)
                writer.writeheader()
                writer.writerows(occupancy_rows)
            evaluation = evaluate_submission(self.instance, copied, scenario="A")
        self.assertFalse(evaluation.internally_feasible)
        self.assertTrue(
            any("unknown activity" in violation for violation in evaluation.hard_violations)
        )

    def test_c_portfolio_selection_requires_checked_strict_improvement(self) -> None:
        a_run = ROOT / "deliverables" / "public" / "A"
        c_run = ROOT / "deliverables" / "public" / "C"
        with tempfile.TemporaryDirectory() as temp_dir:
            fallback_dir = Path(temp_dir) / "fallback"
            relabel_submission_scenario(self.instance, a_run, fallback_dir, "C")
            fallback = evaluate_submission(self.instance, fallback_dir, scenario="C")
            candidate = evaluate_submission(self.instance, c_run, scenario="C")
        self.assertTrue(_candidate_is_better(candidate, fallback))
        self.assertFalse(_candidate_is_better(fallback, candidate))
        self.assertFalse(_candidate_is_better(candidate, candidate))
        invalid_low_score = replace(
            candidate, objective_score=0.0, hard_violations=("synthetic violation",)
        )
        self.assertFalse(_candidate_is_better(invalid_low_score, fallback))

    def test_submission_copy_contains_exactly_three_csv_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "answer_key"
            _copy_submission(PACK / "03_submission_sample", output)
            self.assertEqual(
                sorted(path.name for path in output.iterdir()), sorted(SUBMISSION_FILES)
            )

    def test_pruner_preserves_minimal_public_a_incumbent(self) -> None:
        source = ROOT / "deliverables" / "public" / "A"
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "pruned"
            report = prune_submission(self.instance, source, output, "A")
            evaluation = evaluate_submission(self.instance, output, scenario="A")
            self.assertEqual(sorted(path.name for path in output.iterdir()), sorted(SUBMISSION_FILES))
            for name in SUBMISSION_FILES:
                self.assertNotIn(b"\r\n", (output / name).read_bytes())
        self.assertEqual(report.initial_access_rows, 192)
        self.assertEqual(report.final_access_rows, 192)
        self.assertEqual(report.removed_accesses, ())
        self.assertAlmostEqual(evaluation.objective_score, 137.9)

    def test_strict_pruner_preserves_dual_policy_answer_key(self) -> None:
        source = ROOT / "deliverables" / "public" / "A"
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "strict-pruned"
            report = prune_submission(
                self.instance,
                source,
                output,
                "A",
                forbid_buffer_overlap=True,
            )
            access, occupancy, _ = load_submission(output)
            strict_conflicts = screen_closures(
                self.instance,
                access,
                occupancy,
                forbid_buffer_overlap=True,
            )
            for name in SUBMISSION_FILES:
                self.assertNotIn(b"\r\n", (output / name).read_bytes())
        self.assertTrue(report.strict_buffer_overlap_checked)
        self.assertEqual(report.removed_accesses, ())
        self.assertEqual(strict_conflicts, ())

    def test_checked_hint_is_a_protected_incumbent_not_only_a_search_hint(self) -> None:
        source = ROOT / "deliverables" / "public" / "A"
        with tempfile.TemporaryDirectory() as temp_dir:
            telemetry = solve_flexible_supply_relaxation(
                self.instance,
                temp_dir,
                "A",
                time_limit_seconds=0.0,
                sample_hint_dir=source,
                forbid_buffer_overlap=True,
            )
            evaluation = evaluate_submission(self.instance, temp_dir, scenario="A")
            access, occupancy, _ = load_submission(temp_dir)
            strict_conflicts = screen_closures(
                self.instance,
                access,
                occupancy,
                forbid_buffer_overlap=True,
            )
            for name in SUBMISSION_FILES:
                self.assertNotIn(b"\r\n", (Path(temp_dir) / name).read_bytes())
        self.assertEqual(telemetry.status, "FEASIBLE_SAFE_INCUMBENT")
        self.assertIsNotNone(telemetry.deterministic_time_seconds)
        self.assertAlmostEqual(telemetry.objective_score, 137.9)
        self.assertEqual(telemetry.primary_bound_scope, "full_instance")
        self.assertEqual(evaluation.hard_violations, ())
        self.assertEqual(strict_conflicts, ())
        with tempfile.TemporaryDirectory() as temp_dir:
            heuristic = solve_flexible_supply_relaxation(
                self.instance,
                temp_dir,
                "A",
                time_limit_seconds=0.0,
                sample_hint_dir=source,
                forbid_buffer_overlap=True,
                separator_mode="direct_heuristic",
            )
        self.assertEqual(heuristic.status, "HEURISTIC_SAFE_INCUMBENT")
        self.assertIsNone(heuristic.best_bound)
        self.assertFalse(heuristic.primary_score_proven_optimal)
        self.assertFalse(heuristic.tie_break_proven_optimal)

    def test_frozen_access_telemetry_declares_conditional_bound_scope(self) -> None:
        source = ROOT / "deliverables" / "public" / "C"
        with tempfile.TemporaryDirectory() as temp_dir:
            partial = solve_flexible_supply_relaxation(
                self.instance,
                temp_dir,
                "C",
                time_limit_seconds=0.0,
                sample_hint_dir=source,
                freeze_access_hint=True,
                freeze_access_except={"A001"},
            )
        self.assertEqual(partial.primary_bound_scope, "frozen_access_neighborhood")
        self.assertIn("only to the frozen-access neighborhood", partial.limitation)

        with tempfile.TemporaryDirectory() as temp_dir:
            fixed = solve_flexible_supply_relaxation(
                self.instance,
                temp_dir,
                "C",
                time_limit_seconds=0.0,
                sample_hint_dir=source,
                freeze_access_hint=True,
            )
        self.assertEqual(fixed.primary_bound_scope, "fixed_access_schedule")
        self.assertIn("only to the fixed access schedule", fixed.limitation)

    def test_freeze_access_requires_an_explicit_hint(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaisesRegex(ValueError, "requires sample_hint_dir"):
                solve_flexible_supply_relaxation(
                    self.instance,
                    temp_dir,
                    "C",
                    time_limit_seconds=0.0,
                    freeze_access_hint=True,
                )
            with self.assertRaisesRegex(ValueError, "requires freeze_access_hint"):
                solve_flexible_supply_relaxation(
                    self.instance,
                    temp_dir,
                    "C",
                    time_limit_seconds=0.0,
                    freeze_access_except={"A001"},
                )
            with self.assertRaisesRegex(ValueError, "unknown free activities"):
                solve_flexible_supply_relaxation(
                    self.instance,
                    temp_dir,
                    "C",
                    time_limit_seconds=0.0,
                    sample_hint_dir=ROOT / "runs" / "c_relax_seed1",
                    freeze_access_hint=True,
                    freeze_access_except={"UNKNOWN_ACTIVITY"},
                )

    def test_separator_mode_rejects_unknown_policy(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaisesRegex(ValueError, "separator_mode"):
                solve_flexible_supply_relaxation(
                    self.instance,
                    temp_dir,
                    "A",
                    time_limit_seconds=0.0,
                    separator_mode="unsafe-unknown",
                )
            with self.assertRaisesRegex(ValueError, "max_deterministic_time_per_solve"):
                solve_flexible_supply_relaxation(
                    self.instance,
                    temp_dir,
                    "A",
                    time_limit_seconds=0.0,
                    max_deterministic_time_per_solve=0.0,
                )
            with self.assertRaisesRegex(ValueError, "heuristic_attempts"):
                solve_staged_scenario(
                    self.instance,
                    Path(temp_dir) / "staged",
                    "B",
                    heuristic_attempts=0,
                )
            with self.assertRaisesRegex(ValueError, "fallback_attempts"):
                solve_staged_scenario(
                    self.instance,
                    Path(temp_dir) / "staged-fallback",
                    "B",
                    fallback_attempts=0,
                )

    def test_staged_solver_uses_sound_fallback_after_heuristic_failure(self) -> None:
        def telemetry(
            formulation: str,
            status: str,
            objective: float | None,
            remaining_conflicts: int,
        ) -> SolveTelemetry:
            return SolveTelemetry(
                formulation=formulation,
                status=status,
                objective_score=objective,
                best_bound=None,
                wall_time_seconds=0.0,
                conflicts=0,
                branches=0,
                seed=1,
                workers=1,
                time_limit_seconds=0.0,
                model_variables=0,
                model_constraints=0,
                limitation="test fixture",
                remaining_closure_conflicts=remaining_conflicts,
            )

        failed = telemetry("direct_heuristic", "FEASIBLE", 48.3, 1)
        fallback_one = telemetry("bridge_safe", "FEASIBLE_SAFE_INCUMBENT", 48.3, 0)
        fallback_two = telemetry("bridge_safe", "FEASIBLE_SAFE_INCUMBENT", 32.2, 0)

        def fake_solve(instance, output_dir, scenario, **kwargs):
            if kwargs["separator_mode"] == "direct_heuristic":
                _copy_submission(PACK / "03_submission_sample", Path(output_dir))
                return failed
            hint = kwargs.get("sample_hint_dir")
            if hint is not None and Path(hint).name == "bridge_safe_fallback_attempt_2_pruned":
                _copy_submission(ROOT / "deliverables" / "public" / "A", Path(output_dir))
                return fallback_two
            if kwargs["seed"] == 1:
                _copy_submission(PACK / "03_submission_sample", Path(output_dir))
                return fallback_one
            _copy_submission(ROOT / "deliverables" / "public" / "A", Path(output_dir))
            return fallback_two

        with tempfile.TemporaryDirectory() as temp_dir, patch(
            "nebula_ps1.staged.solve_flexible_supply_relaxation",
            side_effect=fake_solve,
        ) as solve:
            report = solve_staged_scenario(
                self.instance,
                Path(temp_dir) / "submission",
                "A",
                audit_output_dir=Path(temp_dir) / "audit",
                heuristic_attempts=1,
                fallback_attempts=2,
            )
        self.assertEqual(solve.call_count, 4)
        self.assertEqual(
            Path(solve.call_args_list[1].kwargs["sample_hint_dir"]).name,
            "heuristic_attempt_1_raw",
        )
        self.assertEqual(report["selected_stage"], "bridge_safe_fallback")
        self.assertEqual(report["bridge_safe_fallback_selected_attempt"], 1)
        self.assertAlmostEqual(report["selected_objective_score"], 137.9)
        self.assertIsNone(report["heuristic_telemetry"])
        self.assertEqual(
            report["bridge_safe_fallback_telemetry"]["status"],
            "FEASIBLE_SAFE_INCUMBENT",
        )
        self.assertEqual(
            report["verification_telemetry"]["status"],
            "FEASIBLE_SAFE_INCUMBENT",
        )

    def test_staged_solver_evaluates_all_heuristic_attempts_and_selects_best(self) -> None:
        prefix_instance = load_instance(ROOT / "fixtures" / "prefix_040")

        def fake_solve(instance, output_dir, scenario, **kwargs):
            self.assertEqual(scenario, "B")
            use_best = kwargs["separator_mode"] != "direct_heuristic" or kwargs["seed"] == 2
            source = (
                ROOT / "fixtures" / "prefix_040_submissions" / ("b_20" if use_best else "b_30")
            )
            _copy_submission(source, Path(output_dir))
            objective = 20.0 if use_best else 30.0
            return SolveTelemetry(
                formulation=kwargs["separator_mode"],
                status="FEASIBLE_SAFE_INCUMBENT",
                objective_score=objective,
                best_bound=None,
                wall_time_seconds=0.0,
                conflicts=0,
                branches=0,
                seed=kwargs["seed"],
                workers=1,
                time_limit_seconds=1.0,
                model_variables=0,
                model_constraints=0,
                limitation="test fixture",
                remaining_closure_conflicts=0,
            )

        with tempfile.TemporaryDirectory() as temp_dir, patch(
            "nebula_ps1.staged.solve_flexible_supply_relaxation", side_effect=fake_solve
        ) as solve:
            report = solve_staged_scenario(
                prefix_instance,
                Path(temp_dir) / "submission",
                "B",
                audit_output_dir=Path(temp_dir) / "audit",
                heuristic_attempts=3,
            )
        self.assertEqual(solve.call_count, 5)
        self.assertEqual(report["heuristic_selected_attempt"], 2)
        self.assertEqual(len(report["heuristic_attempts"]), 3)
        self.assertTrue(solve.call_args_list[0].kwargs["use_structural_hints"])
        self.assertFalse(solve.call_args_list[1].kwargs["use_structural_hints"])
        self.assertFalse(solve.call_args_list[2].kwargs["use_structural_hints"])

    def test_staged_b_runs_guarded_cost_repair_on_derived_contributors(self) -> None:
        def fake_solve(instance, output_dir, scenario, **kwargs):
            self.assertEqual(scenario, "B")
            _copy_submission(ROOT / "deliverables" / "public" / "B", Path(output_dir))
            return SolveTelemetry(
                formulation=kwargs["separator_mode"],
                status="FEASIBLE_SAFE_INCUMBENT",
                objective_score=30.0,
                best_bound=30.0,
                wall_time_seconds=0.0,
                conflicts=0,
                branches=0,
                seed=kwargs["seed"],
                workers=1,
                time_limit_seconds=1.0,
                model_variables=0,
                model_constraints=0,
                limitation="test fixture",
                remaining_closure_conflicts=0,
            )

        with tempfile.TemporaryDirectory() as temp_dir, patch(
            "nebula_ps1.staged.solve_flexible_supply_relaxation", side_effect=fake_solve
        ) as solve:
            report = solve_staged_scenario(
                self.instance,
                Path(temp_dir) / "submission",
                "B",
                audit_output_dir=Path(temp_dir) / "audit",
                heuristic_attempts=1,
                local_repair_time_limit_seconds=1.0,
            )
        self.assertEqual(solve.call_count, 3)
        cost_call = solve.call_args_list[2]
        self.assertTrue(cost_call.kwargs["freeze_access_hint"])
        self.assertEqual(cost_call.kwargs["freeze_access_except"], {"A036", "A059"})
        self.assertEqual(
            report["bridge_safe_cost_repair_activities"], ["A036", "A059"]
        )

    def test_staged_c_runs_guarded_cost_repair_on_derived_contributors(self) -> None:
        expected = _scenario_b_cost_contributing_activities(
            self.instance,
            ROOT / "deliverables" / "public" / "C",
            expand_footprints=True,
            expand_contracts=True,
            expand_precedence=True,
            revisit_precedence_after_footprints=True,
            include_delays=True,
        )

        def fake_solve(instance, output_dir, scenario, **kwargs):
            self.assertEqual(scenario, "C")
            _copy_submission(ROOT / "deliverables" / "public" / "C", Path(output_dir))
            return SolveTelemetry(
                formulation=kwargs["separator_mode"],
                status="FEASIBLE_SAFE_INCUMBENT",
                objective_score=62.7,
                best_bound=None,
                wall_time_seconds=0.0,
                conflicts=0,
                branches=0,
                seed=kwargs["seed"],
                workers=1,
                time_limit_seconds=1.0,
                model_variables=0,
                model_constraints=0,
                limitation="test fixture",
                remaining_closure_conflicts=0,
            )

        with tempfile.TemporaryDirectory() as temp_dir, patch(
            "nebula_ps1.staged.solve_flexible_supply_relaxation", side_effect=fake_solve
        ) as solve:
            report = solve_staged_scenario(
                self.instance,
                Path(temp_dir) / "submission",
                "C",
                audit_output_dir=Path(temp_dir) / "audit",
                heuristic_attempts=1,
                local_repair_time_limit_seconds=1.0,
            )
        self.assertEqual(solve.call_count, 3)
        cost_call = solve.call_args_list[2]
        self.assertTrue(cost_call.kwargs["freeze_access_hint"])
        self.assertEqual(cost_call.kwargs["freeze_access_except"], set(expected))
        self.assertEqual(
            report["bridge_safe_cost_repair_activities"], expected
        )

    def test_staged_solver_repairs_only_detected_conflict_activities_first(self) -> None:
        unsafe_access, unsafe_occupancy, _ = load_submission(PACK / "03_submission_sample")
        strict_conflicts = screen_closures(
            self.instance,
            unsafe_access,
            unsafe_occupancy,
            forbid_buffer_overlap=True,
        )
        expected_free = sorted(
            {
                activity_id
                for conflict in strict_conflicts
                for activity_id in (*conflict.first_activities, *conflict.second_activities)
            }
        )

        def telemetry(formulation, objective, conflicts):
            return SolveTelemetry(
                formulation=formulation,
                status="FEASIBLE_SAFE_INCUMBENT" if not conflicts else "UNKNOWN",
                objective_score=objective,
                best_bound=None,
                wall_time_seconds=0.0,
                conflicts=0,
                branches=0,
                seed=1,
                workers=1,
                time_limit_seconds=1.0,
                model_variables=0,
                model_constraints=0,
                limitation="test fixture",
                remaining_closure_conflicts=conflicts,
            )

        def fake_solve(instance, output_dir, scenario, **kwargs):
            if kwargs["separator_mode"] == "direct_heuristic":
                _copy_submission(PACK / "03_submission_sample", Path(output_dir))
                return telemetry("direct_heuristic", 48.3, len(strict_conflicts))
            _copy_submission(ROOT / "deliverables" / "public" / "A", Path(output_dir))
            return telemetry("bridge_safe", 32.2, 0)

        with tempfile.TemporaryDirectory() as temp_dir, patch(
            "nebula_ps1.staged.solve_flexible_supply_relaxation", side_effect=fake_solve
        ) as solve:
            report = solve_staged_scenario(
                self.instance,
                Path(temp_dir) / "submission",
                "A",
                audit_output_dir=Path(temp_dir) / "audit",
                heuristic_attempts=1,
                fallback_attempts=1,
                forbid_buffer_overlap=True,
            )
        self.assertEqual(solve.call_count, 3)
        local_call = solve.call_args_list[1]
        self.assertTrue(local_call.kwargs["freeze_access_hint"])
        self.assertEqual(sorted(local_call.kwargs["freeze_access_except"]), expected_free)
        self.assertEqual(report["selected_stage"], "bridge_safe_local_repair")
        self.assertEqual(report["bridge_safe_local_repair_activities"], expected_free)
        self.assertEqual(report["bridge_safe_fallback_attempts"], [])

    def test_staged_c_preserves_checked_a_derived_fallback(self) -> None:
        tiny_instance = load_instance(ROOT / "fixtures" / "single_a001")
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "submission"
            audit = Path(temp_dir) / "audit"
            report = solve_staged_c_portfolio(
                tiny_instance,
                output,
                audit_output_dir=audit,
                a_heuristic_time_limit_seconds=0.0,
                a_local_repair_time_limit_seconds=0.0,
                a_fallback_time_limit_seconds=1.0,
                a_verification_time_limit_seconds=0.0,
                c_heuristic_time_limit_seconds=0.0,
                c_verification_time_limit_seconds=0.0,
                workers=1,
                seed=21,
                a_heuristic_attempts=1,
                a_fallback_attempts=1,
                c_heuristic_attempts=1,
                closure_round_limit=50,
                forbid_buffer_overlap=True,
            )
            evaluation = evaluate_submission(tiny_instance, output, "C")
            audit_score = independently_score(ROOT / "fixtures" / "single_a001", output)
            self.assertEqual(
                sorted(path.name for path in output.iterdir()), sorted(SUBMISSION_FILES)
            )
            self.assertEqual(evaluation.hard_violations, ())
            self.assertEqual(evaluation.objective_score, 0.0)
            self.assertEqual(audit_score.objective_score, 0.0)
            self.assertTrue(report["strict_buffer_overlap_checked"])
            self.assertEqual(report["selected_objective_score"], 0.0)
            self.assertTrue((audit / "STAGED_C.json").exists())

    def test_staged_c_uses_checked_direct_path_only_after_a_failure(self) -> None:
        failure = RuntimeError(
            "neither direct heuristic nor bridge-safe fallback produced a checked safe incumbent"
        )
        direct = {
            "selected_objective_score": 52.0,
            "selected_submission_hash": "checked-direct-c",
        }
        with tempfile.TemporaryDirectory() as temp_dir, patch(
            "nebula_ps1.staged_c.solve_staged_scenario",
            side_effect=(failure, direct),
        ) as solve:
            report = solve_staged_c_portfolio(
                self.instance,
                Path(temp_dir) / "submission",
                audit_output_dir=Path(temp_dir) / "audit",
                a_heuristic_attempts=1,
                a_fallback_attempts=1,
                c_heuristic_attempts=1,
            )
        self.assertEqual(solve.call_count, 2)
        self.assertEqual(solve.call_args_list[0].args[2], "A")
        self.assertEqual(solve.call_args_list[1].args[2], "C")
        self.assertEqual(report["selected_stage"], "scenario_c_direct_after_a_failure")
        self.assertEqual(report["selected_objective_score"], 52.0)
        self.assertEqual(report["selected_submission_hash"], "checked-direct-c")

    def test_staged_c_selects_checked_heuristic_then_soundly_verifies_it(self) -> None:
        def fake_staged(instance, output_dir, scenario, **kwargs):
            self.assertEqual(scenario, "A")
            _copy_submission(ROOT / "deliverables" / "public" / "A", Path(output_dir))
            return {"selected_objective_score": 137.9}

        def fake_c_solve(instance, output_dir, scenario, **kwargs):
            self.assertEqual(scenario, "C")
            _copy_submission(ROOT / "deliverables" / "public" / "C", Path(output_dir))
            return SolveTelemetry(
                formulation=kwargs["separator_mode"],
                status="HEURISTIC_SAFE_INCUMBENT",
                objective_score=62.7,
                best_bound=None,
                wall_time_seconds=0.0,
                conflicts=0,
                branches=0,
                seed=kwargs["seed"],
                workers=kwargs["workers"],
                time_limit_seconds=kwargs["time_limit_seconds"],
                model_variables=0,
                model_constraints=0,
                limitation="test fixture",
                remaining_closure_conflicts=0,
            )

        with tempfile.TemporaryDirectory() as temp_dir, patch(
            "nebula_ps1.staged_c.solve_staged_scenario", side_effect=fake_staged
        ), patch(
            "nebula_ps1.staged_c.solve_flexible_supply_relaxation",
            side_effect=fake_c_solve,
        ) as solve:
            report = solve_staged_c_portfolio(
                self.instance,
                Path(temp_dir) / "submission",
                audit_output_dir=Path(temp_dir) / "audit",
                workers=1,
                seed=4,
                a_heuristic_attempts=1,
                a_fallback_attempts=1,
                c_heuristic_attempts=1,
                forbid_buffer_overlap=True,
            )
        self.assertEqual(solve.call_count, 3)
        self.assertEqual(solve.call_args_list[0].kwargs["separator_mode"], "direct_heuristic")
        self.assertIsNone(solve.call_args_list[0].kwargs["sample_hint_dir"])
        self.assertEqual(solve.call_args_list[1].kwargs["separator_mode"], "bridge_safe")
        self.assertEqual(solve.call_args_list[2].kwargs["separator_mode"], "bridge_safe")
        self.assertEqual(solve.call_args_list[2].kwargs["time_limit_seconds"], 30.0)
        self.assertTrue(solve.call_args_list[2].kwargs["freeze_access_hint"])
        self.assertEqual(report["selected_stage"], "scenario_c_heuristic")
        self.assertEqual(report["scenario_c_heuristic_selected_attempt"], 1)
        self.assertAlmostEqual(report["selected_objective_score"], 62.7)

    def test_packaged_public_answer_keys_match_manifest(self) -> None:
        deliverables = ROOT / "deliverables" / "public"
        if not deliverables.exists():
            self.skipTest("public answer keys have not been packaged")
        manifest = json.loads((deliverables / "MANIFEST.json").read_text(encoding="utf-8"))
        self.assertTrue(manifest["reference_validator_confirmed"])
        for scenario, expected in manifest["scenarios"].items():
            with self.subTest(scenario=scenario):
                answer_key = deliverables / scenario
                self.assertEqual(
                    sorted(path.name for path in answer_key.iterdir()), sorted(SUBMISSION_FILES)
                )
                for name, expected_hash in expected["files"].items():
                    actual_hash = hashlib.sha256((answer_key / name).read_bytes()).hexdigest()
                    self.assertEqual(actual_hash, expected_hash)
                evaluation = evaluate_submission(self.instance, answer_key, scenario=scenario)
                audit = independently_score(PACK / "01_data", answer_key)
                self.assertEqual(evaluation.hard_violations, ())
                access, occupancy, _ = load_submission(answer_key)
                strict_conflicts = screen_closures(
                    self.instance,
                    access,
                    occupancy,
                    forbid_buffer_overlap=True,
                )
                self.assertEqual(
                    not strict_conflicts,
                    expected["strict_buffer_overlap_checked"],
                )
                self.assertAlmostEqual(
                    evaluation.objective_score, expected["internally_checked_score"]
                )
                self.assertAlmostEqual(
                    evaluation.objective_score, expected["official_score"]
                )
                self.assertAlmostEqual(audit.objective_score, evaluation.objective_score)
                self.assertEqual(evaluation.submission_hash, expected["submission_hash"])
                prune_report = json.loads(
                    (deliverables / f"{scenario}_PRUNE.json").read_text(encoding="utf-8")
                )
                self.assertTrue(prune_report["strict_buffer_overlap_checked"])
                self.assertEqual(
                    prune_report["final_submission_hash"],
                    expected["submission_hash"],
                )


if __name__ == "__main__":
    unittest.main()
