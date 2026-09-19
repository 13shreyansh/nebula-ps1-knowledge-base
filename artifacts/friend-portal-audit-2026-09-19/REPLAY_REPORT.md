# Exact replay of the three supplied submissions

All three original ZIPs are preserved in `uploaded-archives/`; CSVs are safely extracted to `submissions/A`, `B`, and `C`. The replay uses the current eight public input CSVs. It never contacts the portal. The portal evidence is the complete report captured earlier on 19 September 2026.

## Results

| Scenario | Original local checker | Live-platform correction in isolated replay | Recorded official result |
|---|---:|---:|---|
| A | 54 closure conflicts; 49 displayed messages match exactly | 54 conflicts; all 54 displayed messages match | Infeasible, 54 |
| B | 65 closure conflicts; 63 displayed messages match exactly | 67 conflicts; all 67 displayed messages match | Infeasible, 67 |
| C | Feasible, 98.2 | Feasible, 98.2 | Feasible, 98.2 |

All non-closure checks in our local evaluator pass for each submitted ZIP. This is local evidence, not a claim that the official validator exhaustively ran every possible check. Matching uses complete reconstructed sharing components, then the portal's displayed first three sorted members and first four sorted collision locations. There are no unmatched or additional diagnostics after this formatting and the correction.

The earlier two unexplained A messages are resolved: the complete week-25 component is A017, A036, A040, **A042**. The portal displayed only its first three members. A042 accounts for the missing work/closure geometry at S17/S18.

## Confirmed discrepancy: Live buffer endpoint platforms

The production expansion omits endpoint platforms of own-line Live buffer sectors, including their opposite-bound copies. Adding those platforms only for Live closures reproduces every displayed A/B diagnostic. Adding platforms for every buffered work nature was tested in the earlier audit and disagreed with official cases.

The two completely missed B conflicts are:

1. Week 19: A059 inside A074's closure at PLAT:ALP:S06:WB.
2. Week 28: A021 inside A075's closure at PLAT:BET:S13:WB.

This explains the 65-versus-67 discrepancy in the supplied B filename. It does not establish what implementation the teammate used; the same counts are reproduced by our baseline checker.

The correction here is an isolated replay patch. Production solver/validator source has not been modified by this audit. All three previously accepted reference schedules still pass the expanded local evaluator at 137.9, 30.0 and 62.7.

## Confirmed discrepancy: strict buffer-only overlap rule

The exact officially feasible C input has four collisions under our EXTRA strict buffer-to-buffer screen:

| Week | First component | Second component | Shared external buffer sector |
|---|---|---|---|
| 19 | A003, A007, A040, A057 | A008 | SEC:BET:S16_S17:EB |
| 23 | A001, A008, A011, A042 | A007, A036 | SEC:BET:H02_S15:EB |
| 23 | A006, A023 | A013 | SEC:ALP:H02_S05:WB |
| 27 | A049 | A051 | SEC:BET:S16_S17:WB |

Thus that extra screen is stricter than the observed official acceptance rule. The blanket wording 'buffers never overlap' should not be presented as a fully confirmed description of the current portal. Acceptance does not determine whether the wording or the implementation should change; that remains an organiser-intent question.

## Exact explanation of C = 98.2

The submitted files confirm:

- A036 uses ECLO in weeks 22 and 23, completes in week 27, and makes C006 seven days late: 42.7 delay points plus 10 ECLO points.
- A059 uses seven standard accesses, weeks 14 through 20. It makes C010 finish on 23 May rather than its planned 16 May deadline: 45.5 delay points.
- There is no excess-capacity charge and no other late contract.
- Total: 42.7 + 45.5 + 10 = 98.2.

The reason the teammate chose that schedule cannot be inferred from output files alone. What the rows establish is that a profitable ECLO substitution for A059 was left unused.

## Minimal C repair, locally verified only

Starting from the friend's exact C schedule:

1. Mark A059's existing week-18 and week-19 accesses as ECLO.
2. Remove A059's week-20 access and its five occupancy rows.
3. Recompute RESULTS: C010 now finishes 16 May with zero overrun.

This supplies 4 standard units + 2 x 1.5 ECLO units = 7 required units. Alpha's ECLO window is weeks 18-19; Beta's remains weeks 22-23. All other activities keep their access and occupancy rows.

The result is 62.7 = 42.7 delay + 20 ECLO, zero excess, zero violations under the expanded portal-matching checker. The separate raw-CSV scorer also returns 62.7. The same four strict buffer-only findings remain, with none added. This candidate has NOT been officially submitted; do not label it officially feasible.

Artifact: `C_62.7_minimal_repair_LOCAL_ONLY.zip`, containing exactly the required three CSVs. Verification: `C-minimal-repair-verification.json`.

## What A and B reveal about optimisation

The friend's A has a local soft penalty of 130.9 BEFORE feasibility, but it is not a valid achieved official score. A036 works week 27 on local night index 3 while A075 works that week on index 1. The portal rejects their closure collision despite different indices. This directly supports treating those indices as insufficient to establish separated physical nights. A075 is placed in week 27 rather than our accepted week 29, avoiding seven delay points at the cost of violating closure rules. There are 53 other directional closure diagnostics too.

The friend's B has a local soft penalty of 30, matching our accepted B's cost, but it is infeasible due to its 67 closure diagnostics. B's flexible supply does not waive closures. An optimiser must first find a feasible arrangement; a low soft cost alone is insufficient.

These results support several current interpretations and identify a real checker omission. They do not prove the organisers' intended global optimum. In particular, these uploads do not test whether more than one access per activity per week could legally be used. The A lower-bound argument relies on work entering a closure, not the additional blanket buffer-only overlap screen, so relaxing that extra screen does not by itself refute the bound.

## Reproduce

From the repository root:

```sh
PYTHONPATH=src .venv/bin/python artifacts/friend-portal-audit-2026-09-19/replay_submissions.py
PYTHONPATH=src .venv/bin/python artifacts/friend-portal-audit-2026-09-19/repair_c.py
```

`submission-replay.json` contains full conflict components, full collision locations, exact archive hashes, local evaluations, each activity's submitted weeks/ECLO/night indices, and differences against the accepted references. No external upload is part of either script.
