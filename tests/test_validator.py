from __future__ import annotations

import csv
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
import warnings
import zipfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from nebula_ps1.validator import validate

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "current-problem-statement/PS1/01_data"
SAMPLE = ROOT / "current-problem-statement/PS1/03_submission_sample"
PUBLIC = ROOT / "deliverables/public"


def rewrite(path, change):
    with path.open(newline="") as f:
        reader = csv.DictReader(f)
        fields, rows = reader.fieldnames, list(reader)
    change(rows)
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


class ValidatorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def submission(self, scenario="A"):
        path = self.root / "submission"
        shutil.copytree(PUBLIC / scenario, path)
        return path

    def data(self):
        path = self.root / "data"
        shutil.copytree(DATA, path)
        return path

    def assert_rejected(self, report, rule=None):
        self.assertFalse(report["feasible"])
        self.assertTrue(report["hard_violations"])
        self.assertNotIn("objective_score", report["soft_scores"])
        self.assertNotIn("formula_version", report["soft_scores"])
        json.dumps(report, allow_nan=False)
        if rule:
            self.assertIn(rule, {v["rule"] for v in report["hard_violations"]})

    def test_official_accepted_archives_and_scores(self):
        for scenario, filename, score, days, eclo in (
            ("A", "A-002.zip", 137.9, 28, 0),
            ("B", "B-001.zip", 30.0, 0, 6),
            ("C", "C-001.zip", 62.7, 7, 4),
        ):
            with self.subTest(scenario=scenario):
                report = validate(DATA, ROOT / "deliverables/validator" / filename, scenario)
                self.assertTrue(report["feasible"], report)
                self.assertEqual(report["soft_scores"]["objective_score"], score)
                self.assertEqual(report["soft_scores"]["overrun_days_total"], days)
                self.assertEqual(report["soft_scores"]["eclo_nights_total"], eclo)
                self.assertEqual(report["soft_scores"]["excess_access_nights_total"], 0)
                self.assertTrue(report["soft_scores"]["independent_score_matches"])
                self.assertFalse(report["validator"]["reference_validator_confirmed"])
                self.assertEqual(report["detail"]["strict_buffer_overlap"]["additional_conflicts"], [])

    def test_official_a001_reproduces_five_directional_closure_failures(self):
        report = validate(DATA, ROOT / "deliverables/validator/A.zip", "A")
        self.assert_rejected(report, "closure")
        self.assertEqual(len(report["hard_violations"]), 5)
        self.assertEqual({v["rule"] for v in report["hard_violations"]}, {"closure"})
        details = "\n".join(v["detail"] for v in report["hard_violations"])
        for pair in (("A035", "A058"), ("A058", "A035"), ("A001", "A074"), ("A011", "A074"), ("A023", "A075")):
            self.assertIn(f"between ['{pair[0]}'] and ['{pair[1]}']", details)

    def test_sample_strict_advisory_is_not_default_infeasibility(self):
        report = validate(DATA, SAMPLE)
        self.assertTrue(report["feasible"])
        self.assertEqual(report["soft_scores"]["objective_score"], 137.9)
        self.assertEqual(len(report["detail"]["strict_buffer_overlap"]["additional_conflicts"]), 4)
        strict = validate(DATA, SAMPLE, strict_buffers=True)
        self.assert_rejected(strict, "closure")
        self.assertEqual(len(strict["hard_violations"]), 4)

    def test_synthetic_input_has_no_public_id_dependency(self):
        report = validate(ROOT / "fixtures/independent_synthetic_v1", ROOT / "fixtures/independent_synthetic_v1_oracle")
        self.assertTrue(report["feasible"], report)
        self.assertEqual(report["soft_scores"]["objective_score"], 7.0)

    def test_data_zip_and_submission_folder_match_directory_result(self):
        archive = self.root / "data.zip"
        with zipfile.ZipFile(archive, "w") as z:
            for p in DATA.glob("*.csv"):
                z.write(p, p.name)
        zipped = validate(archive, PUBLIC / "C")
        plain = validate(DATA, PUBLIC / "C")
        self.assertEqual(zipped, plain)

    def test_extra_missing_nested_and_duplicate_zip_members_rejected(self):
        for mutation in ("extra", "missing", "nested", "duplicate", "traversal"):
            with self.subTest(mutation=mutation):
                archive = self.root / f"{mutation}.zip"
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", UserWarning)
                    with zipfile.ZipFile(archive, "w") as z:
                        for p in (PUBLIC / "A").iterdir():
                            if mutation == "missing" and p.name == "RESULTS.csv":
                                continue
                            z.write(p, "nested/" + p.name if mutation == "nested" else p.name)
                        if mutation == "extra":
                            z.writestr("TELEMETRY.json", "{}")
                        if mutation == "duplicate":
                            z.write(PUBLIC / "A/RESULTS.csv", "RESULTS.csv")
                        if mutation == "traversal":
                            z.writestr("../escape.txt", "bad")
                self.assert_rejected(validate(DATA, archive), "packaging")
                self.assertFalse((self.root / "escape.txt").exists())

    def test_extra_submission_folder_file_rejected(self):
        p = self.submission()
        (p / "TELEMETRY.json").write_text("{}")
        self.assert_rejected(validate(DATA, p), "packaging")

    def test_missing_path_and_corrupt_archive_rejected(self):
        self.assert_rejected(validate(DATA, self.root / "missing"), "packaging")
        p = self.root / "bad.zip"
        p.write_text("not a zip")
        self.assert_rejected(validate(DATA, p), "packaging")

    def test_truncated_row_duplicate_header_and_invalid_number_rejected(self):
        for text in (
            "activity_id,access_seq,week,eclo,access_night\nA001,1\n",
            "activity_id,access_seq,week,eclo,access_night,week\nA001,1,1,0,1,1\n",
            "activity_id,access_seq,week,eclo,access_night\nA001,abc,1,0,1\n",
        ):
            with self.subTest(text=text):
                p = self.root / "bad-csv"
                shutil.copytree(PUBLIC / "A", p, dirs_exist_ok=True)
                (p / "SCHEDULE_ACCESS.csv").write_text(text)
                self.assert_rejected(validate(DATA, p), "schema")

    def test_unknown_activity_is_diagnostic_not_crash(self):
        p = self.submission()
        rewrite(p / "SCHEDULE_ACCESS.csv", lambda rows: rows[0].update(activity_id="UNKNOWN"))
        self.assert_rejected(validate(DATA, p), "schema")

    def test_huge_week_is_rejected_before_date_overflow(self):
        p = self.submission()
        rewrite(p / "SCHEDULE_ACCESS.csv", lambda rows: rows[0].update(week="9999999999999999999"))
        self.assert_rejected(validate(DATA, p), "horizon")

    def test_duplicate_access_and_missing_occupancy_rejected(self):
        p = self.submission()
        rewrite(p / "SCHEDULE_ACCESS.csv", lambda rows: rows.append(dict(rows[0])))
        rewrite(p / "SCHEDULE_OCCUPANCY.csv", lambda rows: rows.pop())
        report = validate(DATA, p)
        self.assert_rejected(report, "access_sequence")
        self.assertIn("occupancy", {v["rule"] for v in report["hard_violations"]})

    def test_workload_and_results_cannot_be_falsified(self):
        p = self.submission("B")
        rewrite(p / "SCHEDULE_ACCESS.csv", lambda rows: [r.update(eclo="0") for r in rows if r["activity_id"] == "A036"])
        rewrite(p / "RESULTS.csv", lambda rows: rows[0].update(overrun_days="-7"))
        report = validate(DATA, p)
        self.assert_rejected(report, "workload")
        self.assertIn("results", {v["rule"] for v in report["hard_violations"]})

    def test_score_cross_check_disagreement_fails_closed(self):
        fake = SimpleNamespace(
            objective_score=-1.0,
            priority_weighted_delay=-1.0,
            excess_access_nights=-1,
            eclo_nights=-1,
        )
        with patch("nebula_ps1.validator.independently_score", return_value=fake):
            report = validate(DATA, PUBLIC / "A", "A")
        self.assert_rejected(report, "internal_consistency")

    def test_scenario_mismatch_and_mixed_results_rejected(self):
        self.assert_rejected(validate(DATA, PUBLIC / "A", "B"), "scenario")
        self.assert_rejected(validate(DATA, PUBLIC / "A", "D"), "scenario")
        p = self.submission()
        rewrite(p / "RESULTS.csv", lambda rows: rows[0].update(scenario="C"))
        self.assert_rejected(validate(DATA, p), "scenario")

    def test_bad_input_priority_and_predecessor_cycle_rejected(self):
        p = self.data()
        rewrite(p / "07_PROJECT_DETAILS.csv", lambda rows: rows[0].update(contract_priority="4"))
        self.assert_rejected(validate(p, PUBLIC / "A"), "input")
        shutil.copyfile(DATA / "07_PROJECT_DETAILS.csv", p / "07_PROJECT_DETAILS.csv")
        rewrite(p / "08_ACTIVITY_DETAILS.csv", lambda rows: rows[0].update(predecessor_activity_id=rows[0]["activity_id"]))
        self.assert_rejected(validate(p, PUBLIC / "A"), "input")

    def test_disconnected_input_topology_and_bad_boolean_rejected(self):
        p = self.data()
        rewrite(p / "03_SECTORS.csv", lambda rows: rows[1].update(from_station_id="S01"))
        self.assert_rejected(validate(p, PUBLIC / "A"), "input")
        shutil.copyfile(DATA / "03_SECTORS.csv", p / "03_SECTORS.csv")
        rewrite(p / "02_STATIONS.csv", lambda rows: rows[0].update(is_interchange="2"))
        self.assert_rejected(validate(p, PUBLIC / "A"), "input")

    def test_cli_returns_json_and_meaningful_exit_codes(self):
        output = self.root / "report.json"
        base = [sys.executable, str(ROOT / "validate_ps1.py"), "--data", str(DATA)]
        good = subprocess.run(base + ["--submission", str(PUBLIC / "B"), "--output", str(output)], capture_output=True, text=True)
        self.assertEqual(good.returncode, 0, good.stderr)
        self.assertEqual(json.loads(good.stdout), json.loads(output.read_text()))
        bad = subprocess.run(base + ["--submission", str(PUBLIC / "B"), "--scenario", "A"], capture_output=True, text=True)
        self.assertEqual(bad.returncode, 1, bad.stderr)
        self.assert_rejected(json.loads(bad.stdout), "scenario")

    def test_portable_build_is_deterministic_and_runs_without_site_packages(self):
        spec = importlib.util.spec_from_file_location("package_local_validator", ROOT / "scripts/package_local_validator.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        first = module.build()
        self.assertEqual(first, module.build())
        portable = ROOT / "deliverables/local-validator/nebula-ps1-validator.pyz"
        result = subprocess.run([sys.executable, "-I", "-S", str(portable), "--data", str(DATA), "--submission", str(ROOT / "deliverables/final-submission/C.zip")], cwd=self.root, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["soft_scores"]["objective_score"], 62.7)
        extracted = self.root / "source"
        with zipfile.ZipFile(ROOT / "deliverables/local-validator/nebula-ps1-validator-source.zip") as z:
            z.extractall(extracted)
        source = subprocess.run([sys.executable, "-I", "-S", str(extracted), "--data", str(DATA), "--submission", str(PUBLIC / "A")], cwd=self.root, capture_output=True, text=True)
        self.assertEqual(source.returncode, 0, source.stderr)
        self.assertEqual(json.loads(source.stdout)["soft_scores"]["objective_score"], 137.9)


if __name__ == "__main__":
    unittest.main()
