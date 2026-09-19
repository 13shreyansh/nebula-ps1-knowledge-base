from __future__ import annotations

import base64
import io
import zipfile
from pathlib import Path

from fastapi.testclient import TestClient

from nebula_ps1.instance import FILES
from nebula_ps1.web import PUBLIC_DATA_ROOT, app


client = TestClient(app)


def _public_input_zip() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name in sorted(FILES.values()):
            archive.writestr(name, (PUBLIC_DATA_ROOT / name).read_bytes())
    return buffer.getvalue()


def test_health_and_readiness() -> None:
    health = client.get("/api/health")
    assert health.status_code == 200
    assert health.json()["ok"] is True
    readiness = client.get("/api/readiness")
    assert readiness.status_code == 200
    assert readiness.json()["all_ready"] is True
    assert set(readiness.json()["scenarios"]) == {"A", "B", "C"}


def test_public_reference_is_explicit_and_contains_real_views() -> None:
    response = client.get("/api/reference/B")
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["validation"]["feasible"] is True
    assert payload["validation"]["reference_validator_confirmed"] is True
    assert payload["validation"]["objective_score"] == 0.0
    assert payload["insights"]["summary"]["delivered_work"] == 192
    assert len(payload["insights"]["activities"]) == 54
    assert len(payload["insights"]["contracts"]) == 14
    archive_bytes = base64.b64decode(payload["archive_base64"])
    with zipfile.ZipFile(io.BytesIO(archive_bytes)) as archive:
        assert set(archive.namelist()) == {
            "RESULTS.csv",
            "SCHEDULE_ACCESS.csv",
            "SCHEDULE_OCCUPANCY.csv",
        }


def test_rejects_incomplete_input_pack() -> None:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("01_LINES.csv", "line_code,line_name\n")
    response = client.post(
        "/api/solve",
        data={"scenario": "A"},
        files={"file": ("broken.zip", buffer.getvalue(), "application/zip")},
    )
    assert response.status_code == 400
    assert "exactly the required root files" in response.json()["detail"]


def test_home_serves_application_shell() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "NightShift" in response.text
    assert "Calculate new plan" in response.text
