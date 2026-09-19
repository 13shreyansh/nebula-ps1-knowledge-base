# Nebula PS1 solver handoff

Solver revision: `a62a2ef9725940fe13d1ef8ec1b9ddf06e77cf10`

## What this is

This is a Python 3.11 constraint-optimisation engine built with OR-Tools CP-SAT. It is not a trained neural-network checkpoint and does not run in the browser. A backend process must call the solver and return its output to the frontend.

## Install

From the extracted package root:

```bash
python3.11 -m venv .venv
.venv/bin/pip install -e .
```

## Input contract

Pass a directory containing these eight official-schema CSV files:

1. `01_LINES.csv`
2. `02_STATIONS.csv`
3. `03_SECTORS.csv`
4. `04_LOCATION_SUPPLY.csv`
5. `05_BUFFER_LOCATION.csv`
6. `06_PARAMETERS.csv`
7. `07_PROJECT_DETAILS.csv`
8. `08_ACTIVITY_DETAILS.csv`

The included `sample-data/` directory is the official public instance.

## Run

```bash
.venv/bin/nebula-ps1 solve-candidate-portfolio \
  --data sample-data \
  --output generated/A \
  --audit-output generated/A-audit \
  --scenario A \
  --workers 1 \
  --seed 1
```

Use `--scenario B` or `--scenario C` for the other policies. The command prints a JSON execution report to standard output.

## Output contract

On success, the output directory contains exactly the three competition files:

- `RESULTS.csv`
- `SCHEDULE_ACCESS.csv`
- `SCHEDULE_OCCUPANCY.csv`

The backend should zip these three root-level files when the user asks to export a submission. The `validated-outputs/` directory contains the current public-instance incumbents for UI development and demos.

## Recommended frontend boundary

Expose one backend operation with:

- input: eight CSV uploads or one ZIP containing them;
- option: scenario `A`, `B`, or `C`;
- response: run status, the solver's JSON report, previews of the three CSVs, and a downloadable ZIP.

Run the solver as a background job because solve time varies with instance difficulty. Do not report an internal candidate as final until the process exits successfully and all three output files exist.

## Important distinction

`validated-outputs/A.zip`, `B.zip`, and `C.zip` are already-computed answers for the public dataset. They are useful for submission and frontend previews, but they are not the general solver.
