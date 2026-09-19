"""Make a minimal local C candidate from the supplied schedule; no upload."""
import csv
from dataclasses import asdict
import json
from pathlib import Path
import zipfile

from nebula_ps1 import closure
from nebula_ps1.evaluate import evaluate_submission, load_submission
from nebula_ps1.instance import load_instance
from nebula_ps1.independent_score import independently_score
from nebula_ps1.submission import relabel_submission_scenario

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
source = OUT / 'submissions/C'
candidate = OUT / 'C-minimal-repair-local-only'
candidate.mkdir(exist_ok=True)
instance = load_instance(ROOT / 'current-problem-statement/PS1/01_data')

for name in ('SCHEDULE_ACCESS.csv', 'SCHEDULE_OCCUPANCY.csv', 'RESULTS.csv'):
    with (source / name).open(newline='') as handle:
        reader = csv.DictReader(handle)
        columns = reader.fieldnames
        rows = list(reader)
    if name != 'RESULTS.csv':
        rows = [r for r in rows if not (r['activity_id'] == 'A059' and r['week'] == '20')]
    if name == 'SCHEDULE_ACCESS.csv':
        for row in rows:
            if row['activity_id'] == 'A059' and row['week'] in ('18', '19'):
                row['eclo'] = '1'
    with (candidate / name).open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)

relabel_submission_scenario(instance, candidate, candidate, 'C')
base = closure._blocked_locations
def expanded(instance, component):
    result = base(instance, component)
    for aid in component:
        if instance.projects[instance.activities[aid].contract_number].nature_of_activity != 'Live':
            continue
        for loc in base(instance, {aid}):
            if loc.startswith('SEC:'):
                _, line, sector_id, bound = loc.split(':')
                sector = instance.sectors[f'SEC:{line}:{sector_id}']
                result.update(f'PLAT:{line}:{station}:{bound}' for station in (sector.from_station_id, sector.to_station_id))
    return result
closure._blocked_locations = expanded
try:
    evaluation = evaluate_submission(instance, candidate, 'C')
    access, occupancy, _ = load_submission(candidate)
    strict = closure.screen_closures(instance, access, occupancy, forbid_buffer_overlap=True)
    source_access, source_occupancy, _ = load_submission(source)
    source_strict = closure.screen_closures(instance, source_access, source_occupancy, forbid_buffer_overlap=True)
finally:
    closure._blocked_locations = base
independent = independently_score(ROOT / 'current-problem-statement/PS1/01_data', candidate)
result = json.loads(evaluation.as_json())
result['strict_closure_conflicts'] = [c.describe() for c in strict]
result['officially_accepted_source_strict_conflicts'] = [c.describe() for c in source_strict]
result['independent_score'] = asdict(independent)
assert evaluation.internally_feasible, evaluation.hard_violations
assert evaluation.objective_score == 62.7
assert independent.objective_score == evaluation.objective_score
assert strict == source_strict, 'Repair must not add any strict buffer-only conflict.'
result['status'] = 'Locally validated candidate only; never submitted to official portal.'
(OUT / 'C-minimal-repair-verification.json').write_text(json.dumps(result, indent=2) + '\n')
with zipfile.ZipFile(OUT / 'C_62.7_minimal_repair_LOCAL_ONLY.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
    for name in ('SCHEDULE_ACCESS.csv', 'SCHEDULE_OCCUPANCY.csv', 'RESULTS.csv'):
        archive.write(candidate / name, name)
print(json.dumps(result, indent=2))
