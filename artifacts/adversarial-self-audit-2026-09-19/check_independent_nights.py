"""A separate CP-SAT consistency test of physical-night semantics, no optimizer imports."""
import csv
import json
from collections import defaultdict
from pathlib import Path
from ortools.sat.python import cp_model

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
def read(p):
    with p.open() as f:return list(csv.DictReader(f))
access=read(ROOT/'deliverables/official-zero/A/SCHEDULE_ACCESS.csv')
occ=read(ROOT/'deliverables/official-zero/A/SCHEDULE_OCCUPANCY.csv')
acts={r['activity_id']:r for r in read(ROOT/'current-problem-statement/PS1/01_data/08_ACTIVITY_DETAILS.csv')}
byaw=defaultdict(list)
for r in access:byaw[r['activity_id'],int(r['week'])].append(r)
reports=[]
for w in sorted({int(r['week']) for r in access}):
    single={aid:rr[0] for (aid,ww),rr in byaw.items() if ww==w and len(rr)==1}
    model=cp_model.CpModel()
    physical={aid:model.new_int_var(0,6,aid) for aid in single}
    byloc=defaultdict(list)
    for r in occ:
        if int(r['week'])==w and r['activity_id'] in single:byloc[r['location_id']].append(r)
    for loc,rr in byloc.items():
        for i,a in enumerate(rr):
            for b in rr[i+1:]:
                if a['co_share_group']==b['co_share_group']:model.add(physical[a['activity_id']]==physical[b['activity_id']])
                else:model.add(physical[a['activity_id']]!=physical[b['activity_id']])
    aa=sorted(single)
    for i,aid in enumerate(aa):
        for bid in aa[i+1:]:
            if (acts[aid]['contract_number'],acts[aid]['activity_type'])!=(acts[bid]['contract_number'],acts[bid]['activity_type']):continue
            if single[aid]['access_night']==single[bid]['access_night']:model.add(physical[aid]==physical[bid])
            else:model.add(physical[aid]!=physical[bid])
    solver=cp_model.CpSolver();solver.parameters.num_search_workers=1;solver.parameters.max_time_in_seconds=5
    status=solver.solve(model)
    reports.append({'week':w,'status':solver.status_name(status),'single_visit_activities':len(single),'seconds':solver.wall_time})
payload={'assumptions':['an activity access occupies its corridor on one physical night','same co-share group at a location-week means same night','different groups at the same location-week mean different nights','contract-local night indices map consistently to physical nights within that contract/type/week'],'limitations':'Does not test official implementation. Multi-visit activities are removed, which relaxes this model. No closure or capacity constraints are needed for these contradictions.','weeks':reports}
(OUT/'night-cp-sat.json').write_text(json.dumps(payload,indent=2)+'\n')
print(json.dumps(payload,indent=2))
