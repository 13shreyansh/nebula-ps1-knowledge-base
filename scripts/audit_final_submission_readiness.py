from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

from nebula_ps1.closure import screen_closures
from nebula_ps1.evaluate import evaluate_submission, load_submission
from nebula_ps1.independent_score import independently_score
from nebula_ps1.instance import load_instance


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "current-problem-statement" / "PS1" / "01_data"
PUBLIC = ROOT / "deliverables" / "public"
FINAL = ROOT / "deliverables" / "final-submission"
VALIDATOR_HISTORY = ROOT / "deliverables" / "validator"
REQUIRED_FILES = {"RESULTS.csv", "SCHEDULE_ACCESS.csv", "SCHEDULE_OCCUPANCY.csv"}
CONFIRMED_UPLOADS = {
    "A": (
        "A-002.zip",
        "76bf26e19161337daf4f186d2a678aeb23bcb8613bc3bba42d00451d30325437",
    ),
    "B": (
        "B-001.zip",
        "1ef95698cc456f5a037bcd3939a6ee6a6ea06bd32fc4c74c0ff403eb3d00b76c",
    ),
    "C": (
        "C-001.zip",
        "ee6b09ccf0584cf4d3dfb6b825669c39491329a9f756ca50dc1879fd5e274f43",
    ),
}


def _sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def main() -> None:
    instance = load_instance(DATA)
    protected = json.loads((PUBLIC / "MANIFEST.json").read_text(encoding="utf-8"))
    packaged = json.loads((FINAL / "MANIFEST.json").read_text(encoding="utf-8"))
    records: dict[str, object] = {}
    for scenario in ("A", "B", "C"):
        source_dir = PUBLIC / scenario
        expected = protected["scenarios"][scenario]
        archive_record = packaged["scenarios"][scenario]
        archive_path = FINAL / archive_record["archive"]
        evaluation = evaluate_submission(instance, source_dir, scenario)
        independent = independently_score(DATA, source_dir)
        access, occupancy, _ = load_submission(source_dir)
        strict_conflicts = screen_closures(
            instance,
            access,
            occupancy,
            forbid_buffer_overlap=True,
        )
        with zipfile.ZipFile(archive_path) as archive:
            names = archive.namelist()
            archived_hashes = {
                name: _sha256_bytes(archive.read(name)) for name in names
            }
        archive_hash = _sha256_bytes(archive_path.read_bytes())
        confirmed_name, confirmed_expected_hash = CONFIRMED_UPLOADS[scenario]
        confirmed_path = VALIDATOR_HISTORY / confirmed_name
        confirmed_archive_hash = _sha256_bytes(confirmed_path.read_bytes())
        with zipfile.ZipFile(confirmed_path) as confirmed_archive:
            confirmed_names = confirmed_archive.namelist()
            confirmed_member_hashes = {
                name: _sha256_bytes(confirmed_archive.read(name))
                for name in confirmed_names
            }
        checks = {
            "exact_three_root_members": (
                len(names) == 3 and set(names) == REQUIRED_FILES
            ),
            "archive_hash_matches": (
                archive_hash == archive_record["archive_sha256"]
            ),
            "member_hashes_match": archived_hashes == expected["files"],
            "confirmed_upload_archive_hash_matches": (
                confirmed_archive_hash == confirmed_expected_hash
            ),
            "confirmed_upload_members_match": (
                len(confirmed_names) == 3
                and set(confirmed_names) == REQUIRED_FILES
                and confirmed_member_hashes == archived_hashes
            ),
            "submission_hash_matches": (
                evaluation.submission_hash == expected["submission_hash"]
            ),
            "official_score_matches": (
                evaluation.objective_score == expected["official_score"]
            ),
            "independent_score_matches": (
                independent.objective_score == evaluation.objective_score
            ),
            "hard_feasible": not evaluation.hard_violations,
            "strict_closure_clean": not strict_conflicts,
        }
        records[scenario] = {
            "ready": all(checks.values()),
            "checks": checks,
            "official_validator_run": expected["official_validator_run"],
            "official_score": expected["official_score"],
            "local_score": evaluation.objective_score,
            "independent_score": independent.objective_score,
            "submission_hash": evaluation.submission_hash,
            "archive_sha256": archive_hash,
            "confirmed_upload_archive": confirmed_name,
            "confirmed_upload_archive_sha256": confirmed_archive_hash,
            "hard_violations": list(evaluation.hard_violations),
            "strict_conflicts": len(strict_conflicts),
        }
    payload = {
        "scope": "local pre-upload audit; no portal interaction",
        "dataset_hash": instance.dataset_hash,
        "reference_validator_confirmed_incumbents": True,
        "all_ready": all(bool(record["ready"]) for record in records.values()),
        "scenarios": records,
    }
    (FINAL / "READINESS.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
