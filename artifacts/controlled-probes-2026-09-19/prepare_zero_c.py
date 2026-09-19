"""Test whether standard repeat visits can replace all ECLO work, using the
activity/week occupancy encoding accepted by official B1. No upload here.
"""
from collections import defaultdict
from dataclasses import asdict, replace
import csv
import hashlib
import json
from pathlib import Path
import zipfile
from nebula_ps1 import closure
from nebula_ps1.evaluate import load_submission, evaluate_submission, AccessRow
from nebula_ps1.instance import load_instance

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
I=load_instance(ROOT/'current-problem-statement/PS1/01_data')
access, occupancy, results=load_submission(OUT/'baseline/B')
access=[replace(r,eclo=0) for r in access]
added=[]
for aid,week in [('A036',22),('A036',23),('A059',14)]:
    activity=I.activities[aid]; project=I.projects[activity.contract_number]
    used_by_activity={r.access_night for r in access if r.activity_id==aid and r.week==week}
    for night in range(1,project.number_of_maximum_access_per_week+1):
        if night in used_by_activity:continue
        users={r.activity_id for r in access if r.week==week and r.access_night==night and I.activities[r.activity_id].contract_number==activity.contract_number and I.activities[r.activity_id].activity_type==activity.activity_type}
        if len(users)+1>project.number_of_workfronts:continue
        row=AccessRow(aid,0,week,0,night)
        access.append(row);added.append(asdict(row));break
    else:raise AssertionError((aid,week,'no spare permitted contract night'))
groups=defaultdict(list)
for row in access:groups[row.activity_id].append(row)
access=[replace(row,access_seq=seq) for aid, rows in sorted(groups.items()) for seq,row in enumerate(sorted(rows,key=lambda r:(r.week,r.access_night)),1)]
results=[replace(r,scenario='C') for r in results]
dest=OUT/'C1-zero-score-repeat-standard'
dest.mkdir(exist_ok=True)
for filename,rows in [('SCHEDULE_ACCESS.csv',access),('SCHEDULE_OCCUPANCY.csv',occupancy),('RESULTS.csv',results)]:
    dictionaries=[asdict(r) for r in rows]
    with (dest/filename).open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(dictionaries[0]),lineterminator='\n');w.writeheader();w.writerows(dictionaries)
original=closure._blocked_locations
def corrected(instance,component):
    blocked=original(instance,component)
    for aid in component:
        if instance.projects[instance.activities[aid].contract_number].nature_of_activity!='Live':continue
        for loc in original(instance,{aid}):
            if loc.startswith('SEC:'):
                _,line,sid,bound=loc.split(':');sector=instance.sectors[f'SEC:{line}:{sid}']
                blocked.update(f'PLAT:{line}:{station}:{bound}' for station in (sector.from_station_id,sector.to_station_id))
    return blocked
closure._blocked_locations=corrected
evaluation=evaluate_submission(I,dest,'C')
assert set(evaluation.hard_violations)=={'A036: more than one access in week 22','A036: more than one access in week 23','A059: more than one access in week 14'}, evaluation.hard_violations
assert evaluation.objective_score==0
assert len(access)==sum(a.total_accesses for a in I.activities.values())==192
assert not any(r.eclo for r in access)
assert len({(r.activity_id,r.week,r.access_night) for r in access})==len(access)
assert not any(r.overrun_days for r in results)
archive=dest.with_suffix('.zip')
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
    for name in ('SCHEDULE_ACCESS.csv','SCHEDULE_OCCUPANCY.csv','RESULTS.csv'):z.write(dest/name,name)
manifest=json.loads((OUT/'manifest.json').read_text())
manifest['probes']['C1']={'archive':str(archive),'sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'question':'Does C allow repeat standard visits using the activity/week occupancy representation accepted in B1?','starting_point':'Previously official-feasible B-001 CSVs, relabelled C','changes':'Replace six ECLO rows with standard work and add three standard visits; retain all occupied activity-weeks and completion dates.','added_rows_before_resequencing':added,'local_violations':list(evaluation.hard_violations),'expected_score_if_allowed':0,'work_units':192,'capacity_caveat':'A036 has a footprint location of nominal supply one; submitted distinct sharing groups remain within capacity. Acceptance would establish this representation passes the portal, not settle whether physical nightly capacity should charge repeated accesses separately.'}
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
(OUT/'C1-local-evaluation.json').write_text(evaluation.as_json()+'\n')
print(json.dumps(manifest['probes']['C1'],indent=2))
