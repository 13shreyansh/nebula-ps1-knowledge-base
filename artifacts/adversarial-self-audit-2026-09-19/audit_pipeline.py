"""Exercise existing code read-only; temporary files are never submitted."""
import csv
import io
import json
import zipfile
from pathlib import Path
from unittest.mock import patch
from nebula_ps1 import closure, web
from nebula_ps1.instance import load_instance
from nebula_ps1.evaluate import evaluate_submission, load_submission
from nebula_ps1.independent_score import independently_score

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
DATA=ROOT/'current-problem-statement/PS1/01_data'
instance=load_instance(DATA)
report={'portal_used':False,'production_modified':False,'zero':{},'friend':{},'web':{}}
original=closure._blocked_locations
def expanded(i,component):
    blocked=original(i,component)
    for aid in component:
        if i.projects[i.activities[aid].contract_number].nature_of_activity!='Live':continue
        for loc in original(i,{aid}):
            if loc.startswith('SEC:'):
                _,line,sector,bound=loc.split(':');s=i.sectors[f'SEC:{line}:{sector}']
                blocked.update(f'PLAT:{line}:{station}:{bound}' for station in (s.from_station_id,s.to_station_id))
    return blocked
for s in 'ABC':
    path=ROOT/f'deliverables/official-zero/{s}'
    evaluation=evaluate_submission(instance,path,s)
    a,o,_=load_submission(path)
    try: independent=json.loads(independently_score(DATA,path).as_json())
    except Exception as e:independent={'exception':type(e).__name__,'message':str(e)}
    with patch.object(closure,'_blocked_locations',expanded):
        corrected=evaluate_submission(instance,path,s)
        strict=closure.screen_closures(instance,a,o,forbid_buffer_overlap=True)
    report['zero'][s]={'legacy':json.loads(evaluation.as_json()),'independent':independent,'expanded_violations':list(corrected.hard_violations),'strict_buffer_conflict_count':len(strict)}
    friend=ROOT/f'artifacts/friend-portal-audit-2026-09-19/submissions/{s}'
    base=evaluate_submission(instance,friend,s)
    with patch.object(closure,'_blocked_locations',expanded):fixed=evaluate_submission(instance,friend,s)
    report['friend'][s]={'legacy_violations':len(base.hard_violations),'expanded_violations':len(fixed.hard_violations),'score':fixed.objective_score}
def pack(reverse=False):
    out=io.BytesIO()
    with zipfile.ZipFile(out,'w') as z:
        for p in sorted(DATA.glob('*.csv')):
            content=p.read_bytes()
            if reverse:
                rows=list(csv.reader(io.StringIO(content.decode('utf-8-sig'))))
                serialized=io.StringIO(newline='')
                writer=csv.writer(serialized,lineterminator='\n')
                writer.writerow(rows[0]);writer.writerows(reversed(rows[1:]))
                content=serialized.getvalue().encode()
            z.writestr(p.name,content)
    return out.getvalue()
class ComputeBranchReached(Exception):pass
for s in 'ABC':
    with patch.object(web,'solve_candidate_portfolio',side_effect=ComputeBranchReached('computed branch reached')) as mocked:
        result=web._solve(pack(),s)
        report['web'][s]={'method':result['method'],'score':result['validation']['objective_score'],'reference_confirmed':result['validation']['reference_validator_confirmed'],'compute_called':mocked.called,'seconds':result['duration_seconds']}
with patch.object(web,'solve_candidate_portfolio',side_effect=ComputeBranchReached('computed branch reached')):
    try:web._solve(pack(reverse=True),'B')
    except ComputeBranchReached:report['web']['row_reversed_control']='equivalent rows bypass public cache and reach compute branch; solver deliberately not run'
report['limitations']='Expanded closures use the earlier inferred correction, not an independent official validator. Web compute branch was intercepted; this test does not measure hidden-input solving.'
(OUT/'pipeline-audit.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'zero':{s:{k:v for k,v in r.items() if k!='legacy'} for s,r in report['zero'].items()},'friend':report['friend'],'web':report['web']},indent=2))
