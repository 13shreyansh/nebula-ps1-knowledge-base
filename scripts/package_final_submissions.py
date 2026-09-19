from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "deliverables" / "public"
OUTPUT = ROOT / "deliverables" / "final-submission"
SUBMISSION_FILES = ("RESULTS.csv", "SCHEDULE_ACCESS.csv", "SCHEDULE_OCCUPANCY.csv")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_deterministic_zip(source_dir: Path, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(
        output_path,
        "w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
    ) as archive:
        for name in SUBMISSION_FILES:
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, (source_dir / name).read_bytes())


def main() -> None:
    protected = json.loads((PUBLIC / "MANIFEST.json").read_text(encoding="utf-8"))
    packaged: dict[str, object] = {}
    for scenario in ("A", "B", "C"):
        source_dir = PUBLIC / scenario
        output_path = OUTPUT / f"{scenario}.zip"
        _write_deterministic_zip(source_dir, output_path)
        expected = protected["scenarios"][scenario]
        with zipfile.ZipFile(output_path) as archive:
            names = archive.namelist()
            if names != list(SUBMISSION_FILES):
                raise RuntimeError(f"{scenario}: unexpected ZIP members {names}")
            archived_hashes = {
                name: hashlib.sha256(archive.read(name)).hexdigest()
                for name in names
            }
        if archived_hashes != expected["files"]:
            raise RuntimeError(f"{scenario}: packaged bytes differ from protected files")
        packaged[scenario] = {
            "archive": f"{scenario}.zip",
            "archive_sha256": _sha256(output_path),
            "members": names,
            "file_sha256": archived_hashes,
            "submission_hash": expected["submission_hash"],
            "official_score": expected["official_score"],
            "official_validator_run": expected["official_validator_run"],
        }
    payload = {
        "source_manifest": "../public/MANIFEST.json",
        "dataset_hash": protected["dataset_hash"],
        "reference_validator_confirmed": protected["reference_validator_confirmed"],
        "warning": "Upload only after explicit user authorization; packaging is not submission.",
        "scenarios": packaged,
    }
    (OUTPUT / "MANIFEST.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
