"""Build a reproducible stdlib-only Python zipapp and matching source archive."""
from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "deliverables/local-validator"
MODULES = ("__init__.py", "validator.py", "evaluate.py", "instance.py", "topology.py", "closure.py", "objective.py", "independent_score.py")


def build() -> dict:
    OUT.mkdir(parents=True, exist_ok=True)
    content = {"nebula_ps1/" + name: (ROOT / "src/nebula_ps1" / name).read_bytes() for name in MODULES}
    content["__main__.py"] = b"from nebula_ps1.validator import main\nraise SystemExit(main())\n"
    files = {}
    for archive_name in ("nebula-ps1-validator.pyz", "nebula-ps1-validator-source.zip"):
        with zipfile.ZipFile(OUT / archive_name, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for name, data in sorted(content.items()):
                info = zipfile.ZipInfo(name, date_time=(2026, 9, 19, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o100644 << 16
                archive.writestr(info, data)
            if archive_name.endswith("-source.zip"):
                info = zipfile.ZipInfo("README.md", date_time=(2026, 9, 19, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o100644 << 16
                archive.writestr(info, (OUT / "README.md").read_bytes())
        files[archive_name] = hashlib.sha256((OUT / archive_name).read_bytes()).hexdigest()
    manifest = {"python": ">=3.9", "external_dependencies": [], "archives": files, "source_files": {name: hashlib.sha256(data).hexdigest() for name, data in sorted(content.items())}}
    (OUT / "MANIFEST.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return manifest


if __name__ == "__main__":
    print(json.dumps(build(), indent=2, sort_keys=True))
