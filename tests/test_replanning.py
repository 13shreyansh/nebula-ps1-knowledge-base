import base64, io, zipfile, json
from fastapi.testclient import TestClient
from test_live_engine import tiny_instance
from nebula_ps1.web import app, _zip_submission
from nebula_ps1.instance import load_instance
from nebula_ps1.flexible_solver import solve_flexible_supply_relaxation
from nebula_ps1.evaluate import load_submission, evaluate_submission
from nebula_ps1.topology import activity_footprint


def test_real_recovery_closes_week_one_and_moves_work(tmp_path):
    data=tiny_instance(tmp_path); instance=load_instance(data); old=tmp_path/'old'
    solve_flexible_supply_relaxation(instance,old,'A',allow_repeat_accesses=True,time_limit_seconds=5,workers=1)
    loc=next(iter(activity_footprint(instance,next(iter(instance.activities.values())))))
    buffer=io.BytesIO()
    with zipfile.ZipFile(buffer,'w') as z:
        for p in data.iterdir(): z.writestr(p.name,p.read_bytes())
    payload={'scenario':'A','input_base64':base64.b64encode(buffer.getvalue()).decode(),'baseline_base64':base64.b64encode(_zip_submission(old)).decode(),'incidents':[{'location_id':loc,'from_week':1,'to_week':1,'capacity':0}],'freeze_before_week':1}
    response=TestClient(app).post('/api/replan-stream',json=payload)
    events=[json.loads(s) for s in response.text.splitlines()]
    assert not any(e['type']=='error' for e in events),events
    result=next(e['data'] for e in events if e['type']=='result')
    a=result['insights']['activities'][0]
    assert all(v['week']==2 for v in a['visits'])
    assert result['comparison']['changed_activities']==['work-custom']
    assert result['comparison']['history_preserved']
    assert result['validation']['objective_score']>0


def test_voice_rejects_invalid_sdp():
    r=TestClient(app).post('/api/voice/session',json={'sdp':'bad'})
    assert r.status_code==400
