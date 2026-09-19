# Nebula PS1 local validator

A portable local validator for the published railway scheduling problem. Its feasibility engine packages the same tested local rule implementation used by this repository, while a separately implemented raw-CSV scorer recomputes every accepted objective. It reproduces the recorded A-001 closure failure and the accepted A-002/B-001/C-001 scores. It is **not the organiser's program**, and complete equivalence on hidden instances is not established.

Requires Python 3.9 or newer. No pip installation, OR-Tools, network connection, or portal access is required.

## Run the portable validator

From the repository root:

```sh
python3 deliverables/local-validator/nebula-ps1-validator.pyz \
  --data current-problem-statement/PS1/01_data \
  --submission deliverables/final-submission/A.zip \
  --scenario A \
  --output validation-A.json
```

Use `B.zip`/`--scenario B` or `C.zip`/`--scenario C` for the other scenarios. `--scenario` is optional: by default it is read from `RESULTS.csv`; when supplied, a mismatch is rejected.

The `.pyz` can be copied to another computer and run with the same arguments and that computer's data/submission paths. The repository is not required. The supplied instance and schedules are not embedded in the executable.

For editable source, extract `nebula-ps1-validator-source.zip` and run:

```sh
python3 /path/to/extracted/source --data /path/to/instance --submission /path/to/submission.zip
```

From a source checkout, `python3 validate_ps1.py` accepts the same arguments. The public Python API is:

```python
from nebula_ps1.validator import validate

report = validate("instance_folder", "submission.zip", scenario="C")
if report["feasible"]:
    print(report["soft_scores"]["objective_score"])
else:
    print(report["hard_violations"])
```

## Input and output

`--data` accepts a folder containing the eight instance CSVs or a ZIP containing exactly those eight files at its root. An instance folder may contain other files. `--submission` accepts a folder or ZIP containing exactly these three files at its root:

- `SCHEDULE_ACCESS.csv`
- `SCHEDULE_OCCUPANCY.csv`
- `RESULTS.csv`

JSON is printed to standard output. `--output` also saves the same JSON. Parent directories for that output path must already exist. Exit codes are 0 for locally feasible, 1 for rejected input/submission, and 2 for command-line usage or report-write errors.

The report contains:

- `feasible`: whether this local validator found any enforced hard violation.
- `hard_violations`: structured rule tags, severity, and explanations.
- `soft_scores`: overrun, excess, ECLO, and priority diagnostics. `objective_score`, `formula_version`, and `independent_score_matches=true` appear **only when the feasibility engine accepts the submission and the separate raw-CSV score calculation agrees**.
- `detail`: per-contract completion/penalty, capacity hotspots, and additional buffer-screen findings.
- `dataset_hash` and `submission_hash`: when parsing progressed far enough to compute them.
- `validator`: implementation version, policy, known evidence, and explicit non-official status.

Malformed packs or unsafe numeric domains can stop validation early. Such reports still reject the input but may have empty soft scores/details; they do not promise to list every downstream error.

## Checks and scoring

The local engine checks CSV shape and identifiers, complete workload, chronological access sequences, one access per activity/week, planned starts, horizon, predecessors, full corridor occupancy, legal PM/PC/C mixes, contract/type weekly allocation, workfront limits, possession capacities, Live mirroring/interchange closures, ECLO policy, and exact agreement of declared contract results with the access schedule.

Standard access yields 1 work unit and ECLO yields 1.5. Workload must be at least the demand; surplus workload is not silently rejected as an equality violation.

| Scenario | Hard policy | Objective |
|---|---|---|
| A | No capacity excess; no ECLO | Weighted contract delay |
| B | No planned completion overrun | 7 × excess + 5 × ECLO |
| C | At most 1 excess possession per location/week; two-week ECLO window per affected line | Weighted contract delay + 7 × excess + 5 × ECLO |

Weighted delay uses **final contract completion**, charged across all activities in that contract. Contract priority weight is 100/10/1; activity multiplier is 1.3/1.2/1.0. Actual completion is the Sunday at the end of the final scheduled week; delay is against `planned_completion_date`.

`access_night` is a contract/type/week allocation index. It is not a global physical-night index, and changing it does not bypass the weekly possession closure checks. Local same-location/group connections form transitive co-sharing components.

## Standard versus strict buffers

The default `observed_standard` policy reproduces the current official evidence and accepts the organiser's sample. The additional buffer-to-buffer overlap screen always runs as an **advisory**, with its additional findings kept separate.

To enforce this conservative extra screen, pass `--strict-buffers`. The organiser's sample has four additional strict findings, so this mode rejects it even though the standard mode accepts it. Our protected A/B/C submissions pass both modes.

This distinction is intentional. A stricter interpretation must not silently be represented as exact official-validator behavior.

## Compatibility boundaries

- The interface is similar to the published validator report, but diagnostic wording and tags are ours. The formula version is explicitly local.
- Input validation is independently implemented. Malformed-input handling can differ from the organiser's parser.
- ZIPs must have flat, exact membership. Nested paths, duplicate names, encrypted members, and symlinks are rejected. Local archive limits are 64 MiB per uncompressed member and 256 MiB total; these are tool limits, not claimed competition rules.
- The topology loader expects the published linear sector representation, EB/WB bounds, and the three documented nature-of-work categories. It is not a general railway graph validator.
- No result from this program asserts official acceptance. Only an actual official run can do that.
- A feasible score does not establish optimality; proof requires a separate valid lower bound.

## Verification and rebuilding

Core rules remain in `src/nebula_ps1/evaluate.py`, `closure.py`, `topology.py`, `instance.py`, and `objective.py`. The duplicate score calculation is in `independent_score.py`. The portable API/CLI is `src/nebula_ps1/validator.py`. The source archive includes those modules and this readme.

```sh
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p 'test_validator.py' -v
python3 scripts/package_local_validator.py
PYTHONPATH=src .venv/bin/python scripts/verify_local_validator.py
```

The package builder emits deterministic ZIPs and a SHA-256 manifest. The verification command rebuilds the package, runs the full and focused regressions, executes both portable forms under isolated system Python without site packages, replays the observed sample and historical official archives, and regenerates `VERIFICATION.json` plus the case reports. It never contacts the portal.
