from __future__ import annotations

import asyncio
import base64
import csv
import hashlib
import io
import json
import logging
import os
import shutil
import stat
import tempfile
import time
import zipfile
from dataclasses import asdict
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool

from .flexible_solver import solve_flexible_supply_relaxation
from .insights import schedule_insights
from .evaluate import evaluate_submission
from .independent_score import independently_score
from .instance import FILES, InputError, load_instance
from .portfolio import SUBMISSION_FILES

LOGGER = logging.getLogger("nebula.web")
MAX_UPLOAD_BYTES = int(os.environ.get("NEBULA_MAX_UPLOAD_BYTES", 32 * 1024 * 1024))
MAX_EXTRACTED_BYTES = int(os.environ.get("NEBULA_MAX_EXTRACTED_BYTES", 64 * 1024 * 1024))
MAX_RESULT_BYTES = int(os.environ.get("NEBULA_MAX_RESULT_BYTES", 32 * 1024 * 1024))
ROOT = Path(os.environ.get("NEBULA_ROOT", Path(__file__).resolve().parents[2]))
STATIC_ROOT = Path(__file__).with_name("static")
PUBLIC_DATA_ROOT = ROOT / "current-problem-statement" / "PS1" / "01_data"
BASELINE_ROOT = ROOT / "deliverables" / "official-zero"
INPUT_FILES = frozenset(FILES.values())
OUTPUT_FILES = frozenset(SUBMISSION_FILES)
SOLVER_SEMAPHORE = asyncio.Semaphore(int(os.environ.get("NEBULA_SOLVER_CONCURRENCY", "1")))

app = FastAPI(
    title="NightShift Railway Access Control",
    version="3.0.0",
    description="Explainable, validator-gated railway possession scheduling.",
)


def _readiness() -> dict:
    path = BASELINE_ROOT / "MANIFEST.json"
    if not path.is_file():
        return {"all_ready": False, "scenarios": {}}
    manifest = json.loads(path.read_text(encoding="utf-8"))
    records = {}
    for scenario, record in manifest["scenarios"].items():
        archive = BASELINE_ROOT / record["archive"]
        ready = archive.is_file() and hashlib.sha256(archive.read_bytes()).hexdigest() == record["sha256"]
        records[scenario] = {"ready": ready, "official_score": record["official_score"],
                             "official_validator_run": record["probe_id"],
                             "submission_hash": record["sha256"]}
    return {"all_ready": all(r["ready"] for r in records.values()), "scenarios": records,
            "dataset_hash": PUBLIC_DATASET_HASH}


def _safe_extract(archive_bytes: bytes, destination: Path, expected: frozenset[str]) -> None:
    try:
        with zipfile.ZipFile(io.BytesIO(archive_bytes)) as archive:
            members = archive.infolist()
            names = [member.filename for member in members]
            if len(names) != len(set(names)):
                raise ValueError("ZIP contains duplicate filenames.")
            if set(names) != expected:
                missing = sorted(expected - set(names))
                extra = sorted(set(names) - expected)
                raise ValueError(
                    f"ZIP must contain exactly the required root files. Missing: {missing or 'none'}; "
                    f"unexpected: {extra or 'none'}."
                )
            if sum(member.file_size for member in members) > MAX_EXTRACTED_BYTES:
                raise ValueError("The uncompressed ZIP contents exceed the 64 MiB limit.")
            for member in members:
                if member.is_dir() or stat.S_ISLNK(member.external_attr >> 16):
                    raise ValueError("ZIP members must be regular files.")
                if member.flag_bits & 1:
                    raise ValueError("Encrypted ZIP files are not supported.")
                if member.file_size > MAX_UPLOAD_BYTES:
                    raise ValueError(f"{member.filename} exceeds the upload limit.")
                (destination / member.filename).write_bytes(archive.read(member))
    except zipfile.BadZipFile as exc:
        raise ValueError("The uploaded file is not a readable ZIP archive.") from exc


def _extract_file_archive(path: Path, destination: Path, expected: frozenset[str]) -> None:
    _safe_extract(path.read_bytes(), destination, expected)


def _zip_submission(output_dir: Path) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name in sorted(OUTPUT_FILES):
            archive.writestr(name, (output_dir / name).read_bytes())
    return buffer.getvalue()


def _preview_csv(path: Path, limit: int = 200) -> dict:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        rows = []
        for index, row in enumerate(reader):
            if index >= limit:
                break
            rows.append(row)
        return {"columns": reader.fieldnames or [], "rows": rows}


def _public_dataset_hash() -> str | None:
    try:
        return load_instance(PUBLIC_DATA_ROOT).dataset_hash
    except (FileNotFoundError, InputError, ValueError):
        return None


PUBLIC_DATASET_HASH = _public_dataset_hash()


def _result(instance, output_dir, scenario, started, method, solver_report, reference=False, capacity_overrides=None):
    evaluation = evaluate_submission(instance, output_dir, scenario, capacity_overrides=capacity_overrides)
    if not evaluation.internally_feasible:
        raise RuntimeError("Schedule did not pass validation: " + "; ".join(evaluation.hard_violations[:8]))
    independent = independently_score(instance.root, output_dir, capacity_overrides=capacity_overrides)
    if evaluation.objective_score != independent.objective_score:
        raise RuntimeError("Independent score did not match the primary evaluation.")
    archive = _zip_submission(output_dir)
    if len(archive) > MAX_RESULT_BYTES:
        raise RuntimeError("Generated result exceeds the response limit.")
    return {
        "ok": True, "scenario": scenario, "method": method,
        "duration_seconds": round(time.monotonic() - started, 3),
        "dataset_hash": instance.dataset_hash,
        "validation": {
            "feasible": True, "objective_score": evaluation.objective_score,
            "priority_weighted_delay": evaluation.priority_weighted_score,
            "excess_access_nights": evaluation.excess_access_nights_total,
            "eclo_nights": evaluation.eclo_nights_total,
            "access_rows": evaluation.access_rows, "occupancy_rows": evaluation.occupancy_rows,
            "submission_hash": evaluation.submission_hash,
            "independent_score_agrees": True, "reference_validator_confirmed": reference,
        },
        "solver": solver_report,
        "insights": schedule_insights(instance, output_dir, capacity_overrides),
        "previews": {name: _preview_csv(output_dir / name) for name in sorted(OUTPUT_FILES)},
        "archive_filename": f"NightShift-{scenario}-results.zip",
        "archive_sha256": hashlib.sha256(archive).hexdigest(),
        "archive_base64": base64.b64encode(archive).decode("ascii"),
    }


def _solve(input_zip: bytes, scenario: str, progress=None) -> dict:
    started = time.monotonic()
    notify = progress or (lambda event: None)
    with tempfile.TemporaryDirectory(prefix="nebula-web-") as temporary:
        work = Path(temporary)
        data_dir, output_dir = work / "data", work / "output"
        data_dir.mkdir(); output_dir.mkdir()
        _safe_extract(input_zip, data_dir, INPUT_FILES)
        instance = load_instance(data_dir)
        notify({"phase": "solving", "message": f"Loaded {len(instance.activities)} activities across {len(instance.projects)} contracts. Solving scenario {scenario}.",
                "activities": len(instance.activities), "contracts": len(instance.projects),
                "work_units": sum(a.total_accesses for a in instance.activities.values())})
        budget = float(os.environ.get("NEBULA_SOLVE_SECONDS", "180"))
        options = dict(allow_repeat_accesses=True,
                       workers=int(os.environ.get("NEBULA_SOLVER_WORKERS", "2")),
                       seed=int(os.environ.get("NEBULA_SOLVER_SEED", "1")),
                       closure_round_limit=500, progress_callback=notify)
        zero_dir = work / "zero-search"
        zero_report = None
        try:
            zero_report = solve_flexible_supply_relaxation(
                instance, zero_dir, scenario, zero_only=True,
                time_limit_seconds=min(45, budget * .3), **options)
        except ValueError as exc:
            if "no eligible week" not in str(exc):
                raise
        zero_valid = False
        if (zero_dir / "RESULTS.csv").exists():
            check = evaluate_submission(instance, zero_dir, scenario)
            zero_valid = check.internally_feasible and check.objective_score == 0
        if zero_valid:
            telemetry = zero_report
            for name in OUTPUT_FILES:
                shutil.copyfile(zero_dir / name, output_dir / name)
        else:
            notify({"phase": "solving", "message": "The initial search did not find a zero-penalty schedule. Optimizing the scenario's permitted trade-offs."})
            telemetry = solve_flexible_supply_relaxation(
                instance, output_dir, scenario,
                time_limit_seconds=max(1, budget - (time.monotonic() - started)), **options)
        if not (output_dir / "RESULTS.csv").is_file():
            raise RuntimeError("No complete schedule was found within the search budget. Try a longer planning horizon or a smaller instance.")
        notify({"phase": "validating", "message": "Checking the generated schedule, independently recomputing its score, and preparing the result views."})
        solver_report = {**asdict(telemetry), "zero_first": True,
                         "zero_search": asdict(zero_report) if zero_report else None,
                         "sample_hint_used": False}
        return _result(instance, output_dir, scenario, started,
                       "Computed from uploaded data with CP-SAT", solver_report)


def _reference(scenario):
    if scenario not in {"A", "B", "C"} or not _readiness().get("scenarios", {}).get(scenario, {}).get("ready"):
        raise HTTPException(status_code=404, detail="Accepted reference is unavailable.")
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="nebula-reference-") as temporary:
        output = Path(temporary)
        _extract_file_archive(BASELINE_ROOT / f"{scenario}.zip", output, OUTPUT_FILES)
        return _result(load_instance(PUBLIC_DATA_ROOT), output, scenario, started,
                       "Organizer-accepted public schedule", {"status": "REFERENCE", "primary_score_proven_optimal": True,
                       "best_bound": 0, "solve_rounds": 0, "model_variables": 0}, reference=True)


@app.get("/api/reference/{scenario}")
def reference(scenario: str):
    return _reference(scenario.upper())


@app.get("/api/example")
def example():
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for name in sorted(INPUT_FILES):
            archive.writestr(name, (PUBLIC_DATA_ROOT / name).read_bytes())
    return Response(buffer.getvalue(), media_type="application/zip",
                    headers={"Content-Disposition": 'attachment; filename="NightShift-public-input.zip"'})


@app.get("/api/health")
def health() -> dict:
    return {
        "ok": True,
        "service": "nightshift",
        "version": app.version,
        "public_dataset_available": PUBLIC_DATASET_HASH is not None,
    }


@app.get("/api/readiness")
def readiness() -> dict:
    payload = _readiness()
    return {
        "all_ready": bool(payload.get("all_ready")),
        "dataset_hash": payload.get("dataset_hash"),
        "scenarios": payload.get("scenarios", {}),
        "input_files": sorted(INPUT_FILES),
        "output_files": sorted(OUTPUT_FILES),
    }


@app.post("/api/solve")
async def solve(file: UploadFile = File(...), scenario: str = Form(...)) -> dict:
    selected = scenario.upper().strip()
    if selected not in {"A", "B", "C"}:
        raise HTTPException(status_code=400, detail="Scenario must be A, B, or C.")
    if not file.filename or not file.filename.lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="Upload one ZIP containing the eight required CSV files.")
    payload = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(payload) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Input ZIP exceeds the 32 MiB limit.")
    async with SOLVER_SEMAPHORE:
        try:
            return await run_in_threadpool(_solve, payload, selected)
        except (InputError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except RuntimeError as exc:
            LOGGER.exception("Solver run failed")
            raise HTTPException(status_code=422, detail=str(exc)) from exc


ACTIVE_RUNS = set()

@app.post("/api/solve-stream")
async def solve_stream(file: UploadFile = File(...), scenario: str = Form(...)):
    selected = scenario.upper().strip()
    if selected not in {"A", "B", "C"}:
        raise HTTPException(status_code=400, detail="Scenario must be A, B, or C.")
    payload = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(payload) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Input ZIP exceeds the upload limit.")
    events = asyncio.Queue()
    loop = asyncio.get_running_loop()
    def notify(event):
        loop.call_soon_threadsafe(events.put_nowait, {"type": "progress", **event})
    async def work():
        try:
            async with SOLVER_SEMAPHORE:
                result = await run_in_threadpool(_solve, payload, selected, notify)
            await events.put({"type": "result", "data": result})
        except (InputError, ValueError, RuntimeError) as exc:
            await events.put({"type": "error", "message": str(exc)})
        except Exception:
            LOGGER.exception("Planning request failed")
            await events.put({"type": "error", "message": "The planning service encountered an error. No result was released."})
        finally:
            await events.put(None)
    task = asyncio.create_task(work())
    ACTIVE_RUNS.add(task)
    task.add_done_callback(ACTIVE_RUNS.discard)
    async def stream():
        yield json.dumps({"type": "progress", "phase": "queued", "message": "Input received. Waiting for the planning engine."}) + "\n"
        while True:
            try:
                event = await asyncio.wait_for(events.get(), timeout=10)
            except asyncio.TimeoutError:
                yield json.dumps({"type": "heartbeat"}) + "\n"
                continue
            if event is None:
                break
            yield json.dumps(event) + "\n"
    return StreamingResponse(stream(), media_type="application/x-ndjson",
                             headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"})


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_ROOT / "index.html")


app.mount("/static", StaticFiles(directory=STATIC_ROOT), name="static")

from .control import register_control
register_control(app)
