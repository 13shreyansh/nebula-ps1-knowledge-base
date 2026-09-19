from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from package_local_validator import ROOT, build


CASES = (
    (
        "organiser-sample-A",
        ROOT / "current-problem-statement/PS1/03_submission_sample",
        0,
        137.9,
    ),
    ("A-001", ROOT / "deliverables/validator/A.zip", 1, None),
    ("A-002", ROOT / "deliverables/validator/A-002.zip", 0, 137.9),
    ("B-001", ROOT / "deliverables/validator/B-001.zip", 0, 30.0),
    ("C-001", ROOT / "deliverables/validator/C-001.zip", 0, 62.7),
)


def run_checked(command: list[str], *, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        command,
        cwd=cwd,
        capture_output=True,
        text=True,
    )
    if completed.returncode:
        raise RuntimeError(
            f"command failed ({completed.returncode}): {' '.join(command)}\n"
            f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
        )
    return completed


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Rebuild and independently exercise the portable local validator."
    )
    parser.add_argument(
        "--portable-python",
        default=shutil.which("python3") or "python3",
        help="Python executable used with -I -S for portable-runtime checks",
    )
    args = parser.parse_args()

    manifest = build()
    output = ROOT / "deliverables/local-validator"
    portable = output / "nebula-ps1-validator.pyz"
    data = ROOT / "current-problem-statement/PS1/01_data"

    full = run_checked(
        [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-q"],
        cwd=ROOT,
    )
    match = re.search(r"Ran (\d+) tests", full.stderr + full.stdout)
    if match is None:
        raise RuntimeError("could not parse full regression test count")
    full_test_count = int(match.group(1))

    focused = run_checked(
        [
            sys.executable,
            "-m",
            "unittest",
            "discover",
            "-s",
            "tests",
            "-p",
            "test_validator.py",
            "-q",
        ],
        cwd=ROOT,
    )
    match = re.search(r"Ran (\d+) tests", focused.stderr + focused.stdout)
    if match is None:
        raise RuntimeError("could not parse validator test count")
    focused_test_count = int(match.group(1))

    runtime = run_checked(
        [args.portable_python, "-I", "-S", "-c", "import sys; print(sys.version)"]
    ).stdout.strip()
    cases = []
    with tempfile.TemporaryDirectory(prefix="nebula-validator-verify-") as temporary:
        isolated = Path(temporary)
        for name, submission, expected_exit, expected_score in CASES:
            completed = subprocess.run(
                [
                    args.portable_python,
                    "-I",
                    "-S",
                    str(portable),
                    "--data",
                    str(data),
                    "--submission",
                    str(submission),
                ],
                cwd=isolated,
                capture_output=True,
                text=True,
            )
            if completed.returncode != expected_exit:
                raise RuntimeError(
                    f"{name}: exit {completed.returncode}, expected {expected_exit}\n"
                    f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
                )
            report = json.loads(completed.stdout)
            score = report.get("soft_scores", {}).get("objective_score")
            if score != expected_score:
                raise RuntimeError(
                    f"{name}: score {score!r}, expected {expected_score!r}"
                )
            (output / f"{name}.report.json").write_text(
                json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n",
                encoding="utf-8",
            )
            cases.append(
                {
                    "case": name,
                    "exit_code": completed.returncode,
                    "feasible": report["feasible"],
                    "hard_violations": len(report["hard_violations"]),
                    "score": score,
                }
            )

        source_root = isolated / "source"
        source_root.mkdir()
        with zipfile.ZipFile(output / "nebula-ps1-validator-source.zip") as archive:
            archive.extractall(source_root)
        source = run_checked(
            [
                args.portable_python,
                "-I",
                "-S",
                str(source_root),
                "--data",
                str(data),
                "--submission",
                str(ROOT / "deliverables/final-submission/C.zip"),
                "--scenario",
                "C",
            ],
            cwd=isolated,
        )
        source_report = json.loads(source.stdout)
        if source_report["soft_scores"].get("objective_score") != 62.7:
            raise RuntimeError("extracted source archive did not reproduce C=62.7")

    archive_hash = hashlib.sha256(portable.read_bytes()).hexdigest()
    if archive_hash != manifest["archives"][portable.name]:
        raise RuntimeError("portable archive hash disagrees with manifest")
    verification = {
        "archive_sha256": archive_hash,
        "cases": cases,
        "full_regression_tests_passed": full_test_count,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "isolation": (
            "separate directory, Python -I -S; no third-party site packages; "
            "portable and extracted-source executions"
        ),
        "portal_used": False,
        "runtime": runtime,
        "validator_tests_passed": focused_test_count,
    }
    (output / "VERIFICATION.json").write_text(
        json.dumps(verification, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(verification, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
