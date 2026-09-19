# Exact public-instance optimum: A = 137.9, B = 30.0, C = 62.7

Verified on 19 September 2026 against the eight current public input CSVs. These are exact primary-score optima under the current published rules and the contract-completion scoring observed in the official validator. They are instance-specific, not universal scores for hidden datasets.

| Scenario | Independently established lower bound | Officially feasible witness | Gap |
|---|---:|---:|---:|
| A | 137.9 | A-002: 137.9 | 0 |
| B | 30.0 | B-001: 30.0 | 0 |
| C | 62.7 | C-001: 62.7 | 0 |

The portal confirmed feasibility and scores in the recorded historical runs. It did not issue an optimality certificate. The optimality argument below is independent local work. No portal attempt was consumed during this audit, and no protected submission was changed.

## How to read the proof

A feasible schedule establishes an **upper bound**: we can achieve that score. A mathematical argument that every feasible schedule costs at least a given amount establishes a **lower bound**. Equality proves the optimum.

To avoid relying on the existing optimiser, `audit.py` parses all eight CSV files directly. Its proof calculations do not import the production solver, scorer, instance parser, or closure checker. The production checkers are called only afterwards, in the separate feasible-witness validation stage. The independent models have no input schedule hints and no frozen activities.

The relaxed models deliberately omit location capacity, group packing, workfront limits, and all non-PM closure conflicts. They also omit the nonnegative excess-capacity charge. This gives the schedule more freedom and potentially makes it artificially cheap. If even this easier problem cannot score lower, neither can the real problem. For A, one mandatory PM exclusion is sufficient for the hand proof; the independent CP model automatically derives all 45 PM exclusions from the input geometry.

## Input audit

| Input | Records | Used for |
|---|---:|---|
| `01_LINES.csv` | 2 | Line identities and ECLO windows |
| `02_STATIONS.csv` | 20 | Ordered topology and interchange flags |
| `03_SECTORS.csv` | 18 | Fixed work corridors and neighboring sectors |
| `04_LOCATION_SUPPLY.csv` | 76 | Complete occupancy references and witness capacity/excess checks |
| `05_BUFFER_LOCATION.csv` | 3 | Buffer sizes and opposite-bound closure |
| `06_PARAMETERS.csv` | 2 | Start 2027-01-04; horizon 30 weeks |
| `07_PROJECT_DETAILS.csv` | 14 | Dates, priorities, workfronts, possession types, allocations |
| `08_ACTIVITY_DETAILS.csv` | 54 | 192 required work units and 6 predecessor links |

Every activity's corridor resolves to supplied locations. The predecessor graph is acyclic; all references checked by the audit resolve. All activity starts are Mondays and all planned contract deadlines are Sundays. Week numbering and Sunday completion therefore introduce no partial-week ambiguity in this instance.

`activity_input_audit.csv` contains the derived timing/workload facts for every activity. `contract_bound_curves.csv` enumerates each contract's possible completion weeks and best relaxed ECLO/delay cost. SHA-256 hashes of all eight input files are recorded in `CERTIFICATE.json`.

## Scoring that matters to the proof

Let `D_c` be the positive number of calendar days between contract c's latest activity completion and its planned completion date; early completion contributes zero.

The recorded official results establish the following aggregation:

`delay(c) = D_c × contract_priority_weight × sum(activity_priority_multipliers in c)`

Contract priority weights are 100, 10, and 1. Activity multipliers are 1.3, 1.2, and 1.0. Therefore:

| Contract | Constituent activity multipliers | Cost per late day |
|---|---|---:|
| C006 | A035 1.3; A036 1.3; A037 1.3; A038 1.0; A039 1.2 | 6.1 |
| C010 | A058 1.0; A059 1.0; A060 1.2; A061 1.3; A063 1.0; A064 1.0 | 6.5 |
| C014 | A075 1.0 | 1.0 |

The contract weights for these three contracts are all 1 because their contract priority is 3. This is why pricing only the late activity would undercount the official score.

Each activity has at most one access in a calendar week. A standard access delivers 1 unit and an ECLO access delivers 1.5. ECLO costs 5 per access; excess capacity costs 7 per extra possession-location-week in B/C. All score components are nonnegative.

## The three decisive activities

| Activity | Contract | Work units | First allowed week | Planned deadline week | Standard-only earliest finish |
|---|---|---:|---:|---:|---:|
| A036 | C006 | 7 | 22: 31 May | 26: 4 July | 28: 18 July |
| A059 | C010 | 7 | 14: 5 April | 19: 16 May | 20: 23 May |
| A075 | C014 | 1 | 24: 14 June | 28: 18 July | 24: 20 June |

All dates are in 2027. These activities have no predecessors. Other activities and their dependencies were retained in the independent CP model; they do not raise the matching lower bounds.

## Scenario A: 137.9 is unavoidable

ECLO is forbidden, so A036 requires seven different weeks starting at week 22. Its earliest possible finish is week 28, two weeks after C006's deadline:

`C006 delay >= 14 × 6.1 = 85.4`.

A059 needs seven different weeks from week 14 and cannot finish before week 20, one week after C010's deadline:

`C010 delay >= 7 × 6.5 = 45.5`.

These timing facts alone force 130.9, even with unlimited capacity and teams.

There is also one unavoidable scheduling choice. A075 is a Live PM activity on Beta H01-H02 westbound. Its two-sector buffer is mirrored onto eastbound and includes A036's Beta S14-H01 eastbound sector. A075 is sole-possession PM, so it cannot co-share directly or form a transitive co-sharing bridge. Consequently A036 and A075 cannot occupy the same week under the published weekly closure interpretation.

If A036 finishes at its earliest possible week 28, it must use **every** week 22-28. A075 cannot start before week 24, so its earliest remaining week is 29. That adds seven C014 delay days costing 7.

If instead we keep A075 on time and create a gap for it in weeks 24-28, A036 cannot finish before week 29. The extra week costs at least 42.7 through C006, which is more expensive than delaying A075 by 7.

Thus every A schedule costs at least:

`85.4 + 45.5 + min(7, 42.7) = 137.9`.

The independent enumeration examined **all 5,842 pairs of access subsets** for A036 and A075 over their available horizon, including surplus accesses. Exactly 84 pairs avoid collision. Their minimum combined C006+C014 cost is 92.4; adding C010's 45.5 gives 137.9. If A075 is forced on time, the pair costs at least 128.1 and the whole schedule at least 173.6.

The official A-002 witness achieves 137.9 with A036 in weeks 22-28, A059 in 14-20, and A075 in 29. Every other contract is on time.

## Scenario B: six ECLO accesses force 30.0

All planned deadlines are hard. Let `r` be the number of usable weeks before an activity's deadline. Since there is at most one access per week, its maximum work using `e` ECLO accesses is `r + 0.5e`. Therefore a workload `d` requires:

`e >= max(0, 2d - 2r)`.

A036 has five weeks, 22-26, for seven units. It needs at least four ECLO accesses: `5 + 4/2 = 7`.

A059 has six weeks, 14-19, for seven units. It needs at least two ECLO accesses: `6 + 2/2 = 7`.

These are distinct activities, and the required on-time periods do not overlap. Hence at least six ECLO accesses are necessary, costing `6 × 5 = 30`. Extra capacity cannot create a second weekly access for either activity. Any excess-capacity penalty would only increase the score.

The official B-001 witness uses exactly those six ECLO accesses, has zero excess capacity, and meets every planned deadline. It achieves 30.0.

## Scenario C: 62.7 is unavoidable

All ECLO accesses affecting a line must fit in one two-consecutive-week window. With one access per activity per week, any activity can receive at most two ECLO accesses, adding at most one work unit.

For A036, the five on-time weeks can therefore deliver at most `5 + 1 = 6`, short of its seven-unit workload. It must finish late regardless of how much capacity is available.

| A036 ECLO count | Minimum accesses | Earliest finish | C006 delay cost | ECLO cost | Combined lower bound |
|---|---:|---:|---:|---:|---:|
| 0 | 7 | week 28 | 85.4 | 0 | 85.4 |
| 1 | 7 | week 28 | 85.4 | 5 | 90.4 |
| 2 | 6 | week 27 | 42.7 | 10 | **52.7** |

For A059:

| A059 ECLO count | Minimum accesses | Earliest finish | C010 delay cost | ECLO cost | Combined lower bound |
|---|---:|---:|---:|---:|---:|
| 0 | 7 | week 20 | 45.5 | 0 | 45.5 |
| 1 | 7 | week 20 | 45.5 | 5 | 50.5 |
| 2 | 6 | week 19 | 0 | 10 | **10.0** |

Therefore every C schedule costs at least `52.7 + 10.0 = 62.7`. All remaining penalties are nonnegative.

The official C-001 witness attains this bound. A036 runs in weeks 22-27, with ECLO in Beta weeks 26-27. A059 runs in 14-19, with ECLO in Alpha weeks 18-19. A075 runs in week 28 without conflict. There is no excess capacity or other contract delay. The per-line ECLO windows are legal and independent.

## Independent exact solver checks

The small CP-SAT model was written afresh for this audit. It includes every activity's release, workload, horizon, predecessor, contract deadline/score, and the scenario's ECLO policy. It contains no existing schedule hint, no frozen neighborhood, and no heuristic closure-separation cuts.

| Scenario | Relaxed model status | Minimum / bound | Additional strictly-better query | Result |
|---|---|---:|---|---|
| A | OPTIMAL | 137.9 / 137.9 | score <= 137.8 | INFEASIBLE |
| B | OPTIMAL | 30.0 / 30.0 | score <= 29.9 | INFEASIBLE |
| C | OPTIMAL | 62.7 / 62.7 | score <= 62.6 | INFEASIBLE |

Scores use exact integer tenths internally. All legal scores are multiples of 0.1, so these queries cover every strictly lower possible score. Models are exported as `.pbtxt` and solver summaries as `.response.txt`. Solver infeasibility is computational evidence, not a separately machine-checked SAT proof trace; the elementary and exhaustive arguments above do not depend on trusting that solver status.

## Ten attempts to break the argument

| Possible flaw or improvement | Check and result |
|---|---|
| 1. More supply or teams could eliminate the delay. | Resource limits and excess charges are omitted in the lower-bound models. The bound persists even with those advantages. |
| 2. Better co-sharing or a transitive bridge could rescue A075. | PM must stand alone. A075 cannot connect into any shared component; its mirrored buffer directly intersects A036's sector. |
| 3. Keeping A075 on time could be cheaper. | Exhaustive pair enumeration and a separate constrained CP solve give a whole-schedule lower bound of 173.6. |
| 4. B could use five ECLO accesses and buy extra capacity. | The resource-free B model with at most five ECLO accesses is INFEASIBLE. The separate 4+2 workload calculation explains why. |
| 5. C could use four ECLO accesses on A036 and finish on time. | That requires more than two distinct ECLO weeks. Removing the window artificially lowers the relaxed optimum to 30.0; the real rule forbids it. |
| 6. C could use fewer ECLO accesses and tolerate a little more delay. | Every 0/1/2 choice is priced above. With at most three ECLO accesses total, the relaxed optimum is 98.2. |
| 7. Extra or fractional workload could change the arithmetic. | Workload uses the official >= inequality and exact half-units, not equality. Exhaustive A enumeration includes surplus rows. All accesses remain at most once per week. |
| 8. The result could depend on a helpful seed, fixed schedule, or local repair neighborhood. | Proof models have no hints and no frozen activities. All 54 activities are free; the analytical and enumeration methods are independent of search seeds. |
| 9. Contract aggregation or date rounding could be wrong. | Three score calculations reproduce the archived official scores. Starts are Mondays and deadlines Sundays. Contract finish is the latest activity finish; early finish creates no negative offset. |
| 10. A lower bound might be unattainable once all physical rules return. | Unchanged official A-002/B-001/C-001 CSV bytes attain the bounds. Their archived ZIP hashes are pinned to the ledger; full local evaluation and the stricter buffer screen also pass. |

The A optimum depends on the weekly PM/Live buffer exclusion between A036 and A075. The B/C timing bounds depend on the one-access-per-activity-per-week rule, and C additionally depends on its two-week ECLO restriction. Changing those rules changes the problem. The arithmetic uses the official contract aggregation observed in A-002, not the earlier activity-only interpretation.

## What this means for improving the algorithm

For these exact inputs, further search or training cannot improve the primary score while retaining the same rules. The actionable target is to recover 137.9/30.0/62.7 reliably and quickly, with a proof gap of zero.

Useful next algorithm work is instance-dependent lower-bound calculation, fast feasible construction, and better generalization to changed topology, demand, releases, deadlines, and priorities. A benchmark should measure feasibility, score minus a justified lower bound, construction time, and reliability across seeds. Label a result optimal only when a valid achieved score equals a valid global lower bound.

The public solution can be one regression/teacher example. Training only to reproduce its IDs or fixed scores would not establish hidden-instance performance. Use separately generated and held-out instances, with exact solutions or rigorous bounds where available. There may also be room to improve unscored operational qualities among schedules with equal primary score.

## Reproduction and evidence

Run from the repository root:

```sh
.venv/bin/python artifacts/public-optimality-audit-2026-09-19/audit.py
```

The script writes only into this audit directory. Files named `*.relaxed_access.csv` are lower-bound model outputs and are **not submission files**; their omitted constraints mean they must not be uploaded.

- `CERTIFICATE.json`: input hashes, bounds, solver results, counterfactual checks, witness hashes, and zero-gap results.
- `activity_input_audit.csv`: all 54 activities.
- `contract_bound_curves.csv`: per-contract completion/ECLO alternatives.
- `a_pair_exhaustive.csv`: all 84 nonconflicting A036/A075 subset pairs.
- `*.pbtxt` and `*.response.txt`: independent models and solver summaries.
- `audit.py`: complete reproducible audit.

Official rule source: https://github.com/aochinwen/NebulaX-Hackathon-ProblemStatement/blob/main/PS1/PS1_README.md

Historical official acceptance evidence: `../../OFFICIAL_VALIDATOR_LEDGER.md` and `../../deliverables/validator/A-002.zip`, `B-001.zip`, `C-001.zip`. Release packages remain in `../../deliverables/final-submission`.
