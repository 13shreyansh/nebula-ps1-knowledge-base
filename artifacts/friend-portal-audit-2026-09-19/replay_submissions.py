"""Replay supplied CSV archives locally. Never contacts the official portal."""
from collections import Counter, defaultdict
from dataclasses import asdict
from hashlib import sha256
import json
from pathlib import Path
import zipfile

from nebula_ps1 import closure
from nebula_ps1.evaluate import evaluate_submission, load_submission
from nebula_ps1.instance import load_instance
from nebula_ps1.objective import _combined_contract_weight_tenths

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
FILES = ('SCHEDULE_ACCESS.csv', 'SCHEDULE_OCCUPANCY.csv', 'RESULTS.csv')
INPUTS = {
    'A': Path('/Users/shreyansh/Downloads/A_54_official_violations.zip'),
    'B': Path('/Users/shreyansh/Downloads/B_67_official_65_teammate_violations.zip'),
    'C': Path('/Users/shreyansh/Downloads/C_98.2_official_feasible.zip'),
}
instance = load_instance(ROOT / 'current-problem-statement/PS1/01_data')
observed = json.loads((OUT / 'analysis.json').read_text())
original_blocked = closure._blocked_locations

def candidate_blocked(instance, component):
    result = original_blocked(instance, component)
    for aid in component:
        if instance.projects[instance.activities[aid].contract_number].nature_of_activity != 'Live':
            continue
        for location in original_blocked(instance, {aid}):
            if not location.startswith('SEC:'):
                continue
            _, line, sector_id, bound = location.split(':')
            sector = instance.sectors[f'SEC:{line}:{sector_id}']
            result.update(f'PLAT:{line}:{station}:{bound}' for station in (sector.from_station_id, sector.to_station_id))
    return result

def extract_csvs(source, destination):
    destination.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(source) as archive:
        members = archive.namelist()
        for name in FILES:
            matches = [m for m in members if Path(m).name == name and not m.startswith('__MACOSX/')]
            assert len(matches) == 1, (source, name, matches)
            data = archive.read(matches[0])
            assert len(data) < 10_000_000
            (destination / name).write_bytes(data)
    return members

def signature(conflict):
    assert len(conflict.first_activities) == 1
    return (conflict.week, conflict.first_activities[0], tuple(conflict.second_activities[:3]), tuple(conflict.locations[:4]))

def compare_conflicts(conflicts, scenario):
    expected = Counter((r['week'], r['intruder'], tuple(r['component']), tuple(r['reported_locations'])) for r in observed[scenario]['records'])
    actual = Counter(signature(c) for c in conflicts)
    return {
        'count': len(conflicts), 'matched': sum((expected & actual).values()),
        'official_only': list((expected - actual).elements()),
        'local_only': list((actual - expected).elements()),
        'all_exact_after_display_truncation': actual == expected,
    }

def schedule_summary(directory):
    access, occupancy, results = load_submission(directory)
    by_activity = defaultdict(list)
    for row in access:
        by_activity[row.activity_id].append(row)
    return {
        'access_count': len(access), 'occupancy_count': len(occupancy),
        'eclo': [asdict(r) for r in access if r.eclo],
        'late_contracts': [dict(asdict(r), simulated_completion_date=str(r.simulated_completion_date), delay_cost=r.overrun_days * _combined_contract_weight_tenths(instance, r.contract_number) / 10) for r in results if r.overrun_days],
        'activities': {aid: [asdict(r) for r in sorted(rows, key=lambda x: x.week)] for aid, rows in by_activity.items()},
    }

audit = {'dataset_hash': instance.dataset_hash, 'archives': {}, 'scenarios': {}}
for scenario, source in INPUTS.items():
    raw = source.read_bytes()
    archived = OUT / 'uploaded-archives' / source.name
    archived.parent.mkdir(exist_ok=True)
    archived.write_bytes(raw)
    destination = OUT / 'submissions' / scenario
    members = extract_csvs(source, destination)
    audit['archives'][scenario] = {'source': str(source), 'sha256': sha256(raw).hexdigest(), 'members': members}
    access, occupancy, _ = load_submission(destination)
    baseline = evaluate_submission(instance, destination, scenario)
    base_conflicts = closure.screen_closures(instance, access, occupancy)
    closure._blocked_locations = candidate_blocked
    try:
        expanded = evaluate_submission(instance, destination, scenario)
        expanded_conflicts = closure.screen_closures(instance, access, occupancy)
    finally:
        closure._blocked_locations = original_blocked
    (OUT / f'{scenario}-baseline-evaluation.json').write_text(baseline.as_json() + '\n')
    (OUT / f'{scenario}-candidate-evaluation.json').write_text(expanded.as_json() + '\n')
    audit['scenarios'][scenario] = {
        'baseline_comparison': compare_conflicts(base_conflicts, scenario),
        'candidate_comparison': compare_conflicts(expanded_conflicts, scenario),
        'baseline_total_hard_violations': len(baseline.hard_violations),
        'candidate_total_hard_violations': len(expanded.hard_violations),
        'candidate_nonclosure_violations': [v for v in expanded.hard_violations if 'closure conflict' not in v],
        'candidate_objective': expanded.objective_score,
        'candidate_closures_full': [asdict(c) for c in expanded_conflicts],
        'schedule': schedule_summary(destination),
    }
    assert audit['scenarios'][scenario]['candidate_comparison']['all_exact_after_display_truncation']
    assert not audit['scenarios'][scenario]['candidate_nonclosure_violations']

# Compare exact activity rows with the previously accepted output archives.
for scenario in 'ABC':
    destination = OUT / 'preserved-reference' / scenario
    extract_csvs(ROOT / 'deliverables/final-submission' / f'{scenario}.zip', destination)
    reference = schedule_summary(destination)
    friend = audit['scenarios'][scenario]['schedule']
    changes = {}
    for aid in sorted(instance.activities):
        ours, theirs = reference['activities'][aid], friend['activities'][aid]
        if ours != theirs:
            changes[aid] = {'accepted_reference': ours, 'friend': theirs}
    audit['scenarios'][scenario]['reference_schedule'] = reference
    audit['scenarios'][scenario]['changed_activities'] = changes
    closure._blocked_locations = candidate_blocked
    try:
        ref_evaluation = evaluate_submission(instance, destination, scenario)
    finally:
        closure._blocked_locations = original_blocked
    assert ref_evaluation.internally_feasible
    audit['scenarios'][scenario]['reference_candidate_evaluation'] = json.loads(ref_evaluation.as_json())

(OUT / 'submission-replay.json').write_text(json.dumps(audit, indent=2) + '\n')
for scenario, data in audit['scenarios'].items():
    print(scenario, json.dumps({k: v for k, v in data.items() if k not in ('schedule', 'reference_schedule', 'changed_activities', 'candidate_closures_full')}, indent=2))
    print('ECLO', data['schedule']['eclo'])
    print('LATE', data['schedule']['late_contracts'])
    print('CHANGED ACTIVITIES', len(data['changed_activities']))
