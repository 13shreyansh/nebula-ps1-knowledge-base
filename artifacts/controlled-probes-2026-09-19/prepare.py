"""Prepare inspectable, isolated rule probes. Never submits to a portal."""
from collections import defaultdict
from dataclasses import asdict, replace
import csv
import hashlib
import json
from pathlib import Path
import zipfile

from nebula_ps1 import closure
from nebula_ps1.evaluate import load_submission, evaluate_submission
from nebula_ps1.instance import load_instance
from nebula_ps1.topology import activity_footprint

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
I = load_instance(ROOT / 'current-problem-statement/PS1/01_data')
FILES = ('SCHEDULE_ACCESS.csv','SCHEDULE_OCCUPANCY.csv','RESULTS.csv')
old_blocked = closure._blocked_locations
def corrected_blocked(instance, component):
    blocked = old_blocked(instance, component)
    for aid in component:
        if instance.projects[instance.activities[aid].contract_number].nature_of_activity != 'Live':
            continue
        for loc in old_blocked(instance, {aid}):
            if loc.startswith('SEC:'):
                _, line, sid, bound = loc.split(':')
                sector = instance.sectors[f'SEC:{line}:{sid}']
                blocked.update(f'PLAT:{line}:{station}:{bound}' for station in (sector.from_station_id,sector.to_station_id))
    return blocked
closure._blocked_locations = corrected_blocked

def write_rows(destination, access, occupancy, results):
    destination.mkdir(parents=True, exist_ok=True)
    for filename, rows in zip(FILES, (access,occupancy,results)):
        dictionaries = [asdict(row) for row in rows]
        with (destination/filename).open('w',newline='') as handle:
            writer=csv.DictWriter(handle,fieldnames=list(dictionaries[0]),lineterminator='\n')
            writer.writeheader();writer.writerows(dictionaries)

def package(destination):
    archive_path=destination.with_suffix('.zip')
    with zipfile.ZipFile(archive_path,'w',zipfile.ZIP_DEFLATED) as archive:
        for filename in FILES:archive.write(destination/filename,filename)
    return {'archive':str(archive_path),'sha256':hashlib.sha256(archive_path.read_bytes()).hexdigest()}

baselines={}
for scenario in 'BC':
    dest=OUT/'baseline'/scenario
    dest.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(ROOT/'deliverables/final-submission'/f'{scenario}.zip') as archive:
        for name in FILES:(dest/name).write_bytes(archive.read(name))
    assert evaluate_submission(I,dest,scenario).internally_feasible
    baselines[scenario]=load_submission(dest)

access,occupancy,results=baselines['B']
groups=defaultdict(set);location_groups=defaultdict(set);by_activity=defaultdict(list)
for row in occupancy:
    groups[(row.week,row.location_id,row.co_share_group)].add(row.activity_id)
    location_groups[(row.week,row.location_id)].add(row.co_share_group)
for row in access:by_activity[row.activity_id].append(row)
manifest={'budget':{'initial_remaining':{'A':2,'B':3,'C':3},'reserved_final_per_scenario':1,'first_phase_max_uploads':{'A':0,'B':1,'C':1},'total_experimental_ceiling':4},'probes':{}}
for aid, rows in sorted(by_activity.items()):
    rows=sorted(rows,key=lambda r:r.access_seq)
    activity=I.activities[aid];project=I.projects[activity.contract_number]
    if len(rows)<3 or rows[0].eclo or rows[1].eclo or activity.predecessor_activity_id:continue
    first,second=rows[:2]
    footprint=activity_footprint(I,activity)
    # Even if the repeated access consumes a separate location slot, supply has room.
    if any(len(location_groups[(first.week,loc)])+1>I.locations[loc].supply_capacity for loc in footprint):continue
    # Removal must not destroy another activity's sharing bridge.
    old_occupancy=[r for r in occupancy if r.activity_id==aid and r.week==second.week]
    if any(len(groups[(r.week,r.location_id,r.co_share_group)])!=1 for r in old_occupancy):continue
    for night in range(1,project.number_of_maximum_access_per_week+1):
        if night==first.access_night:continue
        modified=[replace(r,week=first.week,access_night=night) if r==second else r for r in access]
        modified_occupancy=[r for r in occupancy if not (r.activity_id==aid and r.week==second.week)]
        dest=OUT/'B1-two-accesses-same-week'
        write_rows(dest,modified,modified_occupancy,results)
        evaluation=evaluate_submission(I,dest,'B')
        if evaluation.hard_violations!=(f'{aid}: more than one access in week {first.week}',):continue
        manifest['probes']['B1']={**package(dest),'question':'May one activity take two distinct allocated nights in one week in B?', 'baseline_official_score':30,'expected_score_if_allowed':evaluation.objective_score,'activity':aid,'contract':activity.contract_number,'contract_weekly_cap':project.number_of_maximum_access_per_week,'old_row':asdict(second),'new_row':asdict(replace(second,week=first.week,access_night=night)),'other_access_same_week':asdict(first),'occupancy_encoding':'One complete footprint per activity/week, per existing occupancy schema; no access_night column exists there.','local_violations':list(evaluation.hard_violations),'interpretation':'Explicit duplicate activity/week rejection settles this representation. Occupancy-only rejection would leave encoding ambiguity; acceptance alone would not establish physical slot accounting.'}
        break
    if 'B1' in manifest['probes']:break
assert 'B1' in manifest['probes'],'No isolated B duplicate-week probe found'
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps(manifest,indent=2))
