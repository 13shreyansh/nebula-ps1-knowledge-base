# Current portal results and modelling decisions

**Update after the exact ZIPs were supplied:** see [REPLAY_REPORT.md](REPLAY_REPORT.md). All 121 official diagnostics are now reproduced using full submitted sharing components and the Live-platform correction. The two unexplained A messages were truncated four-member components. The source C has four strict buffer-only overlaps despite official acceptance, and a minimal local repair reaches 62.7. The notes below preserve the earlier report before the submissions were available.

Observed live on 19 September 2026 through the existing authenticated team portal. Read-only inspection: no ZIP uploaded and no validation attempt consumed. The user attributes the latest runs to their friend. Exact uploaded files, upload timestamps and file hashes have not yet been supplied.

## Current results

| Scenario | Latest portal state | Earlier accepted result | Remaining attempts |
|---|---|---|---|
| A | Infeasible, 54 closure violations | 137.9 | 2/5 |
| B | Infeasible, 67 closure violations | 30.0 | 3/5 |
| C | Feasible, 98.2; 14 overrun days across two contracts; zero excess; two ECLO accesses | 62.7 | 3/5 |

The portal explicitly retains the latest result, not the best. The earlier accepted CSVs remain preserved locally in `deliverables/final-submission`. Their historical official acceptance does not mean the current portal still displays those scores.

All 121 displayed violations are `Activity inside another group's closure zone`. The complete visible report is in `portal-visible-report.txt`; each parsed diagnostic and geometry comparison is in `analysis.json`. Counts are directional violation records, not 121 independent scheduling decisions. One conflicting pair can produce two records, and one large closure can affect many activities.

## What the complete comparison found

The audit parses the eight public input files and compares each reported intruding activity's footprint with our closure expansion for the component printed by the portal. This conditions on the printed component; it cannot reconstruct the friend's groups or check for missing violations without their CSVs.

| Comparison | A | B |
|---|---:|---:|
| Full local location set exactly equals displayed location set | 36/54 | 57/67 |
| First four sorted local locations equal displayed list | 47/54 | 63/67 |
| Candidate Live buffer endpoint-platform expansion, then first four locations | 52/54 | 67/67 |

The display appears to truncate location lists to four entries. This is an inference from exact prefix matching, not a documented formatting guarantee. Therefore the initial 28 full-set differences are not 28 distinct modelling errors.

The substantive gap: our production closure expansion adds ordinary external buffer sectors and their Live opposite-bound mirrors, but omits endpoint platforms of those own-line Live buffer sectors. Cross-line expansion already includes buffered platforms. Adding endpoint platforms only for Live closures explains nine additional diagnostics. Adding them indiscriminately for all work natures makes agreement worse and was rejected.

Concrete examples:

- B, week 19: A059 enters A074's closure at `PLAT:ALP:S06:WB`. Our current reconstruction of that pair has no intersection; the Live endpoint-platform extension explains it.
- B, week 28: A021 enters A075's closure at `PLAT:BET:S13:WB`. Again, the new candidate expansion explains a platform-only conflict missing locally.
- A, week 27: A036 enters A075's closure at `PLAT:BET:H01:EB`, `PLAT:BET:S14:EB`, and `SEC:BET:S14_H01:EB`. Our code already detects the conflict, but omits the S14 platform from its reported geometry. This is direct new evidence for the A036/A075 exclusion used in the conditional public bound.
- A, week 25: A008 and A071 are reported against `['A017', 'A036', 'A040']`. Two diagnostics remain unexplained from only those printed members. The component list may also be truncated (printed lists contain at most three members), or another expansion/data difference is present. Do not infer the full component without the uploaded occupancy file.

The candidate expansion was tested in an isolated process against all three preserved accepted schedules. It introduces zero closure conflicts in each. `protected-witness-check.json` records this check. Production code and submission CSVs were not changed.

## Why C scores 98.2

Confirmed portal arithmetic:

- Two ECLO rows cost 10.
- Zero excess costs 0.
- The remaining 88.2 is delay cost.
- Compared with our 62.7 = 42.7 delay + 20 ECLO, the new submission saves 10 ECLO points and adds 45.5 delay points: net 35.5 worse.

Under the public dates and our observed contract-delay formula, 14 total late days across two contracts means seven days each. C006 and C010 are the only pair whose weights produce 88.2: 7 x 6.1 + 7 x 6.5. This is an inference awaiting `RESULTS.csv`, not a direct observation of those contract names. The earlier conditional analysis already found 98.2 as the best relaxed score with at most three ECLO rows. It is therefore consistent with a schedule spending too little ECLO to avoid a more expensive delay; the friend's actual algorithm and reason remain unknown.

## Decisions and their reasons

| Decision | Reason | Evidence status |
|---|---|---|
| Use CP-SAT with construction/repair heuristics | Explicit discrete choices and hard constraints can be searched and bounded; an LLM's schedule text is not a feasibility or optimality certificate. | Engineering choice, not an organiser mandate. |
| Encode at most one access per activity per week | The brief states this in the C discussion; interpreted as a universal scheduling rule. | Critical scope assumption still needing clarification. |
| Enforce release weeks and strictly later predecessor weeks | Explicit rules; workload cannot be pulled before release or immediately after a predecessor within one week. | Strong textual support. |
| Keep work footprint fixed by input corridor | Activities have supplied start/end sectors and no relocation decision field. Include intervening sectors and platforms. | Supported by schema and official footprint-overlap failures. |
| Treat night indices as local allocation/workfront counters | Output schema explicitly scopes them to contract/type/week. Different indices did not eliminate historical closure violations. | Strong support; physical-night interpretation still unresolved. |
| Screen closures at week level between sharing components | Weekly occupancy schema and observed official conflicts. | Supported cases, not complete proof of intended semantics. |
| Use transitive co-sharing components | Direct-pair-only interpretation produced extra violations absent from A-001; sample and official component messages support connectivity. | Exact component reconstruction awaits friend's occupancy CSV. |
| Include occupied footprint in closure | Historical A-001 failures exposed missing footprint checks. | Official evidence. |
| Expand Live closure across bounds and interchange lines | Published rules and multiple official failures. | New diagnostics expose missing own-line Live buffer platforms. |
| Charge contract-wide final delay through all activity multipliers | A-002's official 137.9 contradicted our earlier 32.2 activity-only calculation; corrected model also matches C-001. | Empirically supported; initial scorer was wrong. |
| Minimise total score, not ECLO count alone | ECLO costs 5 but can avoid larger delay costs; friend's C comparison illustrates this trade-off. | Formula plus portal arithmetic. |
| Count excess by location/week sharing groups | Published objective and output schema. | Still no accepted nonzero-excess official case in the records reviewed. |
| Keep an additional strict buffer-overlap screen | Literal 'buffers never overlap' wording conflicts with some sample geometry. Accepted schedules pass both screens. | Defensive check; not established as exact official semantics. |
| Treat public optimality as conditional | Independent lower-bound models share the same rule interpretation even when they use separate code. | Organiser's reported statement reopens intended global optimality; neither it nor this audit supplies a lower-score feasible witness. |

## What remains needed

The exact A/B/C ZIPs used for these runs, or all three CSVs for each, plus any modified input files. With them we can reconstruct actual sharing components and night indices; replay every official failure locally; distinguish missing, extra and correctly reproduced violations; and identify exact C rows responsible for the delay. A score screenshot alone cannot do that.

The organiser reportedly says the sample is not optimal. Treat that as a user-reported clarification, not evidence that the organiser claimed optimality previously. Request a legal improvement example or the exact restriction we are applying too strongly. Current recorded official results establish achievable scores, not an official global-optimality certificate.
