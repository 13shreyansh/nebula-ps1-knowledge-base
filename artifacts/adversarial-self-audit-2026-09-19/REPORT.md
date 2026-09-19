# Adversarial audit of the accepted public zero schedules

Audit date: 19 September 2026. No portal access, uploads, organizer messages, or changes to production code or submission files were made. Only audit artifacts were created. The official acceptance evidence is the retained portal snapshot and hash manifests, not a new live observation.

**Verdict: the claim that the current result is an unquestionably correct physical timetable, obtained by a general solver without shortcuts, does not survive this audit.** The narrower claim that these exact public files received feasible zero scores remains supported. Several findings below are conditional on physical-night semantics; those conditions are explicit because the organizers' sample itself contradicts that interpretation.

## Reproducible evidence

Run from the project root using `.venv/bin/python`:

- `artifacts/adversarial-self-audit-2026-09-19/audit_raw.py`
- `artifacts/adversarial-self-audit-2026-09-19/check_independent_nights.py`
- `artifacts/adversarial-self-audit-2026-09-19/audit_pipeline.py`

The raw audit imports no project parser, topology, validator, or scorer. The night model uses a separate CP-SAT formulation. The pipeline audit deliberately exercises the existing code and is not an independent semantic oracle. Reports are `raw-audit.json`, `night-cp-sat.json`, and `pipeline-audit.json`. Fresh upstream byte comparisons are in `upstream-check.json`; the retrieved rules are preserved in `official-rules-snapshot.md`.

## 1. Two credited nights occupy one capacity slot

Severity: critical to physical validity; confirmed file contents, conditional rule interpretation.

A036 has standard visits on local nights 1 and 2 in week 22, and again on nights 1 and 2 in week 23. Its required platform `PLAT:BET:H01:EB` has weekly supply 1. The occupancy file has just one group, `g1`, for that activity/platform/week. The same access and occupancy bytes occur in all three zero archives.

Thus the access file credits two units of work while the occupancy representation charges one possession at this bottleneck. The numerical zero follows from counting groups, not from demonstrating two available physical nights. Under the literal weekly-night interpretation, the current A schedule exceeds supply in both weeks. For fixed access placements in B/C, these two platform-weeks alone imply at least two excess units, costing at least 14. **That is a conditional lower bound for these placements, not a corrected exact score or the optimum of a repaired problem.** Other consistency defects may prevent the schedule from being feasible at all.

The user's clarification permits repeated visits when sufficient nights exist; it does not establish that two distinct visits can use one available slot. B1 tested repeat visits with spare capacity. C1 changed ECLO, workload visits, and occupancy accounting together. Its acceptance does not isolate which intended rule changed. Reusing C1 in A/B is evidence of the same checker behavior, not three independent confirmations of physical feasibility.

## 2. The rows cannot consistently represent physical nights

Severity: critical to dispatchability; proven contradiction under stated semantics.

Minimal witness in week 9:

| Location | A006 group | A058 group | Implication if a group is one night |
|---|---|---|---|
| `PLAT:ALP:H01:WB` | g1 | g1 | Same night |
| `PLAT:ALP:S04:WB` | g2 | g1 | Different nights |

Both activities have exactly one access that week, so this contradiction does not depend on the new repeat-visit construction. Arbitrary label names are not the issue: equality and inequality are compared within each location/week. An activity cannot use one physical night on one part of its corridor and a different physical night on another while recording only one access.

The raw component audit finds 61 location/component contradictions plus 8 contract/type night-index contradictions in single-visit components of the zero schedule. These are overlapping witnesses, **not 69 independent official violations**. Example of the latter: in week 13, A040 and A041 belong to the same co-sharing component, but the same C007/Renewal contract records local nights 3 and 2.

The separate CP-SAT model assigns an actual night to each single-visit activity, equates same-group activities, separates different groups at the same location, and respects each contract/type's local night mapping. It proves infeasibility in 17 of the 29 occupied weeks. It excludes multi-visit activities and does not require closure or supply constraints, so A036's capacity defect is not needed for these contradictions. SAT/OPTIMAL in the remaining weeks establishes only consistency of that reduced test, not full feasibility.

**Adversarial countercheck:** the historical accepted B has 75 component witnesses, and the organizers' supplied sample has 52. This weakens any assertion that we alone introduced an illicit representation. It strengthens the conclusion that the published physical-night story, sample representation, and observed checker are not yet reconciled. The intended formal problem may deliberately use independent local accounting groups. Organizer confirmation must decide that; this audit cannot turn a conditional physical contradiction into a confirmed official disqualification.

## 3. Accepted zero files and the production solver are different systems

Severity: high; confirmed implementation mismatch.

`prepare_zero_c.py` explicitly adds A036/week22, A036/week23, and A059/week14 to a fixed historical B schedule. It removes ECLO and keeps the old occupancy rows. This is a public-instance-specific construction, not the general CP-SAT solver discovering zero.

The production model still has one Boolean access variable per activity/week and the sum of night choices equals that Boolean. It cannot generate the repeated visits. Fresh evaluation rejects every zero archive with three duplicate-week violations; `independent_score.py` raises at A036/week22. Its computed numeric zero must not be cited without its infeasibility flags. Simply removing the duplicate check would leave the missing visit-to-capacity link unresolved.

The old sample/accepted-schedule hints and partially frozen repairs are not inherently improper, but their runtimes and neighborhood proofs cannot be presented as cold-start solving or unrestricted global proofs. The separate historical raw-input/no-hint work is different evidence and does not establish zero generation by the current general solver.

## 4. A known closure correction remains outside production

Severity: high; confirmed reproducible discrepancy.

On the friend's B archive, the current checker finds 65 violations. Applying the previously inferred Live buffer endpoint-platform correction in memory finds 67, matching the recorded official count. The missed cases are week 19 A059/A074 at `PLAT:ALP:S06:WB` and week 28 A021/A075 at `PLAT:BET:S13:WB`. The production `_blocked_locations` still omits these own-line buffer endpoint platforms.

The zero archives have no additional conflicts under that correction, including the optional stricter buffer screen. Therefore this defect is a general-validator risk, not a newly demonstrated closure failure in zero. Conversely, the friend's accepted C has prior evidence of four buffer-only overlaps under the optional strict screen, so adding every stricter interpretation can also reject portal-accepted results. Matching 121 past diagnostics after fitting a correction is in-sample reconstruction, not a held-out proof of checker equivalence.

## 5. The web app recognizes the public data and returns stored results

Severity: high for demo/benchmark claims; confirmed controlled execution.

`web.py` fingerprints the eight input CSVs. On an exact public-data match with ready baselines, it extracts historical `deliverables/final-submission` archives instead of invoking the solver. I intercepted the solver entry point: A/B/C returned 137.9/30/62.7 and did not call it. These local calls took roughly 0.010–0.011 seconds. Equivalent row-reversed inputs reached the compute branch; I deliberately intercepted that branch rather than running a new search.

The response and UI label the method as a reference-confirmed public incumbent, so the inspected implementation does not conceal the reuse. Nonetheless, those timings are cached-result retrieval times. They cannot support a claim of fast new-instance solving. The current frontend also serves historical results, not the separately accepted zero files. Pointing it at zero without semantic changes would make its current validation fail.

The first row-reversal audit harness accidentally joined a final line without a newline to the following row. It failed input parsing. I corrected the harness to parse and serialize CSV rows properly; that failed attempt is a harness error, not evidence of a product parser bug.

## 6. Correlated validators and proof claims

Severity: high; historical failure demonstrated, current scope limited.

The older 137.9/30/62.7 optimality claims were superseded by the portal zero results. Independent code still shared the same at-most-one-access-per-week premise. Independence of implementations does not establish independence of assumptions. CP-SAT certifies its encoded model; it cannot certify that the encoding matches organizer intent.

The code contains useful safeguards: direct-heuristic proofs are suppressed, frozen-neighborhood scope is disclosed, safe incumbents are preserved, and the portfolio checks proof scope. These do not repair omitted semantics. Additive component proofs also rely on the dependency graph containing every real coupling. A newly required physical-night or cross-line constraint could invalidate the decomposition and its early stopping together.

The raw nonnegative-score lower bound remains valid: an accepted zero cannot be numerically beaten under that portal metric. The unsupported upgrade is from that statement to a physically valid optimum, general solver optimality, or complete competition success.

## 7. Compute fairness, randomness, and selection effects

Severity: material generalization/measurement limitation; no fabricated comparison established.

`decomposed.py` gives each component the caller's stage budgets, and changes its seed by component index. It does not divide one global deadline among components. A decomposed run and a monolithic run with identical stage arguments therefore do not have equal total search allowance. Model construction, validation, multiple stages, retries, and multiple policies also add runtime. An internal CP solve limit is not an end-to-end wall-clock SLA.

The retained six-case seed-31 benchmark records failures rather than silently dropping them. In the permuted B case, monolithic fails in 5.037 seconds while decomposition succeeds in 5.557 seconds. In permuted C, objectives are 278 versus 250 at 17.208 versus 15.165 seconds. These are retained results inspected now, not rerun timings. They do not prove broad superiority or equal-compute dominance. Earlier logs also retain order/permutation sensitivity and an 11.6x slowdown counterexample for a policy change.

The tiny synthetic corpus was reused during policy development. Even fixed seeds and precommitted individual experiments do not make the whole evolving corpus a blind test set. Hand-designed motifs, identical local validators, dataset-size choices, and adaptive human decisions can all overfit the benchmark without any identifier appearing in the final policy. No broad seed distribution, hardware-normalized equal-total-budget study, or untouched organizer-distribution evaluation has been established here.

## 8. Learning and contamination

The inspected scheduling path is CP-SAT plus programmed heuristics and human-selected policies. No trained predictor, training loop, feature pipeline, statistical loss, split, or probability calibration appears in that path. CP-SAT's search machinery does not turn these public schedules into an ML generalization experiment. Claims about learned rules or calibrated confidence are therefore unsupported, rather than failed ML metrics.

The relevant analogues are public-instance hand-tuning, complete-schedule hints, repeated exposure to fixtures, adaptive use of portal diagnostics, and a dataset-fingerprint cache. Public inputs and samples are not hidden-test leakage by themselves. I found no evidence in the inspected code/history of hidden-instance access or train/test contamination in a trained model; this is not a forensic proof that no external action ever occurred.

If learning is added later, using portal-zero schedules as optimal targets or portal acceptance as the sole reward risks teaching the occupancy shortcut. Resolve the oracle first. Separate instance families, not just shuffled rows or renamed copies, and keep a frozen untouched evaluation set after tuning. Feasibility labels require an independent oracle; probability calibration is relevant only if a probabilistic prediction is introduced.

## 9. Checks that resisted falsification

- All eight input CSVs are byte-identical to freshly fetched official upstream files.
- All three archived ZIP hashes match the recorded accepted manifests; their three root CSVs match the extracted files exactly.
- All 54 activities, 192 standard visits, and 917 occupancy rows in each zero schedule pass independently parsed coverage, exact-workload, legal-mix, start-week, predecessor, local-night range, workfront, footprint, sequence, and completion-summary checks under the documented weekly representation.
- No duplicate `(activity, week, access_night)` row, missing route location, ECLO flag, or fabricated completion summary explains zero.
- The retained final portal snapshot displays feasible 0.0 in A/B/C, with zero reported delay/excess/ECLO. It is a retained observation, not a fresh portal query.
- Historical score arithmetic matches the inspected 137.9/30/62.7 and friend C98.2 evidence. The known earlier activity-versus-contract aggregation error is recorded rather than hidden.

These checks do not establish nightly realizability, all closure rules, or unseen-instance performance.

## 10. Assumptions still needing independent resolution

1. Does a repeated visit require another possession slot at every route location? How is it encoded when occupancy has no access sequence/night field?
2. Are co-sharing groups physical nights requiring corridor-wide consistency, or independent local accounting constructs? The sample is an essential counterexample to reconcile.
3. Must local contract night indices map consistently to physical co-sharing nights? Are transitive components a safety exemption only, or a single actual possession?
4. Do closure/buffer restrictions apply across an entire week or only simultaneous nights? When do buffer-only overlaps and endpoint platforms count? A blanket weekly exclusion and a nightly safety rule are different models.
5. Does Rule 10's one-access-per-week sentence remain normative despite repeat-row acceptance and the user's reported clarification?
6. What happens when repeated accesses mix standard and ECLO work, exceed two ECLO visits in a two-week window, or share a possession with activities having different ECLO flags? The zero files do not test these cases.
7. Does positive excess score exactly by groups, actual visits, or physical possessions? The inspected accepted public ledger has zero reported excess throughout; the positive-excess branch and C's +1 boundary lack independent official calibration here.
8. Is the observed contract-delay aggregation guaranteed on heterogeneous priority tiers, changed contract sizes, and non-week-boundary dates? Zero makes these branches invisible; known positive public overruns chiefly exercise priority-3 contracts.
9. Are horizon limits, surplus completed work, sequence enforcement, zero-work/empty-contract cases, and infeasible hidden inputs specified sufficiently? Current public passes do not test every boundary.
10. Are hidden scenario inputs identical or scenario-specific, especially amended C supply? Public transfer must not become an unconditional cross-scenario assumption.
11. What are the total runtime, CPU, memory, concurrency, library/network, and input-size limits? Cached public performance says nothing about a hidden upload under those limits.
12. Does the final judging contract treat accepted abstract schedules as sufficient despite physical inconsistencies? Public CSV acceptance is separate from hidden technical execution, app usability, and final deliverables.

## Required changes to claims and next validation

Do not claim an independently certified physical optimum, no shortcuts, a trained general scheduling model, or fast cold-start zero generation. Report the public zero as observed portal behavior with the unresolved interpretation disclosed. Keep the old positive results historical; current readiness scripts still certify those files, not zero.

The first organizer clarification should include the exact A036 capacity counterexample and the A006/A058 same-night/different-night counterexample alongside the analogous issue in the supplied sample. After resolving semantics, rebuild visit-to-occupancy accounting and any required night linkage, integrate the demonstrated closure correction, and re-audit the resulting model. Then measure a frozen general solver on unseen structural families under a single end-to-end compute budget with cache use separately labelled. Repeating large solver runs against the current unsettled oracle would not establish correctness.
