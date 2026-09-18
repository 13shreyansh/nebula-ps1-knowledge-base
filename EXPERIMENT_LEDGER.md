# Nebula PS1 Experiment Ledger

Append-only implementation and optimisation experiments. Negative and failed results are retained.

## Experiment schema

Each entry records timestamp, experiment ID, hypothesis, dataset hash, scenario, code commit, solver and version, parameters, seed, workers, time limit, feasibility evidence, objective components, best bound, runtime, output hashes, result, and next decision. Missing fields are written as `not available`, never inferred.

## 2026-09-18

No executable experiments have completed yet. The organiser-supplied Scenario A output is a regression fixture, not a result produced by our solver and not a locally reference-validator-confirmed incumbent.

### E001: Independent public-fixture baseline

- Timestamp: 2026-09-18 22:35:51 +08
- Hypothesis: schema-driven corridor expansion and the published score formula can reproduce the organiser fixture without public-activity special cases.
- Dataset hash: `e6608a9b396df162a6cf9ed74527c493eb07edf1ff89cc81f6906771c82f2188`
- Submission hash: `eb51ad2e0282a2d2a90d5a343ce18d7791327c6b84700e198dd810f763b0dfde`
- Scenario: A
- Code commit: uncommitted working tree
- Solver: none; independent parser and partial checker
- Seed, workers, time limit, bound: not applicable
- Result: 192 access rows expand to exactly 928 distinct required occupancy rows. All 13 implemented rule families pass. Derived penalty is `48.3`, comprising 42 Priority-3 activity overrun-days with activity-priority nudges. ECLO and excess access nights are both zero.
- Runtime: unit suite 0.006 seconds on the local machine; not a performance benchmark.
- Evidence: three passing `unittest` regressions and deterministic CLI output.
- Limitation: closure and buffer compatibility is deliberately unverified because the reference expander and validator are unavailable. This is not a validator-confirmed incumbent and not our solver's output.
- Decision: retain the sample as a regression fixture; proceed to mutation tests and an exact solver only after protecting this evidence boundary.

### E002: Unconstrained-closure Scenario A relaxation

- Timestamp: 2026-09-18 22:38:56 +08
- Hypothesis: the resource-independent `25.2` bound is reachable once workload, starts, predecessors, local possession mixes, nominal capacity, weekly allocation, workfronts, and the exact published penalty are co-optimised.
- Dataset hash: `e6608a9b396df162a6cf9ed74527c493eb07edf1ff89cc81f6906771c82f2188`
- Submission hash: `1903477cfbd54eb471d5f79480e911d3d52873e4412be5c5066efcb7969107a5`
- Scenario: A
- Code commit: uncommitted working tree
- Solver: OR-Tools CP-SAT 9.15.6755
- Parameters: 20-second limit, seed 1, 8 workers, public sample used only as a solution hint
- Result: `OPTIMAL` for the relaxation at `25.2`, with matching best bound. Model size was 21,065 variables and 44,257 constraints. Solver wall time was 0.428 seconds.
- Independent screen: rejected. The sample-consistent closure screen found eight conflicts, including A075 against A036 and A047 in week 28.
- Decision: quarantine permanently as a lower-bound witness. It is neither a feasible incumbent nor a submission candidate.

### E003: Minimal late-row Scenario A repair

- Timestamp: 2026-09-18 22:44:45 +08
- Hypothesis: the avoidable sample penalties from A035 and A038 can be removed without perturbing any already-on-time access or any other activity.
- Dataset hash: `e6608a9b396df162a6cf9ed74527c493eb07edf1ff89cc81f6906771c82f2188`
- Submission hash: `e290bd7fde77480cf4e7c804860b15c9376d34475568b2e6fd58c924770213e9`
- Scenario: A
- Code commit: uncommitted working tree
- Solver: OR-Tools CP-SAT 9.15.6755
- Parameters: 20-second limit, seed 1, 8 workers; freeze every non-target activity; preserve every on-time sample access for A035 and A038; allow only their late rows to move
- Result: `OPTIMAL` for the repair model at `32.2`, with matching best bound. A035 week 27 moved to week 11; A038 week 27 moved to week 26. All other activity weeks remained fixed. Solver wall time was 0.066 seconds.
- Checks: 192 access rows, 928 occupancy rows, complete workload, dates, predecessors, local legal mixes, capacity, allocations, workfronts, results, score, and the sample-consistent closure screen all pass. Six regression tests pass.
- Output hashes: `SCHEDULE_ACCESS.csv` `0adcb58e9d9eddfc5f7192fd38caa0b1c4a70820197a3772993fc6e75ddfb885`; `SCHEDULE_OCCUPANCY.csv` `67974be64e27bb7328c6e86e0a88bb07c5ae5ffdca1fade670bd67cabd2a49e2`; `RESULTS.csv` `9eca188c07c21438f3b1adc03cb83bb7ec0264f0a816756f9293c565bbc0ae1a`.
- Lower-bound argument: A036 requires seven standard weekly accesses from its week-22 planned start, so it occupies the H01 eastbound boundary through week 28. A075 is a Live PM at BET H01-H02 westbound, starts in week 24, and mirrors closure through the interchange. It therefore cannot use weeks 24-28 alongside A036 under the sample-consistent closure semantics and must incur at least seven days of delay. Adding A075's `7.0` to the independent A036/A059 bound of `25.2` yields `32.2`.
- Limitation: the official reference validator has not confirmed either the inferred closure screen or the lower-bound proof. This candidate is protected as the best internally checked result, not as a validator-confirmed incumbent.
- Decision: preserve E003 unchanged; next seek validator confirmation and independently attack the closure interpretation and `32.2` lower bound.

### E004: Scenario B iterative inferred-closure solve

- Timestamp: 2026-09-18 22:52:58 +08
- Hypothesis: Scenario B can meet every planned date at the closure-free lower bound by using ECLO without excess location capacity.
- Dataset hash: `e6608a9b396df162a6cf9ed74527c493eb07edf1ff89cc81f6906771c82f2188`
- Submission hash: `32cee150a8b106676dd2b8687451e8cae7a35a594a8669ed5e474e575b09cdfe`
- Scenario: B
- Code commit: uncommitted working tree after `faa7edb`
- Solver: OR-Tools CP-SAT 9.15.6755
- Parameters: 180-second total limit, seed 1, 8 workers, 200-round ceiling, lexicographic access-row tie-breaker
- Result: internally feasible at `30.0`, comprising six ECLO rows and zero excess access nights. All activities meet planned completion dates. Output contains 189 access rows and 917 occupancy rows.
- Bound and convergence: the closure-free model proved `30.0` optimal. Iterative separation reached zero inferred closure conflicts after 99 rounds without raising the objective; final solver status `OPTIMAL`, reported bound `30.0`, wall time 99.976 seconds.
- Model size after cuts: 26,483 variables and 53,395 constraints.
- Output hashes: `SCHEDULE_ACCESS.csv` `e3a7f17711c63567219743ca09eb541d717783e0835bc7c95606eb4b21dafd58`; `SCHEDULE_OCCUPANCY.csv` `d0d1cd2bdbda6924c32681d74039b29414fd6728b78df7f3564ea5de9c334779`; `RESULTS.csv` `6b11cc1d0dac6c47a5549b1ac410c81dc629117aa44fbdaacaf21e8e343badd7`.
- Limitation: closure feasibility is established only against the inferred screen, not the reference validator. Cross-seed reproducibility remains untested.
- Decision: protect as the Scenario B internally checked incumbent and attempt independent seeds.

### E005: Scenario C iterative inferred-closure attempt

- Timestamp: 2026-09-18 22:58:42 +08
- Hypothesis: the `25.2` closure-free lower bound can survive C's inferred closure rules, possibly using the permitted ECLO/capacity levers.
- Dataset hash: `e6608a9b396df162a6cf9ed74527c493eb07edf1ff89cc81f6906771c82f2188`
- Submission hash: `9f1043fe97f3464ad7b4ee8d6c1c45e6b4a40013ebbd4340b1210a1a6ceb1563`
- Scenario: C
- Code commit: uncommitted working tree after `faa7edb`
- Solver: OR-Tools CP-SAT 9.15.6755
- Parameters: 180-second total limit, seed 1, 8 workers, 200-round ceiling
- Result: rejected. The last schedule scored `29.1` from `9.1` delay plus four ECLO rows, with zero excess capacity, but retained five inferred closure conflicts after 93 separation rounds. Status was `FEASIBLE`; closure-free lower bound remained `25.2`.
- Decision: quarantine. It is neither feasible nor an incumbent; improve convergence or formulation before using its score.

### E006: Safe Scenario C fallback from protected A schedule

- Timestamp: 2026-09-18 22:59:38 +08
- Hypothesis: Scenario A's internally feasible `32.2` schedule remains feasible under C's looser capacity and ECLO rules when the scenario result rows are recomputed.
- Dataset hash: `e6608a9b396df162a6cf9ed74527c493eb07edf1ff89cc81f6906771c82f2188`
- Submission hash: `c3526299af69571461c8dbb88e753d198989061455e5985fa67b83079495f639`
- Scenario: C
- Solver: none; deterministic unchanged-schedule relabelling followed by independent evaluation
- Result: internally feasible at `32.2`, with 192 access rows, 928 occupancy rows, zero ECLO, zero excess capacity, and zero implemented hard violations.
- Output hashes: `SCHEDULE_ACCESS.csv` `0adcb58e9d9eddfc5f7192fd38caa0b1c4a70820197a3772993fc6e75ddfb885`; `SCHEDULE_OCCUPANCY.csv` `67974be64e27bb7328c6e86e0a88bb07c5ae5ffdca1fade670bd67cabd2a49e2`; `RESULTS.csv` `07593f680a1d3a89762d0b27167b93bb29b12eecf8c03a61aa073e951a4fe9d2`.
- Limitation: it is a safe fallback, not evidence that `32.2` is optimal for C. The reference validator remains unavailable.
- Decision: protect as the current C incumbent while pursuing a closure-feasible result below `32.2`.

### E007: Warm-started Scenario C inferred-closure optimum

- Timestamp: 2026-09-18 23:01:12 +08
- Hypothesis: a known-safe `32.2` hint will keep the separator in productive possession partitions and expose a valid improvement below the fallback.
- Dataset hash: `e6608a9b396df162a6cf9ed74527c493eb07edf1ff89cc81f6906771c82f2188`
- Submission hash: `d5b8e7a35462c0e980ec391e0c34c1cb9a4eb9866d1a420efc96cc3a8d28b438`
- Scenario: C
- Code commit: uncommitted working tree after `faa7edb`
- Solver: OR-Tools CP-SAT 9.15.6755
- Parameters: 600-second limit, seed 1, 8 workers, 500-round ceiling, E006 used only as a complete solution hint
- Result: internally feasible and `OPTIMAL` under the accumulated inferred-closure cuts at `26.1`. Score comprises `16.1` Priority-3 delay plus two ECLO rows; excess capacity is zero. Output contains 191 access rows and 925 occupancy rows.
- Convergence: 19 closure-separation rounds, zero remaining inferred conflicts, matching `26.1` bound, 21.536 seconds, 23,298 variables, 45,807 constraints.
- Output hashes: `SCHEDULE_ACCESS.csv` `520925fdb3afa85cbca937af458a345c9deb55a39ba1b1ee2c9aa7379e9b4b37`; `SCHEDULE_OCCUPANCY.csv` `80f73d10302d35edc38cea6f5266f17615fc175cf424ec8e902be1b55e86a26d`; `RESULTS.csv` `68e519a555962b1b73dae1287307a9df33807b6b2b8e4e159672a25e6f4eae98`.
- Interpretation: because every added separator is necessary under the inferred screen, matching feasibility and bound support `26.1` as the inferred-model optimum. This is not a reference-validator proof.
- Decision: supersede E006 as the protected Scenario C incumbent; retain E006 as fallback.

### E008: Cross-seed reproducibility

- Timestamp: 2026-09-18 23:02:04 +08
- Hypothesis: protected scores are structural rather than lucky outcomes from one random seed.
- Scenario C seed 2: `OPTIMAL` at `26.1` after 20 closure rounds in 23.890 seconds; zero implemented violations; 191 access rows, 925 occupancy rows, two ECLO rows, zero excess capacity, and the same `16.1 + 10.0` score decomposition. Submission hash `3e0b93f28582e0fda77f630fc34a6f1d36d71ef14136dd43a121c3f23a80a6d2` differs from seed 1.
- Scenario B seed 2: `OPTIMAL` at `30.0`, zero closure rounds from the protected hint, zero implemented violations, six ECLO rows, zero excess capacity, zero delay. Access rows match seed 1; occupancy hash differs because equivalent legal group labels/packing were selected.
- Scenario A seed 2: the restricted repair reproduces the identical `32.2` submission hash and passes every implemented check.
- Decision: score and feasibility reproduce across two seeds for all protected scenarios. This reduces random-search risk but does not reduce the reference-validator semantic risk.

### E009: Unrestricted Scenario A inferred-closure optimum

- Timestamp: 2026-09-18 23:04:01 +08
- Hypothesis: the restricted E003 repair score remains optimal when every activity, week, access night, and local group is released.
- Dataset hash: `e6608a9b396df162a6cf9ed74527c493eb07edf1ff89cc81f6906771c82f2188`
- Submission hash: `b21a32b40b23ce01ad18dbfae84e01693be03ddd5de2e8db5be32e151aad0773`
- Scenario: A
- Solver: OR-Tools CP-SAT 9.15.6755
- Parameters: 300-second limit, seed 1, 8 workers, 500-round ceiling, E003 used only as a complete solution hint; no activity was frozen
- Result: internally feasible and `OPTIMAL` under the accumulated inferred-closure cuts at `32.2`, with zero ECLO, zero excess capacity, 192 access rows, 928 occupancy rows, and zero implemented violations.
- Convergence: 34 closure-separation rounds, matching `32.2` bound, 11.700 seconds, 19,212 variables, 37,275 constraints.
- Output hashes: `SCHEDULE_ACCESS.csv` `1993c779f6b729ffcbca2e7b42daa9bb85eb1ac44de0f1f4720e42edc49614e8`; `SCHEDULE_OCCUPANCY.csv` `4172605a8f1fa47ad1a8db33ababcebdb5d6f53c49c3550285b265c3691781b1`; `RESULTS.csv` `9eca188c07c21438f3b1adc03cb83bb7ec0264f0a816756f9293c565bbc0ae1a`.
- Cross-seed check: seed 2 independently reached `32.2`, zero conflicts, and zero implemented violations after 38 rounds in 13.781 seconds, with a different submission hash.
- Decision: supersede the restricted E003 output as the protected Scenario A inferred-model incumbent. Retain E003 as a conservative fallback close to the organiser fixture.

### E010: Independent raw-CSV score recomputation

- Timestamp: 2026-09-18 23:08:48 +08
- Hypothesis: the protected scores are not artifacts of shared scorer/model code.
- Method: a second implementation directly parses the eight input/submission CSV schemas and recomputes workload, activity completion, published activity-level delay weights, distinct-group excess, ECLO count, and scenario objective. It imports no solver, topology, instance, closure, or primary-evaluator code.
- Result: exact agreement for A=`32.2` (`32.2` delay), B=`30.0` (six ECLO, zero delay/excess), and C=`26.1` (`16.1` delay plus two ECLO, zero excess). Twelve regressions pass.
- Limitation: this reduces correlated arithmetic/parsing risk only. It does not independently validate topology expansion, closure semantics, or official aggregation behaviour.
- Decision: require both score implementations to agree before protecting future incumbents.

### E011: Deterministic runtime falsification and anytime-loop correction

- Timestamp: 2026-09-18 23:19:08 +08
- Hypothesis: the C=`26.1` result can be reproduced with one worker and does not depend on parallel-search timing.
- Failed attempt: one worker with no per-round cap consumed the 300-second total budget after one closure round and ended on an invalid `25.2` schedule with three conflicts. It exited with code 4 and was not promoted.
- Root cause: a single CP-SAT call could consume all remaining time while proving or improving the current cut relaxation. The loop also stopped immediately upon finding any safe schedule, even when status was only `FEASIBLE` and a lower bound remained.
- Correction: cap each solve round; preserve the best closure-safe rows separately; continue below a safe but unproven incumbent; never serialize the last invalid solver state over a safe incumbent; aggregate branches/conflicts/round counts in telemetry.
- Corrected C result: one worker, seed 1, three-second rounds, 300-second total limit, safe A-derived hint. `OPTIMAL` at `26.1` after 38 solves/35 closure rounds in 111.876 seconds, with zero implemented violations. Submission hash `3d7b66edf9da5c8c27b599b94304101671dafb52f923c958d4b4913af4342f00`; both scorers agree.
- Corrected A result: one worker reproduced `32.2` as `OPTIMAL` after 41 solves/39 closure rounds in 120.329 seconds.
- Corrected B result: one worker reproduced `30.0` as `OPTIMAL` after two solves in 3.164 seconds.
- Decision: use three-second per-round limits as the tested default and retain safe incumbents across all subsequent searches.

### E012: No-hint construction from raw public inputs

- Timestamp: 2026-09-18 23:29:48 +08
- Hypothesis: protected scores do not require a complete organiser or prior schedule as a search hint.
- Parameters: no `sample_hint`; seed 1; 8 workers; three-second solve rounds; 300-second total limits; 500 closure-round ceiling.
- Scenario C: `OPTIMAL` at `26.1` after 49 solves/48 closure rounds in 84.967 seconds. Both scorers report `16.1` delay, two ECLO rows, zero excess, and zero implemented violations. Submission hash `93afe29fc91e24df8ba39830bcda5414be38e79986c9967b40462ac5917fb7a8`.
- Scenario A: `OPTIMAL` at `32.2` after 167 solves/166 closure rounds in 209.412 seconds. Both scorers report `32.2` delay, zero ECLO/excess, and zero implemented violations. Submission hash `46bd59a2235eeb57f30ea89b1ca80b36a77f615b78e79f55f6a698626d25f69c`.
- Scenario B: `OPTIMAL` at `30.0` after 154 solves/153 closure rounds in 154.713 seconds. Both scorers report six ECLO rows, zero delay/excess, and zero implemented violations. Submission hash `9e5ec2a550be74f4efe1486297ef973c54d92259e47f202db9633d996ce54072`.
- Result: complete-schedule hints are not necessary on the public instance. No-hint runtime remains a material risk for larger hidden inputs, especially A/B.
- Decision: promote the no-hint outputs as the current-code protected incumbents; retain hinted variants as faster fallbacks for the public deliverable.
