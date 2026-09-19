from __future__ import annotations

import unittest
import csv
import hashlib
import itertools
import json
import shutil
import tempfile
import zipfile
from collections import defaultdict
from dataclasses import replace
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from nebula_ps1.cli import main as cli_main
from nebula_ps1.closure import _blocked_locations, _external_buffer_sectors, screen_closures
from nebula_ps1.eclo_compact import (
    best_serialized_eclo_compaction_sequence,
    best_single_lane_eclo_compaction,
)
from nebula_ps1.evaluate import _legal_possession_mix, evaluate_submission, load_submission
from nebula_ps1.flexible_solver import (
    _group_limit,
    _write_submission_rows,
    solve_flexible_supply_relaxation,
)
from nebula_ps1.independent_score import independently_score
from nebula_ps1.idle_compact import (
    _predicted_objective as predict_idle_compaction_objective,
    best_idle_week_compaction_sequence,
)
from nebula_ps1.instance import load_instance
from nebula_ps1.objective import (
    ACTIVITY_NUDGE,
    CONTRACT_WEIGHT,
    ECLO_COST,
    ECLO_COST_TENTHS,
    EXCESS_COST,
    EXCESS_COST_TENTHS,
    contract_costs_tenths,
    delay_score_from_completion_weeks,
)
from nebula_ps1.portfolio import SUBMISSION_FILES, _candidate_is_better, _copy_submission
from nebula_ps1.postprocess import best_checked_c_postprocessing_sequence
from nebula_ps1.prune import prune_submission
from nebula_ps1.solver import SolveTelemetry, _contract_costs
from nebula_ps1.staged import (
    _run_strict_score_preserving_hedge,
    _scenario_b_cost_contributing_activities,
    _strict_conflict_repair_activities,
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

    def test_three_line_fixture_proves_all_scenarios_and_cross_line_topology(self) -> None:
        data = ROOT / "fixtures" / "independent_three_line_v1"
        oracle = ROOT / "fixtures" / "independent_three_line_v1_oracle"
        instance = load_instance(data)
        oracle_evaluation = evaluate_submission(instance, oracle, "A")
        oracle_independent = independently_score(data, oracle)
        self.assertEqual(
            instance.dataset_hash,
            "71e1e417e3ede8385a5d957368f7b963fa65b89f703c859438bded342654e0da",
        )
        self.assertEqual(set(instance.lines), {"LNX", "LNY", "LNZ"})
        self.assertEqual(len(instance.activities), 10)
        self.assertEqual(oracle_evaluation.hard_violations, ())
        self.assertEqual(oracle_evaluation.objective_score, 7.0)
        self.assertEqual(oracle_independent.objective_score, 7.0)
        crossover = interchange_cross_line_locations(instance, instance.activities["Q003"])
        self.assertEqual(len(crossover), 12)
        self.assertEqual({location.split(":")[1] for location in crossover}, {"LNY", "LNZ"})

        expected_scores = {"A": 7.0, "B": 10.0, "C": 7.0}
        hashes = set()
        for scenario, expected_score in expected_scores.items():
            submission = ROOT / "runs" / f"independent_three_line_v1_{scenario.lower()}"
            audit = submission.with_name(f"{submission.name}_audit")
            evaluation = evaluate_submission(instance, submission, scenario)
            independent = independently_score(data, submission)
            access, occupancy, _ = load_submission(submission)
            telemetry = json.loads(
                (audit / "verification_raw" / "TELEMETRY.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(evaluation.hard_violations, ())
            self.assertEqual(evaluation.objective_score, expected_score)
            self.assertEqual(independent.objective_score, expected_score)
            self.assertEqual(
                screen_closures(
                    instance,
                    access,
                    occupancy,
                    forbid_buffer_overlap=True,
                ),
                (),
            )
            self.assertEqual(telemetry["best_bound"], expected_score)
            self.assertEqual(telemetry["primary_bound_scope"], "full_instance")
            hashes.add(evaluation.submission_hash)
        self.assertEqual(len(hashes), 3)

    def test_multi_bridge_fixture_proves_composed_cross_line_topology(self) -> None:
        data = ROOT / "fixtures" / "independent_multi_bridge_v1"
        oracle = ROOT / "fixtures" / "independent_multi_bridge_v1_oracle_a"
        instance = load_instance(data)
        oracle_evaluation = evaluate_submission(instance, oracle, "A")
        oracle_independent = independently_score(data, oracle)
        self.assertEqual(
            instance.dataset_hash,
            "68379defb1fb02785c1d4aa9ab88747faa395b5c888f6f1245d40df5d1b391e7",
        )
        self.assertEqual(oracle_evaluation.hard_violations, ())
        self.assertEqual(oracle_evaluation.objective_score, 0.0)
        self.assertEqual(oracle_independent.objective_score, 0.0)
        first = interchange_cross_line_locations(instance, instance.activities["M001"])
        second = interchange_cross_line_locations(instance, instance.activities["M003"])
        self.assertEqual(len(first), 10)
        self.assertEqual(len(second), 6)
        self.assertIn("SEC:LNY:X1_X2:WB", first)
        self.assertIn("SEC:LNY:X2_X3:EB", first)
        self.assertIn("SEC:LNX:X2_X3:WB", second)

        hashes = set()
        for scenario in ("A", "B", "C"):
            submission = ROOT / "runs" / f"independent_multi_bridge_v1_{scenario.lower()}"
            audit = submission.with_name(f"{submission.name}_audit")
            telemetry_root = (
                audit / "verification_raw"
                if scenario != "C"
                else audit / "stages" / "scenario_c_verification_raw"
            )
            evaluation = evaluate_submission(instance, submission, scenario)
            independent = independently_score(data, submission)
            access, occupancy, _ = load_submission(submission)
            telemetry = json.loads(
                (telemetry_root / "TELEMETRY.json").read_text(encoding="utf-8")
            )
            self.assertEqual(evaluation.hard_violations, ())
            self.assertEqual(evaluation.objective_score, 0.0)
            self.assertEqual(independent.objective_score, 0.0)
            self.assertEqual(
                screen_closures(
                    instance,
                    access,
                    occupancy,
                    forbid_buffer_overlap=True,
                ),
                (),
            )
            self.assertEqual(telemetry["best_bound"], 0.0)
            self.assertEqual(telemetry["primary_bound_scope"], "full_instance")
            hashes.add(evaluation.submission_hash)
        self.assertEqual(len(hashes), 3)

    def test_multi_bridge_congestion_proves_eclo_tradeoff(self) -> None:
        data = ROOT / "fixtures" / "independent_multi_bridge_congestion_v1"
        instance = load_instance(data)
        self.assertEqual(
            instance.dataset_hash,
            "07d5fb97a92c194da5ff70bfec984f3b4dc44c1d701502fc08eabcb0d54aa105",
        )
        expected = {"A": (700.0, 0), "B": (10.0, 2), "C": (10.0, 2)}
        for scenario, (score, eclo_nights) in expected.items():
            oracle = ROOT / "fixtures" / f"independent_multi_bridge_congestion_v1_oracle_{scenario.lower()}"
            oracle_evaluation = evaluate_submission(instance, oracle, scenario)
            oracle_independent = independently_score(data, oracle)
            self.assertEqual(oracle_evaluation.hard_violations, ())
            self.assertEqual(oracle_evaluation.objective_score, score)
            self.assertEqual(oracle_independent.objective_score, score)

            submission = ROOT / "runs" / f"independent_multi_bridge_congestion_v1_{scenario.lower()}"
            audit = submission.with_name(f"{submission.name}_audit")
            telemetry_root = (
                audit / "verification_raw"
                if scenario != "C"
                else audit / "stages" / "scenario_c_verification_raw"
            )
            evaluation = evaluate_submission(instance, submission, scenario)
            independent = independently_score(data, submission)
            access, occupancy, _ = load_submission(submission)
            telemetry = json.loads(
                (telemetry_root / "TELEMETRY.json").read_text(encoding="utf-8")
            )
            self.assertEqual(evaluation.hard_violations, ())
            self.assertEqual(evaluation.objective_score, score)
            self.assertEqual(independent.objective_score, score)
            self.assertEqual(evaluation.eclo_nights_total, eclo_nights)
            self.assertEqual(
                screen_closures(
                    instance,
                    access,
                    occupancy,
                    forbid_buffer_overlap=True,
                ),
                (),
            )
            self.assertEqual(telemetry["best_bound"], score)
            self.assertEqual(telemetry["primary_bound_scope"], "full_instance")

    def test_checked_single_lane_eclo_compaction_improves_scaled_c_only(self) -> None:
        data = ROOT / "fixtures" / "independent_multi_bridge_scale_v1"
        source = ROOT / "runs" / "independent_multi_bridge_scale_v1_c"
        instance = load_instance(data)
        with tempfile.TemporaryDirectory() as temp_dir:
            selected_dir, selected, report = best_single_lane_eclo_compaction(
                instance,
                source,
                Path(temp_dir) / "candidates",
            )
            self.assertIsNotNone(selected_dir)
            self.assertIsNotNone(selected)
            assert selected_dir is not None
            assert selected is not None
            independent = independently_score(data, selected_dir)
            access, occupancy, _ = load_submission(selected_dir)
            self.assertEqual(selected.hard_violations, ())
            self.assertEqual(selected.objective_score, 262.0)
            self.assertEqual(independent.objective_score, 262.0)
            self.assertEqual(selected.eclo_nights_total, 2)
            self.assertEqual(
                screen_closures(
                    instance,
                    access,
                    occupancy,
                    forbid_buffer_overlap=True,
                ),
                (),
            )
            self.assertTrue(report["applicable"])
            self.assertEqual(report["unique_candidates_ranked"], 8)
            self.assertEqual(report["candidates_checked"], 1)
            self.assertEqual(report["duplicate_candidates_skipped"], 8)
            self.assertEqual(report["candidates_pruned_by_exact_score_order"], 7)
            self.assertEqual(report["score_prediction_mismatches"], 0)
            self.assertEqual(report["feasible_candidates"], 1)
            self.assertEqual(report["improving_candidates"], 1)
            self.assertEqual(report["selected_score"], 262.0)

        with tempfile.TemporaryDirectory() as temp_dir:
            exhaustive_dir, exhaustive_selected, exhaustive_report = (
                best_single_lane_eclo_compaction(
                    instance,
                    source,
                    Path(temp_dir) / "candidates",
                    forbid_buffer_overlap=True,
                    exhaustive=True,
                )
            )
            self.assertIsNotNone(exhaustive_dir)
            self.assertIsNotNone(exhaustive_selected)
            assert exhaustive_selected is not None
            self.assertEqual(
                exhaustive_selected.submission_hash, selected.submission_hash
            )
            self.assertEqual(exhaustive_report["candidates_checked"], 8)
            self.assertEqual(exhaustive_report["feasible_candidates"], 8)
            self.assertEqual(exhaustive_report["improving_candidates"], 7)
            self.assertEqual(exhaustive_report["score_prediction_mismatches"], 0)

        with tempfile.TemporaryDirectory() as temp_dir:
            second_dir, second, second_report = best_single_lane_eclo_compaction(
                instance,
                ROOT / "runs" / "independent_multi_bridge_scale_v1_c_compaction_controller",
                Path(temp_dir) / "candidates",
                forbid_buffer_overlap=True,
            )
        self.assertIsNone(second_dir)
        self.assertIsNone(second)
        self.assertEqual(second_report["source_score"], 262.0)
        self.assertEqual(second_report["unique_candidates_ranked"], 0)
        self.assertEqual(second_report["candidates_checked"], 0)
        self.assertEqual(second_report["duplicate_candidates_skipped"], 0)
        self.assertEqual(
            second_report["candidates_skipped_existing_eclo_window"], 7
        )
        self.assertEqual(second_report["feasible_candidates"], 0)

    def test_serialized_eclo_compaction_repeats_across_independent_lines(
        self,
    ) -> None:
        data = ROOT / "fixtures" / "independent_eclo_multipass_v1"
        source = ROOT / "fixtures" / "independent_eclo_multipass_v1_source_c"
        instance = load_instance(data)
        with tempfile.TemporaryDirectory() as temp_dir:
            selected_dir, selected, report = (
                best_serialized_eclo_compaction_sequence(
                    instance,
                    source,
                    Path(temp_dir) / "candidates",
                    forbid_buffer_overlap=True,
                )
            )
            self.assertIsNotNone(selected_dir)
            self.assertIsNotNone(selected)
            assert selected_dir is not None
            assert selected is not None
            independent = independently_score(data, selected_dir)
            access, occupancy, _ = load_submission(selected_dir)
            self.assertEqual(selected.hard_violations, ())
            self.assertEqual(selected.objective_score, 18220.0)
            self.assertEqual(independent.objective_score, 18220.0)
            self.assertEqual(report["source_score"], 23660.0)
            self.assertEqual(report["selected_score"], 18220.0)
            self.assertEqual(report["promotions"], 2)
            self.assertEqual(len(report["rounds"]), 3)
            self.assertEqual(report["score_prediction_mismatches"], 0)
            self.assertEqual(
                report["candidates_skipped_existing_eclo_window"], 3
            )
            self.assertEqual(
                screen_closures(
                    instance,
                    access,
                    occupancy,
                    forbid_buffer_overlap=True,
                ),
                (),
            )

        public_hashes = {
            name: hashlib.sha256(
                (ROOT / "deliverables" / "public" / "C" / name).read_bytes()
            ).hexdigest()
            for name in SUBMISSION_FILES
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            selected_dir, selected, report = best_single_lane_eclo_compaction(
                self.instance,
                ROOT / "deliverables" / "public" / "C",
                Path(temp_dir) / "candidates",
            )
        self.assertIsNone(selected_dir)
        self.assertIsNone(selected)
        self.assertFalse(report["applicable"])
        self.assertEqual(report["candidates_checked"], 0)
        self.assertEqual(
            public_hashes,
            {
                name: hashlib.sha256(
                    (ROOT / "deliverables" / "public" / "C" / name).read_bytes()
                ).hexdigest()
                for name in SUBMISSION_FILES
            },
        )

    def test_scaled_multi_bridge_c_compaction_matches_enumerated_lower_bound(
        self,
    ) -> None:
        data = ROOT / "fixtures" / "independent_multi_bridge_scale_v1"
        candidate = ROOT / "runs" / "independent_multi_bridge_scale_v1_c_compact_t003"
        instance = load_instance(data)
        activity_ids = sorted(instance.activities)
        self.assertEqual(
            {
                instance.projects[activity.contract_number].access_type
                for activity in instance.activities.values()
            },
            {"PM"},
        )
        self.assertTrue(
            all(
                interchange_cross_line_locations(instance, activity)
                for activity in instance.activities.values()
            )
        )
        conflict_pairs = 0
        for first_id, second_id in itertools.combinations(activity_ids, 2):
            access = [
                SimpleNamespace(activity_id=first_id, week=1),
                SimpleNamespace(activity_id=second_id, week=1),
            ]
            occupancy = [
                SimpleNamespace(
                    activity_id=activity_id,
                    week=1,
                    location_id=location_id,
                    co_share_group=f"group-{activity_id}",
                )
                for activity_id in (first_id, second_id)
                for location_id in activity_footprint(
                    instance, instance.activities[activity_id]
                )
            ]
            if screen_closures(instance, access, occupancy):
                conflict_pairs += 1
        self.assertEqual(conflict_pairs, 28)

        due_week = {
            activity_id: instance.week_for_date(
                instance.projects[
                    instance.activities[activity_id].contract_number
                ].planned_completion_date
            )
            for activity_id in activity_ids
        }
        contract_weight = {1: 100, 2: 10, 3: 1}
        activity_nudge = {1: 1.3, 2: 1.2, 3: 1.0}
        delay_weight = {
            activity_id: (
                contract_weight[
                    instance.projects[
                        instance.activities[activity_id].contract_number
                    ].contract_priority
                ]
                * activity_nudge[instance.activities[activity_id].activity_priority]
            )
            for activity_id in activity_ids
        }
        best_score = float("inf")
        for compressed_activity in [None, *activity_ids]:
            for sequence in itertools.permutations(activity_ids):
                completion_week = 0
                delay_score = 0
                for activity_id in sequence:
                    completion_week += 2 if activity_id == compressed_activity else 3
                    delay_score += (
                        7
                        * delay_weight[activity_id]
                        * max(0, completion_week - due_week[activity_id])
                    )
                score = delay_score + (10 if compressed_activity is not None else 0)
                best_score = min(best_score, score)
        evaluation = evaluate_submission(instance, candidate, "C")
        independent = independently_score(data, candidate)
        self.assertEqual(best_score, 262)
        self.assertEqual(evaluation.hard_violations, ())
        self.assertEqual(evaluation.objective_score, best_score)
        self.assertEqual(independent.objective_score, best_score)

    def test_generic_staged_c_promotes_checked_eclo_compaction_before_verification(
        self,
    ) -> None:
        data = ROOT / "fixtures" / "independent_multi_bridge_scale_v1"
        source = ROOT / "runs" / "independent_multi_bridge_scale_v1_c"
        instance = load_instance(data)
        calls = 0

        def fake_solve(instance, output_dir, scenario, **kwargs):
            nonlocal calls
            calls += 1
            selected_source = source if calls == 1 else Path(kwargs["sample_hint_dir"])
            _copy_submission(selected_source, Path(output_dir))
            evaluation = evaluate_submission(instance, output_dir, scenario)
            return SolveTelemetry(
                formulation=kwargs["separator_mode"],
                status="FEASIBLE_SAFE_INCUMBENT",
                objective_score=evaluation.objective_score,
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
            "nebula_ps1.staged.solve_flexible_supply_relaxation",
            side_effect=fake_solve,
        ) as solve:
            report = solve_staged_scenario(
                instance,
                Path(temp_dir) / "submission",
                "C",
                audit_output_dir=Path(temp_dir) / "audit",
                local_repair_time_limit_seconds=0.0,
                heuristic_attempts=1,
                fallback_attempts=1,
                workers=1,
                forbid_buffer_overlap=True,
            )
            final = evaluate_submission(instance, Path(temp_dir) / "submission", "C")
        self.assertEqual(solve.call_count, 2)
        self.assertTrue(report["eclo_compaction_promoted"])
        self.assertEqual(report["eclo_compaction"]["selected_score"], 262.0)
        self.assertEqual(report["selected_stage"], "eclo_compaction_incumbent")
        self.assertEqual(final.objective_score, 262.0)

    def test_generic_staged_c_applies_all_independent_line_compactions(
        self,
    ) -> None:
        data = ROOT / "fixtures" / "independent_eclo_multipass_v1"
        source = ROOT / "fixtures" / "independent_eclo_multipass_v1_source_c"
        instance = load_instance(data)
        calls = 0

        def fake_solve(instance, output_dir, scenario, **kwargs):
            nonlocal calls
            calls += 1
            selected_source = source if calls == 1 else Path(kwargs["sample_hint_dir"])
            _copy_submission(selected_source, Path(output_dir))
            evaluation = evaluate_submission(instance, output_dir, scenario)
            return SolveTelemetry(
                formulation=kwargs["separator_mode"],
                status="FEASIBLE_SAFE_INCUMBENT",
                objective_score=evaluation.objective_score,
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
            "nebula_ps1.staged.solve_flexible_supply_relaxation",
            side_effect=fake_solve,
        ):
            report = solve_staged_scenario(
                instance,
                Path(temp_dir) / "submission",
                "C",
                audit_output_dir=Path(temp_dir) / "audit",
                local_repair_time_limit_seconds=0.0,
                heuristic_attempts=1,
                fallback_attempts=1,
                workers=1,
                forbid_buffer_overlap=True,
            )
            final = evaluate_submission(instance, Path(temp_dir) / "submission", "C")
        self.assertEqual(calls, 2)
        self.assertTrue(report["eclo_compaction_promoted"])
        self.assertEqual(report["eclo_compaction"]["promotions"], 2)
        self.assertEqual(report["eclo_compaction"]["selected_score"], 18220.0)
        self.assertEqual(final.objective_score, 18220.0)

    def test_generic_staged_c_removes_idle_week_before_eclo_compaction(
        self,
    ) -> None:
        data = ROOT / "fixtures" / "independent_idle_week_v1"
        source = ROOT / "fixtures" / "independent_idle_week_v1_source_c"
        instance = load_instance(data)
        calls = 0

        def fake_solve(instance, output_dir, scenario, **kwargs):
            nonlocal calls
            calls += 1
            selected_source = source if calls == 1 else Path(kwargs["sample_hint_dir"])
            _copy_submission(selected_source, Path(output_dir))
            evaluation = evaluate_submission(instance, output_dir, scenario)
            return SolveTelemetry(
                formulation=kwargs["separator_mode"],
                status="FEASIBLE_SAFE_INCUMBENT",
                objective_score=evaluation.objective_score,
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
            "nebula_ps1.staged.solve_flexible_supply_relaxation",
            side_effect=fake_solve,
        ):
            report = solve_staged_scenario(
                instance,
                Path(temp_dir) / "submission",
                "C",
                audit_output_dir=Path(temp_dir) / "audit",
                local_repair_time_limit_seconds=0.0,
                heuristic_attempts=1,
                fallback_attempts=1,
                workers=1,
                forbid_buffer_overlap=True,
            )
            final = evaluate_submission(instance, Path(temp_dir) / "submission", "C")
        self.assertEqual(calls, 2)
        self.assertTrue(report["idle_week_compaction_promoted"])
        self.assertEqual(report["idle_week_compaction"]["selected_score"], 23660.0)
        self.assertTrue(report["eclo_compaction_promoted"])
        self.assertEqual(report["eclo_compaction"]["selected_score"], 18220.0)
        self.assertEqual(final.objective_score, 18220.0)

    def test_generic_staged_c_uses_equal_idle_normalization_only_as_seed(
        self,
    ) -> None:
        data = ROOT / "fixtures" / "independent_idle_unlock_v1"
        source = ROOT / "fixtures" / "independent_idle_unlock_v1_source_c"
        instance = load_instance(data)
        calls = 0

        def fake_solve(instance, output_dir, scenario, **kwargs):
            nonlocal calls
            calls += 1
            selected_source = source if calls == 1 else Path(kwargs["sample_hint_dir"])
            _copy_submission(selected_source, Path(output_dir))
            evaluation = evaluate_submission(instance, output_dir, scenario)
            return SolveTelemetry(
                formulation=kwargs["separator_mode"],
                status="FEASIBLE_SAFE_INCUMBENT",
                objective_score=evaluation.objective_score,
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
            "nebula_ps1.staged.solve_flexible_supply_relaxation",
            side_effect=fake_solve,
        ):
            report = solve_staged_scenario(
                instance,
                Path(temp_dir) / "submission",
                "C",
                audit_output_dir=Path(temp_dir) / "audit",
                local_repair_time_limit_seconds=0.0,
                heuristic_attempts=1,
                fallback_attempts=1,
                workers=1,
                forbid_buffer_overlap=True,
            )
            final = evaluate_submission(instance, Path(temp_dir) / "submission", "C")
        self.assertEqual(calls, 2)
        self.assertFalse(report["idle_week_compaction_promoted"])
        self.assertTrue(report["idle_week_compaction_used_as_seed"])
        self.assertEqual(report["idle_week_compaction"]["selected_score"], 910.0)
        self.assertTrue(report["eclo_compaction_promoted"])
        self.assertEqual(report["eclo_compaction"]["selected_score"], 10.0)
        self.assertEqual(final.objective_score, 10.0)

    def test_generic_staged_c_postprocesses_verification_winner(self) -> None:
        data = ROOT / "fixtures" / "independent_postselection_compaction_v1"
        heuristic = (
            ROOT / "fixtures" / "independent_postselection_compaction_v1_heuristic_c"
        )
        verification = ROOT / "fixtures" / "independent_eclo_multipass_v1_source_c"
        instance = load_instance(data)
        calls = 0

        def fake_solve(instance, output_dir, scenario, **kwargs):
            nonlocal calls
            calls += 1
            _copy_submission(heuristic if calls == 1 else verification, Path(output_dir))
            evaluation = evaluate_submission(instance, output_dir, scenario)
            return SolveTelemetry(
                formulation=kwargs["separator_mode"],
                status="FEASIBLE_SAFE_INCUMBENT",
                objective_score=evaluation.objective_score,
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
            "nebula_ps1.staged.solve_flexible_supply_relaxation",
            side_effect=fake_solve,
        ):
            output = Path(temp_dir) / "submission"
            report = solve_staged_scenario(
                instance,
                output,
                "C",
                audit_output_dir=Path(temp_dir) / "audit",
                local_repair_time_limit_seconds=0.0,
                heuristic_attempts=1,
                fallback_attempts=1,
                workers=1,
                forbid_buffer_overlap=True,
            )
            final = evaluate_submission(instance, output, "C")
            independent = independently_score(data, output)
        self.assertEqual(calls, 2)
        self.assertEqual(report["idle_week_compaction"]["selected_score"], 25480.0)
        self.assertIsNone(report["eclo_compaction"]["selected_score"])
        self.assertTrue(report["postselection_compaction_promoted"])
        self.assertEqual(report["postselection_compaction"]["source_score"], 23660.0)
        self.assertEqual(report["postselection_compaction"]["selected_score"], 22760.0)
        self.assertEqual(report["selected_stage"], "postselection_eclo_compaction")
        self.assertEqual(final.objective_score, 22760.0)
        self.assertEqual(independent.objective_score, 22760.0)

    def test_staged_c_portfolio_promotes_checked_eclo_compaction_before_verification(
        self,
    ) -> None:
        data = ROOT / "fixtures" / "independent_multi_bridge_scale_v1"
        source_a = ROOT / "runs" / "independent_multi_bridge_scale_v1_a"
        source_c = ROOT / "runs" / "independent_multi_bridge_scale_v1_c"
        instance = load_instance(data)
        calls = 0

        def fake_staged(instance, output_dir, scenario, **kwargs):
            self.assertEqual(scenario, "A")
            _copy_submission(source_a, Path(output_dir))
            return {"selected_objective_score": 273.0}

        def fake_c_solve(instance, output_dir, scenario, **kwargs):
            nonlocal calls
            calls += 1
            selected_source = (
                source_c if calls == 1 else Path(kwargs["sample_hint_dir"])
            )
            _copy_submission(selected_source, Path(output_dir))
            evaluation = evaluate_submission(instance, output_dir, scenario)
            return SolveTelemetry(
                formulation=kwargs["separator_mode"],
                status="FEASIBLE_SAFE_INCUMBENT",
                objective_score=evaluation.objective_score,
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
                instance,
                Path(temp_dir) / "submission",
                audit_output_dir=Path(temp_dir) / "audit",
                a_local_repair_time_limit_seconds=0.0,
                c_heuristic_attempts=1,
                workers=1,
                forbid_buffer_overlap=True,
            )
            final = evaluate_submission(instance, Path(temp_dir) / "submission", "C")
        self.assertEqual(solve.call_count, 2)
        self.assertTrue(report["scenario_c_eclo_compaction_promoted"])
        self.assertEqual(
            report["scenario_c_eclo_compaction"]["selected_score"], 262.0
        )
        self.assertEqual(report["selected_stage"], "scenario_c_eclo_compaction")
        self.assertEqual(final.objective_score, 262.0)

    def test_staged_c_portfolio_composes_equal_idle_seed_with_eclo(self) -> None:
        data = ROOT / "fixtures" / "independent_idle_unlock_v1"
        source = ROOT / "fixtures" / "independent_idle_unlock_v1_source_c"
        instance = load_instance(data)
        calls = 0

        def fake_staged(instance, output_dir, scenario, **kwargs):
            self.assertEqual(scenario, "A")
            relabel_submission_scenario(instance, source, Path(output_dir), "A")
            return {"selected_objective_score": 910.0}

        def fake_c_solve(instance, output_dir, scenario, **kwargs):
            nonlocal calls
            calls += 1
            selected_source = source if calls == 1 else Path(kwargs["sample_hint_dir"])
            _copy_submission(selected_source, Path(output_dir))
            evaluation = evaluate_submission(instance, output_dir, scenario)
            return SolveTelemetry(
                formulation=kwargs["separator_mode"],
                status="FEASIBLE_SAFE_INCUMBENT",
                objective_score=evaluation.objective_score,
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
        ):
            report = solve_staged_c_portfolio(
                instance,
                Path(temp_dir) / "submission",
                audit_output_dir=Path(temp_dir) / "audit",
                a_local_repair_time_limit_seconds=0.0,
                c_heuristic_attempts=1,
                workers=1,
                forbid_buffer_overlap=True,
            )
            final = evaluate_submission(instance, Path(temp_dir) / "submission", "C")
        self.assertEqual(calls, 2)
        self.assertFalse(report["scenario_c_idle_week_compaction_promoted"])
        self.assertTrue(report["scenario_c_idle_week_compaction_used_as_seed"])
        self.assertTrue(report["scenario_c_eclo_compaction_promoted"])
        self.assertEqual(report["scenario_c_eclo_compaction"]["selected_score"], 10.0)
        self.assertEqual(report["selected_stage"], "scenario_c_eclo_compaction")
        self.assertEqual(final.objective_score, 10.0)

    def test_staged_c_portfolio_postprocesses_final_selection(self) -> None:
        data = ROOT / "fixtures" / "independent_postselection_compaction_v1"
        heuristic = (
            ROOT / "fixtures" / "independent_postselection_compaction_v1_heuristic_c"
        )
        verification = ROOT / "fixtures" / "independent_eclo_multipass_v1_source_c"
        instance = load_instance(data)
        calls = 0

        def fake_staged(instance, output_dir, scenario, **kwargs):
            self.assertEqual(scenario, "A")
            relabel_submission_scenario(instance, heuristic, Path(output_dir), "A")
            return {"selected_objective_score": 26390.0}

        def fake_c_solve(instance, output_dir, scenario, **kwargs):
            nonlocal calls
            calls += 1
            _copy_submission(heuristic if calls == 1 else verification, Path(output_dir))
            evaluation = evaluate_submission(instance, output_dir, scenario)
            return SolveTelemetry(
                formulation=kwargs["separator_mode"],
                status="FEASIBLE_SAFE_INCUMBENT",
                objective_score=evaluation.objective_score,
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
        ):
            output = Path(temp_dir) / "submission"
            report = solve_staged_c_portfolio(
                instance,
                output,
                audit_output_dir=Path(temp_dir) / "audit",
                a_local_repair_time_limit_seconds=0.0,
                c_heuristic_attempts=1,
                workers=1,
                forbid_buffer_overlap=True,
            )
            final = evaluate_submission(instance, output, "C")
            independent = independently_score(data, output)
        self.assertEqual(calls, 2)
        self.assertTrue(report["scenario_c_postselection_compaction_promoted"])
        self.assertEqual(
            report["scenario_c_postselection_compaction"]["source_score"],
            23660.0,
        )
        self.assertEqual(
            report["scenario_c_postselection_compaction"]["selected_score"],
            22760.0,
        )
        self.assertEqual(
            report["selected_stage"],
            "scenario_c_postselection_eclo_compaction",
        )
        self.assertEqual(final.objective_score, 22760.0)
        self.assertEqual(independent.objective_score, 22760.0)

    def test_final_postprocessor_preserves_official_c_hash(self) -> None:
        source = ROOT / "deliverables" / "public" / "C"
        expected = evaluate_submission(self.instance, source, "C")
        with tempfile.TemporaryDirectory() as temporary:
            selected_dir, selected, report = best_checked_c_postprocessing_sequence(
                self.instance,
                source,
                Path(temporary),
                forbid_buffer_overlap=True,
            )
        self.assertEqual(selected_dir, source)
        self.assertFalse(report["strict_improvement"])
        self.assertEqual(selected.objective_score, 62.7)
        self.assertEqual(selected.submission_hash, expected.submission_hash)

    def test_final_postprocessor_retained_c_audit_is_hash_safe(self) -> None:
        audit = json.loads(
            (
                ROOT / "runs" / "postselection_compaction_retained_c_audit.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(audit["case_count"], 19)
        self.assertEqual(audit["promoted_count"], 0)
        self.assertEqual(audit["hash_changed_count"], 0)
        self.assertEqual(audit["total_idle_candidates_checked"], 3)
        self.assertEqual(audit["total_eclo_candidates_checked"], 0)
        public = next(case for case in audit["cases"] if case["case"] == "public_C")
        self.assertEqual(public["source_score"], 62.7)
        self.assertEqual(public["selected_score"], 62.7)
        self.assertFalse(public["hash_changed"])
        self.assertEqual(public["strict_conflicts"], 0)

    def test_benchmark_matrix_matches_recomputed_scores_and_feasibility(self) -> None:
        matrix = json.loads((ROOT / "BENCHMARK_MATRIX.json").read_text(encoding="utf-8"))
        self.assertEqual(matrix["schema_version"], 1)
        self.assertEqual(len(matrix["cases"]), 46)
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
            elif row["case"].startswith("independent_three_line_"):
                data = ROOT / "fixtures" / "independent_three_line_v1"
                submission = (
                    ROOT
                    / "runs"
                    / f"independent_three_line_v1_{row['scenario'].lower()}"
                )
            elif row["case"].startswith("independent_multi_bridge_"):
                if row["case"].startswith("independent_multi_bridge_scale_"):
                    fixture = "independent_multi_bridge_scale_v1"
                elif row["case"].startswith("independent_multi_bridge_congestion_"):
                    fixture = "independent_multi_bridge_congestion_v1"
                else:
                    fixture = "independent_multi_bridge_v1"
                data = ROOT / "fixtures" / fixture
                submission = ROOT / "runs" / (
                    "independent_multi_bridge_scale_v1_c_compact_t003"
                    if row["case"] == "independent_multi_bridge_scale_C"
                    else f"{fixture}_{row['scenario'].lower()}"
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
            elif row["case"] == "independent_post_precedence_contract_C":
                data = ROOT / "fixtures" / "independent_post_precedence_contract_v1"
                submission = ROOT / "runs" / "c_postprecedence_contract_targeted_repair"
            elif row["case"] == "independent_post_contract_precedence_C":
                data = ROOT / "fixtures" / "independent_post_contract_precedence_v1"
                submission = ROOT / "runs" / "c_postcontract_precedence_final_repair"
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

    def test_eclo_compaction_retained_c_audit_has_no_false_improvement(self) -> None:
        audit = json.loads(
            (ROOT / "runs" / "eclo_compaction_retained_c_audit.json").read_text(
                encoding="utf-8"
            )
        )
        matrix = json.loads((ROOT / "BENCHMARK_MATRIX.json").read_text(encoding="utf-8"))
        retained_c = [row for row in matrix["cases"] if row["scenario"] == "C"]
        self.assertEqual(audit["case_count"], len(retained_c))
        self.assertEqual(audit["case_count"], 19)
        self.assertEqual(audit["applicable_count"], 2)
        self.assertEqual(audit["improved_count"], 0)
        self.assertEqual(audit["total_candidates_checked"], 0)
        self.assertEqual(audit["total_duplicate_candidates_skipped"], 0)
        self.assertEqual(
            audit["total_candidates_skipped_existing_eclo_window"], 7
        )
        self.assertEqual(
            {record["case"] for record in audit["cases"]},
            {row["case"] for row in retained_c},
        )
        self.assertTrue(
            all(record["selected_score"] is None for record in audit["cases"])
        )

    def test_eclo_compaction_score_order_matches_120_job_exhaustive_audit(
        self,
    ) -> None:
        benchmark = json.loads(
            (ROOT / "runs" / "eclo_compaction_scale_benchmark.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(benchmark["activity_count"], 120)
        self.assertEqual(benchmark["horizon_weeks"], 360)
        by_name = {record["case"]: record for record in benchmark["cases"]}
        floor = by_name["zero_score_floor"]
        ranked = by_name["reverse_positive_score"]
        exhaustive = by_name["reverse_positive_score_exhaustive"]
        self.assertEqual(floor["source_score"], 0.0)
        self.assertEqual(floor["candidates_checked"], 0)
        self.assertFalse(floor["selected"])
        self.assertEqual(ranked["unique_candidates_ranked"], 120)
        self.assertEqual(ranked["candidates_checked"], 1)
        self.assertEqual(ranked["candidates_pruned_by_exact_score_order"], 119)
        self.assertEqual(exhaustive["candidates_checked"], 120)
        self.assertEqual(exhaustive["score_prediction_mismatches"], 0)
        self.assertEqual(ranked["selected_score"], exhaustive["selected_score"])
        self.assertEqual(ranked["minimum_candidate_score"], 2864830.0)
        self.assertEqual(ranked["source_score"], 2880360.0)

    def test_final_postprocessing_is_safe_on_120_job_scale_audit(self) -> None:
        benchmark = json.loads(
            (
                ROOT / "runs" / "postselection_compaction_scale_benchmark.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(benchmark["activity_count"], 120)
        self.assertEqual(benchmark["horizon_weeks"], 360)
        by_name = {record["case"]: record for record in benchmark["cases"]}
        floor = by_name["zero_score_floor"]
        self.assertEqual(floor["source_score"], 0.0)
        self.assertEqual(floor["selected_score"], 0.0)
        self.assertFalse(floor["strict_improvement"])
        self.assertFalse(floor["hash_changed"])
        self.assertEqual(floor["idle_candidates_checked"], 0)
        self.assertEqual(floor["eclo_candidates_checked"], 0)
        reverse = by_name["reverse_positive_score"]
        self.assertEqual(reverse["source_score"], 2880360.0)
        self.assertEqual(reverse["selected_score"], 2864830.0)
        self.assertEqual(reverse["independent_score"], 2864830.0)
        self.assertEqual(reverse["score_change"], -15530.0)
        self.assertTrue(reverse["strict_improvement"])
        self.assertEqual(reverse["selected_stage"], "eclo_compaction")
        self.assertEqual(reverse["strict_conflicts"], 0)
        self.assertEqual(reverse["idle_candidates_checked"], 0)
        self.assertEqual(reverse["eclo_candidates_checked"], 1)
        self.assertEqual(
            reverse["eclo_candidates_pruned_by_exact_score_order"], 119
        )

    def test_final_postprocessing_handles_59_idle_gaps_at_scale(self) -> None:
        benchmark = json.loads(
            (ROOT / "runs" / "idle_compaction_scale_benchmark.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(benchmark["activity_count"], 60)
        self.assertEqual(benchmark["horizon_weeks"], 240)
        self.assertEqual(benchmark["initial_gap_count"], 59)
        self.assertEqual(benchmark["idle_promotions"], 59)
        self.assertEqual(benchmark["idle_candidates_checked"], 59)
        self.assertEqual(benchmark["idle_prediction_mismatches"], 0)
        self.assertEqual(benchmark["eclo_promotions"], 1)
        self.assertEqual(benchmark["eclo_candidates_checked"], 1)
        self.assertEqual(benchmark["source_score"], 1116689.0)
        self.assertEqual(benchmark["selected_score"], 733120.0)
        self.assertEqual(benchmark["independent_score"], 733120.0)
        self.assertEqual(benchmark["score_change"], -383569.0)
        self.assertEqual(benchmark["selected_stage"], "eclo_compaction")
        self.assertEqual(benchmark["strict_conflicts"], 0)

    def test_eclo_compaction_score_order_matches_contract_aggregation_audit(
        self,
    ) -> None:
        audit = json.loads(
            (ROOT / "runs" / "eclo_contract_aggregation_audit.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(audit["contract_count"], 3)
        self.assertEqual(audit["activity_count"], 6)
        self.assertEqual(audit["source_score"], 23765.0)
        self.assertEqual(audit["source_independent_score"], 23765.0)
        self.assertEqual(audit["source_hard_violations"], [])
        self.assertEqual(audit["source_strict_conflicts"], 0)
        ranked = audit["ranked"]
        exhaustive = audit["exhaustive"]
        self.assertEqual(ranked["unique_candidates_ranked"], 6)
        self.assertEqual(ranked["candidates_checked"], 1)
        self.assertEqual(ranked["candidates_pruned_by_exact_score_order"], 5)
        self.assertEqual(exhaustive["candidates_checked"], 6)
        self.assertEqual(exhaustive["duplicate_candidates_skipped"], 12)
        self.assertEqual(exhaustive["score_prediction_mismatches"], 0)
        self.assertTrue(
            all(candidate["matches"] for candidate in exhaustive["candidate_scores"])
        )
        self.assertEqual(ranked["selected_score"], 21990.0)
        self.assertEqual(ranked["selected_score"], exhaustive["selected_score"])
        self.assertEqual(
            ranked["selected_submission_hash"],
            exhaustive["selected_submission_hash"],
        )
        self.assertEqual(ranked["independent_score"], ranked["selected_score"])
        self.assertEqual(exhaustive["strict_conflicts"], 0)

    def test_eclo_compaction_prediction_includes_zero_supply_excess(self) -> None:
        source_data = ROOT / "fixtures" / "independent_eclo_multipass_v1"
        source_submission = ROOT / "fixtures" / "independent_eclo_multipass_v1_source_c"
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            data = root / "data"
            shutil.copytree(source_data, data)
            supply_path = data / "04_LOCATION_SUPPLY.csv"
            with supply_path.open(newline="", encoding="utf-8") as handle:
                supply_rows = list(csv.DictReader(handle))
                fieldnames = list(supply_rows[0])
            target_location = "PLAT:MPX:MPX1:EB"
            for row in supply_rows:
                if row["location_id"] == target_location:
                    row["supply_capacity"] = "0"
                    break
            else:
                self.fail(f"missing zero-supply mutation target {target_location}")
            with supply_path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(supply_rows)

            instance = load_instance(data)
            source = evaluate_submission(instance, source_submission, "C")
            ranked_dir, ranked, ranked_report = best_single_lane_eclo_compaction(
                instance,
                source_submission,
                root / "ranked",
                forbid_buffer_overlap=True,
            )
            exhaustive_dir, exhaustive, exhaustive_report = best_single_lane_eclo_compaction(
                instance,
                source_submission,
                root / "exhaustive",
                forbid_buffer_overlap=True,
                exhaustive=True,
            )
            self.assertIsNotNone(ranked_dir)
            self.assertIsNotNone(exhaustive_dir)
            self.assertIsNotNone(ranked)
            self.assertIsNotNone(exhaustive)
            self.assertEqual(source.excess_access_nights_total, 6)
            self.assertEqual(ranked_report["score_prediction_mismatches"], 0)
            self.assertEqual(exhaustive_report["score_prediction_mismatches"], 0)
            self.assertEqual(ranked.objective_score, exhaustive.objective_score)
            self.assertEqual(ranked.submission_hash, exhaustive.submission_hash)

    def test_eclo_window_filter_matches_unfiltered_sequence_enumeration(
        self,
    ) -> None:
        audit = json.loads(
            (ROOT / "runs" / "eclo_filter_falsification.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(audit["permutation_count"], 24)
        self.assertTrue(audit["all_ranked_scores_match_exhaustive"])
        self.assertEqual(
            audit["total_unique_candidates_filtered_by_window"], 288
        )
        self.assertEqual(audit["total_feasible_candidates_filtered_by_window"], 0)
        self.assertTrue(
            all(
                record["score_matches_exhaustive"]
                and record["feasible_candidates_filtered_by_window"] == 0
                for record in audit["permutations"]
            )
        )
        long_access = audit["long_access_case"]
        self.assertEqual(long_access["permutation_count"], 24)
        self.assertTrue(long_access["all_ranked_scores_match_exhaustive"])
        self.assertEqual(
            long_access["total_unique_candidates_filtered_by_window"], 1920
        )
        self.assertEqual(
            long_access["total_feasible_candidates_filtered_by_window"], 0
        )
        live = audit["live_cross_line_case"]
        self.assertEqual(live["source_score"], 262.0)
        self.assertEqual(live["best_score"], 262.0)
        self.assertEqual(live["unique_candidates_filtered_by_window"], 7)
        self.assertEqual(live["feasible_candidates_filtered_by_window"], 0)

    def test_eclo_compaction_generalizes_to_four_standard_accesses(self) -> None:
        audit = json.loads(
            (ROOT / "runs" / "eclo_long_access_audit.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(audit["activity_count"], 4)
        self.assertEqual(audit["line_count"], 2)
        self.assertEqual(audit["total_accesses_per_activity"], [4])
        self.assertEqual(audit["source_score"], 32760.0)
        self.assertEqual(audit["source_independent_score"], 32760.0)
        self.assertEqual(audit["source_hard_violations"], [])
        ranked = audit["ranked"]
        exhaustive = audit["exhaustive"]
        self.assertEqual(ranked["promotions"], 2)
        self.assertEqual(ranked["candidates_checked"], 2)
        self.assertEqual(ranked["candidates_pruned_by_exact_score_order"], 10)
        self.assertEqual(exhaustive["candidates_checked"], 12)
        self.assertEqual(exhaustive["score_prediction_mismatches"], 0)
        self.assertEqual(ranked["selected_score"], 27320.0)
        self.assertEqual(ranked["selected_score"], exhaustive["selected_score"])
        self.assertEqual(
            ranked["selected_submission_hash"],
            exhaustive["selected_submission_hash"],
        )
        self.assertEqual(ranked["independent_score"], ranked["selected_score"])
        self.assertEqual(exhaustive["strict_conflicts"], 0)

    def test_eclo_compaction_access_length_sweep_matches_exhaustive(self) -> None:
        audit = json.loads(
            (ROOT / "runs" / "eclo_access_length_sweep.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(audit["access_counts"], [3, 4, 5, 6, 7])
        self.assertTrue(audit["all_scores_match"])
        self.assertTrue(audit["all_hashes_match"])
        self.assertEqual(audit["total_prediction_mismatches"], 0)
        for case in audit["cases"]:
            ranked = case["ranked"]
            exhaustive = case["exhaustive"]
            self.assertEqual(ranked["promotions"], 2)
            self.assertEqual(ranked["candidates_checked"], 2)
            self.assertEqual(ranked["selected_score"], exhaustive["selected_score"])
            self.assertEqual(
                ranked["selected_submission_hash"],
                exhaustive["selected_submission_hash"],
            )
            self.assertEqual(
                exhaustive["independent_score"], exhaustive["selected_score"]
            )
            self.assertEqual(exhaustive["strict_conflicts"], 0)

    def test_idle_week_compaction_unlocks_checked_eclo_sequence(self) -> None:
        audit = json.loads(
            (ROOT / "runs" / "idle_week_compaction_audit.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(audit["source_score"], 26390.0)
        self.assertEqual(audit["source_independent_score"], 26390.0)
        self.assertEqual(audit["idle_score"], 23660.0)
        self.assertEqual(audit["idle_report"]["promotions"], 1)
        self.assertEqual(audit["idle_report"]["candidates_checked"], 1)
        self.assertEqual(audit["idle_report"]["score_prediction_mismatches"], 0)
        self.assertEqual(audit["final_score"], 18220.0)
        self.assertEqual(audit["final_independent_score"], 18220.0)
        self.assertEqual(audit["final_strict_conflicts"], 0)
        self.assertEqual(audit["eclo_promotions"], 2)
        self.assertEqual(audit["retained_case_count"], 19)
        self.assertEqual(audit["retained_promoted_count"], 0)
        self.assertEqual(audit["retained_total_initial_gaps"], 9)
        self.assertEqual(audit["retained_total_candidates_checked"], 3)
        unlock = audit["equal_score_unlock"]
        self.assertEqual(unlock["source_score"], 910.0)
        self.assertEqual(unlock["idle_score"], 910.0)
        self.assertFalse(unlock["idle_report"]["strict_improvement"])
        self.assertEqual(unlock["final_score"], 10.0)
        self.assertEqual(unlock["final_independent_score"], 10.0)
        self.assertEqual(unlock["final_strict_conflicts"], 0)
        self.assertEqual(unlock["eclo_promotions"], 1)
        leading = audit["leading_idle"]
        self.assertEqual(leading["source_score"], 27300.0)
        self.assertEqual(leading["idle_score"], 23660.0)
        self.assertTrue(leading["idle_report"]["strict_improvement"])
        self.assertEqual(leading["final_score"], 18220.0)
        self.assertEqual(leading["final_independent_score"], 18220.0)
        self.assertEqual(leading["final_strict_conflicts"], 0)
        self.assertEqual(leading["eclo_promotions"], 2)
        tie = audit["equal_score_gap_tie"]
        self.assertEqual(tie["source_score"], 2730.0)
        self.assertEqual(tie["idle_score"], 1820.0)
        self.assertEqual(tie["idle_report"]["rounds"][0]["selected_gap_week"], 5)
        self.assertEqual(tie["final_score"], 920.0)
        self.assertEqual(tie["final_independent_score"], 920.0)
        self.assertEqual(tie["final_strict_conflicts"], 0)
        self.assertEqual(tie["eclo_promotions"], 1)

    def test_idle_gap_tie_prioritizes_internal_eclo_unlock(self) -> None:
        data = ROOT / "fixtures" / "independent_idle_tie_v1"
        source = ROOT / "fixtures" / "independent_idle_tie_v1_source_c"
        instance = load_instance(data)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            idle_dir, idle, idle_report = best_idle_week_compaction_sequence(
                instance,
                source,
                root / "idle",
                forbid_buffer_overlap=True,
                allow_equal=True,
            )
            self.assertIsNotNone(idle_dir)
            self.assertIsNotNone(idle)
            self.assertEqual(idle_report["rounds"][0]["selected_gap_week"], 5)
            self.assertEqual(idle.objective_score, 1820.0)
            final_dir, final, _ = best_serialized_eclo_compaction_sequence(
                instance,
                idle_dir,
                root / "eclo",
                forbid_buffer_overlap=True,
            )
            self.assertIsNotNone(final_dir)
            self.assertIsNotNone(final)
            self.assertEqual(final.objective_score, 920.0)
            self.assertEqual(independently_score(data, final_dir).objective_score, 920.0)

    def test_idle_gap_tie_stays_internal_after_prediction_mismatch(self) -> None:
        data = ROOT / "fixtures" / "independent_idle_tie_v1"
        source = ROOT / "fixtures" / "independent_idle_tie_v1_source_c"
        instance = load_instance(data)
        with tempfile.TemporaryDirectory() as temporary, patch(
            "nebula_ps1.idle_compact._predicted_objective",
            side_effect=lambda _instance, _access, gap_week, **_kwargs: (
                0.0 if gap_week == 1 else 1.0
            ),
        ):
            idle_dir, idle, report = best_idle_week_compaction_sequence(
                instance,
                source,
                Path(temporary) / "idle",
                forbid_buffer_overlap=True,
                allow_equal=True,
            )
        self.assertIsNotNone(idle_dir)
        self.assertIsNotNone(idle)
        self.assertTrue(report["score_prediction_untrusted"])
        self.assertGreater(report["score_prediction_mismatches"], 0)
        self.assertEqual(report["rounds"][0]["selected_gap_week"], 5)
        self.assertEqual(idle.objective_score, 1820.0)

    def test_idle_prediction_uses_confirmed_scenario_c_excess_weight(self) -> None:
        data = ROOT / "fixtures" / "independent_irregular_partial_v1"
        source = (
            ROOT
            / "runs"
            / "independent_irregular_partial_v1_guarded_independent_c120_costrepair_w8"
        )
        instance = load_instance(data)
        evaluation = evaluate_submission(instance, source, "C")
        access, _, _ = load_submission(source)
        self.assertEqual(evaluation.excess_access_nights_total, 3)
        predicted = predict_idle_compaction_objective(
            instance,
            access,
            max(row.week for row in access),
            excess_total=evaluation.excess_access_nights_total,
            eclo_total=evaluation.eclo_nights_total,
        )
        self.assertEqual(predicted, evaluation.objective_score)
        self.assertEqual(predicted, 31.0)

    def test_idle_gap_greedy_search_matches_exhaustive_composition(self) -> None:
        audit = json.loads(
            (ROOT / "runs" / "idle_gap_search_audit.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(audit["case_count"], 16)
        self.assertEqual(audit["score_match_count"], 16)
        self.assertEqual(audit["mismatch_count"], 0)
        for case in audit["cases"]:
            self.assertTrue(case["score_matches"])
            self.assertEqual(case["greedy_score"], case["exhaustive"]["score"])
            self.assertEqual(
                case["greedy_independent_score"], case["greedy_score"]
            )
            self.assertEqual(
                case["exhaustive"]["independent_score"],
                case["exhaustive"]["score"],
            )

    def test_multiline_idle_branching_matches_full_normalization_graph(self) -> None:
        audit = json.loads(
            (ROOT / "runs" / "multiline_idle_branching_audit.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(audit["case_count"], 256)
        self.assertEqual(audit["score_match_count"], 256)
        self.assertEqual(audit["mismatch_count"], 0)
        self.assertEqual(audit["mismatches"], [])
        self.assertEqual(audit["max_reachable_normalization_states"], 16)

    def test_constrained_idle_branching_matches_full_normalization_graph(self) -> None:
        audit = json.loads(
            (ROOT / "runs" / "constrained_idle_branching_audit.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(audit["variant_count"], 3)
        self.assertEqual(audit["case_count"], 768)
        self.assertEqual(audit["score_match_count"], 768)
        self.assertEqual(audit["mismatch_count"], 0)
        self.assertEqual(
            {row["variant"] for row in audit["variants"]},
            {"staggered_starts", "precedence_chain", "staggered_chain"},
        )
        self.assertTrue(
            all(row["mismatch_examples"] == [] for row in audit["variants"])
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

    def test_scale_optimizations_preserve_360_activity_results(self) -> None:
        data = ROOT / "fixtures" / "independent_scaled_m40"
        instance = load_instance(data)
        baseline = json.loads(
            (
                ROOT
                / "runs"
                / "independent_scaled_m40_seed1_w1"
                / "SEED_MATRIX.json"
            ).read_text(encoding="utf-8")
        )
        optimized = json.loads(
            (
                ROOT
                / "runs"
                / "independent_scaled_m40_seed1_w1_weeklocal"
                / "SEED_MATRIX.json"
            ).read_text(encoding="utf-8")
        )
        cached = json.loads(
            (
                ROOT
                / "runs"
                / "independent_scaled_m40_seed3_w1_footprint_cache"
                / "SEED_MATRIX.json"
            ).read_text(encoding="utf-8")
        )
        current = json.loads(
            (
                ROOT
                / "runs"
                / "independent_scaled_m40_post_checked_hint_seed5_w1"
                / "SEED_MATRIX.json"
            ).read_text(encoding="utf-8")
        )

        self.assertEqual(baseline["dataset_hash"], optimized["dataset_hash"])
        self.assertEqual(baseline["policy"], optimized["policy"])
        self.assertEqual(optimized["dataset_hash"], cached["dataset_hash"])
        self.assertEqual(optimized["policy"], cached["policy"])
        self.assertEqual(cached["dataset_hash"], current["dataset_hash"])
        self.assertEqual(cached["policy"], current["policy"])
        self.assertEqual(baseline["successes"], 3)
        self.assertEqual(optimized["successes"], 3)
        self.assertEqual(cached["successes"], 3)
        self.assertEqual(current["successes"], 3)
        self.assertEqual(baseline["failures"], 0)
        self.assertEqual(optimized["failures"], 0)
        self.assertEqual(cached["failures"], 0)
        self.assertEqual(current["failures"], 0)

        baseline_runs = {row["scenario"]: row for row in baseline["runs"]}
        optimized_runs = {row["scenario"]: row for row in optimized["runs"]}
        cached_runs = {row["scenario"]: row for row in cached["runs"]}
        current_runs = {row["scenario"]: row for row in current["runs"]}
        self.assertEqual(set(baseline_runs), {"A", "B", "C"})
        self.assertEqual(set(optimized_runs), {"A", "B", "C"})
        self.assertEqual(set(cached_runs), {"A", "B", "C"})
        self.assertEqual(set(current_runs), {"A", "B", "C"})
        self.assertEqual(
            {scenario: row["score"] for scenario, row in optimized_runs.items()},
            {"A": 280.0, "B": 400.0, "C": 280.0},
        )

        for scenario in ("A", "B", "C"):
            with self.subTest(scenario=scenario):
                before = baseline_runs[scenario]
                after = optimized_runs[scenario]
                after_cache = cached_runs[scenario]
                current_row = current_runs[scenario]
                for field in (
                    "status",
                    "score",
                    "selected_stage",
                    "strict_conflicts",
                    "submission_hash",
                ):
                    self.assertEqual(before[field], after[field])
                    self.assertEqual(after[field], after_cache[field])
                for field in ("status", "score", "selected_stage", "strict_conflicts"):
                    self.assertEqual(after_cache[field], current_row[field])
                self.assertEqual(after["status"], "SUCCESS")
                self.assertEqual(after["strict_conflicts"], 0)
                self.assertGreaterEqual(
                    before["wall_seconds"] / after["wall_seconds"], 5.0
                )
                self.assertGreaterEqual(
                    after["wall_seconds"] / after_cache["wall_seconds"], 3.0
                )

                submission = (
                    ROOT
                    / "runs"
                    / "independent_scaled_m40_post_checked_hint_seed5_w1"
                    / f"{scenario.lower()}_seed_5"
                )
                evaluation = evaluate_submission(
                    instance, submission, scenario=scenario
                )
                independent = independently_score(data, submission)
                self.assertEqual(evaluation.hard_violations, ())
                self.assertEqual(evaluation.objective_score, after["score"])
                self.assertEqual(independent.objective_score, after["score"])

    def test_720_activity_scale_holdout_succeeds_without_oracle_input(self) -> None:
        data = ROOT / "fixtures" / "independent_scaled_m80"
        oracle = ROOT / "fixtures" / "independent_scaled_m80_oracle"
        instance = load_instance(data)
        oracle_evaluation = evaluate_submission(instance, oracle, scenario="A")
        oracle_independent = independently_score(data, oracle)
        self.assertEqual(len(instance.projects), 640)
        self.assertEqual(len(instance.activities), 720)
        self.assertEqual(oracle_evaluation.hard_violations, ())
        self.assertEqual(oracle_evaluation.objective_score, 560.0)
        self.assertEqual(oracle_independent.objective_score, 560.0)

        matrix = json.loads(
            (
                ROOT
                / "runs"
                / "independent_scaled_m80_seed1_w1"
                / "SEED_MATRIX.json"
            ).read_text(encoding="utf-8")
        )
        current = json.loads(
            (
                ROOT
                / "runs"
                / "independent_scaled_m80_post_checked_hint_seed2_w1"
                / "SEED_MATRIX.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(matrix["dataset_hash"], instance.dataset_hash)
        self.assertEqual(matrix["successes"], 3)
        self.assertEqual(matrix["failures"], 0)
        self.assertEqual(matrix["dataset_hash"], current["dataset_hash"])
        self.assertEqual(matrix["policy"], current["policy"])
        self.assertEqual(current["successes"], 3)
        self.assertEqual(current["failures"], 0)
        historical_runs = {row["scenario"]: row for row in matrix["runs"]}
        runs = {row["scenario"]: row for row in current["runs"]}
        self.assertEqual(
            {scenario: row["score"] for scenario, row in runs.items()},
            {"A": 560.0, "B": 800.0, "C": 560.0},
        )
        self.assertEqual(
            historical_runs["A"]["selected_stage"], "bridge_safe_fallback"
        )
        self.assertEqual(runs["A"]["selected_stage"], "heuristic_incumbent")
        self.assertEqual(runs["B"]["selected_stage"], "heuristic_incumbent")
        self.assertEqual(runs["C"]["selected_stage"], "scenario_c_fallback")
        for scenario, row in runs.items():
            with self.subTest(scenario=scenario):
                self.assertEqual(row["status"], "SUCCESS")
                self.assertEqual(row["strict_conflicts"], 0)
                submission = (
                    ROOT
                    / "runs"
                    / "independent_scaled_m80_post_checked_hint_seed2_w1"
                    / f"{scenario.lower()}_seed_2"
                )
                evaluation = evaluate_submission(instance, submission, scenario)
                independent = independently_score(data, submission)
                self.assertEqual(evaluation.hard_violations, ())
                self.assertEqual(evaluation.objective_score, row["score"])
                self.assertEqual(independent.objective_score, row["score"])

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

    def test_checked_complete_hint_recovers_dense_scale_failure(self) -> None:
        data = ROOT / "fixtures" / "independent_dense_m20"
        instance = load_instance(data)
        failed = json.loads(
            (
                ROOT
                / "runs"
                / "independent_dense_m20_seed1_w1"
                / "SEED_MATRIX.json"
            ).read_text(encoding="utf-8")
        )
        recovered = json.loads(
            (
                ROOT
                / "runs"
                / "independent_dense_m20_hint_candidate_seed1_w1"
                / "SEED_MATRIX.json"
            ).read_text(encoding="utf-8")
        )
        zero_floor = json.loads(
            (
                ROOT
                / "runs"
                / "independent_dense_m20_zero_floor_seed1_w1"
                / "SEED_MATRIX.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(failed["dataset_hash"], recovered["dataset_hash"])
        self.assertEqual(failed["policy"], recovered["policy"])
        self.assertEqual(failed["successes"], 0)
        self.assertEqual(failed["failures"], 3)
        self.assertEqual(recovered["successes"], 3)
        self.assertEqual(recovered["failures"], 0)
        self.assertEqual(recovered["dataset_hash"], zero_floor["dataset_hash"])
        self.assertEqual(recovered["policy"], zero_floor["policy"])
        self.assertEqual(zero_floor["successes"], 3)
        self.assertEqual(zero_floor["failures"], 0)

        oracle_access, _, _ = load_submission(
            ROOT / "fixtures" / "independent_dense_m20_oracle"
        )
        oracle_keys = {
            (row.activity_id, row.week, row.eclo, row.access_night)
            for row in oracle_access
        }
        recovered_runs = {row["scenario"]: row for row in recovered["runs"]}
        for row in zero_floor["runs"]:
            scenario = row["scenario"]
            with self.subTest(scenario=scenario):
                prior = recovered_runs[scenario]
                for field in (
                    "status",
                    "score",
                    "strict_conflicts",
                    "selected_stage",
                    "submission_hash",
                ):
                    self.assertEqual(prior[field], row[field])
                self.assertGreaterEqual(
                    prior["wall_seconds"] / row["wall_seconds"], 1.5
                )
                self.assertEqual(row["score"], 0.0)
                self.assertEqual(row["strict_conflicts"], 0)
                submission = (
                    ROOT
                    / "runs"
                    / "independent_dense_m20_zero_floor_seed1_w1"
                    / f"{scenario.lower()}_seed_1"
                )
                evaluation = evaluate_submission(instance, submission, scenario)
                independent = independently_score(data, submission)
                access, _, _ = load_submission(submission)
                candidate_keys = {
                    (item.activity_id, item.week, item.eclo, item.access_night)
                    for item in access
                }
                self.assertEqual(evaluation.hard_violations, ())
                self.assertEqual(evaluation.objective_score, 0.0)
                self.assertEqual(independent.objective_score, 0.0)
                self.assertNotEqual(candidate_keys, oracle_keys)

    def test_invalid_complete_structural_hint_is_not_promoted(self) -> None:
        data = ROOT / "fixtures" / "independent_dense_v1"
        instance = load_instance(data)

        def corrupt_structural_candidate(
            checked_instance,
            output_dir,
            scenario,
            access_rows,
            occupancy_rows,
        ) -> None:
            rows = occupancy_rows
            if Path(output_dir).name.startswith("nebula-structural-hint-"):
                rows = occupancy_rows[:-1]
            _write_submission_rows(
                checked_instance,
                output_dir,
                scenario,
                access_rows,
                rows,
            )

        with tempfile.TemporaryDirectory() as temporary, patch(
            "nebula_ps1.flexible_solver._write_submission_rows",
            side_effect=corrupt_structural_candidate,
        ):
            output = Path(temporary) / "candidate"
            telemetry = solve_flexible_supply_relaxation(
                instance,
                output,
                "A",
                time_limit_seconds=1e-9,
                workers=1,
                closure_round_limit=1,
                separator_mode="direct_heuristic",
            )
            self.assertTrue(telemetry.structural_hint_complete)
            self.assertTrue(telemetry.structural_hint_checked)
            self.assertFalse(telemetry.structural_hint_feasible)
            self.assertIsNone(telemetry.structural_hint_objective_score)
            self.assertFalse(
                any((output / name).exists() for name in SUBMISSION_FILES)
            )

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
        self.assertEqual(
            _scenario_b_cost_contributing_activities(
                instance,
                incumbent,
                expand_footprints=True,
                expand_contracts=True,
                expand_precedence=True,
                revisit_precedence_after_footprints=True,
                revisit_contracts_after_precedence=True,
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
            revisit_contracts_after_precedence=True,
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
        self.assertEqual(
            _scenario_b_cost_contributing_activities(
                instance,
                incumbent,
                expand_footprints=True,
                expand_contracts=True,
                expand_precedence=True,
                revisit_precedence_after_footprints=True,
                revisit_contracts_after_precedence=True,
                include_delays=True,
            ),
            ["COMP", "DIRECT", "FOLLOW", "PEER"],
        )
    def test_irregular_two_tier_repair_matrix_is_dual_scored_and_clean(self) -> None:
        data = ROOT / "fixtures" / "independent_irregular_partial_v1"
        matrix_root = ROOT / "runs" / "c_two_tier_irregular_repair_seed_matrix5"
        matrix = json.loads((matrix_root / "REPAIR_MATRIX.json").read_text())
        instance = load_instance(data)
        self.assertEqual(len(matrix["records"]), 5)
        self.assertEqual({row["seed"] for row in matrix["records"]}, {1, 2, 3, 4, 5})
        hashes = set()
        for row in matrix["records"]:
            self.assertEqual(row["narrow"]["score"], 31.0)
            self.assertEqual(row["expanded"]["score"], 31.0)
            self.assertEqual(row["final"]["score"], 31.0)
            self.assertEqual(row["final"]["standard_conflicts"], 0)
            self.assertEqual(row["final"]["strict_conflicts"], 0)
            final = matrix_root / f"seed_{row['seed']}" / "final"
            evaluation = evaluate_submission(instance, final, "C")
            independent = independently_score(data, final)
            self.assertEqual(evaluation.hard_violations, ())
            self.assertEqual(evaluation.objective_score, 31.0)
            self.assertEqual(independent.objective_score, 31.0)
            hashes.add(evaluation.submission_hash)
        self.assertEqual(len(hashes), 5)

    def test_renamed_irregular_series_preserves_score_not_proof(self) -> None:
        cases = (
            ("", "baaf099eeb469ec74074bb11e116861fe569c6594caad619fee24a03bf3d5233", 147.0, 27, 0),
            ("_s2", "c2f9fc4e4fc0d1f16e3acbe5486555ec73888b373a0354fef4026f252e95e8be", 140.0, 52, 0),
            ("_s3", "b254b9ff508add4c777c96d20da017b19f9f47e856890feb9d42da9931570d49", 112.0, 27, 1),
        )
        hashes = set()
        for suffix, dataset_hash, construction_score, narrow_count, strict_count in cases:
            with self.subTest(suffix=suffix or "_s1"):
                data = ROOT / "fixtures" / f"independent_irregular_partial_v1_renamed{suffix}"
                submission = ROOT / "runs" / f"c_irregular_renamed{suffix}_seed5_production"
                report_path = submission.with_name(f"{submission.name}_audit") / "STAGED.json"
                instance = load_instance(data)
                evaluation = evaluate_submission(instance, submission, "C")
                independent = independently_score(data, submission)
                access, occupancy, _ = load_submission(submission)
                report = json.loads(report_path.read_text(encoding="utf-8"))

                self.assertEqual(instance.dataset_hash, dataset_hash)
                self.assertEqual(set(instance.lines), {"L01", "L02"})
                self.assertTrue(
                    all(activity_id.startswith("Z") for activity_id in instance.activities)
                )
                self.assertEqual(evaluation.hard_violations, ())
                self.assertEqual(evaluation.objective_score, 31.0)
                self.assertEqual(independent.objective_score, 31.0)
                self.assertEqual(evaluation.priority_weighted_score, 0.0)
                self.assertEqual(evaluation.eclo_nights_total, 2)
                self.assertEqual(evaluation.excess_access_nights_total, 3)
                self.assertEqual(screen_closures(instance, access, occupancy), ())
                self.assertEqual(
                    len(
                        screen_closures(
                            instance,
                            access,
                            occupancy,
                            forbid_buffer_overlap=True,
                        )
                    ),
                    strict_count,
                )
                self.assertEqual(report["selected_stage"], "bridge_safe_cost_repair")
                self.assertEqual(report["heuristic_telemetry"]["objective_score"], construction_score)
                self.assertEqual(len(report["bridge_safe_cost_repair_activities"]), narrow_count)
                self.assertEqual(len(report["bridge_safe_expanded_cost_repair_activities"]), 29)
                self.assertIsNone(report["bridge_safe_cost_repair_telemetry"]["best_bound"])
                self.assertFalse(
                    report["bridge_safe_cost_repair_telemetry"][
                        "primary_score_proven_optimal"
                    ]
                )
                hashes.add(evaluation.submission_hash)
        self.assertEqual(len(hashes), 3)

    def test_renamed_irregular_strict_hedge_preserves_score(self) -> None:
        data = ROOT / "fixtures" / "independent_irregular_partial_v1_renamed_s3"
        submission = ROOT / "runs" / "c_irregular_renamed_s3_strict_repair_pruned"
        telemetry_path = (
            ROOT / "runs" / "c_irregular_renamed_s3_strict_repair" / "TELEMETRY.json"
        )
        instance = load_instance(data)
        evaluation = evaluate_submission(instance, submission, "C")
        independent = independently_score(data, submission)
        access, occupancy, _ = load_submission(submission)
        telemetry = json.loads(telemetry_path.read_text(encoding="utf-8"))
        self.assertEqual(evaluation.hard_violations, ())
        self.assertEqual(evaluation.objective_score, 31.0)
        self.assertEqual(independent.objective_score, 31.0)
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
        self.assertEqual(telemetry["best_bound"], 31.0)
        self.assertEqual(telemetry["primary_bound_scope"], "frozen_access_neighborhood")
        self.assertEqual(
            _strict_conflict_repair_activities(
                instance,
                ROOT / "runs" / "c_irregular_renamed_s3_seed5_production",
            ),
            ["Z528", "Z572", "Z596"],
        )

    def test_strict_hedge_rejects_higher_score_clean_candidate(self) -> None:
        data = ROOT / "fixtures" / "independent_irregular_partial_v1_renamed_s3"
        source = ROOT / "runs" / "c_irregular_renamed_s3_seed5_production"
        higher = ROOT / "runs" / "c_irregular_renamed_s3_strict_higher112_pruned"
        instance = load_instance(data)
        selected = evaluate_submission(instance, source, "C")

        def fake_solve(instance, output_dir, scenario, **kwargs):
            _copy_submission(higher, Path(output_dir))
            return SolveTelemetry(
                formulation=kwargs["separator_mode"],
                status="OPTIMAL",
                objective_score=112.0,
                best_bound=112.0,
                wall_time_seconds=0.0,
                conflicts=0,
                branches=0,
                seed=kwargs["seed"],
                workers=1,
                time_limit_seconds=kwargs["time_limit_seconds"],
                model_variables=0,
                model_constraints=0,
                limitation="test fixture",
                remaining_closure_conflicts=0,
                primary_score_proven_optimal=True,
            )

        with tempfile.TemporaryDirectory() as temp_dir, patch(
            "nebula_ps1.staged.solve_flexible_supply_relaxation", side_effect=fake_solve
        ):
            (
                returned_dir,
                returned,
                conflicts_before,
                conflicts_after,
                activities,
                telemetry,
                prune_report,
                promoted,
            ) = _run_strict_score_preserving_hedge(
                instance,
                source,
                selected,
                "C",
                Path(temp_dir),
                time_limit_seconds=1.0,
                workers=1,
                seed=7,
                closure_round_limit=50,
            )
        self.assertFalse(promoted)
        self.assertEqual(returned_dir, source)
        self.assertEqual(returned.objective_score, 31.0)
        self.assertEqual(len(conflicts_before), 1)
        self.assertEqual(len(conflicts_after), 1)
        self.assertEqual(activities, ["Z528", "Z572", "Z596"])
        self.assertEqual(telemetry.objective_score, 112.0)
        self.assertEqual(prune_report.final_score, 112.0)

    def test_post_contract_precedence_holdout_is_frozen_before_repair(self) -> None:
        data = ROOT / "fixtures" / "independent_post_contract_precedence_v1"
        oracle = ROOT / "fixtures" / "independent_post_contract_precedence_v1_oracle"
        incumbent = ROOT / "fixtures/independent_post_contract_precedence_v1_incumbent"
        instance = load_instance(data)
        self.assertEqual(
            instance.dataset_hash,
            "ab66356785225b6b5ff03d5d9495c125ae8bc88c5067cfc774a039f3bc697996",
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
                revisit_contracts_after_precedence=True,
                include_delays=True,
            ),
            ["COMP", "DIRECT", "FOLLOW", "PEER"],
        )

        self.assertEqual(
            _scenario_b_cost_contributing_activities(
                instance,
                incumbent,
                expand_footprints=True,
                expand_contracts=True,
                expand_precedence=True,
                revisit_precedence_after_footprints=True,
                revisit_contracts_after_precedence=True,
                revisit_precedence_after_contracts=True,
                include_delays=True,
            ),
            ["COMP", "DIRECT", "FOLLOW", "PEER", "PREPEER"],
        )

    def test_final_precedence_repair_reaches_post_contract_oracle(self) -> None:
        data = ROOT / "fixtures" / "independent_post_contract_precedence_v1"
        source = ROOT / "fixtures/independent_post_contract_precedence_v1_incumbent"
        instance = load_instance(data)
        free = _scenario_b_cost_contributing_activities(
            instance,
            source,
            expand_footprints=True,
            expand_contracts=True,
            expand_precedence=True,
            revisit_precedence_after_footprints=True,
            revisit_contracts_after_precedence=True,
            revisit_precedence_after_contracts=True,
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
        self.assertTrue(telemetry.primary_score_proven_optimal)
        self.assertEqual(telemetry.primary_bound_scope, "frozen_access_neighborhood")
        self.assertEqual(telemetry.best_bound, 0.0)
        self.assertEqual(evaluation.hard_violations, ())
        self.assertEqual(evaluation.objective_score, 0.0)
        self.assertEqual(independent.objective_score, 0.0)

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

    def test_shared_production_objective_matches_independent_score(self) -> None:
        self.assertEqual(CONTRACT_WEIGHT, {1: 100.0, 2: 10.0, 3: 1.0})
        self.assertEqual(ACTIVITY_NUDGE, {1: 0.3, 2: 0.2, 3: 0.0})
        self.assertEqual((EXCESS_COST, ECLO_COST), (7.0, 5.0))
        self.assertEqual(
            (EXCESS_COST_TENTHS, ECLO_COST_TENTHS), (70, 50)
        )
        source = ROOT / "deliverables" / "public" / "A"
        evaluation = evaluate_submission(self.instance, source, "A")
        independent = independently_score(PACK / "01_data", source)
        access, _, _ = load_submission(source)
        completion_by_contract: dict[str, int] = {}
        for row in access:
            contract = self.instance.activities[row.activity_id].contract_number
            completion_by_contract[contract] = max(
                completion_by_contract.get(contract, 0), row.week
            )
        shared_delay = delay_score_from_completion_weeks(
            self.instance, completion_by_contract
        )
        self.assertEqual(shared_delay, evaluation.priority_weighted_score)
        self.assertEqual(shared_delay, independent.priority_weighted_delay)
        for contract in self.instance.projects:
            self.assertEqual(
                contract_costs_tenths(self.instance, contract),
                _contract_costs(self.instance, contract),
            )
        incomplete = dict(completion_by_contract)
        incomplete.pop(next(iter(incomplete)))
        with self.assertRaisesRegex(ValueError, "contract completion mapping mismatch"):
            delay_score_from_completion_weeks(self.instance, incomplete)

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

    def test_incremental_closure_acceptance_equals_affected_week_screen(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            with zipfile.ZipFile(
                ROOT / "deliverables" / "validator" / "A.zip"
            ) as archive:
                archive.extractall(temp_dir)
            access, occupancy, _ = load_submission(temp_dir)

        access_by_occurrence = {
            (row.activity_id, row.week): row for row in access
        }
        self.assertEqual(len(access_by_occurrence), len(access))
        occupancy_by_occurrence = defaultdict(list)
        for row in occupancy:
            occupancy_by_occurrence[(row.activity_id, row.week)].append(row)

        occurrences = sorted(access_by_occurrence)
        orders = (
            occurrences,
            list(reversed(occurrences)),
            sorted(
                occurrences,
                key=lambda item: hashlib.sha256(
                    f"{item[0]}:{item[1]}".encode()
                ).hexdigest(),
            ),
        )
        for forbid_buffer_overlap in (False, True):
            for order_index, order in enumerate(orders):
                with self.subTest(
                    forbid_buffer_overlap=forbid_buffer_overlap,
                    order=order_index,
                ):
                    provisional_access = []
                    provisional_occupancy = []
                    rejected = 0
                    for occurrence in order:
                        candidate_access = access_by_occurrence[occurrence]
                        candidate_occupancy = occupancy_by_occurrence[occurrence]
                        week = candidate_access.week
                        full_conflicts = screen_closures(
                            self.instance,
                            [*provisional_access, candidate_access],
                            [*provisional_occupancy, *candidate_occupancy],
                            forbid_buffer_overlap=forbid_buffer_overlap,
                        )
                        week_conflicts = screen_closures(
                            self.instance,
                            [
                                *(row for row in provisional_access if row.week == week),
                                candidate_access,
                            ],
                            [
                                *(
                                    row
                                    for row in provisional_occupancy
                                    if row.week == week
                                ),
                                *candidate_occupancy,
                            ],
                            forbid_buffer_overlap=forbid_buffer_overlap,
                        )
                        self.assertEqual(full_conflicts, week_conflicts)
                        if full_conflicts:
                            rejected += 1
                            continue
                        provisional_access.append(candidate_access)
                        provisional_occupancy.extend(candidate_occupancy)
                    self.assertGreater(rejected, 0)

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
            revisit_contracts_after_precedence=True,
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

    def test_public_boundary_mutations_pin_core_constraint_thresholds(self) -> None:
        def evaluate_mutation(
            scenario: str,
            mutate_access=None,
            mutate_occupancy=None,
        ):
            source = ROOT / "deliverables" / "public" / scenario
            temporary = tempfile.TemporaryDirectory()
            self.addCleanup(temporary.cleanup)
            copied = Path(temporary.name)
            for name in SUBMISSION_FILES:
                shutil.copy(source / name, copied / name)
            for filename, mutation in (
                ("SCHEDULE_ACCESS.csv", mutate_access),
                ("SCHEDULE_OCCUPANCY.csv", mutate_occupancy),
            ):
                if mutation is None:
                    continue
                path = copied / filename
                with path.open(newline="", encoding="utf-8") as handle:
                    rows = list(csv.DictReader(handle))
                    fieldnames = list(rows[0])
                mutation(rows)
                with path.open("w", newline="", encoding="utf-8") as handle:
                    writer = csv.DictWriter(handle, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(rows)
            return evaluate_submission(self.instance, copied, scenario=scenario)

        def merge_five_c(rows) -> None:
            for row in rows:
                if (
                    row["week"] == "14"
                    and row["location_id"] == "PLAT:BET:S16:EB"
                ):
                    row["co_share_group"] = "g1"

        five_c = evaluate_mutation("A", mutate_occupancy=merge_five_c)
        self.assertTrue(
            any("illegal mix PM=0 PC=0 C=5" in item for item in five_c.hard_violations),
            five_c.hard_violations,
        )

        def merge_pc_plus_four_c(rows) -> None:
            for row in rows:
                if (
                    row["week"] == "15"
                    and row["location_id"] == "PLAT:BET:S15:EB"
                ):
                    row["co_share_group"] = "g2"

        pc_plus_four_c = evaluate_mutation("A", mutate_occupancy=merge_pc_plus_four_c)
        self.assertTrue(
            any(
                "illegal mix PM=0 PC=1 C=4" in item
                for item in pc_plus_four_c.hard_violations
            ),
            pc_plus_four_c.hard_violations,
        )

        def split_c_capacity(rows, third_group: bool) -> None:
            target = [
                row
                for row in rows
                if row["week"] == "20"
                and row["location_id"] == "PLAT:BET:H02:EB"
            ]
            target[0]["co_share_group"] = "capacity-g2"
            if third_group:
                target[1]["co_share_group"] = "capacity-g3"

        c_plus_one = evaluate_mutation(
            "C", mutate_occupancy=lambda rows: split_c_capacity(rows, False)
        )
        self.assertEqual(c_plus_one.excess_access_nights_total, 1)
        self.assertFalse(
            any("Scenario C capacity exceeded" in item for item in c_plus_one.hard_violations),
            c_plus_one.hard_violations,
        )
        c_plus_two = evaluate_mutation(
            "C", mutate_occupancy=lambda rows: split_c_capacity(rows, True)
        )
        self.assertEqual(c_plus_two.excess_access_nights_total, 2)
        self.assertTrue(
            any("Scenario C capacity exceeded by 2" in item for item in c_plus_two.hard_violations),
            c_plus_two.hard_violations,
        )

        def split_a_capacity(rows) -> None:
            target = [
                row
                for row in rows
                if row["week"] == "23"
                and row["location_id"] == "PLAT:BET:H02:EB"
            ]
            target[0]["co_share_group"] = "capacity-g2"

        a_plus_one = evaluate_mutation("A", mutate_occupancy=split_a_capacity)
        self.assertEqual(a_plus_one.excess_access_nights_total, 1)
        self.assertTrue(
            any("Scenario A capacity exceeded by 1" in item for item in a_plus_one.hard_violations),
            a_plus_one.hard_violations,
        )

        def split_b_capacity(rows) -> None:
            target = [
                row
                for row in rows
                if row["week"] == "25"
                and row["location_id"] == "PLAT:BET:H01:EB"
            ]
            for index, row in enumerate(target, 1):
                row["co_share_group"] = f"capacity-g{index}"

        b_plus_three = evaluate_mutation("B", mutate_occupancy=split_b_capacity)
        self.assertEqual(b_plus_three.excess_access_nights_total, 3)
        self.assertFalse(
            any("Scenario B capacity exceeded" in item for item in b_plus_three.hard_violations),
            b_plus_three.hard_violations,
        )

        def remove_half_unit(rows) -> None:
            next(
                row
                for row in rows
                if row["activity_id"] == "A036" and row["eclo"] == "1"
            )["eclo"] = "0"

        insufficient = evaluate_mutation("B", mutate_access=remove_half_unit)
        self.assertTrue(
            any("A036: workload 13/2 below 14/2" in item for item in insufficient.hard_violations),
            insufficient.hard_violations,
        )

        def collapse_predecessor_gap_access(rows) -> None:
            next(
                row
                for row in rows
                if row["activity_id"] == "A004" and row["access_seq"] == "1"
            )["week"] = "18"

        def collapse_predecessor_gap_occupancy(rows) -> None:
            for row in rows:
                if row["activity_id"] == "A004" and row["week"] == "19":
                    row["week"] = "18"

        predecessor_overlap = evaluate_mutation(
            "B",
            mutate_access=collapse_predecessor_gap_access,
            mutate_occupancy=collapse_predecessor_gap_occupancy,
        )
        self.assertTrue(
            any(
                "A004: starts week 18 before predecessor A003 finishes" in item
                for item in predecessor_overlap.hard_violations
            ),
            predecessor_overlap.hard_violations,
        )

        def exceed_workfront(rows) -> None:
            next(
                row
                for row in rows
                if row["activity_id"] == "A013" and row["week"] == "23"
            )["access_night"] = "2"

        workfront = evaluate_mutation("A", mutate_access=exceed_workfront)
        self.assertTrue(
            any(
                "C002/Renewal week 23 night 2: workfront cap exceeded" in item
                for item in workfront.hard_violations
            ),
            workfront.hard_violations,
        )

        def exceed_allocation_index(rows) -> None:
            next(
                row
                for row in rows
                if row["activity_id"] == "A013" and row["week"] == "23"
            )["access_night"] = "4"

        allocation = evaluate_mutation("A", mutate_access=exceed_allocation_index)
        self.assertTrue(
            any("access_night 4 outside contract cap" in item for item in allocation.hard_violations),
            allocation.hard_violations,
        )

        def set_a_eclo(rows) -> None:
            rows[0]["eclo"] = "1"

        scenario_a_eclo = evaluate_mutation("A", mutate_access=set_a_eclo)
        self.assertIn("Scenario A forbids ECLO", scenario_a_eclo.hard_violations)

        def move_a003_before_start_access(rows) -> None:
            next(
                row
                for row in rows
                if row["activity_id"] == "A003" and row["week"] == "11"
            )["week"] = "10"

        def move_a003_before_start_occupancy(rows) -> None:
            for row in rows:
                if row["activity_id"] == "A003" and row["week"] == "11":
                    row["week"] = "10"

        early_start = evaluate_mutation(
            "A",
            mutate_access=move_a003_before_start_access,
            mutate_occupancy=move_a003_before_start_occupancy,
        )
        self.assertTrue(
            any("A003: starts in week 10 before week 11" in item for item in early_start.hard_violations),
            early_start.hard_violations,
        )

        def move_a075_outside_horizon_access(rows) -> None:
            next(row for row in rows if row["activity_id"] == "A075")["week"] = "31"

        def move_a075_outside_horizon_occupancy(rows) -> None:
            for row in rows:
                if row["activity_id"] == "A075":
                    row["week"] = "31"

        outside_horizon = evaluate_mutation(
            "A",
            mutate_access=move_a075_outside_horizon_access,
            mutate_occupancy=move_a075_outside_horizon_occupancy,
        )
        self.assertTrue(
            any("A075: week 31 outside horizon" in item for item in outside_horizon.hard_violations),
            outside_horizon.hard_violations,
        )

        def move_a001_past_b_deadline_access(rows) -> None:
            next(
                row
                for row in rows
                if row["activity_id"] == "A001" and row["week"] == "23"
            )["week"] = "24"

        def move_a001_past_b_deadline_occupancy(rows) -> None:
            for row in rows:
                if row["activity_id"] == "A001" and row["week"] == "23":
                    row["week"] = "24"

        scenario_b_late = evaluate_mutation(
            "B",
            mutate_access=move_a001_past_b_deadline_access,
            mutate_occupancy=move_a001_past_b_deadline_occupancy,
        )
        self.assertTrue(
            any(
                "A001: Scenario B planned completion exceeded" in item
                for item in scenario_b_late.hard_violations
            ),
            scenario_b_late.hard_violations,
        )

    def test_legal_mix_checker_matches_solver_inequalities_exhaustively(self) -> None:
        for pm in range(6):
            for pc in range(6):
                for coworkers in range(6):
                    if pm + pc + coworkers == 0:
                        continue
                    solver_accepts = (
                        pm <= 1
                        and pc <= 1
                        and coworkers <= 4 - pc
                        and pc + coworkers <= 4 * (1 - pm)
                    )
                    access_types = ["PM"] * pm + ["PC"] * pc + ["C"] * coworkers
                    self.assertEqual(
                        _legal_possession_mix(access_types),
                        solver_accepts,
                        (pm, pc, coworkers),
                    )

    def test_scenario_group_limits_match_capacity_policy_exhaustively(self) -> None:
        for supply in range(6):
            for candidates in range(11):
                with self.subTest(supply=supply, candidates=candidates):
                    self.assertEqual(
                        _group_limit("A", "bridge_safe", candidates, supply),
                        min(candidates, supply),
                    )
                    self.assertEqual(
                        _group_limit("C", "bridge_safe", candidates, supply),
                        min(candidates, supply + 1),
                    )
                    self.assertEqual(
                        _group_limit("B", "bridge_safe", candidates, supply),
                        candidates,
                    )
                    self.assertEqual(
                        _group_limit("B", "direct_heuristic", candidates, supply),
                        min(candidates, supply + 1),
                    )

    def test_malformed_submission_mutations_are_rejected(self) -> None:
        source = ROOT / "deliverables" / "public" / "A"

        def evaluate_mutation(filename: str, mutation):
            temporary = tempfile.TemporaryDirectory()
            self.addCleanup(temporary.cleanup)
            copied = Path(temporary.name)
            for name in SUBMISSION_FILES:
                shutil.copy(source / name, copied / name)
            path = copied / filename
            with path.open(newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
                fieldnames = list(rows[0])
            mutation(rows)
            with path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)
            return evaluate_submission(self.instance, copied, scenario="A")

        duplicate_access = evaluate_mutation(
            "SCHEDULE_ACCESS.csv", lambda rows: rows.append(dict(rows[0]))
        )
        self.assertTrue(
            any("more than one access in week" in item for item in duplicate_access.hard_violations),
            duplicate_access.hard_violations,
        )

        def gap_sequence(rows) -> None:
            rows[0]["access_seq"] = "99"

        sequence = evaluate_mutation("SCHEDULE_ACCESS.csv", gap_sequence)
        self.assertTrue(
            any("access_seq does not follow chronological weeks" in item for item in sequence.hard_violations),
            sequence.hard_violations,
        )

        missing_occupancy = evaluate_mutation(
            "SCHEDULE_OCCUPANCY.csv", lambda rows: rows.pop()
        )
        self.assertTrue(
            any("missing 1 required occupancy rows" in item for item in missing_occupancy.hard_violations),
            missing_occupancy.hard_violations,
        )

        duplicate_occupancy = evaluate_mutation(
            "SCHEDULE_OCCUPANCY.csv", lambda rows: rows.append(dict(rows[0]))
        )
        self.assertTrue(
            any("duplicate occupancy row" in item for item in duplicate_occupancy.hard_violations),
            duplicate_occupancy.hard_violations,
        )

        def add_unexpected_occupancy(rows) -> None:
            extra = dict(rows[0])
            extra["location_id"] = "PLAT:ALP:S01:EB"
            rows.append(extra)

        extra_occupancy = evaluate_mutation(
            "SCHEDULE_OCCUPANCY.csv", add_unexpected_occupancy
        )
        self.assertTrue(
            any("found 1 unexpected occupancy rows" in item for item in extra_occupancy.hard_violations),
            extra_occupancy.hard_violations,
        )

        def empty_group(rows) -> None:
            rows[0]["co_share_group"] = ""

        empty_group_result = evaluate_mutation("SCHEDULE_OCCUPANCY.csv", empty_group)
        self.assertTrue(
            any("empty co_share_group" in item for item in empty_group_result.hard_violations),
            empty_group_result.hard_violations,
        )

        missing_result = evaluate_mutation("RESULTS.csv", lambda rows: rows.pop())
        self.assertTrue(
            any("RESULTS contract mismatch" in item for item in missing_result.hard_violations),
            missing_result.hard_violations,
        )

        def corrupt_result(rows) -> None:
            rows[0]["simulated_completion_date"] = "2030-01-01"
            rows[0]["overrun_days"] = "0"

        wrong_result = evaluate_mutation("RESULTS.csv", corrupt_result)
        self.assertTrue(
            any("RESULTS expected" in item for item in wrong_result.hard_violations),
            wrong_result.hard_violations,
        )

        def change_result_scenario(rows) -> None:
            for row in rows:
                row["scenario"] = "B"

        wrong_scenario = evaluate_mutation("RESULTS.csv", change_result_scenario)
        self.assertTrue(
            any("RESULTS scenario ['B'] disagrees with A" in item for item in wrong_scenario.hard_violations),
            wrong_scenario.hard_violations,
        )

        duplicate_result = evaluate_mutation(
            "RESULTS.csv", lambda rows: rows.append(dict(rows[0]))
        )
        self.assertTrue(
            any("duplicate RESULTS contract" in item for item in duplicate_result.hard_violations),
            duplicate_result.hard_violations,
        )

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

    def test_checked_zero_score_hint_returns_global_floor_without_model(self) -> None:
        data = ROOT / "fixtures" / "independent_dense_m20"
        source = (
            ROOT
            / "runs"
            / "independent_dense_m20_hint_candidate_seed1_w1"
            / "b_seed_1"
        )
        instance = load_instance(data)
        with tempfile.TemporaryDirectory() as temp_dir:
            telemetry = solve_flexible_supply_relaxation(
                instance,
                temp_dir,
                "B",
                time_limit_seconds=10.0,
                sample_hint_dir=source,
                workers=1,
            )
            evaluation = evaluate_submission(instance, temp_dir, "B")
            independent = independently_score(data, temp_dir)
        self.assertEqual(telemetry.status, "PRIMARY_OPTIMAL_SAFE_INCUMBENT")
        self.assertEqual(telemetry.objective_score, 0.0)
        self.assertEqual(telemetry.best_bound, 0.0)
        self.assertEqual(telemetry.model_variables, 0)
        self.assertEqual(telemetry.model_constraints, 0)
        self.assertEqual(telemetry.solve_rounds, 0)
        self.assertTrue(telemetry.primary_score_proven_optimal)
        self.assertFalse(telemetry.tie_break_proven_optimal)
        self.assertEqual(
            telemetry.primary_bound_scope, "full_instance_nonnegative_floor"
        )
        self.assertEqual(evaluation.hard_violations, ())
        self.assertEqual(evaluation.objective_score, 0.0)
        self.assertEqual(independent.objective_score, 0.0)

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
        self.assertEqual(solve.call_count, 5)
        self.assertTrue(solve.call_args_list[-1].kwargs["forbid_buffer_overlap"])
        self.assertTrue(solve.call_args_list[-1].kwargs["freeze_access_hint"])
        self.assertEqual(
            Path(solve.call_args_list[1].kwargs["sample_hint_dir"]).name,
            "heuristic_attempt_1_raw",
        )
        self.assertEqual(report["selected_stage"], "strict_score_preserving_hedge")
        self.assertTrue(report["strict_hedge_promoted"])
        self.assertTrue(report["strict_buffer_overlap_clean"])
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
        self.assertEqual(solve.call_count, 6)
        self.assertTrue(solve.call_args_list[-1].kwargs["forbid_buffer_overlap"])
        self.assertTrue(solve.call_args_list[-1].kwargs["freeze_access_hint"])
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
        expected_narrow = _scenario_b_cost_contributing_activities(
            self.instance,
            ROOT / "deliverables" / "public" / "C",
            expand_footprints=True,
            expand_contracts=True,
            expand_precedence=True,
            include_delays=True,
        )
        expected_expanded = _scenario_b_cost_contributing_activities(
            self.instance,
            ROOT / "deliverables" / "public" / "C",
            expand_footprints=True,
            expand_contracts=True,
            expand_precedence=True,
            revisit_precedence_after_footprints=True,
            revisit_contracts_after_precedence=True,
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
        self.assertEqual(solve.call_count, 4)
        cost_call = solve.call_args_list[2]
        self.assertTrue(cost_call.kwargs["freeze_access_hint"])
        self.assertEqual(
            cost_call.kwargs["freeze_access_except"], set(expected_narrow)
        )
        expanded_call = solve.call_args_list[3]
        self.assertEqual(
            expanded_call.kwargs["freeze_access_except"], set(expected_expanded)
        )
        self.assertEqual(expanded_call.kwargs["time_limit_seconds"], 1.0)
        self.assertEqual(
            report["bridge_safe_cost_repair_activities"], expected_narrow
        )
        self.assertEqual(
            report["bridge_safe_expanded_cost_repair_activities"], expected_expanded
        )

    def test_staged_c_escalates_from_narrow_to_expanded_cost_repair(self) -> None:
        data = ROOT / "fixtures" / "independent_post_precedence_contract_v1"
        incumbent = ROOT / "fixtures/independent_post_precedence_contract_v1_incumbent"
        oracle = ROOT / "fixtures" / "independent_post_precedence_contract_v1_oracle"
        instance = load_instance(data)
        calls = 0

        def fake_solve(instance, output_dir, scenario, **kwargs):
            nonlocal calls
            calls += 1
            source = oracle if calls == 4 else incumbent
            _copy_submission(source, Path(output_dir))
            objective = 0.0 if calls == 4 else 10.0
            return SolveTelemetry(
                formulation=kwargs["separator_mode"],
                status="OPTIMAL",
                objective_score=objective,
                best_bound=objective,
                wall_time_seconds=0.0,
                conflicts=0,
                branches=0,
                seed=kwargs["seed"],
                workers=1,
                time_limit_seconds=kwargs["time_limit_seconds"],
                model_variables=0,
                model_constraints=0,
                limitation="test fixture",
                remaining_closure_conflicts=0,
                primary_score_proven_optimal=True,
            )

        with tempfile.TemporaryDirectory() as temp_dir, patch(
            "nebula_ps1.staged.solve_flexible_supply_relaxation", side_effect=fake_solve
        ) as solve:
            report = solve_staged_scenario(
                instance,
                Path(temp_dir) / "submission",
                "C",
                audit_output_dir=Path(temp_dir) / "audit",
                heuristic_attempts=1,
                local_repair_time_limit_seconds=1.0,
            )
            final = evaluate_submission(instance, Path(temp_dir) / "submission", "C")
        self.assertEqual(solve.call_count, 4)
        self.assertEqual(
            solve.call_args_list[2].kwargs["freeze_access_except"],
            {"COMP", "DIRECT"},
        )
        self.assertEqual(
            solve.call_args_list[3].kwargs["freeze_access_except"],
            {"COMP", "DIRECT", "FOLLOW", "PEER"},
        )
        self.assertEqual(report["selected_stage"], "bridge_safe_expanded_cost_repair")
        self.assertEqual(final.objective_score, 0.0)

    def test_staged_solver_integrates_terminal_precedence_revisit(self) -> None:
        data = ROOT / "fixtures" / "independent_post_contract_precedence_v1"
        incumbent = ROOT / "fixtures/independent_post_contract_precedence_v1_incumbent"
        oracle = ROOT / "fixtures" / "independent_post_contract_precedence_v1_oracle"
        instance = load_instance(data)
        calls = 0

        def fake_solve(instance, output_dir, scenario, **kwargs):
            nonlocal calls
            calls += 1
            source = oracle if calls == 4 else incumbent
            _copy_submission(source, Path(output_dir))
            objective = 0.0 if calls == 4 else 10.0
            return SolveTelemetry(
                formulation=kwargs["separator_mode"],
                status="OPTIMAL",
                objective_score=objective,
                best_bound=objective,
                wall_time_seconds=0.0,
                conflicts=0,
                branches=0,
                seed=kwargs["seed"],
                workers=1,
                time_limit_seconds=kwargs["time_limit_seconds"],
                model_variables=0,
                model_constraints=0,
                limitation="test fixture",
                remaining_closure_conflicts=0,
                primary_score_proven_optimal=True,
            )

        with tempfile.TemporaryDirectory() as temp_dir, patch(
            "nebula_ps1.staged.solve_flexible_supply_relaxation", side_effect=fake_solve
        ) as solve:
            report = solve_staged_scenario(
                instance,
                Path(temp_dir) / "submission",
                "C",
                audit_output_dir=Path(temp_dir) / "audit",
                heuristic_attempts=1,
                local_repair_time_limit_seconds=1.0,
            )
            final = evaluate_submission(instance, Path(temp_dir) / "submission", "C")
        self.assertEqual(solve.call_count, 4)
        self.assertEqual(
            solve.call_args_list[3].kwargs["freeze_access_except"],
            {"COMP", "DIRECT", "FOLLOW", "PEER", "PREPEER"},
        )
        self.assertEqual(report["selected_stage"], "bridge_safe_expanded_cost_repair")
        self.assertEqual(final.objective_score, 0.0)

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

    def test_staged_c_portfolio_integrates_terminal_precedence_revisit(self) -> None:
        data = ROOT / "fixtures" / "independent_post_contract_precedence_v1"
        incumbent = ROOT / "fixtures/independent_post_contract_precedence_v1_incumbent"
        oracle = ROOT / "fixtures" / "independent_post_contract_precedence_v1_oracle"
        instance = load_instance(data)
        calls = 0

        def fake_staged(instance, output_dir, scenario, **kwargs):
            _copy_submission(incumbent, Path(output_dir))
            return {"selected_objective_score": 10.0}

        def fake_solve(instance, output_dir, scenario, **kwargs):
            nonlocal calls
            calls += 1
            source = oracle if calls == 4 else incumbent
            _copy_submission(source, Path(output_dir))
            objective = 0.0 if calls == 4 else 10.0
            return SolveTelemetry(
                formulation=kwargs["separator_mode"],
                status="OPTIMAL",
                objective_score=objective,
                best_bound=objective,
                wall_time_seconds=0.0,
                conflicts=0,
                branches=0,
                seed=kwargs["seed"],
                workers=1,
                time_limit_seconds=kwargs["time_limit_seconds"],
                model_variables=0,
                model_constraints=0,
                limitation="test fixture",
                remaining_closure_conflicts=0,
                primary_score_proven_optimal=True,
            )

        with tempfile.TemporaryDirectory() as temp_dir, patch(
            "nebula_ps1.staged_c.solve_staged_scenario", side_effect=fake_staged
        ), patch(
            "nebula_ps1.staged_c.solve_flexible_supply_relaxation", side_effect=fake_solve
        ) as solve:
            report = solve_staged_c_portfolio(
                instance,
                Path(temp_dir) / "submission",
                audit_output_dir=Path(temp_dir) / "audit",
                a_local_repair_time_limit_seconds=1.0,
                c_heuristic_time_limit_seconds=1.0,
                c_verification_time_limit_seconds=1.0,
                c_heuristic_attempts=1,
                workers=1,
            )
            final = evaluate_submission(instance, Path(temp_dir) / "submission", "C")
        self.assertEqual(solve.call_count, 4)
        self.assertEqual(
            solve.call_args_list[3].kwargs["freeze_access_except"],
            {"COMP", "DIRECT", "FOLLOW", "PEER", "PREPEER"},
        )
        self.assertEqual(report["selected_stage"], "scenario_c_expanded_cost_repair")
        self.assertEqual(final.objective_score, 0.0)

    def test_staged_c_portfolio_promotes_equal_score_strict_hedge(self) -> None:
        data = ROOT / "fixtures" / "independent_irregular_partial_v1_renamed_s3"
        incumbent = ROOT / "runs" / "c_irregular_renamed_s3_seed5_production"
        hedge = ROOT / "runs" / "c_irregular_renamed_s3_strict_repair_pruned"
        instance = load_instance(data)

        def fake_staged(instance, output_dir, scenario, **kwargs):
            _copy_submission(incumbent, Path(output_dir))
            return {"selected_objective_score": 31.0}

        def fake_solve(instance, output_dir, scenario, **kwargs):
            source = hedge if kwargs["forbid_buffer_overlap"] else incumbent
            _copy_submission(source, Path(output_dir))
            return SolveTelemetry(
                formulation=kwargs["separator_mode"],
                status="OPTIMAL",
                objective_score=31.0,
                best_bound=31.0,
                wall_time_seconds=0.0,
                conflicts=0,
                branches=0,
                seed=kwargs["seed"],
                workers=1,
                time_limit_seconds=kwargs["time_limit_seconds"],
                model_variables=0,
                model_constraints=0,
                limitation="test fixture",
                remaining_closure_conflicts=0,
                primary_score_proven_optimal=True,
            )

        with tempfile.TemporaryDirectory() as temp_dir, patch(
            "nebula_ps1.staged_c.solve_staged_scenario", side_effect=fake_staged
        ), patch(
            "nebula_ps1.staged_c.solve_flexible_supply_relaxation", side_effect=fake_solve
        ) as solve, patch(
            "nebula_ps1.staged.solve_flexible_supply_relaxation", side_effect=fake_solve
        ) as strict_solve:
            report = solve_staged_c_portfolio(
                instance,
                Path(temp_dir) / "submission",
                audit_output_dir=Path(temp_dir) / "audit",
                a_local_repair_time_limit_seconds=1.0,
                c_heuristic_time_limit_seconds=1.0,
                c_verification_time_limit_seconds=1.0,
                c_heuristic_attempts=1,
                workers=1,
            )
            final = evaluate_submission(instance, Path(temp_dir) / "submission", "C")
            access, occupancy, _ = load_submission(Path(temp_dir) / "submission")
        self.assertGreaterEqual(solve.call_count, 3)
        self.assertEqual(strict_solve.call_count, 1)
        self.assertTrue(strict_solve.call_args_list[-1].kwargs["forbid_buffer_overlap"])
        self.assertEqual(
            strict_solve.call_args_list[-1].kwargs["freeze_access_except"],
            {"Z528", "Z572", "Z596"},
        )
        self.assertEqual(
            report["selected_stage"], "scenario_c_strict_score_preserving_hedge"
        )
        self.assertTrue(report["scenario_c_strict_hedge_promoted"])
        self.assertTrue(report["strict_buffer_overlap_clean"])
        self.assertEqual(final.objective_score, 31.0)
        self.assertEqual(
            screen_closures(
                instance,
                access,
                occupancy,
                forbid_buffer_overlap=True,
            ),
            (),
        )

    def test_staged_c_uses_checked_direct_path_only_after_a_failure(self) -> None:
        failure = RuntimeError(
            "neither direct heuristic nor bridge-safe fallback produced a checked safe incumbent"
        )
        direct = {
            "selected_objective_score": 52.0,
            "selected_submission_hash": "checked-direct-c",
            "bridge_safe_cost_repair_activities": ["NARROW"],
            "bridge_safe_cost_repair_telemetry": {"objective_score": 52.0},
            "bridge_safe_cost_repair_prune": {"final_score": 52.0},
            "bridge_safe_expanded_cost_repair_activities": ["NARROW", "EXPANDED"],
            "bridge_safe_expanded_cost_repair_telemetry": {"objective_score": 52.0},
            "bridge_safe_expanded_cost_repair_prune": {"final_score": 52.0},
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
        self.assertEqual(report["scenario_c_cost_repair_activities"], ["NARROW"])
        self.assertEqual(report["scenario_c_cost_repair_prune"], {"final_score": 52.0})
        self.assertEqual(
            report["scenario_c_expanded_cost_repair_activities"],
            ["NARROW", "EXPANDED"],
        )
        self.assertEqual(
            report["scenario_c_expanded_cost_repair_prune"], {"final_score": 52.0}
        )

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
        self.assertEqual(solve.call_count, 4)
        self.assertEqual(solve.call_args_list[0].kwargs["separator_mode"], "direct_heuristic")
        self.assertIsNone(solve.call_args_list[0].kwargs["sample_hint_dir"])
        self.assertEqual(solve.call_args_list[1].kwargs["separator_mode"], "bridge_safe")
        self.assertEqual(solve.call_args_list[2].kwargs["separator_mode"], "bridge_safe")
        self.assertEqual(solve.call_args_list[2].kwargs["time_limit_seconds"], 30.0)
        self.assertTrue(solve.call_args_list[2].kwargs["freeze_access_hint"])
        self.assertEqual(solve.call_args_list[3].kwargs["separator_mode"], "bridge_safe")
        self.assertEqual(solve.call_args_list[3].kwargs["time_limit_seconds"], 10.0)
        self.assertTrue(solve.call_args_list[3].kwargs["freeze_access_hint"])
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

    def test_final_submission_archives_match_protected_incumbents(self) -> None:
        public = json.loads(
            (ROOT / "deliverables" / "public" / "MANIFEST.json").read_text(
                encoding="utf-8"
            )
        )
        final_root = ROOT / "deliverables" / "final-submission"
        packaged = json.loads(
            (final_root / "MANIFEST.json").read_text(encoding="utf-8")
        )
        self.assertTrue(packaged["reference_validator_confirmed"])
        self.assertEqual(packaged["dataset_hash"], public["dataset_hash"])
        for scenario in ("A", "B", "C"):
            with self.subTest(scenario=scenario):
                record = packaged["scenarios"][scenario]
                expected = public["scenarios"][scenario]
                archive_path = final_root / record["archive"]
                self.assertEqual(
                    hashlib.sha256(archive_path.read_bytes()).hexdigest(),
                    record["archive_sha256"],
                )
                with zipfile.ZipFile(archive_path) as archive:
                    self.assertEqual(len(archive.namelist()), len(SUBMISSION_FILES))
                    self.assertEqual(set(archive.namelist()), set(SUBMISSION_FILES))
                    archived_hashes = {
                        name: hashlib.sha256(archive.read(name)).hexdigest()
                        for name in archive.namelist()
                    }
                self.assertEqual(archived_hashes, expected["files"])
                self.assertEqual(record["file_sha256"], expected["files"])
                self.assertEqual(
                    record["submission_hash"], expected["submission_hash"]
                )
                self.assertEqual(record["official_score"], expected["official_score"])
                self.assertEqual(
                    record["official_validator_run"],
                    expected["official_validator_run"],
                )

    def test_final_submission_readiness_audit_passes_every_check(self) -> None:
        readiness = json.loads(
            (
                ROOT / "deliverables" / "final-submission" / "READINESS.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(
            readiness["scope"], "local pre-upload audit; no portal interaction"
        )
        self.assertTrue(readiness["reference_validator_confirmed_incumbents"])
        self.assertTrue(readiness["all_ready"])
        self.assertEqual(set(readiness["scenarios"]), {"A", "B", "C"})
        for scenario, record in readiness["scenarios"].items():
            with self.subTest(scenario=scenario):
                self.assertTrue(record["ready"])
                self.assertTrue(all(record["checks"].values()))
                self.assertEqual(record["hard_violations"], [])
                self.assertEqual(record["strict_conflicts"], 0)
                self.assertEqual(record["local_score"], record["official_score"])
                self.assertEqual(
                    record["independent_score"], record["official_score"]
                )

    def test_public_incumbents_bypass_strict_hedge_unchanged(self) -> None:
        manifest = json.loads(
            (ROOT / "deliverables" / "public" / "MANIFEST.json").read_text(
                encoding="utf-8"
            )
        )
        for scenario in ("A", "B", "C"):
            with self.subTest(scenario=scenario), tempfile.TemporaryDirectory() as temp_dir:
                source = ROOT / "deliverables" / "public" / scenario
                selected = evaluate_submission(self.instance, source, scenario)
                (
                    returned_dir,
                    returned,
                    conflicts_before,
                    conflicts_after,
                    activities,
                    telemetry,
                    prune_report,
                    promoted,
                ) = _run_strict_score_preserving_hedge(
                    self.instance,
                    source,
                    selected,
                    scenario,
                    Path(temp_dir),
                    time_limit_seconds=10.0,
                    workers=8,
                    seed=9,
                    closure_round_limit=500,
                )
                self.assertEqual(returned_dir, source)
                self.assertEqual(conflicts_before, ())
                self.assertEqual(conflicts_after, ())
                self.assertEqual(activities, [])
                self.assertIsNone(telemetry)
                self.assertIsNone(prune_report)
                self.assertFalse(promoted)
                self.assertEqual(
                    returned.submission_hash,
                    manifest["scenarios"][scenario]["submission_hash"],
                )

    def test_current_public_replay_matches_scores_without_replacing_incumbents(
        self,
    ) -> None:
        matrix = json.loads(
            (
                ROOT
                / "runs"
                / "public_current_post_checked_hint_seed6_w8"
                / "SEED_MATRIX.json"
            ).read_text(encoding="utf-8")
        )
        manifest = json.loads(
            (ROOT / "deliverables" / "public" / "MANIFEST.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(matrix["dataset_hash"], self.instance.dataset_hash)
        self.assertEqual(matrix["successes"], 3)
        self.assertEqual(matrix["failures"], 0)
        expected_strict = {"A": 4, "B": 0, "C": 9}
        for row in matrix["runs"]:
            scenario = row["scenario"]
            with self.subTest(scenario=scenario):
                official = manifest["scenarios"][scenario]
                submission = (
                    ROOT
                    / "runs"
                    / "public_current_post_checked_hint_seed6_w8"
                    / f"{scenario.lower()}_seed_6"
                )
                evaluation = evaluate_submission(
                    self.instance, submission, scenario
                )
                independent = independently_score(PACK / "01_data", submission)
                self.assertEqual(row["status"], "SUCCESS")
                self.assertEqual(evaluation.hard_violations, ())
                self.assertEqual(row["score"], official["official_score"])
                self.assertEqual(evaluation.objective_score, row["score"])
                self.assertEqual(independent.objective_score, row["score"])
                self.assertEqual(row["strict_conflicts"], expected_strict[scenario])
                self.assertNotEqual(
                    row["submission_hash"], official["submission_hash"]
                )


if __name__ == "__main__":
    unittest.main()
