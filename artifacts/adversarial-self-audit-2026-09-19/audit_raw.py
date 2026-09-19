"""Read-only audit of input/submission bytes; writes only this audit's report.

No project parser, topology helper, scorer, or validator imports. Physical-night
checks explicitly assume that a co-share group represents a single night and
an activity's corridor is occupied on that same night. They are not assertions
about what the unavailable official validator implements.
"""
import csv
import hashlib
import io
import json
import zipfile
from collections import Counter, defaultdict
from datetime import date, timedelta, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
DATA = ROOT / 'current-problem-statement/PS1/01_data'

def read(path):
    with path.open(newline='', encoding='utf-8-sig') as f:
        return list(csv.DictReader(f))

activities = {r['activity_id']: r for r in read(DATA/'08_ACTIVITY_DETAILS.csv')}
projects = {r['contract_number']: r for r in read(DATA/'07_PROJECT_DETAILS.csv')}
sectors = {r['sector_id']: r for r in read(DATA/'03_SECTORS.csv')}
supplies = {r['location_id']: int(r['supply_capacity']) for r in read(DATA/'04_LOCATION_SUPPLY.csv')}
params = {r['key']: r['value'] for r in read(DATA/'06_PARAMETERS.csv')}
start = date.fromisoformat(params['horizon_start'])
footprints = {}
for aid, a in activities.items():
    _, line, first, bound = a['start_location_id'].split(':')
    _, last_line, last, last_bound = a['end_location_id'].split(':')
    assert (line,bound)==(last_line,last_bound)
    lo,hi=sorted([int(sectors[f'SEC:{line}:{s}']['seq']) for s in (first,last)])
    corridor=[s for s in sectors.values() if s['line_code']==line and lo<=int(s['seq'])<=hi]
    assert len(corridor)==hi-lo+1
    footprints[aid]={f"{s['sector_id']}:{bound}" for s in corridor}
    footprints[aid].update(f"PLAT:{line}:{s[k]}:{bound}" for s in corridor for k in ('from_station_id','to_station_id'))

def audit(directory):
    access=read(directory/'SCHEDULE_ACCESS.csv')
    occupancy=read(directory/'SCHEDULE_OCCUPANCY.csv')
    results=read(directory/'RESULTS.csv')
    errors=[]
    by=defaultdict(list); byweek=defaultdict(list); byaw=defaultdict(list)
    for r in access:
        aid=r['activity_id'];w=int(r['week']);n=int(r['access_night'])
        if aid not in activities: errors.append(['unknown_activity',aid]);continue
        by[aid].append(r);byweek[w].append(r);byaw[aid,w].append(r)
        p=projects[activities[aid]['contract_number']]
        if not (1<=w<=int(params['horizon_weeks'])):errors.append(['horizon',aid,w])
        if not (1<=n<=int(p['number_of_maximum_access_per_week'])):errors.append(['night_range',aid,w,n])
        if r['eclo'] not in ('0','1'):errors.append(['eclo',aid,w])
    if set(by)!=set(activities):errors.append(['coverage'])
    keys=[(r['activity_id'],r['week'],r['access_night']) for r in access]
    if len(set(keys))!=len(keys):errors.append(['duplicate_access_night'])
    for aid,a in activities.items():
        rr=sorted(by[aid],key=lambda r:(int(r['week']),int(r['access_night'])))
        if not rr:continue
        if [int(r['access_seq']) for r in rr]!=list(range(1,len(rr)+1)):errors.append(['sequence',aid])
        units=sum(2+int(r['eclo']) for r in rr)
        if units!=2*int(a['total_accesses']):errors.append(['exact_workload',aid,units])
        startweek=(date.fromisoformat(a['planned_start_date'])-start).days//7+1
        if int(rr[0]['week'])<startweek:errors.append(['early_start',aid])
        pred=a['predecessor_activity_id']
        if pred and int(rr[0]['week'])<=max(int(r['week']) for r in by[pred]):errors.append(['precedence',aid,pred])
    expected={(aid,w,loc) for aid,w in byaw for loc in footprints[aid]}
    actual=[(r['activity_id'],int(r['week']),r['location_id']) for r in occupancy]
    if len(actual)!=len(set(actual)):errors.append(['duplicate_occupancy'])
    if set(actual)!=expected:errors.append(['footprint',len(expected-set(actual)),len(set(actual)-expected)])
    workfronts=defaultdict(set);nights=defaultdict(set)
    for r in access:
        a=activities[r['activity_id']];key=(a['contract_number'],a['activity_type'],int(r['week']))
        nights[key].add(int(r['access_night']))
        workfronts[key+(int(r['access_night']),)].add(r['activity_id'])
    for key,ns in nights.items():
        if len(ns)>int(projects[key[0]]['number_of_maximum_access_per_week']):errors.append(['contract_nights',key])
    for key,aa in workfronts.items():
        if len(aa)>int(projects[key[0]]['number_of_workfronts']):errors.append(['workfront',key])
    finish={aid:start+timedelta(days=7*max(int(r['week']) for r in rr)-1) for aid,rr in by.items()}
    if len(results)!=len(projects) or {r['contract_number'] for r in results}!=set(projects):errors.append(['results_coverage'])
    for r in results:
        c=r['contract_number'];done=max(finish[aid] for aid,a in activities.items() if a['contract_number']==c)
        overrun=max(0,(done-date.fromisoformat(projects[c]['planned_completion_date'])).days)
        if (r['simulated_completion_date'],int(r['overrun_days']))!=(done.isoformat(),overrun):errors.append(['result_mismatch',c])
    groups=defaultdict(list);locgroups=defaultdict(set);locrows=defaultdict(list)
    for r in occupancy:
        w=int(r['week']);loc=r['location_id'];g=r['co_share_group']
        groups[w,loc,g].append(r['activity_id']);locgroups[w,loc].add(g);locrows[w,loc].append(r)
    for key,aa in groups.items():
        kinds=Counter(projects[activities[aid]['contract_number']]['access_type'] for aid in aa)
        legal=(kinds['PM']==1 and len(aa)==1) or (kinds['PM']==0 and kinds['PC']==1 and kinds['C']<=3) or (kinds['PM']==0 and kinds['PC']==0 and kinds['C']<=4)
        if not legal:errors.append(['illegal_mix',key,dict(kinds)])
    capacity_lower_bounds=[]
    for (aid,w),rr in byaw.items():
        for loc in sorted(footprints[aid]):
            if len(rr)>supplies[loc]:capacity_lower_bounds.append({'activity':aid,'week':w,'location':loc,'required_distinct_nights':len(rr),'supply':supplies[loc]})
    # Test single-visit components only. Repeated-visit components need a richer
    # occurrence-to-occupancy schema and are excluded from these witnesses.
    contradictions=[];component_stats=[]
    for w,rr in sorted(byweek.items()):
        parent={r['activity_id']:r['activity_id'] for r in rr}
        def find(a):
            while parent[a]!=a:
                parent[a]=parent[parent[a]];a=parent[a]
            return a
        def union(a,b):parent[find(b)]=find(a)
        for (ww,loc,g),aa in groups.items():
            if ww==w:
                for aid in aa[1:]:union(aa[0],aid)
        comps=defaultdict(list)
        for aid in parent:comps[find(aid)].append(aid)
        component_stats.append({'week':w,'sizes':sorted(map(len,comps.values()),reverse=True)})
        for component in comps.values():
            if any(len(byaw[aid,w])!=1 for aid in component):continue
            contract_nights=defaultdict(list)
            for aid in component:
                a=activities[aid];r=byaw[aid,w][0]
                contract_nights[a['contract_number'],a['activity_type']].append((aid,int(r['access_night'])))
            for key,pairs in contract_nights.items():
                if len({n for aid,n in pairs})>1:contradictions.append({'kind':'same_possession_different_contract_nights','week':w,'component':sorted(component),'contract_type':key,'assignments':pairs})
            for (ww,loc),ors in locrows.items():
                if ww!=w:continue
                subset=[r for r in ors if r['activity_id'] in component]
                if len({r['co_share_group'] for r in subset})>1:contradictions.append({'kind':'same_night_different_possession_groups','week':w,'location':loc,'component':sorted(component),'assignments':[(r['activity_id'],r['co_share_group']) for r in subset]})
    return {'basic_errors':errors,'activities':len(by),'access_rows':len(access),'occupancy_rows':len(occupancy),'eclo_rows':sum(int(r['eclo']) for r in access),'group_count_excess':sum(max(0,len(gs)-supplies[loc]) for (w,loc),gs in locgroups.items()),'repeated_visits':[{'activity':aid,'week':w,'nights':[int(r['access_night']) for r in rr]} for (aid,w),rr in byaw.items() if len(rr)>1],'physical_capacity_lower_bound_witnesses':capacity_lower_bounds,'single_visit_night_consistency_witnesses':contradictions,'component_stats':component_stats}

report={'timestamp':datetime.now(timezone.utc).isoformat(),'portal_used':False,'assumption':'co-sharing synchronizes physical nights across an activity corridor; different groups at the same location-week are different nights','inputs_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(DATA.glob('*.csv'))},'audits':{}}
manifest=json.loads((ROOT/'deliverables/official-zero/MANIFEST.json').read_text())
for s in 'ABC':
    directory=ROOT/f'deliverables/official-zero/{s}'
    archive=directory.with_suffix('.zip')
    assert hashlib.sha256(archive.read_bytes()).hexdigest()==manifest['scenarios'][s]['sha256']
    with zipfile.ZipFile(archive) as z:
        assert len(z.namelist())==3 and set(z.namelist())=={'SCHEDULE_ACCESS.csv','SCHEDULE_OCCUPANCY.csv','RESULTS.csv'}
        for name in z.namelist():assert z.read(name)==(directory/name).read_bytes()
    report['audits'][f'zero_{s}']=audit(directory)
report['audits']['historical_B']=audit(ROOT/'artifacts/controlled-probes-2026-09-19/baseline/B')
report['audits']['organizer_sample']=audit(ROOT/'current-problem-statement/PS1/03_submission_sample')
(OUT/'raw-audit.json').write_text(json.dumps(report,indent=2)+'\n')
for name,r in report['audits'].items():
    print(name,{k:v for k,v in r.items() if k not in ('component_stats','single_visit_night_consistency_witnesses')})
    print('night_consistency_witness_count',len(r['single_visit_night_consistency_witnesses']))
    print('first_witnesses',r['single_visit_night_consistency_witnesses'][:3])
