"""Read-only audit of portal diagnostics; does not reconstruct missing submissions."""
import ast
from collections import Counter
import itertools
import json
from pathlib import Path
import re

from nebula_ps1.instance import load_instance
from nebula_ps1.topology import activity_footprint
from nebula_ps1.closure import _blocked_locations
from nebula_ps1.objective import _combined_contract_weight_tenths

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
raw = Path('/tmp/nebula-portal-current-2026-09-19.txt').read_text()
OUT.joinpath('portal-visible-report.txt').write_text(raw)
instance = load_instance(ROOT / 'current-problem-statement/PS1/01_data')
pattern = re.compile(r"wk(\d+): (A\d+) inside closure of (\[[^\n]*?\]) at (\[[^\n]*?\])")

def live_platform_hypothesis(component):
    """Candidate explanation, not a change to the production validator."""
    blocked = _blocked_locations(instance, set(component))
    for activity_id in component:
        activity = instance.activities[activity_id]
        if instance.projects[activity.contract_number].nature_of_activity != 'Live':
            continue
        for location in _blocked_locations(instance, {activity_id}):
            if location.startswith('SEC:'):
                _, line, sector_id, bound = location.split(':')
                sector = instance.sectors[f'SEC:{line}:{sector_id}']
                blocked.update(f'PLAT:{line}:{station}:{bound}' for station in (sector.from_station_id, sector.to_station_id))
    return blocked

parts = re.split(r'Scenario\s+([ABC])', raw)
results = {}
for index in range(1, len(parts), 2):
    scenario, body = parts[index:index+2]
    records = []
    for match in pattern.finditer(body):
        week, intruder, component, locations = match.groups()
        component, locations = ast.literal_eval(component), ast.literal_eval(locations)
        footprint = set(activity_footprint(instance, instance.activities[intruder]))
        predicted = footprint & _blocked_locations(instance, set(component))
        live_prediction = sorted(footprint & live_platform_hypothesis(component))
        sources = []
        for activity_id in component:
            blocked = _blocked_locations(instance, {activity_id})
            implicated = footprint & blocked
            if not implicated:
                continue
            own_footprint = set(activity_footprint(instance, instance.activities[activity_id]))
            activity = instance.activities[activity_id]
            project = instance.projects[activity.contract_number]
            sources.append({
                'activity': activity_id,
                'nature': project.nature_of_activity,
                'access_type': project.access_type,
                'work_footprint_overlap': sorted(implicated & own_footprint),
                'closure_only_overlap': sorted(implicated - own_footprint),
                'cross_line': activity.start_location_id.split(':')[1] != instance.activities[intruder].start_location_id.split(':')[1],
            })
        records.append({
            'week': int(week), 'intruder': intruder, 'component': component,
            'reported_locations': locations, 'predicted_locations': sorted(predicted),
            'exact_geometry_match': predicted == set(locations), 'sources': sources,
            'base_first_four_match': sorted(predicted)[:4] == locations,
            'live_platform_hypothesis_locations': live_prediction,
            'live_platform_first_four_match': live_prediction[:4] == locations,
        })
    if scenario in 'AB':
        assert len(records) == {'A': 54, 'B': 67}[scenario]
    results[scenario] = {
        'count': len(records),
        'exact_geometry_matches': sum(r['exact_geometry_match'] for r in records),
        'base_first_four_matches': sum(r['base_first_four_match'] for r in records),
        'live_platform_first_four_matches': sum(r['live_platform_first_four_match'] for r in records),
        'by_week': dict(sorted(Counter(r['week'] for r in records).items())),
        'multi_activity_closure_components': sum(len(r['component']) > 1 for r in records),
        'cross_line_records': sum(any(s['cross_line'] for s in r['sources']) for r in records),
        'records_with_work_footprint_overlap': sum(any(s['work_footprint_overlap'] for s in r['sources']) for r in records),
        'records_with_only_closure_extension_overlap': sum(not any(s['work_footprint_overlap'] for s in r['sources']) for r in records),
        'blocking_activities': dict(Counter(s['activity'] for r in records for s in r['sources']).most_common()),
        'records': records,
    }

# Public deadlines and weekly completion boundaries imply two late contracts
# with 14 total days must each be seven days late. This infers a compatible
# explanation from the score; it cannot replace the missing RESULTS.csv.
pairs = []
for first, second in itertools.combinations(instance.projects, 2):
    delay_tenths = 7 * (_combined_contract_weight_tenths(instance, first) + _combined_contract_weight_tenths(instance, second))
    if delay_tenths == 882:
        pairs.append([first, second])
results['C']['portal_summary'] = {'feasible': True, 'score': 98.2, 'overrun_days': 14, 'overrunning_contracts': 2, 'excess': 0, 'eclo_rows': 2}
results['C']['inferred_delay_cost'] = 88.2
results['C']['compatible_two_contract_pairs_under_current_scoring'] = pairs
results['limitations'] = [
    'Submission CSVs and upload timestamps/hashes are not yet available.',
    'Geometry checks condition on the closure components printed by the portal.',
    'Cannot independently reconstruct co-sharing, access-night assignments, omitted conflicts, or full feasibility without uploaded CSVs.',
    'No official validation attempt was made; this is a read-only snapshot.',
]
OUT.joinpath('analysis.json').write_text(json.dumps(results, indent=2) + '\n')
for scenario in 'ABC':
    print(scenario, json.dumps({k: v for k, v in results[scenario].items() if k != 'records'}, indent=2))
