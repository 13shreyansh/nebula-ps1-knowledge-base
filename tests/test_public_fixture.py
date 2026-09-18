from __future__ import annotations

import unittest
import csv
import hashlib
import json
import shutil
import tempfile
from dataclasses import replace
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from nebula_ps1.cli import main as cli_main
from nebula_ps1.closure import _blocked_locations, _external_buffer_sectors, screen_closures
from nebula_ps1.evaluate import evaluate_submission, load_submission
from nebula_ps1.independent_score import independently_score
from nebula_ps1.instance import load_instance
from nebula_ps1.portfolio import SUBMISSION_FILES, _candidate_is_better, _copy_submission
from nebula_ps1.prune import prune_submission
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
        self.assertEqual(len(self.instance.projects), 14)
        self.assertEqual(len(self.instance.activities), 54)
        self.assertEqual(len(self.instance.locations), 76)
        self.assertEqual(self.instance.horizon_weeks, 30)

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
        self.assertAlmostEqual(evaluation.priority_weighted_score, 48.3)
        self.assertAlmostEqual(evaluation.objective_score, 48.3)
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
        self.assertEqual(direct_collision, {"SEC:BET:S16_S17:EB"})

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
        ]
        with patch("sys.argv", argv), patch(
            "nebula_ps1.cli.solve_scenario_c_portfolio", return_value={}
        ) as solve:
            cli_main()
        self.assertEqual(solve.call_args.kwargs["audit_output_dir"], "custom-audit")

    def test_minimal_32_2_repair_passes_sample_consistent_closure_screen(self) -> None:
        candidate = ROOT / "runs" / "a_repair_late_a035_a038"
        if not candidate.exists():
            self.skipTest("candidate is generated by the solver experiment")
        evaluation = evaluate_submission(self.instance, candidate, scenario="A")
        self.assertEqual(evaluation.hard_violations, ())
        self.assertAlmostEqual(evaluation.objective_score, 32.2)

    def test_unrestricted_scenario_a_incumbent_is_optimal_under_inferred_model(self) -> None:
        candidate = ROOT / "runs" / "a_anytime_nohint_seed1_w8_round3"
        if not candidate.exists():
            self.skipTest("candidate is generated by the solver experiment")
        evaluation = evaluate_submission(self.instance, candidate, scenario="A")
        self.assertEqual(evaluation.hard_violations, ())
        self.assertEqual(evaluation.eclo_nights_total, 0)
        self.assertEqual(evaluation.excess_access_nights_total, 0)
        self.assertAlmostEqual(evaluation.objective_score, 32.2)

    def test_scenario_b_incumbent_passes_all_implemented_rules(self) -> None:
        candidate = ROOT / "runs" / "b_anytime_nohint_seed1_w8_round3"
        if not candidate.exists():
            self.skipTest("candidate is generated by the solver experiment")
        evaluation = evaluate_submission(self.instance, candidate, scenario="B")
        self.assertEqual(evaluation.hard_violations, ())
        self.assertEqual(evaluation.eclo_nights_total, 6)
        self.assertEqual(evaluation.excess_access_nights_total, 0)
        self.assertAlmostEqual(evaluation.objective_score, 30.0)

    def test_relabelled_a_incumbent_is_a_safe_scenario_c_fallback(self) -> None:
        source = ROOT / "runs" / "a_repair_late_a035_a038"
        if not source.exists():
            self.skipTest("candidate is generated by the solver experiment")
        with tempfile.TemporaryDirectory() as temp_dir:
            relabel_submission_scenario(self.instance, source, temp_dir, "C")
            evaluation = evaluate_submission(self.instance, temp_dir, scenario="C")
        self.assertEqual(evaluation.hard_violations, ())
        self.assertEqual(evaluation.eclo_nights_total, 0)
        self.assertEqual(evaluation.excess_access_nights_total, 0)
        self.assertAlmostEqual(evaluation.objective_score, 32.2)

    def test_scenario_c_incumbent_passes_all_implemented_rules(self) -> None:
        candidate = ROOT / "runs" / "c_anytime_nohint_seed1_w8_round3"
        if not candidate.exists():
            self.skipTest("candidate is generated by the solver experiment")
        evaluation = evaluate_submission(self.instance, candidate, scenario="C")
        self.assertEqual(evaluation.hard_violations, ())
        self.assertEqual(evaluation.eclo_nights_total, 2)
        self.assertEqual(evaluation.excess_access_nights_total, 0)
        self.assertAlmostEqual(evaluation.priority_weighted_score, 16.1)
        self.assertAlmostEqual(evaluation.objective_score, 26.1)

    def test_scenario_c_rejects_discontinuous_eclo_window(self) -> None:
        source = ROOT / "runs" / "c_anytime_nohint_seed1_w8_round3"
        if not source.exists():
            self.skipTest("candidate is generated by the solver experiment")
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
            "a_anytime_nohint_seed1_w8_round3": ("A", 32.2, 32.2, 0, 0),
            "b_anytime_nohint_seed1_w8_round3": ("B", 30.0, 0.0, 0, 6),
            "c_anytime_nohint_seed1_w8_round3": ("C", 26.1, 16.1, 0, 2),
        }
        for run_name, components in expected.items():
            with self.subTest(run=run_name):
                candidate = ROOT / "runs" / run_name
                if not candidate.exists():
                    self.skipTest("candidate is generated by the solver experiment")
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
            self.assertAlmostEqual(evaluation.objective_score, 48.3)

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
        self.assertAlmostEqual(evaluation.objective_score, 48.3)

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
        a_run = ROOT / "runs" / "a_anytime_nohint_seed1_w8_round3"
        c_run = ROOT / "runs" / "c_anytime_nohint_seed1_w8_round3"
        if not a_run.exists() or not c_run.exists():
            self.skipTest("portfolio fixtures are generated by solver experiments")
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
        source = ROOT / "runs" / "a_anytime_nohint_seed1_w8_round3"
        if not source.exists():
            self.skipTest("candidate is generated by the solver experiment")
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "pruned"
            report = prune_submission(self.instance, source, output, "A")
            evaluation = evaluate_submission(self.instance, output, scenario="A")
            self.assertEqual(sorted(path.name for path in output.iterdir()), sorted(SUBMISSION_FILES))
        self.assertEqual(report.initial_access_rows, 192)
        self.assertEqual(report.final_access_rows, 192)
        self.assertEqual(report.removed_accesses, ())
        self.assertAlmostEqual(evaluation.objective_score, 32.2)

    def test_packaged_public_answer_keys_match_manifest(self) -> None:
        deliverables = ROOT / "deliverables" / "public"
        if not deliverables.exists():
            self.skipTest("public answer keys have not been packaged")
        manifest = json.loads((deliverables / "MANIFEST.json").read_text(encoding="utf-8"))
        self.assertFalse(manifest["reference_validator_confirmed"])
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
                self.assertAlmostEqual(audit.objective_score, evaluation.objective_score)
                self.assertEqual(evaluation.submission_hash, expected["submission_hash"])


if __name__ == "__main__":
    unittest.main()
