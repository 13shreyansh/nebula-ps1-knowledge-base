from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_VALIDATOR_ARCHIVE = (
    "495d4ef700dbed2c7a55460ed0afaeacd7f950b08ec5fe6137c870f9b843f1a1"
)


def _run(command: list[str]) -> None:
    completed = subprocess.run(command, cwd=ROOT, check=False)
    if completed.returncode:
        raise RuntimeError(
            f"release gate failed ({completed.returncode}): {' '.join(command)}"
        )


def main() -> None:
    # These gates intentionally run serially. The validator verification rebuilds
    # its archive, so a concurrent regression run can create a false hash mismatch.
    _run([sys.executable, "scripts/verify_local_validator.py"])
    _run([sys.executable, "scripts/audit_final_submission_readiness.py"])

    verification = json.loads(
        (ROOT / "deliverables" / "local-validator" / "VERIFICATION.json").read_text(
            encoding="utf-8"
        )
    )
    readiness = json.loads(
        (ROOT / "deliverables" / "final-submission" / "READINESS.json").read_text(
            encoding="utf-8"
        )
    )
    true_checks = sum(
        sum(value is True for value in scenario["checks"].values())
        for scenario in readiness["scenarios"].values()
    )
    if verification["archive_sha256"] != EXPECTED_VALIDATOR_ARCHIVE:
        raise RuntimeError("portable validator archive hash changed")
    if verification["validator_tests_passed"] != 19:
        raise RuntimeError("isolated portable validator suite is incomplete")
    if verification["portal_used"] is not False:
        raise RuntimeError("release verification unexpectedly reports portal use")
    if readiness["all_ready"] is not True or true_checks != 30:
        raise RuntimeError("final-package readiness is incomplete")
    print(
        json.dumps(
            {
                "full_regression_tests_passed": verification[
                    "full_regression_tests_passed"
                ],
                "validator_tests_passed": verification["validator_tests_passed"],
                "validator_archive_sha256": verification["archive_sha256"],
                "final_package_checks_passed": true_checks,
                "all_ready": readiness["all_ready"],
                "portal_used": False,
                "execution": "serial",
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
