# NightShift Google Cloud hosting

## Live deployment

- Public URL: https://nightshift-hmhb4fs4qa-uc.a.run.app
- Project: `qwiklabs-gcp-01-3b5669da2868`
- Service: `nightshift`, region `us-central1`
- Application version: `2.0.0`
- Ready revision: `nightshift-00003-c7f`, serving 100% of traffic
- Deployed and verified: 2026-09-19
- Build: `d0be1608-7ae0-4f4b-be67-2f30694892a5`
- Uploaded source bundle SHA-256: `e984468248892c5dd7118d40ded71fa6e5c61f76a690ad3f76e84a2720a57179`

The app accepts the eight input CSVs in one ZIP, constructs a fresh CP-SAT model,
validates the schedule, independently recomputes its score, and releases exactly
three submission CSVs in a ZIP. Every new planning run computes from its uploaded
inputs: no stored-result substitution and no sample solution hints.

The model supports distinct accesses for an activity within the same week and
counts ECLO costs per visit. It first searches a zero-penalty subproblem, then uses
the remaining budget for the selected scenario's permitted trade-offs if needed.
Only a validated schedule is published. Finding a valid zero proves the primary
nonnegative objective's floor under the implemented rules; arbitrary inputs are
not guaranteed to reach an optimum within the search budget.

The interface streams actual search progress and derives the activity timeline,
visit details, weekly network/capacity view, and contract delivery table from the
returned schedule. It exposes hashes, solver status and bound, model size, and
validation evidence. The public dataset can be loaded or downloaded from the UI.

Organizer-accepted A/B/C archives under `deliverables/official-zero/` remain
unchanged and are available through explicit reference buttons. Newly computed
outputs are labelled as locally validated, not as newly organizer-confirmed.
The historical restricted CLI portfolio and old final-submission pipeline are
separate from the deployed web engine.

## Verified results

Fresh public-input runs on Google Cloud, with no sample hints:

| Scenario | Score | Runtime | Access rows | Occupancy rows |
|---|---:|---:|---:|---:|
| A | 0.0 | 21.032 s | 192 | 549 |
| B | 0.0 | 20.785 s | 192 | 549 |
| C | 0.0 | 36.812 s | 192 | 553 |

These runs used application revision `nightshift-00002-bp7`; the subsequent
`nightshift-00003-c7f` revision changes only request concurrency. Each downloaded
archive was independently validated locally. A separate browser run computed A
at 0.0 in 21.0 seconds with 192 access rows and 560 occupancy rows; its actual
browser-downloaded ZIP passed the same checks. Solver timing and schedules can
vary across runs.

A custom one-activity dataset with previously unseen activity/contract IDs,
three required work units, a two-access weekly cap and a hard first-week deadline
returned B = 10.0 with two ECLO accesses. A malformed ZIP returned HTTP 400.
The focused regression suite passed 24 tests plus 66 constraint subchecks.

Evidence, generated ZIPs, streamed progress, response metadata and independently
recomputed scores are retained in `output/cloud-deploy-v2/verification/`.
No organizer submission attempts were used for this deployment.

## Local run

```bash
python3.11 -m venv .venv
.venv/bin/pip install -e '.[test]'
.venv/bin/uvicorn nebula_ps1.web:app --host 127.0.0.1 --port 8080
```

Open `http://127.0.0.1:8080`.

## Cloud Run configuration

- Container port: 8080
- Capacity: 2 CPU, 4 GiB memory
- Request timeout: 900 seconds
- HTTP request concurrency: 8, so interface requests can run while a solve is active
- Solver concurrency: 1 per container, enforced by an application semaphore
- Solver workers: 2; solve budget: 180 seconds
- Maximum instances: 2
- Existing public access preserved

Uploaded data and generated files are held in temporary working directories for
processing; users retain results by downloading the ZIP. Streaming uses one
connection and does not depend on polling a particular container instance.

## Deployment and rollback

From Google Cloud Shell authenticated to the existing project, in the source root:

```bash
gcloud run deploy nightshift \
  --source . \
  --region us-central1 \
  --port 8080 \
  --cpu 2 \
  --memory 4Gi \
  --timeout 900 \
  --concurrency 8 \
  --max-instances 2 \
  --set-env-vars NEBULA_SOLVER_WORKERS=2,NEBULA_SOLVER_CONCURRENCY=1,NEBULA_SOLVE_SECONDS=180
```

Verify `/api/health`, `/api/readiness`, real scheduling, browser visualizations,
and the downloaded three-file ZIP after changes. The previous application
revision is `nightshift-00001-skw`; traffic can be routed back if a rollback is
necessary, but that version retains the earlier model and cached reference flow.
