import csv
import io
import json
import zipfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from nebula_ps1.evaluate import evaluate_submission
from nebula_ps1.flexible_solver import solve_flexible_supply_relaxation
from nebula_ps1.independent_score import independently_score
from nebula_ps1.instance import FILES, load_instance
from nebula_ps1.web import PUBLIC_DATA_ROOT, app


def write_rows(path, rows):
    with path.open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator='\n')
        writer.writeheader(); writer.writerows(rows)


def tiny_instance(tmp_path, workload=2, cap=2):
    data = tmp_path / 'data'; data.mkdir()
    for name in FILES.values():
        (data / name).write_bytes((PUBLIC_DATA_ROOT / name).read_bytes())
    activities = list(csv.DictReader((data / FILES['activities']).open()))
    a = dict(activities[0], activity_id='work-custom', contract_number='contract-custom',
             total_accesses=str(workload), planned_start_date='2027-01-04', predecessor_activity_id='')
    projects = list(csv.DictReader((data / FILES['projects']).open()))
    project = dict(projects[0], contract_number='contract-custom', planned_completion_date='2027-01-10',
                   number_of_maximum_access_per_week=str(cap))
    write_rows(data / FILES['activities'], [a]); write_rows(data / FILES['projects'], [project])
    write_rows(data / FILES['parameters'], [{'key':'horizon_start','value':'2027-01-04'}, {'key':'horizon_weeks','value':'2'}])
    return data


@pytest.mark.parametrize('scenario', ['A', 'B', 'C'])
def test_repeat_visits_are_computed_on_unseen_ids(tmp_path, scenario):
    data = tiny_instance(tmp_path)
    instance = load_instance(data); output = tmp_path / 'result'
    report = solve_flexible_supply_relaxation(instance, output, scenario,
        allow_repeat_accesses=True, zero_only=True, time_limit_seconds=5, workers=1)
    assert report.primary_score_proven_optimal
    assert report.model_variables > 0
    evaluation = evaluate_submission(instance, output, scenario)
    assert evaluation.internally_feasible, evaluation.hard_violations
    assert independently_score(data, output).objective_score == 0
    rows = list(csv.DictReader((output / 'SCHEDULE_ACCESS.csv').open()))
    assert {(r['week'], r['access_night']) for r in rows} == {('1','1'),('1','2')}


def test_eclo_is_counted_per_visit(tmp_path):
    data = tiny_instance(tmp_path, workload=3)
    instance = load_instance(data); output = tmp_path / 'result'
    solve_flexible_supply_relaxation(instance, output, 'B', allow_repeat_accesses=True,
                                    time_limit_seconds=5, workers=1)
    e = evaluate_submission(instance, output, 'B')
    assert e.internally_feasible
    assert e.eclo_nights_total == 2
    assert e.objective_score == independently_score(data, output).objective_score == 10


def test_stream_runs_real_solver_and_views_match_csv(tmp_path, monkeypatch):
    data = tiny_instance(tmp_path)
    monkeypatch.setenv('NEBULA_SOLVE_SECONDS', '5')
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w') as z:
        for path in data.iterdir(): z.writestr(path.name, path.read_bytes())
    response = TestClient(app).post('/api/solve-stream', data={'scenario':'B'},
        files={'file':('new-input.zip', buffer.getvalue(), 'application/zip')})
    assert response.status_code == 200
    events = [json.loads(line) for line in response.text.splitlines()]
    assert any(e.get('phase') == 'solving' for e in events)
    assert not any(e['type'] == 'error' for e in events), events
    result = next(e['data'] for e in events if e['type'] == 'result')
    assert result['solver']['model_variables'] > 0
    assert result['validation']['reference_validator_confirmed'] is False
    assert result['insights']['summary']['delivered_work'] == 2
    assert result['insights']['contracts'][0]['id'] == 'contract-custom'
    assert result['validation']['objective_score'] == 0


def test_duplicate_visit_is_rejected(tmp_path):
    data = tiny_instance(tmp_path); i = load_instance(data); output = tmp_path/'result'
    solve_flexible_supply_relaxation(i, output, 'B', allow_repeat_accesses=True, time_limit_seconds=5, workers=1)
    p = output/'SCHEDULE_ACCESS.csv'; rows = list(csv.DictReader(p.open()))
    rows[1]['access_night'] = rows[0]['access_night']; write_rows(p, rows)
    assert any('duplicate access night' in e for e in evaluate_submission(i, output, 'B').hard_violations)


def test_zero_archives_pass_updated_checker():
    i = load_instance(PUBLIC_DATA_ROOT)
    for scenario in 'ABC':
        directory = PUBLIC_DATA_ROOT.parents[2]/'deliverables'/'official-zero'/scenario
        evaluation = evaluate_submission(i, directory, scenario)
        assert evaluation.internally_feasible, evaluation.hard_violations
        assert independently_score(PUBLIC_DATA_ROOT, directory).objective_score == 0
