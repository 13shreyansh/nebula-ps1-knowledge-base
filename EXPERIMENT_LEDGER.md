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

### E013: Scenario-specific solve-round budget

- Timestamp: 2026-09-18 23:41:10 +08
- Hypothesis: shorter separation rounds improve time to the same protected score by adding closure cuts sooner.
- Method: repeat no-hint seed-1 eight-worker A/B/C solves with one-second rounds; compare against the E012 three-second-round runs. All other solver logic and total budgets remain unchanged.
- Result: A reproduced `32.2` in 99.533 seconds versus 209.412; B reproduced `30.0` in 101.731 seconds versus 154.713; C reproduced `26.1` in 120.856 seconds versus 84.967. Every retained output has zero implemented violations.
- Interpretation: one-second rounds materially helped A/B but hurt C. This is one multithreaded seed, so the time differences are directional rather than stable performance estimates.
- Decision: use one-second default rounds for A/B and three seconds for C; continue recording an explicit override and benchmark additional seeds before a stronger runtime claim.

### E014: Renamed/shuffled fixture falsification and protected C portfolio

- Timestamp: 2026-09-18 23:58:20 +08
- Hypothesis: the generic solver should retain feasibility and score when all identifiers are bijectively renamed and every input CSV is row-shuffled.
- Dataset hash: `ee1e97246c45b1a91d49aa3fe23a69ce0ff9d8783e78f6b3f5a7d99afbaf7aa1`
- Transformation check: an independent multiset reconstruction exactly matches all eight expected transformed tables; no deadlines, capacities, priorities, predecessors, workload, topology, or activity semantics changed.
- Failed direct-C evidence: a 180-second no-hint run ended `UNKNOWN` with one closure conflict and no safe incumbent. After canonicalising model and closure iteration, a second 180-second run still ended `FEASIBLE` with six closure conflicts and no safe incumbent. Neither output was promoted.
- Staged evidence: transformed A solved without a hint at `32.2` in 96.102 seconds. Using that generated A schedule only as a C hint produced `26.1` in 22.767 seconds. Both scorers report `16.1` delay, two ECLO rows, zero excess, and zero implemented violations.
- Portfolio verification: the executable portfolio independently rebuilt transformed A at `32.2`, relabelled and checked it as the protected C fallback, then selected a checked C=`26.1` candidate after 102.930 seconds for A and 20.187 seconds for C. Final submission hash: `30075901e8ecc15d364ef6b45f797256f1d4483697c1adda6a2aa7809712ae7c`.
- Interpretation: direct C search is not robust to a semantics-preserving rename under the tested budget. The data-derived A-to-C portfolio is robust on this falsification and never replaces the fallback with an infeasible or non-improving candidate.
- Limitation: this is still one topology and one transformed seed; both acceptance and separation use the inferred closure semantics, and no reference-validator result exists.
- Decision: make protected A-to-C staging the default robust C strategy; retain both direct-C failures and test further topology/capacity perturbations.

### E015: Deterministic transformed-fixture construction failures

- Timestamp: 2026-09-19 00:10:02 +08
- Hypothesis: the protected transformed A-to-C portfolio can remove eight-worker scheduling luck by using one worker.
- Failure 1: one-second A rounds stopped after 21.222 seconds when one round returned `UNKNOWN`, despite 159 seconds remaining. No safe incumbent existed.
- Correction 1: retry `UNKNOWN` with a bounded doubled round budget rather than abandoning the remaining total budget.
- Failure 2: the corrected run consumed all 180 seconds but repeatedly returned to one-second rounds after intermediate solutions; it ended with two closure conflicts and no safe A output.
- Correction 2: preserve the escalated per-round budget as accumulated cuts make later relaxations harder.
- Failure 3: persistent escalation consumed the full 300-second A budget and ended on a `3482.5` candidate with seven closure conflicts; it was rejected. One worker therefore still lacks a generic no-hint transformed A constructor under the tested budget.
- Alternative failure: forbidding every singleton closure-conflicting activity pair up front made A infeasible in 0.571 seconds. This is too conservative because legal possession-component merging is necessary; the option was removed from production code.
- Integrity result: every failed portfolio exited nonzero, produced no selected final submission, and left the eight-worker incumbents unchanged.
- Decision: retain adaptive `UNKNOWN` handling because it fixes premature abandonment, but do not claim deterministic transformed-instance robustness. Do not use the over-conservative formulation. Prioritise official semantic evidence and the working checked eight-worker portfolio over additional blind runtime spending.

### E016: Random identifier-permutation metamorphic test

- Timestamp: 2026-09-19 00:18:02 +08
- Hypothesis: the protected scores and construction path do not depend on the lexical ordering of public line, station, contract, or activity identifiers.
- Method: randomly permute each identifier namespace, derive every foreign key and location ID through the bijection, shuffle every CSV table, and run the unchanged solver without any original submission. This changes model variable/constraint order while preserving scheduling semantics.
- Dataset hash: `faff596536fa26f8747056e7a3dfe27e352471a5f1c9dc7c2a72185ec068e794`
- Scenario C portfolio: transformed A reached `32.2` in 118.813 seconds; hinted C reached `26.1` in 35.196 seconds; the candidate replaced the checked fallback. Final hash `3a0a52adf449939a0e08f23bb86cecba723c4548519829e1b63f37c6cdfcb1d8`.
- Scenario B: no-hint search reached `30.0` in 109.001 seconds, with six ECLO rows, zero delay/excess, and hash `c3f24b727d20727775ab31655a8299e9623675888e2dcd766322aeb92bc4ef55`.
- Verification: the primary checker reports zero implemented violations; the independent raw-CSV scorer exactly reproduces both objectives and components.
- Interpretation: the eight-worker pipeline survives a stronger metamorphic test than row shuffling or order-preserving renaming. It does not prove performance on different topology, demand, capacity, or scale distributions.
- Decision: keep random identifier permutation as a regression fixture generator and proceed to structural, not merely nominal, perturbations.

### E017: Invalid-identifier checker hardening

- Timestamp: 2026-09-19 00:18:02 +08
- Falsification: evaluating an original-ID submission against a renamed instance correctly accumulated unknown-activity violations, but then the closure screen dereferenced an unknown ID and crashed.
- Correction: pass only known activities, known locations, and access-backed occupancy rows into the closure screen after recording schema/domain violations.
- Verification: a dedicated mutation regression now rejects an unknown activity without crashing; all 15 tests pass.
- Decision: retain the filter as defensive validation. Malformed or foreign output must fail as evidence, not terminate the checker before producing diagnostics.

### E018: Capacity-pressure and priority-landscape structural fixture

- Timestamp: 2026-09-19 00:28:35 +08
- Hypothesis: success extends beyond isomorphic identifier changes to a materially different capacity and objective landscape.
- Method: derive a known-feasible fixture by reducing each location's capacity to the maximum distinct groups used there by the protected A oracle (minimum 1), then independently permute contract and activity priorities. This leaves topology/workload intact but changes 67 of 76 locations to capacity 1 and moves delay costs across activities. The oracle schedule remains feasible by construction.
- Dataset hash: `40c206b401c78941a3fc4914d5acaa2dd97733a9bf29eefd6270db01ef71ae14`
- Oracle check: the unchanged protected A schedule has zero implemented violations and now scores `949.2`, proving the altered instance is feasible before testing the solver.
- Scenario A no hint: `OPTIMAL` at `867.3` after 177 solves/176 closure rounds in 140.817 seconds. Both scorers agree; 192 access rows, 928 occupancy rows, zero ECLO/excess, and zero implemented violations.
- Scenario C clean portfolio: rebuilt A=`867.3` in 95.178 seconds, protected it as fallback, then reached `OPTIMAL` C=`29.1` in 12.396 seconds. C comprises `9.1` delay plus four ECLO rows, zero excess; 190 access rows and 920 occupancy rows. Final hash `5445e6b97f254c9c110b7078b9f49b4f69245d7cdc772daffc5117011e90ffe2`.
- Scenario B no hint: `OPTIMAL` at `30.0` after 125 solves/124 closure rounds in 108.999 seconds, with six ECLO rows, zero delay/excess, and hash `ad9b55d483907a4b6eaef105f11eaa1313f0df2543926a15a91d8ae0f82d7a9a`.
- Packaging verification: the selected C submission directory contains exactly `SCHEDULE_ACCESS.csv`, `SCHEDULE_OCCUPANCY.csv`, and `RESULTS.csv`; `PORTFOLIO.json` and all stage outputs are in the sibling audit directory.
- Interpretation: the eight-worker pipeline handles a substantially tighter supply pattern and a different priority objective without an external schedule. This is stronger hidden-instance evidence, but still shares the original topology, workloads, dates, and predecessor graph.
- Decision: retain the structural fixture generator and clean-output portfolio. Next change workload/date/predecessor structure or scale while maintaining an explicit feasible oracle.

### E019: Demand and precedence mutation

- Timestamp: 2026-09-19 00:38:42 +08
- Method: starting from the oracle-feasible pressure fixture, reduce 16 activity workloads by one, advance 37 planned starts by up to two weeks, and add 10 acyclic predecessor edges only where the oracle has a strictly earlier predecessor completion. The unchanged A oracle remains feasible and scores `113.4`.
- Dataset hash: `ab6f4710d65312ef3ffa9246a8372b15b5656457d065e8d3a56b7123a1e95043`
- A no hint: `OPTIMAL` at the `0.0` floor in 84.294 seconds; 176 access rows, 854 occupancy rows, zero implemented violations, and both scorers agree.
- B no hint: primary-score `OPTIMAL` at `0.0` in 82.899 seconds with zero ECLO/excess/delay and zero implemented violations, but the first safe incumbent contained 211 access rows.
- C clean portfolio: reconstructed A=`0.0`; C also reached `0.0`; strict-improvement selection correctly retained the equal-score checked fallback. The independently checked final output has 176 access rows and exactly three CSV files.
- Interpretation: the eight-worker pipeline survives material workload, release-date, and predecessor-graph changes. The zero floors make these feasibility/generalisation tests, not difficult objective benchmarks.

### E020: Full-gate redundant-row pruning

- Timestamp: 2026-09-19 00:38:42 +08
- Defect: the safe-incumbent loop proves the primary score by searching strictly below it, so it can preserve the first safe primary optimum without completing the subordinate row-count objective. The B demand output had 211 rows for 176 required standard accesses.
- Correction: a postprocessor tentatively removes one access and all matching occupancy, resequences the activity, recomputes contract results, and accepts the deletion only when the full checker preserves hard feasibility and does not worsen the official score. It repeats to a fixed point. This gate is necessary because deleting a bridge activity can split a co-sharing component and create a closure conflict.
- Result: the B demand output pruned `211 → 176` rows, retained objective `0.0`, retained zero implemented violations, and both scorers agree. Final hash `963c637f30393ac8a5523ce4a6172ea9a7db27d79c7eb979ec084067c1624e36`.
- Portfolio integration: both the C fallback and candidate are pruned before comparison; raw stages and prune reports remain in the audit directory. An integrated demand-fixture rerun retained 176-row C=`0.0`, exact-three-CSV output, and hash `0f9d89ef22ed478a7e38562c4f0864caba1a75c6bbd898f436cdf9645b65e431`.
- Decision: describe solver `OPTIMAL` as primary-score optimal unless the subordinate objective is separately completed. Use checked pruning before packaging every answer key.

### E021: Public answer-key release gate

- Timestamp: 2026-09-19 00:43:00 +08
- Method: pass each protected public incumbent through the full-gate pruner into a dedicated scenario directory, require exactly the three official CSV filenames, run the main checker and independent raw-CSV scorer, and pin both aggregate and per-file SHA-256 hashes in a manifest.
- A: `32.2`, 192 access rows, 928 occupancy rows, submission hash `46bd59a2235eeb57f30ea89b1ca80b36a77f615b78e79f55f6a698626d25f69c`.
- B: `30.0`, 189 access rows, 917 occupancy rows, submission hash `9e5ec2a550be74f4efe1486297ef973c54d92259e47f202db9633d996ce54072`.
- C: `26.1`, 191 access rows, 925 occupancy rows, submission hash `93afe29fc91e24df8ba39830bcda5414be38e79986c9967b40462ac5917fb7a8`.
- Result: pruning removes nothing from any public incumbent; each directory contains exactly `SCHEDULE_ACCESS.csv`, `SCHEDULE_OCCUPANCY.csv`, and `RESULTS.csv`; both scorers agree; all implemented checks pass; 19 release regressions pass.
- Limitation: `MANIFEST.json` explicitly records `reference_validator_confirmed=false`.
- Decision: use `deliverables/public/{A,B,C}` as the protected public answer keys. Do not package telemetry, stages, manifests, or audit reports inside the scenario directories.

### E022: Strict buffer-overlap hedge with no score cost

- Timestamp: 2026-09-19 00:55:00 +08
- Risk: the official README says buffers never overlap, but its unchanged stated-feasible sample has four buffer-only overlaps under the published topology expansion. The sample-consistent checker allowed buffer-buffer overlap and rejected only buffer-to-work collisions.
- Method: add an explicit alternate closure policy that also rejects overlap between external buffer sectors of distinct possession components, including Live opposite-bound mirrored buffers. Keep the existing checker default unchanged; solve new candidates under the stricter policy and require both screens to pass before promotion.
- Scenario A: `OPTIMAL` at `32.2`, matching bound, 145 solves/144 closure rounds, 106.178 seconds, 192 access rows, zero strict conflicts.
- Scenario B: `OPTIMAL` at `30.0`, matching bound, 173 solves/172 closure rounds, 151.510 seconds, 189 access rows, six ECLO rows, zero excess/delay, zero strict conflicts.
- Scenario C: `OPTIMAL` at `26.1`, matching bound, 30 solves/29 closure rounds, 76.730 seconds, 191 access rows, two ECLO rows, `16.1` delay, zero excess, zero strict conflicts.
- Verification: full-gate pruning removed no rows; the main checker and independent raw-CSV scorer agree; each promoted answer key passes both closure screens; the manifest pins normalized file hashes and marks `strict_buffer_overlap_checked=true`; 22 regressions pass.
- Result: all three protected scores are unchanged while no longer depending on the known buffer-only ambiguity. This is stronger robustness evidence, not reference-validator confirmation, because other closure details remain inferred.
- Implementation defect found during the same audit: `solve-a-relaxation` referenced an undefined CLI argument and `solve-c-portfolio --audit-output` ignored its value. Both routes are corrected and directly regression-tested.

### E023: Hidden-date boundary hardening

- Timestamp: 2026-09-19 01:03:00 +08
- Defect: Scenario B bounded eligible weeks with `week_for_date(planned_completion_date)`. That is equivalent to the final on-time week only when the date is the week's Sunday, as in the public instance. A midweek hidden deadline would admit the containing week even though its Sunday completion is late.
- Correction: compute the latest week whose derived completion date is on or before the hard deadline. A regression uses Wednesday 2027-01-13: it is contained in week 2, but week 1 is the latest week completing by that date. Public-instance behaviour is unchanged.
- Related semantic guards: sample regressions now prove that possession closure exemption propagates through transitive local co-sharing links, while `access_night` remains a contract/type accounting index and must not equal physical possession membership.
- Verification: all 25 regressions and `git diff --check` pass. No score or answer-key artifact changed.

### E024: Preserve closure hedge through pruning and portfolio selection

- Timestamp: 2026-09-19 01:07:00 +08
- Risk: removing a redundant access can split a transitive possession component. A candidate generated by the strict closure solver could therefore regain a buffer-overlap conflict if pruning checked only the sample-consistent policy.
- Correction: strict-buffer mode now propagates through A construction, C hinting, fallback pruning, candidate pruning, final selection, and standalone pruning. Every tentative deletion must retain strict closure feasibility; final prune reports record the policy.
- Verification: strict pruning leaves the dual-policy A answer key unchanged; portfolio and CLI flag propagation are regression-tested; release tests require each prune report's final submission hash to match the manifest. All 26 tests pass.

### E025: No-hint strict C portfolio

- Timestamp: 2026-09-19 01:02:00 +08
- Hypothesis: strict-buffer robustness must survive the actual hidden-instance path without an external schedule hint.
- Method: seed 2, eight workers, raw public input only. Construct strict A, relabel and strict-prune it as the protected C fallback, use that generated fallback only as a nonbinding C hint, strict-prune the candidate, and replace the fallback only after a checked strict improvement.
- A stage: primary-optimal safe incumbent `32.2` in 89.593 seconds, 113 solves/111 closure rounds. The subordinate tie was not solver-proven, but strict pruning retained the necessary 192 rows.
- C stage: `OPTIMAL` at `26.1` with matching bound in 19.088 seconds, 17 solves/16 closure rounds. The candidate has 191 access rows, two ECLO rows, `16.1` delay, zero excess, zero hard violations, and zero strict conflicts.
- Release gate: the selected directory contains exactly the three CSVs; main and independent scorers agree; strict pruning reports are present only in the separate audit directory. Final hash `56c649621654ae3fac62c64b839e576de1d7862e220e247bba3b8313219b01c1`.
- Decision: retain the existing protected C because its score, components, row counts, and dual-policy feasibility are equal. Preserve this run as independent no-hint construction evidence, not as a score improvement.

### E026: Closure-cut soundness correction

- Timestamp: 2026-09-19 01:20:00 +08
- Invalidated proof mechanism: the former cut required conflicting possession components to merge directly. A legal repair may instead add a third activity that bridges them transitively, as demonstrated by the public sample. Feasible schedules remain valid, but matching bounds from that cut model are not sound global-optimality evidence.
- Exact-layout no-good: logically safe but impractical. A strict A run exhausted 300 seconds after 424 closure rounds, returned a `6065.5` candidate with ten conflicts, and never rediscovered the checked hint. It exited nonzero.
- Incumbent correction: a fully checked hint is now a protected safe fallback, not only CP-SAT guidance. Search is constrained to strict primary-score improvement; a zero-time regression proves the fallback survives without solver cooperation.
- Bridge-safe cut: if conflicting activities remain in the week, permit the first component to join any activity sharing a local footprint, which preserves every possible direct or transitive path. A 300-second strict A run retained the checked `32.2` fallback with zero conflicts but did not prove a lower bound; 127 solves, 123 closure rounds, three `UNKNOWN` retries, 127,564 variables, and 362,941 constraints.
- Consequence: A=`32.2`, B=`30.0`, and C=`26.1` remain the protected dual-screen feasible scores. B's `30.0` still matches its independent workload/deadline lower bound. C=`26.1` is no longer described as proven optimal; its closure-free lower bound remains `25.2`.
- Next direction: reduce connectivity-cut growth or encode possession connectivity exactly. Do not regain speed by restoring the unsound direct-component cut.

### E027: Targeted C=25.2 repair neighborhoods

- Timestamp: 2026-09-19 01:26:00 +08
- Starting point: closure-free C=`25.2` has six strict closure conflicts involving 15 activities.
- Group-only repair: fix every access week, ECLO value, and local night index while leaving all possession groups free. The bridge-safe model became infeasible after one cut in 0.123 seconds. Regrouping alone cannot repair that exact access plan under the strict screen.
- Conflict-activity neighborhood: free access decisions only for the 15 conflict activities and fix all others. The model reached strict-feasible `26.1` and a matching restricted bound in 9.211 seconds over 21 solves/20 rounds. Main and independent scorers agree; hash `10940b782b678be691bdac11647a4623e26941e76bbc1772b20c177f33e2c08c`.
- Topology neighborhood: expand freedom to all 43 activities sharing any footprint with an original conflict activity; keep 11 remote activities fixed. The 300-second run ended nonzero with seven conflicts, 134,604 variables, 381,265 constraints, and no safe incumbent.
- Interpretation: the protected `26.1` is optimal in the small conflict neighborhood, not globally proven. The larger failure is a formulation-growth result, not evidence that `25.2` is impossible.

### E028: Analytical C=26.1 lower bound and bridge-neighborhood failure

- Timestamp: 2026-09-19 01:33:00 +08
- Lower-bound chain: A059's seven standard accesses from week 14 finish in week 20, contributing unavoidable delay `7.0`; replacing that delay requires at least two ECLO nights costing `10`. A036's seven accesses from week 22 occupy every week 22–28 without ECLO and contribute `18.2` delay in week 28. Live PM A075 must use one of weeks 24–28 to remain on time and its mirrored/buffered closure blocks A036's `S14_H01:EB`; the two cannot co-share.
- Cheapest resolution: six A036 rows require at least two ECLO bonuses, cost `10`, and can finish in week 27 at delay `9.1`; schedule A075 in week 28. Adding A059's `7.0` yields `26.1`. Leaving A036 uncompressed forces A075 to week 29 and gives at least `18.2 + 7.0 + 7.0 = 32.2`. More ECLO or excess capacity cannot reduce the hard closure at lower cost.
- Verification: the protected strict schedule attains `26.1`; regressions pin the three workloads, start/planned weeks, activity costs, A075 PM type, disjoint work footprints, and A075-to-A036 blocked-location intersection.
- Conclusion: C=`26.1` is optimal under the implemented published-rule interpretation without using the withdrawn direct-component proof. Reference-validator confirmation remains absent.
- Additional search: a 30-activity neighborhood containing the 15 original conflict activities plus every one-step bridge candidate exhausted 300 seconds, reached 140,487 variables/400,285 constraints, and ended `UNKNOWN` with five conflicts and no safe incumbent. It adds no score evidence and is retained as a scalability failure.

### E029: Separate fast heuristic construction from sound verification

- Timestamp: 2026-09-19 01:35:00 +08
- Design: `bridge_safe` remains the default sound separator. `direct_heuristic` restores the faster over-restrictive direct-component cut only for candidate generation; it suppresses all solver bounds and optimality flags and labels safe output `HEURISTIC_SAFE_INCUMBENT`.
- Construction test: strict B, raw input, seed 3, eight workers, no hint. The direct heuristic produced checked B=`30.0` in 53.450 seconds over 65 solves/64 closure rounds.
- Verification test: use that checked candidate as a protected bridge-safe incumbent and search only below `30.0`. The base model proved infeasible in 0.180 seconds with zero branches, so B's primary optimum is soundly certified without using heuristic cuts.
- Result: a two-stage generate-then-verify pattern retains the practical speed of the heuristic while preventing its restricted feasible space from becoming false optimality evidence.

### E030: Integrated staged workflow and multi-seed fallback

- Timestamp: 2026-09-19 01:43:49 +08
- Workflow: `solve-staged` runs bounded direct-heuristic attempts with consecutive seeds, full-checks and strict-prunes the first safe incumbent, invokes bridge-safe verification/improvement with that incumbent protected, and emits only the three submission CSVs. All stage telemetry stays in a separate audit directory.
- Adversarial run: strict Scenario B from raw input, eight workers, seeds starting at 3, 90 seconds per heuristic attempt, and 30 seconds for verification. Seed 3 exhausted its budget with three strict conflicts and no safe objective. Seed 4 then found a strict-feasible `30.0` incumbent in 80.301 seconds.
- Sound verification: the bridge-safe `<30.0` model was infeasible in 0.179 seconds with zero branches, proving the primary `30.0` bound under the implemented semantics without importing any heuristic bound.
- Independent checks: the main evaluator and raw-CSV scorer both report `30.0`; the strict screen reports zero conflicts; the output contains exactly `RESULTS.csv`, `SCHEDULE_ACCESS.csv`, and `SCHEDULE_OCCUPANCY.csv`. Repository LF normalization changed the byte-level submission hash from runtime `0aeb92848367bcc700e1edaa858b57962ed21a6dff11312c406a7db6f1cd3705` to `80d3ba702661de023c7000db462778c051742f8e9a3e03566229c5cbc90b87c7` without changing parsed rows or score.
- Interface defect found: `--heuristic-attempts` was initially forwarded to the ordinary flexible command and omitted from the staged call. The completed run still used the intended default of three. Routing is corrected and a non-default-value regression now covers it.
- Decision: retain the existing protected public B answer key because the score is equal. Use the staged workflow for fresh-instance construction, while preserving every failed attempt and requiring sound verification before any optimality claim.

### E031: Staged construction on a changed capacity and priority regime

- Timestamp: 2026-09-19 01:51:07 +08
- Fixture: regenerate the known-feasible structural regime from the current strict A oracle, reducing each location to its oracle-required capacity and permuting contract/activity priorities. The oracle remains strict-feasible and scores `949.2`; normalized dataset hash `c9cc5779a332946c0c2323a18ca69e138ed04af577c1f2f56df3e2ad63ebebee`.
- Test: Scenario A from transformed input only, strict buffer policy, eight workers, seed 5, two allowed heuristic attempts, 120 seconds per attempt, and 60 seconds of bridge-safe verification. No submission hint was supplied.
- Result: the first heuristic attempt found a full-check and strict-screen feasible `867.3` candidate in 117.880 seconds, improving the feasible oracle by `81.9`. The separate raw-CSV scorer reproduces `867.3`; the clean output has 192 access rows, 928 occupancy rows, and exactly three CSVs.
- Sound phase: bridge-safe search retained the protected `867.3` incumbent after 60.035 seconds but did not prove a lower bound. It ended with 69,760 variables, 191,667 constraints, 64 closure rounds, and two unknown retries. Therefore `867.3` is a validated structural incumbent, not a sound optimality result.
- Reproducibility defect: all CSV emitters relied on the platform-default `\r\n` dialect. Repository normalization changed byte-level dataset and submission hashes while leaving parsed rows and scores unchanged. Every solver, relabeler, pruner, and fixture generator now explicitly emits LF; regressions check generated submission files.
- Final normalized submission hash: `dc61f3c7d84130fe2e9ee36172d113354ea8863f1d0c058f2bc968ba83e31245`.
- Decision: retain this as cross-regime construction evidence. Do not claim structural optimality, and do not spend more runtime on the same sound formulation without a stronger lower bound or compact connectivity model.

### E032: Sound construction fallback after total heuristic failure

- Timestamp: 2026-09-19 01:54:35 +08
- Defect: the staged workflow aborted when all direct-heuristic seeds failed, even though the bridge-safe model might still construct a schedule. Heuristic failure is not infeasibility.
- Correction: after exhausting heuristic attempts, run one bounded bridge-safe solve from raw input. Keep its telemetry and prune report separate; accept it only after the same full checker, optional strict screen, pruning, exact-three-file, and final-copy gates.
- Real falsification: generate a schema-valid fixture containing only A001/C001 while retaining the full network and parameters. Force the sole heuristic attempt to zero seconds, producing `UNKNOWN` with no objective, then give the bridge-safe fallback 10 seconds with one worker.
- Result: fallback solved Scenario A to the `0.0` floor in one solve and 0.004 seconds; 175 variables, 455 constraints, 47 branches, two access rows, ten occupancy rows, zero strict conflicts. Main and independent scorers agree; hash `35dc55405c542e6bb803cfc62c3bcb0ce6b9a5b2423c25dddcf4bc997e062dbd`.
- Boundary: this proves control flow and small-instance recovery, not public-scale fallback performance. Public-scale bridge-safe failures remain preserved.

### E033: Sound-fallback scale boundary

- Timestamp: 2026-09-19 01:58:13 +08
- Method: generate prefix subinstances of 5, 10, 20, 40, and 50 requested activities, automatically including predecessor closure. Force the direct heuristic to zero seconds and run only strict bridge-safe construction with one worker. Budgets are 15 seconds through 20 activities, 30 seconds at 40, and 60 seconds at 50.
- Successes: 5 activities solved at `0.0` in 0.024 seconds; 10 at `0.0` in 0.206 seconds; 20 at `0.0` in 0.305 seconds. The 40-activity model found a strict-feasible raw `819.7` incumbent in 30.003 seconds; full-gate pruning removed seven redundant late rows and improved it to `105.7`. Both scorers agree on every retained output and all strict screens are clean.
- Failure boundary: the 50-activity model exhausted 60.017 seconds after 33 solves/33 closure rounds, 5,615,550 branches, and 127,854 constraints. Its `7569.8` candidate retained six strict conflicts, so no score or submission was accepted and the final directory remained empty.
- Interpretation: sound fallback is effective on uncongested small/mid-scale instances but degrades sharply between these 40- and 50-activity prefixes. Prefix order is not a controlled hardness measure, so this is an observed boundary, not a universal size threshold.
- New opportunity: pruning can be a major score operator, not only a row-count tie-break. A pruned fallback should be fed back as a protected incumbent to a separate sound improvement/proof phase rather than returned immediately.

### E034: Prune then soundly verify the fallback incumbent

- Timestamp: 2026-09-19 02:02:56 +08
- Correction: fallback construction and verification now have distinct budgets. Every safe fallback is full-gate pruned, then passed as a protected incumbent to a fresh bridge-safe model that searches only below its score. A failed heuristic candidate may be supplied only as a non-protected CP-SAT hint; it cannot become the incumbent until fully checked.
- Test: repeat the strict 40-activity prefix with one worker, 30 seconds of sound construction, and 10 seconds of separate sound verification. The direct heuristic was forced to 30 seconds but ended without a usable objective, so no repair hint was used in this run.
- Result: sound construction found a checked `27.3` schedule; pruning removed seven redundant late rows and improved it to `18.2`. The verifier then proved `<18.2` infeasible in 0.034 seconds with zero branches. Main and independent scorers agree; zero strict conflicts; final hash `e4a542db2e9e4ff3569dd546060f3b1316c407e1b5b8cf28e49267f70477924f`.
- Instability evidence: an earlier nominally identical 30-second one-worker fallback on the same fixture returned raw `819.7`, pruned to `105.7`. Wall-clock termination and iterative solve progress can therefore yield materially different incumbents even without multi-worker search. Preserve both runs; do not select a method from the better outcome alone.
- Decision: keep prune→protected verification as the staged policy. Add cumulative deterministic-time telemetry before comparing repeated time-limited runs.

### E035: Cumulative deterministic-time telemetry

- Timestamp: 2026-09-19 02:03:54 +08
- Correction: `SolveTelemetry` now records CP-SAT deterministic time. Iterative closure solving accumulates it across every solve round rather than exposing only the final response; the closure-free solver records its single response value.
- Smoke test: forced-fallback A001 construction records 0.000332 deterministic seconds, followed by a zero-deterministic-time protected `<0.0` infeasibility proof. The output remains strict-feasible at `0.0` and all 33 regressions pass.
- Boundary: historical telemetry has no deterministic-time field and remains valid wall-time evidence only. Do not infer or backfill missing values. Wall time still governs the live deadline; deterministic time is for fairer search-work comparisons.

### E036: Failed-heuristic repair and diversified sound fallback

- Timestamp: 2026-09-19 02:07:04 +08
- Repair experiment: use the preserved 40-activity heuristic candidate scoring `78.4` but carrying closure violations as a non-protected hint to bridge-safe search. In 30.013 wall seconds / 28.618 deterministic seconds, the sound model produced a strict-feasible `78.4`; full-gate pruning removed seven late redundant rows and improved it to `55.3`. This proves unsafe output can guide repair without being promoted.
- Counterevidence: an unhinted 30-second sound run previously reached and proved `18.2` after pruning. A repair hint can trap search in a worse basin; it is not a universally better fallback.
- Correction: after heuristic failure, staged solving now runs a checked sound portfolio. Attempt 1 may use the best failed heuristic output, ranked by fewest remaining conflicts then score; attempt 2 is unhinted with a different seed. Each safe candidate is independently pruned and only the best checked objective is protected for verification.
- Short portfolio test: on the 40-activity fixture, a 0.5-second heuristic yielded no usable objective. Ten-second sound attempt 1 produced raw `819.7`, pruned `105.7`; attempt 2 reached `18.2` internally but retained one strict conflict and was rejected. The selected `105.7` passes both scorers and the strict screen; five-second verification retained it with lower bound `18.2`.
- Integrity consequence: an invalid lower-score candidate never outranks a safe incumbent. Portfolio diversity improves opportunity but does not justify selecting the best invalid objective or reporting its bound as achieved.

### E037: Previously successful public B seed is not repeatable

- Timestamp: 2026-09-19 02:10:51 +08
- Falsification: rerun the current staged public Scenario B path with strict buffers, eight workers, seed 4, one 90-second heuristic attempt, one one-second fallback, and five-second verification budget. Seed 4 had previously found checked `30.0` in 80.301 seconds.
- Result: the repeated heuristic consumed 90.016 wall seconds / 323.651 deterministic seconds, ended `UNKNOWN` with five strict conflicts, and produced no objective. The one-second sound fallback also produced no objective and retained six conflicts. The workflow failed closed and emitted no submission files.
- Interpretation: a seed label is not a reproducible search trajectory under eight-worker wall-clock search. Prior success remains valid artifact evidence, but cannot be treated as a reliability guarantee. Deterministic work was substantial, so extending the same seed slightly is not a principled correction.
- Decision: preserve the protected B=`30.0` answer key and the repeated failure. Fresh-instance construction must use a true multi-seed/worker portfolio and report feasibility rate, not advertise a single lucky seed.

### E038: Current staged public B recovery with sound proof

- Timestamp: 2026-09-19 02:12:35 +08
- Declared portfolio: strict public Scenario B, eight workers, seeds starting at 3, up to three 120-second heuristic attempts, two 30-second sound fallbacks only if needed, and five seconds of protected sound verification.
- Result: the first attempt, seed 3, produced checked `30.0` in 68.117 wall seconds / 247.174 deterministic seconds over 82 solves and 81 closure rounds. Pruning removed nothing. Bridge-safe verification proved `<30.0` infeasible in 0.167 wall / 0.505 deterministic seconds with zero branches.
- Independent gate: main and raw-CSV scorers agree on six ECLO rows, zero delay/excess, and objective `30.0`; strict conflicts are zero; output has exactly three LF CSVs. Hash `424696c48d07fff54d8ed9a516fcf07db91f87718faefc50775f46815ee71dd1`.
- Selection: retain the existing public B deliverable because it has the same score and already pinned manifest. This run is fresh-construction evidence, not a score improvement.
- Reliability boundary: together with E037, one current public B run succeeded and one failed under different fixed seeds and nearby budgets. This is insufficient for a calibrated feasibility rate and does not make seed 3 deterministic.

### E039: Exact seed-3 public B repeat

- Timestamp: 2026-09-19 02:14:38 +08
- Method: repeat E038 with the same current code, public input, strict policy, seed 3, eight workers, 120-second heuristic cap, and five-second verifier. Limit to one heuristic attempt so no later seed can mask repeatability.
- Result: checked `30.0` again, in 82.114 wall / 296.162 deterministic seconds versus E038's 68.117 / 247.174. Sound verification again proved `<30.0` infeasible in 0.167 wall / 0.505 deterministic seconds. Both scorers and the strict screen agree.
- Variation: the repeat's hash `f169774b61fb20db19b810d8753e86bf9bd735b3a224970e177c5138d7fc3f27` differs from E038's hash despite equal objective, components, and row counts. Parallel timed search is not schedule-reproducible under a fixed seed.
- Evidence boundary: seed 3 is 2/2 successful in these current-code 120-second runs; seed 4 is 0/1 at 90 seconds. This sample is too small and budgets differ, so it is descriptive rather than a calibrated success probability.

### E040: Current staged public A from raw input

- Timestamp: 2026-09-19 02:18:12 +08
- Method: strict public Scenario A, no submission hint, eight workers, seed 1, one 180-second direct-heuristic attempt, and 30 seconds of protected bridge-safe verification.
- Construction: checked `32.2` in 134.381 wall / 607.104 deterministic seconds over 146 solves and 145 closure rounds. Pruning removed nothing; 192 access rows, 928 occupancy rows, zero ECLO/excess, and `32.2` priority-weighted delay.
- Verification: the sound phase retained the protected `32.2` after 30.050 wall / 62.663 deterministic seconds but did not prove a solver lower bound; it grew to 51,185 variables and 133,351 constraints.
- Independent gate: main and raw-CSV scorers agree, both closure policies pass, and the final directory contains exactly three files. Hash `bcbe989f675585eab14b05d682e95c6723543954952a6c166e5c17a50c67deb3`.
- Evidence boundary: A's optimality under implemented semantics comes from the separate analytical lower bound, not heuristic telemetry or this incomplete sound search. Retain the existing equal-score public deliverable.

### E041: Direct current-code public C construction failure

- Timestamp: 2026-09-19 02:22:10 +08
- Method: strict public Scenario C, no submission hint, eight workers, seed 1, one 180-second direct-heuristic attempt, one 30-second repair-hinted sound fallback, and no use of the protected C deliverable.
- Heuristic result: `FEASIBLE` internal objective `112.2` but five strict conflicts after 180.020 wall / 934.504 deterministic seconds, 102 closure rounds, 24,688 variables, and 50,523 constraints. It was rejected.
- Repair result: the unsafe heuristic output was used only as a hint. Sound fallback exhausted 30.020 wall / 161.674 deterministic seconds, returned no objective, and retained six conflicts in a 39,785-variable / 95,291-constraint model. The final directory remained empty.
- Conclusion: direct full-instance C construction is not reliable enough as the primary path. Scenario A's feasible region is a subset of C's policy region, so a fully checked A schedule can be relabelled and protected as a legitimate C fallback before any C-specific improvement search.
- Next implementation: compose the guarded staged A constructor with A→C relabelling, strict pruning, and protected bridge-safe C search. Do not rely on the older C portfolio's raw bridge-safe A construction.

### E042: Guarded staged A-to-C fallback

- Timestamp: 2026-09-19 02:29:15 +08
- Implementation gate: `solve-staged-c` first completes the current staged A workflow, recomputes that schedule under C, strict-prunes and fully checks it, then protects it while running bridge-safe C search. A C candidate can replace the fallback only at a strictly lower fully checked score. Tests cover every CLI budget and an end-to-end forced-fallback fixture; 35 regressions pass.
- Fixture result: with zero heuristic and verification time, one second of sound A fallback solved the one-activity fixture at the `0.0` floor. Relabelled C, zero-time protected C search, both scorers, strict closure screen, exact-three-file gate, and final-copy hash all pass.
- Public result: A was rebuilt from raw input at strict-feasible `32.2` in 103.620 wall / 473.762 deterministic seconds. Ten seconds of sound A verification retained it. The recomputed C fallback is strict-feasible `32.2`; main and independent scorers agree, the directory contains exactly three CSVs, and hash `35fe4c913d49df933d179b9092e2817fd4c935c8c634f65d09222d6df753f74e` is stable across the final copy.
- C search: 120.018 wall / 665.522 deterministic seconds, 46 rounds, 89,095 variables, and 243,434 constraints retained `32.2` without improvement. Its `0.0` internal bound is not a proof because the solve ended with a protected incumbent rather than an exhaustive result.
- Falsification: the safety objective succeeded, but sound-only full-scale C improvement is not competitive. The next version should try bounded direct-heuristic C construction from the protected A hint, accept it only through full evaluation and strict pruning, then use bridge-safe search solely to protect, improve, or prove the checked candidate.

### E043: Guarded C workflow blocked by A construction variance

- Timestamp: 2026-09-19 02:34:11 +08
- Method: current guarded A-to-C workflow, strict public input, seed 2, one 120-second A heuristic attempt, one 60-second sound A fallback, then planned 90-second C heuristic and 30-second C verification. No schedule hint or protected public answer was supplied.
- Failure: the A heuristic ended `UNKNOWN` with two unresolved strict conflicts after 120.010 wall / 524.597 deterministic seconds and 143 solves. The sound fallback ended `UNKNOWN` with nine conflicts after 60.036 wall / 178.373 deterministic seconds. No checked A incumbent existed, so C stages did not run and the final directory remained empty.
- New implementation defect: the heuristic had generated a complete unsafe schedule before its final solve returned `UNKNOWN`, but the solver discarded those last rows and reported no objective. The staged controller therefore had no repair hint. Preserving the latest complete unsafe candidate for hinting can improve recovery without making it eligible for selection.
- Decision: do not retry a favorable A seed yet. First preserve last complete candidates across a terminal `UNKNOWN`, keep their conflicts explicit, and allow the sound fallback to use them only as non-protected hints.

### E044: Retained unsafe A candidate and failed broad repair

- Timestamp: 2026-09-19 02:38:07 +08
- Controlled change: repeat E043 with the same seed, workers, strict policy, and 120/60-second A budgets. The only code change preserves the latest complete candidate when a later solve ends `UNKNOWN`; staged selection still requires zero closure conflicts.
- Retained heuristic state: objective `32.2` with five strict conflicts after 120.010 wall / 528.163 deterministic seconds. The rows and explicit unsafe telemetry were preserved in the audit tree and supplied only as a repair hint.
- Repair result: the sound fallback ended `UNKNOWN` after 60.044 wall / 167.682 deterministic seconds with objective `25.2` and seven conflicts. No final output was emitted. Hint retention improved observability and changed the search state, but did not recover feasibility within the fixed budget.
- Conflict structure: the retained heuristic's five conflicts involve 12 activities: A003, A007, A008, A017, A020, A023, A036, A040, A042, A055, A057, and A074. A targeted bridge-safe repair can freeze all unaffected access decisions and free only this conflict neighborhood.
- Decision: retain last-candidate serialization because it is useful, correctly labelled evidence. Do not claim repair improvement. Test the 12-activity neighborhood before spending another full broad-search budget.

### E045: Conflict-neighborhood recovery and C reconstruction

- Timestamp: 2026-09-19 02:40:09 +08
- A repair: freeze every access, ECLO, and local-night decision outside the 12 activities in E044's five conflicts; solve those activities with bridge-safe strict separation. The model reached strict-feasible A=`32.2` with a matching restricted bound in 1.639 seconds, 12 solves, and 11 closure rounds. Main and independent scorers agree; exact-three-file pruned hash `bd3eaff12b51cc7522191af30d2c1e1c13e34f6efbbf712b634b3e809748365e`.
- C construction: recompute the repaired A schedule as a checked C=`32.2` fallback, then run the direct heuristic with only that generated fallback as a hint. It produced strict-feasible C=`26.1` in 11.370 wall / 44.345 deterministic seconds over 13 solves and 12 closure rounds.
- C gates: strict pruning retained 191 access rows and 925 occupancy rows. Both scorers report `16.1` delay, two ECLO nights, zero excess, and objective `26.1`; hash `f00c728ccf6abbd3610f6b7d0d276629b9c50a1b766f47f5488c2b4ebc0b261b`. Thirty seconds of bridge-safe verification preserved the exact same bytes and zero conflicts but did not prove a global bound.
- Evidence boundary: the A solver proof is restricted to a partially frozen neighborhood. C optimality continues to rely on the independent analytical public-instance argument, not the direct heuristic or incomplete sound verifier. The result reconstructs the incumbent without using the protected C schedule.
- Decision: add conflict-neighborhood repair as the first fallback after an unsafe heuristic. Keep broad hinted and unhinted sound construction only when local repair fails.

### E046: Integrated guarded C reconstruction after local-repair implementation

- Timestamp: 2026-09-19 02:44:17 +08
- Implementation: staged construction now derives local repair activities from the checker, freezes unaffected access/ECLO/night decisions, runs bridge-safe repair first, and falls through to broad fallback on failure. No activity identifiers are hard-coded. Thirty-seven regressions pass, including strict conflict-set derivation and fallback routing.
- Public run: same strict public input and seed 2, with 120 seconds for A heuristic, 30 for local repair, 60 for broad A fallback, five for A verification, 60 for C heuristic, and 15 for C verification. In this repeat A happened to solve directly at `32.2` in 111.547 seconds, so automatic repair was not exercised in this run; E045 remains the real repair-path evidence.
- C result: the generated A schedule was recomputed as a strict C=`32.2` fallback. Direct C search produced strict-feasible `26.1` in 21.775 seconds; bridge-safe verification preserved it for 15.018 seconds without proving a bound. Final hash `c2b4d2962e1578f833eb9930d00342e5a05a62adc018bf25b03d9310baadbccd`.
- Release gates: main and independent scorers report `16.1` delay, two ECLO nights, zero excess, and objective `26.1`; strict conflicts and hard violations are zero; the final directory contains exactly the three submission CSVs.
- Interpretation: the full current controller can reconstruct C=`26.1` without a C answer-key hint. Timed A behavior remains nondeterministic, and the integrated run does not replace or erase the controlled local-repair evidence.

### E047: First official validator run falsifies closure semantics

- Timestamp: 2026-09-19 02:47:43 +08
- Candidate: protected public A ZIP, locally dual-scored at `32.2`, strict-screen clean, exact three files. ZIP hash `51f984fb6d2711c99494d7976bd7b4bb3728f75b0d22f15810bf48fb920289bf`.
- Official result: **Infeasible**, five closure-zone violations; four of five A runs remain. The exact response is preserved in `OFFICIAL_VALIDATOR_LEDGER.md`.
- Counterexample 1: A035 and A058 overlap three work locations in week 18 under different local groups. The internal checker joined them transitively through week-level components and incorrectly exempted the pair. The validator reports both directional closure violations.
- Counterexample 2: Live interchange activities A074 and A075 block work two buffered sectors into the other line, including platforms. The internal cross-line closure covered only H01/H02 and omitted those remote buffer locations.
- Decision: protected A/B/C outputs lose any feasibility claim until revalidated. Do not upload B or C yet. Replace component-level closure exemption with exact location/group exemption, expand Live cross-line buffers, reproduce all five official violations locally, repair A, and use the second A run only after local gates pass.

### E048: Exact local reproduction of A-001 and correction of E047

- Timestamp: 2026-09-19 02:52:41 +08
- Falsification: compare direct-pair-only co-sharing with transitive possession components on every apparent conflict in uploaded A. For each pair, inspect the common locations, local group labels, closure intersections, and shortest same-location/group co-sharing path.
- Result: direct-pair-only semantics produce 15 conflicts, including ten pairs that are connected through valid co-sharing bridges. A035/A058 have no such path. Restoring transitive components, adding occupied work locations to each component's closure, and propagating Live interchange closure plus the configured buffer onto the other line yields exactly the five official directional violations: A035→A058, A058→A035, A001→A074, A011→A074, and A023→A075, at the exact reported locations.
- Correction: E047's claim that A035/A058 were transitively joined was factually wrong, and its proposed exact-location-only exemption is rejected. The defect was omission of the work footprint from `_blocked_locations`, plus incomplete cross-line Live buffer propagation.
- Test consequence: legacy tests and incumbent-feasibility assertions fail under the corrected model. These are meaningful regressions exposing invalid artifacts, not evidence against the correction. The official five must become a permanent regression oracle before repair.
- Decision: preserve component co-sharing, emit directional activity violations to match official granularity, update invalidated tests, and repair A under this checker. Do not consume A-002 until a fully checked candidate ZIP is ready.

### E049: A-002 becomes the first official-feasible incumbent and falsifies the score formula

- Timestamp: 2026-09-19 02:56:30 +08
- Repair: freeze every access/ECLO/night decision except A001, A011, A023, A035, A058, A074, and A075; allow all group assignments to reconfigure; solve with bridge-safe strict separation. The restricted model found and proved a zero-conflict candidate in 0.727 seconds without changing its then-reported local penalty.
- Local gates: 192 access rows, 928 occupancy rows, zero ECLO, zero excess, zero standard/strict closure conflicts, exact three files, byte-identical ZIP extraction, and two independent scorers agreeing under the then-current formula. ZIP hash `76bf26e19161337daf4f186d2a678aeb23bcb8613bc3bba42d00451d30325437`.
- Official result: **Feasible**, all constraints passed, score `137.9`, 28 overrun days across three contracts, no ECLO or excess; three A attempts remain.
- Falsified assumption: internal `32.2` scored each activity against its own completion. Official scoring uses the contract's final completion overrun for every activity in that contract, then applies each activity's nudge. C006 contributes `85.4`, C010 `45.5`, and C014 `7.0`, exactly `137.9`.
- Correction: both local scorers and both solver formulations now use contract-completion cost. They reproduce official `137.9` on the uploaded bytes. All older A/C score claims and lower-bound arguments are superseded until recomputed.
- Decision: protect A=`137.9` as the only official-feasible incumbent. Optimize the corrected contract objective, preserve this ZIP, and never replace the official portal state with an unvalidated candidate.

### E050: Corrected A optimum is `137.9`

- Timestamp: 2026-09-19 03:03:19 +08
- Relaxation: the corrected no-closure model proves `130.9`, consisting of unavoidable C006=`85.4` and C010=`45.5` delay. A 180-second full bridge-safe search and two direct-heuristic searches found no checked improvement over official A=`137.9`.
- Structural bound: A036 needs seven standard weekly accesses starting in week 22, so C006 cannot complete before week 28 and is at least 14 days late (`85.4`). A059 needs seven standard weekly accesses starting week 14, so C010 cannot complete before week 20 and is at least 7 days late (`45.5`). A075 must run by week 28 to keep C014 on time, but its Live-PM closure conflicts with A036, which necessarily occupies every week 22–28. Keeping A036 at its minimum delay forces A075 to week 29 (`7.0`); moving A036 later costs another `42.7`, so the cheaper unavoidable trade-off is `7.0`.
- Conclusion: `85.4 + 45.5 + 7.0 = 137.9`. The official A incumbent reaches this lower bound and is optimal under the confirmed model.

### E051: First official B and C runs are feasible and optimal

- Timestamp: 2026-09-19 03:03:19 +08
- B repair: free A023, A039, A074, and A075 while freezing other access decisions. Bridge-safe repair reached strict-feasible `30.0` in 0.960 seconds. Full verification proved `<30.0` infeasible. B-001 is officially feasible at `30.0`, with 0 overrun, 0 excess, and 6 ECLO; four runs remain.
- C correction and repair: the old C artifact recomputes from `26.1` to `98.2` under contract-completion scoring and has five corrected closure violations. Freeing A001, A011, A023, A056, A059, A074, and A075 produced strict-feasible `62.7` in 1.157 seconds. Full verification proved `<62.7` infeasible.
- C lower bound: A059 needs two ECLO nights to complete its seven units within weeks 14–19. A036 can use at most two ECLO nights in C's two-week line window and therefore needs six access weeks from week 22 through 27, forcing C006 seven days late (`42.7`). The four necessary ECLO nights cost `20.0`; excess location capacity cannot bypass one access per activity per week. Total lower bound is `62.7`, reached by the candidate.
- Official C-001: feasible at `62.7`, with 7 overrun days across one contract, 0 excess, and 4 ECLO; four runs remain.
- Current official public scores: A=`137.9`, B=`30.0`, C=`62.7`, combined penalty=`230.6`. All three portal results agree with the corrected local scorers.

### E052: Corrected hidden-like structural benchmark and strict-hedge falsification

- Timestamp: 2026-09-19 03:13:16 +08
- Input: `fixtures/structural_seed_20260919`, which reduces 67 of 76 location capacities to 1 and permutes contract/activity priorities. No public schedule hint was used.
- Scenario A: standard staged construction reached strict-screen-feasible `4599.7` from raw input in 23.573 seconds; a 15-second bridge-safe phase retained it with lower bound `4559.8`, a `39.9` absolute / `0.87%` gap.
- Scenario B strict hedge: the 90-second heuristic retained `30.0` with 14 strict conflicts. Thirty-second local repair and two 60-second sound fallbacks also remained unsafe; the workflow failed closed. The same input and seed without the unconfirmed buffer-to-buffer hedge reached checked `30.0` in 18.740 seconds and bridge-safe verification proved `<30.0` infeasible in 0.181 seconds.
- Scenario C standard workflow: reconstructed A=`4599.7` from raw input, then reached checked C=`59.9` in 1.834 seconds. Bridge-safe verification proved `<59.9` infeasible in 0.367 seconds.
- Conclusion: corrected scoring does not break raw-input construction, but the strict buffer-to-buffer hedge can destroy reliability on altered inputs and is contradicted by the organizer sample. Keep it as an audit signal, not the default hidden-instance policy. Validator-confirmed standard closure remains the selection gate.
- Integrity: no failed strict candidate was promoted; no public official incumbent changed; all negative telemetry is preserved.

### E053: Prefix-40 deterministic benchmark exposes B-controller instability

- Timestamp: 2026-09-19 03:22:12 +08
- Input: `fixtures/prefix_040`; one worker, seed 1, validator-confirmed standard closure, and no public answer-key hint.
- Scenario A: staged construction returned checked `85.4` with 159 access rows in 10.112 seconds. Bridge-safe verification matched the `85.4` bound in 0.037 seconds.
- Scenario C: the guarded A-to-C workflow returned checked `52.7`; bridge-safe verification matched the `52.7` bound in 0.074 seconds.
- Scenario B first staged run: a 90-second heuristic pruned to `67.0`; 15-second bridge-safe verification improved it to checked `34.0` with a `20.0` bound. A separate bridge-safe run using that checked hint reached and proved `20.0` in 4.476 seconds. The main and independent scorers agree, pruning removes nothing, and the final hash is `53c128c2cb13d02243be5fa7c1d6b0af65f39abc3882675e08adf7a457235346`.
- Falsification rerun: after increasing B's verification per-solve cap from one to five seconds, the same nominal one-worker seed-1 staged command produced a much worse heuristic (`256.0`, pruned to `186.0`) and did not improve it in 15 seconds. A 60-second bridge-safe continuation from that hint reached only checked `179.0`; a no-hint run found objective `20.0` but retained six closure conflicts and was rejected.
- Conclusion: fixed seed plus one worker is not enough to make wall-time-bounded iterative search output-reproducible. The `20.0` candidate is valid and proved optimal for this fixture, but the staged B controller is not robustly able to recover it. A longer round cap alone is not a sufficient fix; safe incumbent portfolios and/or deterministic-budget search require testing.
- Integrity: the `34.0`, `186.0`, and `179.0` candidates remain recorded; the unsafe no-hint `20.0` is not counted as a result; the official public B=`30.0` is unchanged.

### E054: B portfolio and cost-contributor repair recover the prefix-40 optimum

- Timestamp: 2026-09-19 03:28:37 +08
- Controller changes: heuristic portfolios now execute every requested seed and retain the lowest safe candidate instead of stopping at the first safe result. After protected verification, Scenario B can freeze unrelated access decisions and re-optimize only activities that use ECLO or participate in an over-capacity location-week. Every candidate still passes the same full checker and strict-improvement gate.
- Targeted falsification: the recorded checked `30.0` candidate had six ECLO nights, while the proven `20.0` optimum had four. Generic repair of all ECLO-cost activities (`A007` and `A036`, derived from the candidate) reached and proved `20.0` in 0.491 seconds. Repairing only A007 also reached `20.0`, but that narrower run is diagnostic evidence, not the implemented policy.
- End-to-end result: three 30-second one-worker heuristic attempts all ended unsafe; generic conflict-neighborhood repair recovered checked `37.0`; 30-second bridge-safe verification reached and proved `20.0`; the cost-contributor stage preserved the optimum. Independent rescoring reports zero delay, zero excess, four ECLO nights, and objective `20.0`; hash `899e6761db4dbe30584b81f06edf0001900729226eaced83148e70d06d51b766`.
- Tests: 42 regressions pass, including full heuristic-attempt selection, B cost-contributor derivation, and invocation of the guarded repair with only the derived contributor set left free.
- Remaining limitation: the verifier had previously stalled at `30.0` under nominally identical seed/worker settings, so this successful rerun does not establish wall-time reproducibility. The new stages improve recovery opportunities but do not eliminate time-sensitive CP-SAT variance.

### E055: Structural B remains unsolved under a one-worker portfolio

- Timestamp: 2026-09-19 03:35:29 +08
- Method: `fixtures/structural_seed_20260919`, standard closure, one worker, seeds 1–3, three 30-second heuristics, 30-second local repair, and two 60-second bridge-safe fallbacks. No public or prior structural submission hint was supplied.
- Failure: heuristic attempts retained objectives/conflicts of `200.0/24`, `315.0/14`, and `473.0/47`. Conflict-neighborhood repair reduced the best unsafe trajectory to `77.0/7` but did not reach feasibility. Broad fallbacks ended at `393.0/31` and `610.0/45`; no final output was emitted.
- Comparison boundary: E052 solved this fixture at checked and proven `30.0` under a different parallel-search configuration. This run changes both worker count and per-seed allocation, so it falsifies one-worker robustness but does not show a regression against the earlier production-like run.
- Decision: retain the failure, test the same revised controller with eight workers, and keep the one-worker regime as a stress test rather than a required release gate unless the hidden environment restricts parallelism.

### E056: Eight-worker structural B recovers and proves `30.0`

- Timestamp: 2026-09-19 03:37:05 +08
- Method: same structural fixture and total heuristic allocation as E055, changing only workers from one to eight.
- Result: seed 1 retained seven conflicts at `30.0` after 30 seconds; seeds 2 and 3 reached checked `30.0` in 16.648 and 21.169 seconds. The controller selected seed 2's checked/pruned candidate. Bridge-safe verification matched the `30.0` bound in 0.188 seconds, and cost-contributor repair over A036/A059 preserved the optimum in 0.060 seconds.
- Interpretation: the portfolio succeeds in the intended eight-worker regime and tolerates one failed seed, but E055 shows it is not compute-portable to one worker at the same wall-time budget. Worker count is therefore part of the benchmark contract, not a cosmetic setting.
- Integrity: no unsafe seed-1 candidate was selected; score and proof are internal structural-fixture evidence, not an official result.

### E057: Demand-mutated metamorphic fixture solves, but is not independent

- Timestamp: 2026-09-19 03:39:59 +08
- Input: `fixtures/structural_demand_seed_20260920`; it changes workloads, planned starts, up to ten predecessor links, capacities, priorities, and row order. The generator uses the official public A schedule to cap capacity reductions and choose predecessor relations that preserve that schedule's ordering.
- Results: eight-worker, three-seed staged construction and bridge-safe verification reach and prove A=`39.9`, B=`10.0`, and C=`10.0`. Both scorers agree. B/C use two ECLO nights, zero excess, and zero delay; A uses no ECLO/excess and has `39.9` weighted delay.
- Reproducibility: all three B seeds reached checked `10.0`; all three A seeds reached checked `39.9`; all three C seeds reached checked `10.0`. Final hashes are A `132e593a43c2fd05cbb53e25e51f11a554966baf1b727a7f4000b709da599122`, B `d2120848f51e21b76ab78a1bc55da4413f924b76281e4c8c4ea691ba631f176e`, and C `2acb69dc9ade6a4cea14b7b056d26b54e1092e45157944122ef43df96d8d8752`.
- Evidence boundary: this is a metamorphic robustness test, not an independent hidden-like sample. Oracle-guided capacity and predecessor construction can preserve public-schedule structure and therefore cannot rule out topology- or schedule-specific shortcuts.
- Next requirement: build a fully synthetic instance and feasible oracle from a new topology without reading any public submission, then discard the oracle during solver runs and compare reconstruction against independently computed scores/bounds.

### E058: Independent synthetic topology reconstruction and proof

- Timestamp: 2026-09-19 03:42:08 +08
- Generator: `scripts/make_independent_synthetic_fixture.py` creates two new lines (`LNX`, `LNY`), new stations/contracts/activities, an interchange bridge, mixed C/PC/PM access, legal C+PC co-sharing, a predecessor chain, and one tight three-unit activity. It does not read the official data or any public submission.
- Oracle independence: the A oracle is manually scheduled and its footprints and contract result rows are generated by separate local logic, not `nebula_ps1.topology`, the main evaluator, solver, or submission writer. The main checker and independent raw-CSV scorer then both accept it at A=`7.0`.
- Blind reconstruction: staged runs received only the synthetic input tables. They reached and bridge-safe proved A=`7.0`, B=`10.0`, and C=`7.0`. Both scorers agree; all outputs have zero hard violations and zero excess.
- Intended trade-off recovered: A and C schedule Q001 over three standard weeks and pay seven delay points. B's hard deadline forces Q001 into two ECLO weeks, costing `2 × 5 = 10` with zero delay. C correctly chooses the cheaper `7.0` delay rather than the `10.0` ECLO alternative.
- Evidence boundary: the synthetic case is small and authored to cover selected rule interactions. It reduces public-sample leakage risk but does not represent the full size, density, or every topology pattern of a hidden instance.

### E059: Deterministic interleaving reproduces bytes but is much slower

- Timestamp: 2026-09-19 03:49:06 +08
- Method: structural-fixture Scenario B, direct heuristic, eight workers, seed 1, OR-Tools experimental interleaved search, `max_deterministic_time=5` per cut solve, 120-second wall budget, and two identical repetitions. A 0.5 deterministic-time pilot returned no solution and is rejected as underbudgeted.
- Reproducibility result: both 5.0 runs used 31 solves, 29 closure rounds, 7,247,261 branches, 22,736 conflicts, and 230.613294 accumulated deterministic-time units. Both emitted byte-identical access and occupancy files with checked score `30.0`, six ECLO nights, zero excess, and hash `eb52d62e1e18fe9a4e5bb31509670cbe1a3594b9bba97c3d981c094008814c43`.
- Runtime cost: wall times were 98.765 and 104.905 seconds. The ordinary eight-worker portfolio reached the same proven objective in 16.648–21.169 seconds on successful seeds.
- Decision: retain deterministic interleaving as an opt-in audit/reproduction mode. Do not make it the score-maximizing default; its large runtime premium and experimental upstream status outweigh the benefit when a protected incumbent and full telemetry already prevent unsafe promotion.

### E060: Cross-regime benchmark matrix is executable, but the independent sample remains small

- Timestamp: 2026-09-19 03:53:00 +08
- Artifact: `scripts/build_benchmark_matrix.py` rebuilds `BENCHMARK_MATRIX.json` from 12 retained submissions spanning the public, prefix-40, public-derived demand-mutation, and independent-synthetic regimes. Generation aborts on any hard violation or disagreement between the main and independent scorers.
- Result: every retained row is standard-feasible, both scorers agree, and the score equals its recorded model or analytical bound. The three public rows remain the only reference-validator-confirmed rows. The independent synthetic A/B/C rows have zero strict conflicts; public-derived transformations contain one to four buffer-only strict conflicts while remaining clean under the validator-confirmed standard policy.
- Regression: a 44th test reloads all 12 submissions and recomputes feasibility and both scores. The full suite passes in the project Python 3.11 environment.
- Correction: public proof labels now state their actual evidence source. Official validation establishes feasibility and score, while analytical and/or model lower bounds establish optimality; the portal itself did not claim optimality.
- Limitation: this table contains selected retained incumbents, not a fair method comparison or fresh multi-seed distribution. Nine non-public rows come from only three datasets, and only one small dataset is independent of the public fixture. It can detect artifact drift but cannot yet establish hidden-scale reliability.
- Next requirement: scale the independent generator across topology, density, deadlines, and access-type regimes, then report success rate and score/bound distributions under fixed budgets without dropping failed seeds.

### E061: Independent modular scaling is stable through 180 activities, but does not test density

- Timestamp: 2026-09-19 03:58:44 +08
- Generator: `scripts/make_scaled_independent_fixture.py` creates one two-line topology with repeated, spatially separated interchange modules. It does not read the public instance or submission. The 20-module fixture has 160 contracts, 180 activities, 320 oracle access rows, and 1,120 oracle occupancy rows. Separate oracle logic passes both scorers at A=`140.0` with zero hard violations.
- Fair-run policy: `scripts/run_staged_seed_matrix.py` records every requested run before execution, catches and retains failures, dual-scores successes, and never filters the distribution. Five seeds per A/B/C used one worker, one two-second heuristic attempt, one-second local repair, one three-second fallback, and two-second verification.
- Result: 15/15 runs succeeded. Every A reached the proved `140.0`, every B the proved `200.0`, and every C the proved `140.0`; every strict-conflict count is zero. A wall times were 2.067–2.101 seconds, B 1.588–1.595, and C 5.347–5.588. C selected bridge-safe improvement in every seed; A/B retained the checked heuristic incumbent.
- Growth checks: the same policy also achieved 15/15 on one-module, four-module, and eight-module versions. The retained benchmark matrix now includes representative 20-module A/B/C proofs, increasing it to 15 cases. Forty-five regressions pass.
- Limitation: modules are deliberately separated by buffer gaps and share no contracts, so the objective and feasibility decompose. This tests schema/topology generality and raw model size, not bottleneck density, global ECLO-window coupling, or difficult closure-cut convergence. Linear score scaling is expected and is not an algorithmic improvement claim.
- Decision: no decomposition rewrite is justified by this scale result. The next falsification must hold topology size roughly fixed while increasing shared-corridor demand, overlapping closures, predecessor depth, and access-type mixing.

### E062: Dense shared-bottleneck failure and generic constructive-hint recovery

- Timestamp: 2026-09-19 04:08:43 +08
- Fixture: `fixtures/independent_dense_v1` is public-independent and has 84 activities on two compact lines. On each main corridor, ten PC activities and thirty C activities each need two accesses. Nominal capacity therefore requires exactly 20 legal one-PC-plus-three-C possessions per line. Two cross-line Live PM activities and two successor PM activities occupy the remaining safe weeks. The separately generated A oracle has 164 access rows, 492 occupancy rows, zero hard violations, and score `0.0` under both scorers.
- Baseline falsification: the same fixed one-worker policy used for modular scaling failed 15/15 A/B/C seeds. A produced unsafe candidates with 9–18 closure conflicts; B initially built roughly 252,000-variable models and no incumbent; C produced no incumbent or unsafe candidates. No failed output was promoted.
- Rejected partial fixes: limiting only B's direct heuristic to nominal supply plus one cut its candidate model to about 25,700 variables but still found no incumbent after 10 seconds. Exact start-order symmetry for interchangeable singleton activities also failed. A first packing hint that omitted PM chains improved candidate objectives but still left 16–28 closure conflicts. These failures remain in seed summaries and telemetry.
- Implemented recovery: the direct heuristic now gives CP-SAT non-binding structural hints. It packs interchangeable same-footprint PC+C occurrence rounds into legal batches, assigns them within nominal supply, then schedules remaining singleton predecessor chains backward from planned completion while rejecting any hinted placement that creates a standard closure conflict. No activity, station, contract, week, score, or oracle row is hard-coded. The sound checker and bridge-safe verifier remain the promotion gates.
- Result: the identical fixed policy then succeeded 15/15 seeds. Every A/B/C result is byte-identical within its scenario, dual-scored at the proven lower bound `0.0`, and clean under both standard and strict closure screens. A wall times were 1.334–1.352 seconds, B 2.715–2.776, and C 2.430–2.465.
- Cross-regime check: on prefix-40 C at the same five-second direct budget, disabling structural hints returned unsafe `18568.4` with 16 conflicts; the hinted staged attempt returned a lower unsafe candidate before repair. The full prefix workflow still needs its established larger budget, so this is directional evidence, not a fair end-to-end score claim.
- Portfolio protection: only the first direct-heuristic attempt receives structural hints. Later attempts retain the prior unhinted search, so production multi-start does not confuse one heuristic recipe with a proof or sole construction path.
- Limitation: the dense generator and constructive heuristic were developed in the same cycle. Despite identifier-free logic and a prefix ablation, generator-specific structural overfitting remains possible. Test non-identical footprints, mixed deadlines, multi-activity contracts, and deeper predecessor DAGs before generalizing.

### E063: Frozen-hint dense holdout exposes two gaps, then production path reaches 15/15

- Timestamp: 2026-09-19 04:17:28 +08
- Holdout construction: after freezing the E062 hint code, `scripts/make_dense_holdout_fixture.py` generated a new two-line fixture with 106 activities, 202 accesses, 610 occupancy rows, two bottleneck corridors per line, staggered deadlines, two three-activity contracts, three-step predecessor chains, and cross-line Live work. Its separately authored oracle is dual-scored and hard-feasible at A=`0.0`.
- First blind result, preserved before tuning: 5/15 fixed-budget runs succeeded. All five A seeds were feasible but scored `24570.0` against the known zero lower bound. Every B and direct-C seed failed closed. The A verifier bound was `0.0`, proving the large quality gap. This falsified transfer from dense-v1.
- Root cause 1: constructive chain placement excluded every multi-activity contract. Generalizing the same backward scheduler to all contracts, while explicitly enforcing per-contract workfront counts, changed the next seed-1 pilot to A=`0.0`, B=`0.0`, and direct C failure.
- Root cause 2: the seed harness had routed C through generic staged construction, not the intended guarded C controller. Direct C is still a valid failure result, but it is not the deployment path. `--production-c` now uses `solve_staged_c_portfolio`, which first constructs and protects A as a C fallback.
- Final production-path distribution: five seeds per scenario, one worker, one two-second heuristic attempt, one-second local repair, one three-second fallback, and two-second verification. All 15 runs reached and proved `0.0`, all strict-conflict counts are zero, and each scenario has one stable output hash. A took 1.416–1.436 seconds; B 1.933–1.977; C 1.929–1.946 and selected the protected A-derived fallback in every seed.
- Integrity boundary: the original 5/15 result is not overwritten. The multi-contract correction was made only after it was recorded. The C benchmark correction changes the measured controller, so direct-C and production-C results are reported separately. Neither run used the oracle as a hint.
- Remaining limitation: both dense generators share a deliberate legal-batch motif and are authored locally. The holdout is materially different but not an external hidden distribution. Future perturbations should be generated before further hint tuning and include nonzero optimal trade-offs.

### E064: Pre-generated dense nonzero trade-off transfers without tuning

- Timestamp: 2026-09-19 04:20:51 +08
- Construction: before the blind run, `scripts/make_tradeoff_holdout_fixture.py` extended the 106-activity dense holdout with one isolated C activity requiring three standard units from week 1 against a week-2 planned target. The A oracle schedules weeks 1–3 and is dual-scored at `7.0` with zero hard violations.
- Analytical bounds: A forbids ECLO, so one access per week forces completion in week 3 and seven days of tier-3 delay, score `7.0`. B must finish in two weeks; two ECLO rows contribute three units and cost `2 × 5 = 10.0`. C can choose either and therefore has lower bound `min(7.0, 10.0) = 7.0`. Excess groups cannot bypass one access row per activity per week.
- Blind production-path policy: five seeds per scenario, one worker, one two-second structural-hint attempt, one-second local repair, one three-second fallback, two-second verification, and guarded A-as-C for C. No code or budget changed after fixture generation.
- Result: 15/15 successes at the exact analytical optima. A=`7.0` in 1.483–1.526 seconds; B=`10.0` in 2.912–2.940; C=`7.0` in 2.098–2.127. Each scenario has one stable hash, zero standard/strict conflicts, and a matching solver bound.
- Falsification value: the structural hint's standard-only packer cannot fit the tight activity into B's two eligible weeks, yet CP-SAT still discovers the two ECLO solution. The hint therefore did not hard-code or constrain away the intended B trade-off. C consistently preserves the cheaper A-derived delay rather than paying ECLO.
- Limitation: the nonzero activity is spatially isolated from the dense bottlenecks. This validates score/ECLO choice under a dense background, not a coupled trade-off where the tight job competes for the same possession groups.

### E065: Coupled ECLO-window case falsifies the first hint, then reaches all bounds

- Timestamp: 2026-09-19 04:29:29 +08
- Construction: `scripts/make_coupled_tradeoff_fixture.py` generated `fixtures/independent_coupled_tradeoff_v1` before the blind run. Two tier-1 C activities each require three units on contested corridors, target weeks 2 and 6, and share one line. Six background C jobs were removed to keep each delayed schedule feasible without making both ECLO choices simultaneously available in Scenario C. The oracle is hard-feasible at A=`1820.0`.
- Analytical bounds: A must delay both jobs by seven days, `2 × 910 = 1820`. B uses two ECLO rows per job, `4 × 5 = 20`. Scenario C's line-wide two-week ECLO window permits only one pair; the other job delays, `10 + 910 = 920`. The per-activity weekly access limit prevents excess possessions from bypassing either bound.
- Preserved blind result: with the frozen identifier-ordered hint and one-second local repair, all five A seeds and all five C seeds were feasible but scored `16380.0`; all five B seeds failed closed. This disproved coupled transfer from E064.
- Generic correction: structural construction now creates PC slots first and inserts C activities by earliest deadline, transactionally checking workfronts and closures. Activities whose eligible weeks cannot hold their standard rows remain unhinted so exact search can choose ECLO. No oracle schedule, fixture identifier, or expected score is consulted.
- Budget sensitivity: after correction, the one-seed pilot reached A=`1820.0`, B=`48.0`, C=`920.0`. B's lower bound was already `20.0`, but one second of local repair left four excess groups. At ten seconds, five seeds per scenario reached A=`1820.0`, B=`20.0`, C=`920.0`; all 15 results are dual-scored, strict-clean, and match solver bounds.
- Runtime and stability: A took 1.471–1.480 seconds and C 4.150–4.185. B took 6.068–20.025 and selected local repair in four seeds and cost repair in one. All B scores are optimal, but all five hashes differ; score stability must not be reported as byte determinism.
- Integrity boundary: the blind failure and one-second B=`48.0` pilot remain preserved. The ten-second repair budget is reported as part of the method and is below the 30-second production default. The fixture is locally authored from the same dense family, so the result establishes a specific coupled capability, not hidden-distribution generalization.

### E066: Corrected hint preserves prior regimes and reconstructs every public optimum

- Timestamp: 2026-09-19 04:34:09 +08
- Prior-regime regression: rerunning five one-worker seeds per scenario under the original two-second policy preserved 15/15 dense-holdout results at `0.0` and 15/15 additive-trade-off results at A=`7.0`, B=`10.0`, C=`7.0`. Scores, feasibility, strict screens, and within-scenario hashes remained stable.
- Public reconstruction policy: one eight-worker seed, 30-second heuristic, 10-second local repair, 30-second fallback, 10-second verification, one attempt per stage, and guarded production C.
- Result: current code produced locally hard-feasible A=`137.9` in 28.295 seconds, B=`30.0` in 11.160, and C=`62.7` in 29.569. Both local scorers agree. These schedules have new hashes and are not official-validator-confirmed, so the protected official artifacts were not replaced.
- Strict audit: the reconstructed A/B/C schedules have 7/6/4 strict buffer-overlap conflicts while passing the confirmed standard rule. Strict mode remains diagnostic; treating it as a hard requirement would reject score-optimal public schedules without organizer evidence.
- Limitation: one public seed is not a runtime distribution. A and C finished near the heuristic budget, and eight-worker success does not establish one-worker or hidden-hardware reliability.

### E067: Public optimum reconstruction is score-stable but schedule-nondeterministic

- Timestamp: 2026-09-19 04:39:54 +08
- Protocol: E066's fixed eight-worker policy, extended without filtering to seeds 2–5 for A/B/C. The first seed and these 12 additional runs form a five-seed distribution per scenario.
- Result: 15/15 locally feasible reconstructions matched the public optima A=`137.9`, B=`30.0`, C=`62.7`. Across all seeds, A took 20.097–33.840 seconds, B 11.160–23.961, and production C 28.974–39.665.
- Nondeterminism: every run has a different submission hash. Strict diagnostic conflicts range from 3 to 8 even though every schedule passes the confirmed standard rule. Stable objective values therefore do not imply byte identity or stable operational structure.
- Integrity boundary: every requested seed is recorded; no output was portal-submitted or promoted over the protected official artifacts. This is a reconstruction and runtime experiment on the known public dataset, not new score progress or hidden-generalization evidence.

### E068: One-worker public construction fails, and three attempts do not repair it

- Timestamp: 2026-09-19 04:48:51 +08
- Controlled portability test: E066's 30-second heuristic, 10-second local repair, 30-second fallback, and 10-second verification budgets were retained while worker count changed from eight to one.
- Result: A failed closed in 70.979 seconds; B returned checked `149.0` in 51.139 seconds against a verified `30.0` lower bound; guarded C failed because its A stage failed. The one-worker success rate was 1/3 versus 15/15 optimum reconstruction with eight workers.
- Portfolio falsification: raising heuristic attempts from one to three preserved the per-attempt budget but increased total work. A still failed after 131.166 seconds, with 27, 12, and 14 conflicts across attempts. B remained `149.0` after 111.325 seconds. Seed diversification did not fix the structural gap.
- Diagnostic: the first A hint returned objective `30283.4` with 24 conflicts; sound fallback retained 15 conflicts. The current identical-footprint packer does not screen one packed footprint against previously packed different footprints, a risk absent from the deliberately regular dense fixtures.
- Integrity boundary: unsafe candidates remain audit-only, B=`149.0` did not replace any incumbent, and the eight-worker result is no longer described without its hardware condition.

### E069: Transactional cross-footprint screening is rejected

- Timestamp: 2026-09-19 04:51:49 +08
- Hypothesis: independently packed footprint classes were causing the one-worker public closure conflicts, so each packed activity was screened against prior classes and prevented from reusing their local group slots.
- Controlled result: 49 regressions passed, but the same one-worker public A policy still failed with 27 heuristic and 22 fallback conflicts, worse than E068's 24 and 15. B remained checked at `149.0` in 51.154 seconds.
- Decision: revert the code. A locally cleaner partial hint can still steer a timed exact search into a worse trajectory, and the screen did not create a complete global construction. Preserve the negative ledger and test hint-on versus hint-off before another design change.

### E070: Hint coverage explains the public A failure, but a universal gate breaks B

- Timestamp: 2026-09-19 04:57:30 +08
- Coverage diagnostic: structural telemetry now records proposed activity/access coverage and whether the hint is complete. Independent dense, held-out, additive, and coupled A fixtures all covered 100% and solved at their bounds. Public A covered 35/54 activities and 108/192 accesses.
- Matched ablation: with one worker and 30 seconds, public A hint-on returned `11155.9` with 27 closure conflicts; hint-off returned `2713.2` with 7. The partial warm start was harmful.
- Rejected universal rule: clearing every incomplete hint improved staged A to six heuristic conflicts and two after 10-second local repair, but A still failed; B changed from feasible `149.0` to failure with 34 heuristic and 14 fallback conflicts. B needs the partial packing hint for deadline feasibility.
- Longer repair falsification: increasing A local repair from 10 to 30 seconds did not finish the two-conflict repair; timed iterative search instead ended with six conflicts. More wall time is not monotonic without a protected safe incumbent.

### E071: Scenario-aware hint gate preserves scores and improves public runtime tails

- Timestamp: 2026-09-19 05:05:22 +08
- Policy: clear incomplete structural hints for Scenario A only; retain them for B/C and retain complete hints for every scenario. This is schema-derived and records attempted coverage even when the hint is cleared.
- Regression: 51 tests pass. The independent dense, holdout, additive, and coupled cases keep complete hints and their proved results. One eight-worker public seed reconstructed A=`137.9`, B=`30.0`, C=`62.7` before the full comparison.
- Unfiltered five-seed result: 15/15 public A/B/C runs matched their optima. A min/median/max wall time changed from 20.097/23.083/33.840 to 15.425/23.639/25.742 seconds; B from 11.160/14.035/23.961 to 9.902/13.977/23.039; C from 28.974/29.569/39.665 to 17.360/23.505/37.354.
- Boundary: A's median improvement is negligible and one-worker A still fails. The gain is eight-worker tail reduction on known public data, not hidden-score progress or compute portability. Strict diagnostics remain non-objective and variable.

### E072: Three targeted one-worker A repairs fail and are rejected

- Timestamp: 2026-09-19 05:11:34 +08
- Residual structure: the best 10-second local repair retained two week-19 conflicts, A074–A002 and A074–A065 at `PLAT:BET:S13:WB`. Expanding the original seven free activities to their ten-activity predecessor/successor closure did not change either conflict.
- Seeded-cut experiment: adding the unsafe hint's already known bridge-safe cuts before the first solve reduced a 51-round repair from 8.108 to 6.335 seconds but retained both conflicts. With the production 500-round cap it timed out after 73 cut rounds, still with two conflicts. A full staged run failed. The code was reverted because lower overhead without a checked incumbent is not improvement.
- Escape-week experiments: freeing A075, the sole distinct-group blocker in a simple week-30 probe, produced ten final conflicts. Freeing the three week-28 blockers produced four. Static pairwise blocker counts did not capture transitive grouping and closure interactions.
- Diagnostic correction retained: `STAGED_FAILURES.json` now includes the exact local-repair free set and telemetry. This changes observability only.
- Decision: stop tuning public one-worker A. The public submission is already officially optimal, and further seed-specific neighborhood changes create an overfitting risk. Resume on an independently generated irregular partial-hint fixture or compare a fundamentally different sound formulation.

### E073: Irregular partial-hint fixture catches a workfront error and short-budget failure

- Timestamp: 2026-09-19 05:27:39 +08
- Fixture: `scripts/make_irregular_partial_hint_fixture.py` transforms the independent dense holdout without public rows. Five same-footprint C activities become one priority-3 contract with one workfront and one access night per week; three need three workload units and two need two. The corrected dataset hash is `1b3e96d407ebea08d44af862da6f20d5695c2ec14e605ef555874dfa2306066d`.
- Integrity correction: the first generated version misunderstood workfront granularity and was regenerated in place, making its retained outputs incompatible with the current input hash. Those runs are quarantined and support no claim.
- Corrected evidence: the separately constructed A oracle is dual-scored and hard-feasible at `105.0`; it is not claimed optimal. The fixed 30/10/30/10 eight-worker policy failed A, proved B=`30.0`, and failed guarded C because its A foundation failed. A standalone direct C run returned checked `52.0`, while a repeated guarded direct attempt failed, exposing eight-worker nondeterminism.
- Decision: retain B=`30.0`, reject reliability claims from the single C=`52.0` run, and add a fail-closed direct-C path after the exact A-construction failure.

### E074: The irregular C bound is corrected from 52 to 31

- Timestamp: 2026-09-19 05:41:32 +08
- Result: a 120-second direct C run produced a dual-scored, standard-clean, strict-clean `31.0` schedule with two ECLO rows, three excess local groups, zero delay, and hash `269ca2c39ce12bd2c7693055b6e14b6810543149a3e9599f7a59f4e248aae940`.
- Corrected bound: one workfront and one access night per week require at least 12 rows by week 12; 13 workload units therefore require at least two ECLO rows, cost `10`. The affected corridor has 38 C rows before the deadline but 12 nominal groups can hold at most 36, forcing at least one excess group at each of its three locations, cost `21`. The lower bound is `31`, not `52`.
- Failed alternatives: fixed six-second rounds left three conflicts. A 120-second protected bridge-safe solve and a 120-second footprint-wide neighborhood found no improvement and no model proof. The analytical counting proof plus the matching checked construction establishes the result under implemented rules.
- Solver correction: repeated `UNKNOWN` responses no longer stop merely because the active per-round cap reached 30 seconds; the caller's remaining authorized budget is consumed. Fifty-two regressions passed after the change.

### E075: Independent C construction and exact cost repair close both controller traps

- Timestamp: 2026-09-19 05:53:43 +08
- First trap: extending the generic B cost-contributor neighborhood to C reduced a checked `38.0` incumbent to `31.0` in 0.645 seconds, with matching model bound and full checks.
- Second trap: a longer A stage produced a feasible A=`13160.0`; the old controller seeded C exclusively from that schedule and returned C=`13160.0`. Any feasible A was incorrectly allowed to suppress C-specific construction.
- Correction: Scenario C retains A as a protected fallback but runs its first C challenger without the A sample hint. Both generic and A-success C paths apply bridge-safe repair to activities participating in ECLO or excess groups. Promotion remains strictly lower and fully checked.
- End-to-end evidence: a fresh guarded run generated C=`52.0`, repaired it to the proved `31.0` in 0.296 seconds, and emitted hash `12f8415537193b2f45fb8a4dac0c8c95caece0fb6116181d1195db476a6d29bb`. Both scorers agree; standard and strict conflicts are zero; the repair reports `OPTIMAL` with bound `31.0`.
- Regression: 53 tests pass. `BENCHMARK_MATRIX.json` now contains 29 dual-scored, bound-matching cases, including irregular B=`30.0` and C=`31.0`. Its first regression run exposed and corrected a test router that sent the new cases to an older fixture.
- Limitation: direct C construction remains nondeterministic and must first return a safe cost-bearing incumbent. One optimal end-to-end run is not a distributional reliability result.

### E076: Corrected C controller preserves dense fallback and coupled optimum

- Timestamp: 2026-09-19 05:56:30 +08
- Dense holdout: under the established one-worker 2/1/3/2-second policy, production C retained the protected A-derived score `0.0`, remained standard/strict clean, and completed in 3.941 seconds. The independent C challenger did not displace an equal fallback; the cost neighborhood was empty.
- Coupled trade-off: under the one-worker 2/10/3/2-second policy, production C retained the proved `920.0` optimum with zero standard/strict conflicts in 6.254 seconds. The C cost repair examined `WCOUPLED1`, returned the same score and bound, and did not replace the equal incumbent.
- Decision: the independent challenger and generalized cost repair pass both tested cross-regime safety checks. Continue distributional testing; do not infer reliability from one seed per regime.

### E077: Seed 3 falsifies narrow C repair; footprint expansion recovers the optimum

- Timestamp: 2026-09-19 06:11:00 +08
- Reproducibility: irregular seed 2 reached checked C=`31.0` with a distinct hash; direct construction and the narrow exact repair both returned the optimum.
- Falsification: irregular seed 3 returned checked C=`52.0` with two ECLO rows and six excess local groups. The narrow repair over direct ECLO/excess participants returned `52.0` with a matching bound only inside the frozen neighborhood.
- Structural correction: for C only, the repair neighborhood now expands to every incumbent activity touching a location occupied by a direct cost contributor. A manual 30-second test reduced the seed-3 incumbent from `52.0` to `31.0`.
- End-to-end result: the corrected seed-3 controller started from C=`63.0`, verification reached `56.0`, and the expanded ten-second repair reached dual-scored, standard-clean, strict-clean C=`31.0` with hash `aec37022042df9d45d728b5daeeee9d701f75c28fcde64554f939276db3f0b05`.
- Post-change safety checks: dense-holdout C remained `0.0`; coupled C remained `920.0` with a matching cost-repair bound. B keeps the smaller direct-contributor neighborhood. Fifty-four regressions pass.
- Limitation: the correction was designed after the seed-3 failure. A fresh held-out footprint-coupled fixture or further unfiltered seeds are required before claiming broad reliability.

### E078: One-worker irregular C fails before improvement can begin

- Timestamp: 2026-09-19 06:15:11 +08
- Policy: the corrected guarded controller, seed 1, one worker, A budgets 30/10/30/10 seconds and C heuristic/verification budgets 120/10 seconds.
- Result: A failed closed. Direct C consumed 120.002 seconds and returned an unsafe `136584.0` candidate with 56 closure conflicts. The ten-second local repair worsened the residual to 57 conflicts; the 30-second bridge-safe fallback retained 27. No final submission was emitted.
- Interpretation: the footprint-expanded cost repair is irrelevant until a checked incumbent exists. Eight-worker success does not establish one-worker construction portability, and a longer direct budget alone is insufficient on this case.
- Decision: retain one worker as a falsification mode, not the production default. Do not add a fixture-specific ECLO construction rule; first test intermediate worker counts or a generic feasibility decomposition.

### E079: Four workers construct the irregular C optimum, but do not establish a threshold

- Timestamp: 2026-09-19 06:19:58 +08
- Matched test: E078's fixture, seed, budgets, attempts, and controller were retained; only worker count changed from one to four.
- Result: A again failed closed, but direct C reached checked `31.0` in 120.007 seconds after 35 solves and 29 closure rounds. Verification and footprint-expanded repair each retained `31.0`; neither supplied a global solver proof. The final hash is `d45951d25022b6485eebb58a5c2c3d57272fb4fa8d67e0fd2a1f1bb6cd9f74a4`.
- Independent checks: both local scorers report two ECLO rows, three excess groups, zero delay, and objective `31.0`; standard and strict closure screens are clean. The analytical bound from E074 supplies the optimality proof under implemented rules.
- Interpretation: four workers are sufficient on this one seed where one worker failed. This is an empirical compute-sensitivity result, not a universal minimum-worker claim. Test two workers next under the identical policy.

### E080: Two workers reach feasibility but expose a delay-repair gap

- Timestamp: 2026-09-19 06:27:03 +08
- Matched result: the E078/E079 policy with two workers returned a dual-scored, standard-clean, strict-clean C=`63420.0` schedule. Its loss is `63210` priority-weighted delay, 30 excess groups (`210`), and no ECLO. Hash: `77415bedf879cacb7509b2f0d77124bb1475adbd81e99741bf638bf406fa7d5f`.
- Extended repair: increasing the footprint-expanded repair budget from 10 to 120 seconds reduced the same checked incumbent to C=`1914.0`: `1820` delay, two ECLO rows, and 12 excess groups. Both scorers agree, both closure policies are clean, and the hash is `35c4b5bead72eb0ff0fc4836975a144e275e8cde6ecb15740f41fe63fa4502de`.
- Falsification: more repair time helps substantially but does not recover the C=`31.0` optimum. The run ended feasible with a conditional model bound of `1824.6`, not a global proof. Ten-second cost repair is not adequate when the first safe incumbent is dominated by delay.
- Decision: do not tune production around two-worker behavior or promote either result. Production uses eight workers; test fresh eight-worker seeds to measure the corrected controller's relevant reliability.

### E081: Fresh seeds separate the compressed test budget from production repair

- Timestamp: 2026-09-19 06:40:30 +08
- Seed 4, compressed policy: direct C returned `77.0`, verification `63.0`, and the ten-second footprint repair reached the bounded optimum `31.0`. Both scorers agree and the standard closure screen is clean; the strict unpublished hedge reports one conflict. Hash: `fb73e49ad8ee476b017f69424edf4d93ef47cbb509259e65762c3316ab57397a`.
- Seed 5 falsification: the same compressed policy stopped at checked, strict-clean C=`63.0`, consisting of `35` delay and four excess groups (`28`). The ten-second repair returned the incumbent unchanged despite a lower conditional bound.
- Budget test: the identical seed-5 neighborhood reached C=`31.0` in 30.044 seconds. A full controller replay with the existing 30-second production default independently reached C=`31.0`, hash `7c4f563e23a270edb643983c2326b124cee3de77bcd65de02a258f222013b1da`; both scorers agree and both closure screens are clean.
- Conclusion: the footprint expansion transfers to the two fresh seeds, but the compressed ten-second repair is not a reliable production policy. No algorithm or default changed: the CLI already defaults to 30 seconds for this repair. Across irregular seeds 1–5, the corrected controller reaches `31.0` when the production repair budget is used; only seeds 1–3 informed the implementation.

### E082: Cross-module workfront holdout is frozen before solver exposure

- Timestamp: 2026-09-19 06:46:50 +08
- Fixture: `independent_multimodule_tradeoff_v1` transforms the public-independent eight-module topology. One priority-3 C contract couples five three-unit activities across five modules and both lines with one workfront and one access per week. Dataset hash: `3220b2c715aaf57df46d10570ed0de9b6b79a1900e26d6df9c342e760ab9a293`.
- Independent oracle: 72 activities, 134 access rows, four ECLO rows, no excess, no KMM delay, and total C=`76.0`. Both scorers agree and standard/strict closure screens are clean.
- Bound: the eight untouched module bottlenecks contribute `56`. KMM has 15 workload units; zero delay by week 13 requires at most 13 rows, hence at least four ECLO half-unit gains costing `20`. With two or fewer ECLO rows it needs at least 14 rows and pays at least `35` delay plus ECLO cost. The oracle attains `56 + 20 = 76`.
- Protocol: commit the generator, input, oracle, hash, and 55th regression before the first solver run. The purpose is to test contract/workfront coupling across spatially disjoint footprints without adapting the algorithm to the observed outcome.

### E083: Blind cross-module construction reaches and proves 76

- Timestamp: 2026-09-19 06:48:33 +08
- Blind result: the unchanged eight-worker controller generated C=`76.0` in 1.730 seconds; the sound verification model returned the same score and bound in 0.250 seconds. The final hash is `ac27d3e191fc88a5d398e2c3dd0fa0eb187a05a967cb13ceb3781488409e1fd5`.
- Independent checks: both scorers agree; the output has 56 delay points, four ECLO rows, no excess, and zero KMM delay. Standard and strict closure screens are clean.
- Limitation: direct construction solved the fixture before repair, so the blind run did not test the intended spatial-neighborhood omission. A controlled valid suboptimal incumbent is required for that mechanism test.

### E084: Contract peers close a proven spatial-repair blind spot

- Timestamp: 2026-09-19 06:50:56 +08
- Falsification: a checked, strict-clean C=`101.0` incumbent used two ECLO rows and ended KMM in week 14. The existing footprint repair freed only `R0103` and spatial competitor `R0101`, then proved `101.0` optimal under those frozen decisions despite the known C=`76.0` schedule.
- Correction: for Scenario C only, add every activity sharing a contract with a direct ECLO/excess contributor before expanding through affected footprint locations. Scenario B retains its direct-contributor neighborhood.
- Result: the corrected eight-activity neighborhood reduced `101.0` to dual-scored, standard-clean, strict-clean C=`76.0` and proved the bound in 0.114 seconds. The repaired hash is `958a1b2fc5a3552ea0a76ddbc6e8085d4c260e32460769450d034844e6671325`.
- Cross-regime checks: public C retained and proved `62.7` in 0.332 seconds; irregular seed 5 recovered `31.0` in 30.008 seconds; coupled C retained and proved `920.0` in 0.070 seconds. The public repair set grew to 43 activities, so component growth remains a runtime risk.
- Regression: the first 30-case matrix run failed because its expected count remained 29; the second misrouted the new case to the older synthetic fixture. Both harness assumptions were corrected before the 56-test pass.

### E085: Delay-only incumbents require delay contributors in the repair seed

- Timestamp: 2026-09-19 06:55:21 +08
- Falsification: the checked cross-module A-derived C fallback scores `126.0` entirely from delay, with zero ECLO and zero excess. The previous selector returned an empty repair neighborhood although the proved C=`76.0` schedule exists.
- Correction: Scenario C now seeds repair with every activity in an overdue contract as well as direct ECLO/excess participants, then applies contract and footprint expansion. Scenario B remains unchanged because overrun is infeasible there.
- Result: the resulting 18-activity neighborhood reduced `126.0` to proved C=`76.0` in 0.451 seconds. Both scorers and both closure policies accept hash `6e78596d5ac3b795887a5e6d162ec0fa864553dc636c8113612eae5695416302`.
- Cross-regime checks: public C retained and proved `62.7` in 0.321 seconds; irregular seed 5 again recovered `31.0` in 30.007 seconds; coupled C retained and proved `920.0` in 0.070 seconds. Fifty-seven regressions pass.

### E086: Cross-contract predecessor holdout is frozen before repair

- Timestamp: 2026-09-19 06:57:15 +08
- Fixture: `independent_predecessor_tradeoff_v1` contains an on-time predecessor and a priority successor in separate contracts and disjoint footprints. Dataset hash: `145752d013356aaf41be761d89c621a9fad136304b2a6284e3e5328b3e68b022`.
- Oracle and incumbent: the checked optimum schedules `PRED`/`SUCC` in weeks 1/2 for C=`0.0`; the checked delayed incumbent schedules weeks 3/4 for C=`7.0`, with no ECLO or excess. Both scorers agree.
- Protocol: commit the generator, input, oracle, delayed incumbent, and regression before invoking repair. The test asks whether delay seeding can move a delayed successor when its on-time cross-contract predecessor remains frozen.

### E087: Precedence closure removes another conditional-optimum trap

- Timestamp: 2026-09-19 06:58:42 +08
- Falsification: delay-aware contract/footprint repair freed only `SUCC` and proved C=`7.0` with `PRED` frozen in week 3, although the committed weeks-1/2 oracle scores `0.0`.
- Correction: Scenario C now includes the transitive undirected predecessor/successor component of objective and contract contributors before footprint expansion. Scenario B remains unchanged.
- Result: the corrected two-activity neighborhood proved C=`0.0` in 0.006 seconds. Both scorers and both closure policies accept hash `578a90f3f1424d7098acc1fa670f537cb2ec97d6496edf6115fd879ffbc3f48c`.
- Scope check: precedence closure added no activities to the existing public (43), irregular (27), coupled (23), or multimodule delay (18) neighborhoods. Fifty-nine regressions pass.

### E088: Conditional proof scope is explicit; blind fixed-point expansion is withheld

- Timestamp: 2026-09-19 07:03:28 +08
- Adversarial check: a fixed-point contract/precedence/footprint closure would widen public `43→54`, irregular `27→53`, coupled `23→49`, and leave cross-module delay at `18`. Three of four cases converge only after dependencies introduced by later expansion stages are revisited.
- Decision: do not replace the bounded production neighborhood with unconditional fixed-point closure without a targeted failure and matched runtime evidence. The protected incumbent and full checker remain the safety boundary.
- Reporting correction: solver telemetry now emits `primary_bound_scope` as `full_instance`, `frozen_access_neighborhood`, or `fixed_access_schedule`; frozen formulations also explain the scope in `limitation`. This prevents a local proof from being reported as global evidence.
- Verification: the new scope regression and all existing tests pass: 60 total. Official scores and artifacts are unchanged.

### E089: Footprint-introduced dependency holdout is frozen before repair

- Timestamp: 2026-09-19 07:06:13 +08
- Fixture: `independent_footprint_dependency_v1` has three activities. `DIRECT` can avoid two ECLO rows only by using standard access in weeks 2–4. Its week-2 footprint competitor `COMP` can move later only if its disjoint successor `FOLLOW` also moves.
- Checked artifacts: the incumbent is dual-scored, standard-clean, and strict-clean at C=`10.0`; the independently authored oracle is equally checked at C=`0.0`. Dataset hash: `bff7db75338331b9957deda68d00f8798fdff2f3799aca03611e3323c1fbab6f`.
- Pre-exposure hypothesis: the current one-pass selector returns `DIRECT` and footprint-added `COMP` but omits `FOLLOW`, because precedence expansion already ran. Freezing `FOLLOW` should force a misleading conditional optimum above zero.
- Protocol: generator, data, incumbent, oracle, hash, scope assertion, and feasibility regression are committed before invoking either the current repair or any broader variant.

### E090: One bounded precedence revisit fixes the frozen holdout

- Timestamp: 2026-09-19 07:10:05 +08
- Falsification: the unchanged one-pass repair freed only `COMP` and `DIRECT`, retained C=`10.0`, and reported a matching bound in 0.004 seconds. Telemetry correctly labels this as a frozen-neighborhood proof. Hash: `fc4c3a72ec0380378e2ac0be59dab53754625b186b7df0149cd51a8218b3fb8e`.
- Correction: Scenario C now revisits transitive precedence once after footprint expansion. The three-activity neighborhood freed `FOLLOW` and proved C=`0.0` in 0.011 seconds. Both scorers and both closure policies accept hash `d80ceb453972ee6c796b4b2d5d0713c7f01051d0e28fd3fc362e2448235b635b`.
- Growth and score checks: public `43→45`, C=`62.7`, proved; irregular `27→29`, C=`31.0`, safe but unproved within 30 seconds; coupled `23→25`, C=`920.0`, proved; cross-module delay `18→18`, C=`76.0`, proved. Every output is dual-scored, standard-clean, and strict-clean.
- Evidence matrix: the new zero-score case raises the retained matrix to 32 cases. Machine-readable rows now declare proof scope, including legacy inference from formulation names.
- Decision: accept the single post-footprint precedence pass. Do not recurse contracts and footprints to a fixed point without another frozen counterexample and matched runtime evidence.

### E091: Post-precedence contract-peer holdout is frozen before repair

- Timestamp: 2026-09-19 07:12:23 +08
- Fixture: `independent_post_precedence_contract_v1` adds `PEER` to the final successor's contract. The incumbent fixes `PEER` in week 6; the zero-score oracle moves it to week 4 so `COMP`/`FOLLOW` can use weeks 5/6 and `DIRECT` can avoid ECLO in weeks 2–4.
- Checked artifacts: incumbent C=`10.0`, oracle C=`0.0`, both dual-scored and clean under standard and strict closures. Dataset hash: `e5f513a65637232af1d6263763c5f4e437772dee505c7c611464ec188ed9d267`.
- Pre-exposure hypothesis: the accepted post-footprint precedence pass returns `COMP`, `DIRECT`, and `FOLLOW` but omits same-contract `PEER`, because contract expansion ran before `FOLLOW` entered the set. The repair should therefore remain conditionally stuck above zero.
- Protocol: generator, data, oracle, incumbent, hash, and selector assertion are committed before the first repair run. This is an authored mechanism test, not evidence of hidden frequency.

### E092: Narrow-plus-expanded portfolio dominates either repair scope alone

- Timestamp: 2026-09-19 07:19:37 +08
- Contract-peer falsification: the three-activity post-precedence repair conditionally proved C=`10.0`, hash `6233aa42075903ee29075f417c873f65f8229e1ca9523f5e6bbc2bf161c89faa`. Adding only the final dependencies' contract peers freed `PEER` and proved C=`0.0`, hash `cee2e4faaf310d156e9884948760e943373deff3c36a8138bc25fb101bf8dcd2`.
- Search-power falsification: two 30-second 29-activity irregular repairs, including production seed 5, retained C=`63.0`. The former 27-activity neighborhood under seed 5 and the same budget recovered dual-scored, standard-clean, strict-clean C=`31.0`, hash `9a3d12499d9b284d63a0c880738a75177af1aa022ed5c7386e8a3e7440da9d61`.
- Correction: both staged C paths now run the narrow repair first and a separate targeted expansion second. The expanded tier uses seed `seed+1`, at most ten seconds, independent telemetry, independent pruning, and strict-better promotion.
- Regression evidence: public C=`62.7`, coupled C=`920.0`, and cross-module C=`76.0` remain dual-scored and clean under both closure policies. The 33-case matrix records the new zero-score holdout; 64 tests pass.
- Integrity: all failed and successful outputs are retained. The expanded repair is not called globally optimal unless an external lower bound independently makes its score decisive.

### E093: Production seed-5 controller validates the two-tier path

- Timestamp: 2026-09-19 07:24:40 +08
- Full path: guarded A failed closed; direct C supplied a checked C=`63.0` incumbent. The 27-activity narrow repair reached C=`31.0` in 30.009 seconds. The 29-activity expanded repair, using seed 6 and ten seconds, retained C=`31.0` rather than displacing it.
- Final evidence: both scorers report C=`31.0`; standard and strict closure screens are clean; hash `18b6eee516d8239407a52172ae7c5f66bbd0f53bd59a526284bdd22c4079711c`. Neither repair proved its conditional bound, so the independent analytical bound from E074 remains the optimality evidence.
- Reporting failure and correction: the first audit script raised `KeyError` only after completion because the A-failure wrapper nested the generic C report. The wrapper now preserves that nested evidence and exposes stable top-level narrow/expanded repair fields. All 64 regressions pass.

### E094: Five serial seeds reproduce the two-tier C=31 recovery

- Timestamp: 2026-09-19 07:30:23 +08
- Protocol: fixed checked C=`63.0` irregular incumbent, seeds 1–5, eight workers, narrow 30 seconds, expanded 10 seconds, serial execution to avoid CPU-contention confounding. Every raw, pruned, and selected artifact plus telemetry is retained.
- Result: narrow scores `[31, 31, 31, 31, 31]`; expanded scores `[31, 31, 31, 31, 31]`; final scores identical. Standard and strict conflicts are zero for all outputs, and both scorers agree.
- Diversity: all five final submission hashes differ. This rules out copied output as the explanation for score agreement, though it does not establish hidden-distribution generalization.
- Proof boundary: every run ended `FEASIBLE_SAFE_INCUMBENT` without a bound. The C=`31.0` optimality claim continues to rely on the independent counting lower bound, not solver status.
- Regression: the matrix is recomputed by a 65th test.

### E095: Post-contract precedence holdout is frozen before repair

- Timestamp: 2026-09-19 07:32:12 +08
- Fixture: `independent_post_contract_precedence_v1` adds cross-contract `PREPEER` as the predecessor of final contract peer `PEER`. The incumbent fixes `PREPEER`/`PEER` in weeks 5/6; the zero-score oracle moves them to weeks 3/4 so `COMP`/`FOLLOW` can use weeks 5/6 and `DIRECT` can avoid ECLO.
- Checked artifacts: incumbent C=`10.0`, oracle C=`0.0`, both dual-scored and clean under standard and strict closures. Dataset hash: `ab66356785225b6b5ff03d5d9495c125ae8bc88c5067cfc774a039f3bc697996`.
- Pre-exposure hypothesis: the expanded selector returns `COMP`, `DIRECT`, `FOLLOW`, and `PEER` but omits `PREPEER`, because the last operation adds contract peers after precedence expansion. The expanded tier should therefore remain conditionally stuck at C=`10.0`.
- Scope check before change: one final precedence pass adds zero activities to the public, irregular, coupled, and cross-module retained neighborhoods. Generator, artifacts, hash, and selector assertion are committed before the first repair run.

### E096: Final targeted precedence pass removes the fourth conditional trap

- Timestamp: 2026-09-19 07:35:00 +08
- Falsification: the existing expanded selector freed `COMP`, `DIRECT`, `FOLLOW`, and `PEER`, omitted `PREPEER`, and proved C=`10.0` in 0.007 seconds. Both scorers and both closure policies accept hash `4282e9d217271b120c3db72cf5b2218a973b60f2834b63abecd153083046d2bb`.
- Correction: one terminal transitive precedence pass adds `PREPEER`. The five-activity repair proved C=`0.0` in 0.014 seconds; both scorers and both closure policies accept hash `02092a079563ecc2d331c033b2cb42055081edd39546ccba8864e867c51bfb75`.
- Cross-regime scope: activity counts remain public `46`, irregular `29`, coupled `25`, and cross-module `18`. No fixed-point contract or footprint recursion was added.
- Evidence: the new zero-score case raises the matrix to 34 cases; 67 regressions pass.

### E097: Both production controllers execute the terminal dependency repair

- Timestamp: 2026-09-19 07:40:00 +08
- Risk: the selector-level test proved the final precedence revisit, but it did not prove that either production controller passed the flag or promoted its checked result.
- Falsification harness: both the generic staged Scenario C controller and the guarded A-to-C portfolio start from the frozen score-`10.0` post-contract-precedence incumbent. Their narrow and earlier expanded calls retain `10.0`; only the terminal five-activity expansion is supplied the checked score-`0.0` oracle.
- Result: each controller makes the terminal expanded call with exactly `COMP`, `DIRECT`, `FOLLOW`, `PEER`, and `PREPEER`, selects the zero-score artifact, and independently re-evaluates it. The full suite passes 69 tests.
- Scope: this is controller-wiring evidence, not new optimizer or hidden-distribution evidence. Official scores and protected artifacts are unchanged.

### E098: Full dependency closure is rejected as the next default tier

- Timestamp: 2026-09-19 07:41:53 +08
- Frontier audit: the final bounded repair leaves union frontiers of public `8`, irregular `24`, coupled `24`, and cross-module `0` activities. The irregular fixed point contains `53` activities versus `29` in the expanded production tier.
- From C=`31.0`: a ten-second, eight-worker fixed-point repair with seed 7 returned the identical dual-scored, standard-clean, strict-clean C=`31.0` schedule and hash `18b6eee516d8239407a52172ae7c5f66bbd0f53bd59a526284bdd22c4079711c`.
- From C=`63.0`: the matched fixed-point repair returned a worse but checked C=`84.0` candidate, hash `d8416452de4c7f43c01a4d07a4322b056e04fa95effa09b26a90a340b3a481c0`, with bound `12.8`. Protected selection would retain C=`63.0`.
- Decision: preserve the outputs as negative evidence and do not integrate fixed-point recursion. The experiment measures search power, not whether the larger neighborhood contains the optimum.

### E099: Renamed and shuffled irregular input still reaches C=31

- Timestamp: 2026-09-19 07:46:34 +08
- Protocol: bijectively permute all semantic identifiers, shuffle every input CSV, retain numeric and relational semantics, and run direct staged Scenario C with seed 5, eight workers, 120-second construction, 10-second verification, 30-second narrow repair, and 10-second expanded repair. No known schedule is translated into the new namespace.
- Result: construction and verification reached C=`147.0`; the 27-activity narrow repair reached C=`31.0`; the 29-activity expanded repair retained it. The final hash is `337dade9fbc52bee64af93ebc5ea2e61d269fcd9d7c94d2f932723f49d85ab0a`.
- Independent checks: main and raw-CSV scorers agree; delay=`0.0`, ECLO nights=`2`, excess access-nights=`3`; hard, standard-closure, and strict-closure conflicts are all zero.
- Boundary: the worse initial construction confirms wall-time search sensitivity to model ordering. Recovery of the same final score supports controller-level identifier invariance on this regime only. The repair has no solver bound, so the favorable run is deliberately excluded from the proof-only benchmark matrix.

### E100: Three identifier permutations expose one strict-only conflict

- Timestamp: 2026-09-19 07:56:05 +08
- Fixed policy: permutation seeds `20260919`–`20260921`, solver seed 5, eight workers, 120-second construction, 10-second verification, 30-second narrow repair, and 10-second expanded repair; no translated schedule or oracle input.
- Distribution: construction scores were `[147, 140, 112]`; first repair widths were `[27, 52, 27]`; all three final scores were C=`31.0`; all final hashes differ; both scorers agree; all are standard-clean. No repair produced a bound.
- Contradictory evidence: strict conflicts were `[0, 0, 1]`, not 3/3 clean. Permutation 3 conflicts at week 13 between `Z528` and `Z572` on `SEC:L02:N007_N001:WB` under the stricter buffer-to-buffer interpretation.
- Targeted hedge: freeing `Z528`, `Z572`, and successor `Z596` under strict closure produced C=`31.0`, standard conflicts=`0`, strict conflicts=`0`, hash `e551e776edde090420c03a4eab3145697c3311315549a7d154c511bfcb4c031c`, with a conditional bound of `31.0` in 0.282 seconds.
- Decision: retain standard closure as the validator-matching rule. Implement strict closure only as a protected equal-or-better final hedge, never as evidence that the official rule is strict.

### E101: Protected strict hedge is integrated and file-gated

- Timestamp: 2026-09-19 08:02:37 +08
- Controller rule: after standard selection, screen the final candidate under the conservative strict buffer-overlap interpretation. If conflicts exist, free their participants plus fixed-point contract and precedence dependencies for at most ten seconds under strict closure.
- Promotion gate: the candidate files themselves must be standard-feasible and strict-clean after pruning, and their official objective must be no higher than the incumbent. Telemetry alone cannot pass the gate. The original incumbent remains protected otherwise.
- Real replay: the permutation-3 conflict produced repair set `Z528`, `Z572`, `Z596`; conflicts changed `1→0`; both scorers remained C=`31.0`; the solver conditionally proved `31.0` for the frozen neighborhood. A fresh run produced hash `062d4db1e3455caa3fb57e9be58204c577b8ad369a5d736cf68c4f5b0de15516`.
- Regression: both generic staged and guarded Scenario C controllers expose hedge telemetry and promotion state; contradictory mocked telemetry is rejected by raw-file screening. All 72 tests pass.
- Boundary: strict closure remains an optional hedge because it contradicts organizer sample cases. This does not change official public artifacts or scores.

### E102: Strict hedge succeeds on four of six conflicted retained cases

- Timestamp: 2026-09-19 08:04:08 +08
- Protocol: replay the integrated hedge from every strict-conflicted artifact in the 34-case proof matrix, using eight workers, distinct fixed seeds, ten seconds, and score-preserving promotion.
- Results: prefix A `11` free, `0.289s`, promoted at `85.4`; prefix B `19`, `2.684s`, promoted at `20.0`; prefix C `34`, `10.023s`, not promoted at `52.7`; structural A `41`, `1.582s`, promoted at `39.9`; structural B `45`, `10.012s`, not promoted at `10.0`; structural C `36`, `2.063s`, promoted at `10.0`.
- Integrity: all promotions preserve the official objective and end strict-clean. Both failures retain their original artifacts and scores. No official public artifact changed.
- Conclusion: keep the ten-second cap and protected gate. Do not describe conflict-seeded closure as a small neighborhood or promise strict-clean output.

### E103: Higher-score strict-clean hedge is rejected without false reporting

- Timestamp: 2026-09-19 08:05:57 +08
- Counterexample: the permutation-3 C=`31.0` incumbent has one strict-only conflict. A separately checked strict-clean C=`112.0` candidate, hash `b40235fb95bfdebdb71e8f21475f1ccdfb8cfd9b994d42ff3cf7bb1164a2d4a3`, conditionally proves its frozen-neighborhood score.
- Result: the hedge gate rejects C=`112.0`, returns the original C=`31.0` directory and evaluation, keeps promotion false, and reports one final strict conflict. Candidate telemetry and prune evidence remain available.
- Correction: `strict_hedge_conflicts_after` now describes the selected artifact, not a rejected candidate. The full suite passes 73 tests.

### E104: Official incumbents bypass the hedge byte-for-byte

- Timestamp: 2026-09-19 08:07:33 +08
- Result: public A, B, and C each have zero strict conflicts before the hedge. No repair activities are selected, no solver or pruning stage runs, promotion is false, and returned hashes remain exactly `8ecab02f…`, `0b38e83c…`, and `30247f57…`.
- Regression: the behavior is recomputed from the protected directories and manifest; all 74 tests pass.

### E105: Three-line topology proves A/B/C without public identifiers

- Timestamp: 2026-09-19 08:09:37 +08
- Fixture: extend the independent two-line synthetic network with line `LNZ`, a matching `X1–X2` interchange bridge, two unique stations, one contract, and one activity. Dataset hash is `71e1e417e3ede8385a5d957368f7b963fa65b89f703c859438bded342654e0da`.
- Independent oracle: A=`7.0`, dual-scored and hard-feasible. The Live bridge activity on `LNX` derives 12 crossover locations: sector and platform locations in both bounds on `LNY` and `LNZ`.
- No-hint results: staged one-worker solves prove full-instance A=`7.0`, B=`10.0`, and C=`7.0`; all three finals are strict-clean. The proof matrix grows from 34 to 37 cases and the suite passes 75 tests.
- Boundary: the fixture changes line cardinality but remains compact and structurally related to the independent two-line generator.

### E106: Adjacent Live crossover bridges compose and solve from scratch

- Timestamp: 2026-09-19 08:16:21 +08
- Precommit protocol: generator, eight input CSVs, and a dual-scored score-zero oracle were committed as `9273d3d` before the solver saw the fixture. Dataset hash is `68379defb1fb02785c1d4aa9ab88747faa395b5c888f6f1245d40df5d1b391e7`.
- Topology result: `M001` spans `X1–X2–X3` on `LNX` and derives ten unique crossover locations on `LNY`; `M003` works `X2–X3` on `LNY` and derives six on `LNX`.
- No-hint result: one-worker staged production paths prove full-instance A=`0.0`, B=`0.0`, and C=`0.0` in under one second combined. All three outputs are dual-scored and clean under both closure screens; hashes are `4853d08d…`, `5e2adee3…`, and `a92fb00c…`.
- Evidence update: the proof matrix grows from 37 to 40 cases; 34 are full-instance and six are restricted-neighborhood proofs. The suite passes 76 tests.
- Boundary: this isolates topology composition rather than scale or congestion. Zero score is a correctness result, not evidence of difficult-search performance.

### E107: Congested adjacent bridges reproduce the analytical ECLO trade-off

- Timestamp: 2026-09-19 08:19:28 +08
- Precommit protocol: generator, input, and separate A/B/C oracles were committed as `4b569e5` before solver exposure. Dataset hash is `07d5fb97a92c194da5ff70bfec984f3b4dc44c1d701502fc08eabcb0d54aa105`.
- Bound: opposing Live PM activities cannot share a week. `R001` needs three standard weeks, so A cannot finish before week 3 and incurs seven Priority-1 days = `700.0`. In B/C, two ECLO rows deliver its three work units for the unavoidable minimum penalty `2×5=10.0`; `R002` then finishes on time.
- Result: unchanged one-worker production paths prove full-instance A=`700.0`, B=`10.0`, and C=`10.0` in under one second combined. Both scorers agree, both closure screens are clean, and the solver schedules two ECLO nights in B/C exactly as the bound requires.
- Evidence update: the proof matrix grows from 40 to 43 cases; 37 are full-instance and six are restricted-neighborhood proofs. The suite passes 77 tests.
- Boundary: this validates a nonzero topology/objective interaction on two activities, not runtime scaling or a dense hidden distribution.

### E108: Eight interacting Live jobs expose a Scenario C global-move failure

- Timestamp: 2026-09-19 08:24:15 +08
- Precommit protocol: the eight-activity, 24-week fixture was committed as `52b9eb5` before solver exposure. Every activity spans both adjacent interchange bridges and derives ten cross-line locations. Dataset hash is `8a3be5829570b659a574cbad29e4b42712d2e3787376c2605f0b0cd8714ee58e`.
- Fixed budget: one worker; three five-second heuristic attempts; five-second local repair; ten-second fallback and sound verification.
- A result: heuristics returned attractive but conflicting scores `266`, `266`, and `259`; local repair produced safe `273.0`; full-instance sound verification proved `273.0` in 3.94 seconds.
- B result: all three construction attempts safely reached `80.0`; full-instance verification proved `80.0`. Sixteen ECLO rows are required to compress eight three-unit activities into their two-week hard-date blocks.
- C failure: the safe final remains `273.0` with zero ECLO while sound verification stops at lower bound `21.0`. The first direct candidate is invalid C=`115.0` with 14 closure conflicts; two later attempts are safe C=`273.0`. The cost neighborhood already includes all eight activities, so further dependency expansion cannot fix this result.
- Integrity: all returned A/B/C artifacts are dual-scored and clean under both closure screens. C=`273.0` is a valid incumbent, not an optimality claim. The protected official public artifacts are unchanged.
- Next falsification: serialize the predeclared global move that compresses one early activity into a two-week ECLO window and shifts the remaining unique weekly assignments one week earlier. Promote only if the files prove a score below `273.0`.

### E109: Checked ECLO compaction reaches the enumerated C optimum

- Timestamp: 2026-09-19 08:33:42 +08
- Preserved falsification: the predeclared T003 transformation produces feasible, dual-scored, strict-clean C=`262.0` (`252.0` delay + two ECLO rows). A 30-second sound solve retains `262.0` but only raises the full-instance bound to `21.0`; this is retained as a search-proof failure, not reported as solver optimality.
- Independent proof: all 28 PM activity pairs conflict when placed in separate possessions. Every job is released in week 1 and needs three standard rows. All Live jobs affect both lines, so the shared two-week Scenario C window can reduce the row count of at most one job to two. Exhaustive enumeration of all `8! × 9` nonpreemptive order/compression choices gives lower bound `262.0`. A regular completion-time objective admits a non-idling nonpreemptive optimum on this single lane, so the enumeration covers the optimum.
- Implementation: `best_single_lane_eclo_compaction` is called by both Scenario C production controllers before sound verification. It derives candidates from serialized files, regenerates results, applies full standard validation and the requested strict screen, and promotes only a strict score improvement. It is a no-op unless the incumbent has one activity per occupied week, a contiguous horizon, and a three-standard-row activity reducible to two adjacent ECLO rows.
- Real controller: one worker, strict screen, three five-second A attempts, five-second A repair, ten-second A verification, three five-second C attempts, five-second C repair, and ten-second C verification. It selects `scenario_c_eclo_compaction` at C=`262.0`; the sound verifier and subsequent all-activity repair both retain `262.0` safely.
- Cross-regime protection: the official public C schedule is structurally inapplicable and remains unchanged. The full suite passes 81 tests. The benchmark matrix grows from 43 to 46 cases: 40 full-instance proofs and six frozen-neighborhood proofs. No portal attempt was used.

### E110: Adversarial replay corrects ECLO preservation and removes duplicates

- Timestamp: 2026-09-19 08:39:29 +08
- Defect: the first transformation preserved the target's new ECLO flags but cleared existing ECLO flags on every other activity. Candidate validation rejected the resulting workload/window violations, so this caused false negatives rather than an invalid promotion. The transform now copies all non-target flags exactly; an idempotence regression checks an already-compacted source.
- Deduplication: full transformed access and occupancy signatures are compared before file generation. On the same real-controller source, materialized candidates fall from 20 to eight, 12 duplicates are skipped, and the selected hash remains `2eebc28b…` at C=`262.0`. The audit tree shrinks from 580 KB to 432 KB.
- Production replay: the corrected unmocked one-worker strict path again selects `scenario_c_eclo_compaction`, both scorers return `262.0`, both closure screens are clean, and sound verification retains `262.0` with bound `21.0`.
- Retained-corpus audit: `scripts/audit_eclo_compaction_matrix.py` rechecks all 19 proof-matrix C incumbents under the strict screen in 0.19 seconds. Two meet the structural precondition, seven unique candidates are checked, eight duplicates are skipped, and no proven incumbent is displaced.
- Regression status: 82 tests pass. Official hashes and scores remain unchanged; no portal attempt was used.

### E111: A 120-job audit validates exact compaction ranking

- Timestamp: 2026-09-19 08:46:36 +08
- Precommit protocol: the 120-activity, 360-week single-line input and its feasible zero-score serialization were committed as `5f27eb7`; a reverse-order positive-score serialization was committed separately as `d25c2c8`. Both precede exposure to the ranked operator. Dataset hash is `9b8dd3824421989e5aae11044d8a5c40699a3a705accf2bb8bd7de8086bc6431`.
- Baseline failure: before the zero-floor guard, the zero-score source materialized 120 unique candidates and skipped 240 duplicates in 8.34 seconds even though improvement was impossible.
- Zero-floor result: the same source now checks zero candidates in 0.035 seconds and returns no selection.
- Positive-score exhaustive result: the reverse source is dual-scored and strict-clean at `2,880,360`. Exhaustive mode checks 120 feasible improving candidates, observes zero predicted-versus-serialized score mismatches, and selects `2,864,830` in 8.29 seconds.
- Positive-score ranked result: production mode ranks the same 120 transformations, fully validates one, prunes 119 only after exact score agreement, and selects the same `2,864,830` result in 0.24 seconds.
- Real-controller replay: the eight-job strict controller checks one of eight ranked candidates, selects the same C=`262.0` hash `2eebc28b…`, remains dual-scored and strict-clean, and passes the candidate to sound verification. Its audit directory contains one candidate and is 344 KB, down from 20 candidates and 580 KB before hardening.
- Regression status: 83 tests pass. No official artifact, score, or portal quota changed.

### E112: Multi-activity contract holdout preserves exact compaction ranking

- Timestamp: 2026-09-19 08:51:00 +08
- Precommit protocol: the three-contract, six-activity fixture and its serialized source were committed as `0e0c6c1` before calling the compaction helper. Dataset hash is `8167da5960f185f65bf717ac1fdb1b33400b6db20878a129d6f229e2d4a36259`.
- Coverage: every contract has two activities; contract priorities are 1, 2, and 3; activity priorities cover 1, 2, and 3. The source is dual-scored and strict-clean at C=`23,765`, hash `33a1ff54…`.
- Falsification result: exhaustive mode checks all six unique transformations, skips 12 duplicates, and records zero predicted-versus-serialized score mismatches. Ranked mode validates one, prunes five, and selects the same strict-clean hash `2d37c2fa…` at C=`21,990`.
- Boundary: this is independent synthetic evidence for local arithmetic, not official portal confirmation. No protected official artifact or portal quota changed.
- Regression status: 84 tests pass.

### E113: Repeated line-local compaction captures a missed second gain

- Timestamp: 2026-09-19 08:54:03 +08
- Precommit protocol: the two-line, four-activity source and generator were committed as `3b55d40` before the compaction helper saw them. Dataset hash is `71da72ce6966516d9ff1188c745b3729e1987b52425e1fb005bfaaac3378e8cd`.
- Blind result: the first checked compaction lowers C=`23,660` to `20,030`; calling the unchanged helper again on the selected files lowers it to `18,220`. A third call finds no legal improvement.
- Implementation: both production controllers now repeat fully validated strict improvements up to the original access-row count. Existing ECLO line windows safely filter incompatible serialized candidates before file generation, including all-line blocking for Live crossover work.
- Audit: ranked mode checks two candidates; exhaustive mode checks six. Both promote twice, select hash `12695245…` at C=`18,220`, match the independent scorer, remain strict-clean, and report zero score-prediction mismatches. The generic staged production integration reproduces both promotions before verification.
- Retained-corpus replay: the exact repeated operator promotes none of 19 retained Scenario C incumbents. The two structurally applicable finals check no new files: one is already at score zero and the scaled C=`262` incumbent skips seven same-window candidates. Public C remains structurally inapplicable and unchanged.
- Integrity: official scores and files are unchanged. Per the user's explicit instruction, remaining portal attempts A=`3/5`, B=`4/5`, C=`4/5` are frozen until a specific run is authorized.
- Regression status: 86 tests pass.

### E114: Unfiltered enumeration finds no ECLO-window filter counterexample

- Timestamp: 2026-09-19 08:57:13 +08
- Method: enumerate all 24 orders of the four frozen two-line activity blocks. At every recursively reached improving state, materialize every structural three-to-two ECLO transformation without the production prefilter, then apply the full evaluator and strict closure screen.
- Result: the ranked production sequence equals the best exhaustively reachable score in 24/24 orders. Exhaustive state graphs visit up to nine unique schedules and materialize up to 72 candidates per order. All 288 unique candidates that production would filter because their affected line already has ECLO are infeasible.
- Four-access extension: the same differential audit covers all 24 orders of the generalized holdout. Ranked equals exhaustive in 24/24; state graphs visit up to 25 schedules and materialize up to 480 candidates. All 1,920 filtered candidates are infeasible.
- Cross-line Live check: the retained eight-job C=`262` final exposes seven unique same-window candidates. All seven are infeasible under unfiltered materialization; exhaustive best remains the source hash and score.
- Boundary: this supports the filter under serialized schedules but is not a proof for arbitrary non-serialized schedules, where the operator does not run. No official portal attempt was used.
- Regression status: 87 tests pass.

### E115: Generalized compaction improves a frozen four-access holdout

- Timestamp: 2026-09-19 09:01:38 +08
- Precommit protocol: the four-access, two-line fixture and strict-clean source were committed as `f30f900` before generalizing the operator. Dataset hash is `06660e467be28c897c74d57088ed5360fcb3471aa2d847b6950174f536b9a1cb`.
- Preserved blind failure: the old exactly-three-row operator checks zero candidates and leaves C=`32,760` unchanged.
- Implementation: for any all-standard activity with at least three rows, enumerate removal of one row and selection of exactly two retained rows that become adjacent after the global shift. Those two rows receive ECLO; every other target row remains standard and every non-target ECLO flag is preserved.
- Result: ranked production mode checks two candidates, prunes ten, and promotes twice to C=`27,320`. Exhaustive mode checks all 12 unique candidates and reaches the same hash with zero prediction mismatches. Both scorers agree and the strict screen is clean.
- Sequence falsification: all 24 activity orders match unfiltered exhaustive best-reachable scores, including alternate equal-score ECLO pairs.
- Regression status: 88 tests pass. No official portal attempt was used.

### E116: Access-length sweep covers public lengths through seven

- Timestamp: 2026-09-19 09:03:51 +08
- Method: generate isolated two-line serializations with four activities each and uniform access counts 3, 4, 5, 6, and 7. For each length, compare ranked and exhaustive repeated compaction, the main and independent scorers, and the strict closure screen.
- Result: all five ranked scores and hashes equal exhaustive mode; every case promotes twice with zero prediction mismatches and zero strict conflicts. Final scores are `18,220`, `27,320`, `36,420`, `45,520`, and `54,620` respectively.
- Efficiency: ranked mode checks exactly two candidates per case. Exhaustive checks grow from 6 to 30 and duplicate signatures from 12 to 180; measured ranked runtime remains below 0.01 seconds at length 7.
- Boundary: this is locally generated structural evidence, not portal confirmation. No official attempt or protected artifact changed.
- Regression status: 89 tests pass.

### E117: Idle-week normalization unlocks strict and equal-score compound gains

- Timestamp: 2026-09-19 09:09:00 +08
- Strict case: the precommitted `b9737737…` source has one globally empty week and scores C=`26,390`. One checked shift restores hash `46fef54e…` at `23,660`; repeated ECLO then reaches the previously audited hash `12695245…` at `18,220`.
- Equal-score counterexample: fixture `49497489…` was committed as `e37ad8a` while the pipeline remained stuck at C=`910`. Deleting its idle week is fully valid but still scores `910`; using that artifact only as a seed unlocks one ECLO promotion to strict-clean, dual-scored C=`10`, hash `40934472…`.
- Fail-safe correction: the initial idle ranker could trust a non-improving prediction without materializing a candidate. It now checks the first gap, disables early stopping after any mismatch, and evaluates all later gaps if prediction becomes untrusted.
- Retained replay: all six internal gaps across 19 retained C incumbents are serialized and checked. Prediction mismatches and promotions are both zero; the official C artifact has no gap and remains unchanged.
- Regression status: 93 tests pass, including both production controllers. No official portal attempt was used.

### E118: Leading and tied idle gaps survive exhaustive bounded search

- Timestamp: 2026-09-19 09:19:29 +08
- Leading case: a precommitted source delayed by an empty week 1 falls from C=`27,300` to `23,660`; two checked ECLO promotions then reach dual-scored, strict-clean `18,220`.
- Frozen tie failure: deleting leading week 1 or internal week 5 both lowers C=`2,730` to `1,820`. The old numeric tie-break chose week 1 and blocked ECLO; internal-first ordering makes the occupied interval contiguous and reaches checked C=`920`.
- Exhaustive audit: all 16 three-plus-three-row schedules over the eight-week fixture enumerate every valid non-worsening normalization state and run exhaustive per-round ECLO from every state. Production matches the best composed score in 16/16 cases; both scorers agree.
- Retained replay: nine removable weeks occur across eight of 19 retained C schedules. One ranked candidate is checked per affected schedule; prediction mismatches and promotions are zero.
- Regression status: 95 tests pass. Official scores, files, and frozen portal quotas are unchanged.

### E119: Final-selection post-processing closes a verification-stage gap

- Timestamp: 2026-09-19 09:26:42 +08
- Precommit protocol: the 13-week, four-activity fixture and its deliberately non-serialized heuristic source were committed before production code changed. Two failed fixture revisions are preserved: an illegal PM co-share and a same-line closure conflict. The corrected source overlaps only different lines and is dual-scored, standard-clean, and strict-clean at C=`26,390`.
- Preserved failure: pre-verification normalization lowers the heuristic to `25,480`, but an unavoidable cross-line overlap keeps ECLO inapplicable. Verification returns a distinct serialization at C=`23,660`; the old controller selects and copies it without post-processing.
- Correction: a shared final Scenario C gate runs checked non-worsening idle normalization and repeated ECLO compaction after all solver, repair, and strict-hedge selection. Only a strict fully checked decrease replaces the final incumbent.
- Result: both generic and A-to-C production controllers take the selected C=`23,660` artifact to dual-scored C=`22,760`, hash `c6ff70af…`, with zero strict conflicts. The official public C artifact is already structurally inapplicable and remains unchanged.
- Regression status: 98 tests pass, including an exact-hash no-op check on the official C artifact. No official attempt was used.

### E120: Retained-corpus final post-processing changes no incumbent

- Timestamp: 2026-09-19 09:29:02 +08
- Method: run the shared strict final post-processor on all 19 retained Scenario C benchmark artifacts, independently rescore the selected path, reapply the strict closure screen, and compare source/selected hashes.
- Result: zero promotions and zero hash changes. Nine idle candidates are fully checked; ECLO checks zero because retained serializations are already compacted, at the objective floor, or structurally inapplicable. Total elapsed time is 1.210 seconds; maximum per case is 0.490 seconds.
- Official protection: public C stays exactly `62.7`, hash `30247f57…`, with zero strict conflicts.
- Scope note: `prefix040_C` and `structural_demand_C` already contain strict-only diagnostic conflicts and remain byte-identical. The audit distinguishes an unchanged historical source from a promoted unsafe candidate.
- Regression status: 99 tests pass. No official attempt was used.

### E121: Idle normalization exits at the nonnegative score floor

- Timestamp: 2026-09-19 09:30:15 +08
- Proof: the Scenario C objective is a sum of nonnegative delay, excess, and ECLO terms. An equal-score normalization at zero cannot seed a strict negative result, so candidate serialization cannot improve the protected incumbent.
- Result: the retained idle audit still reports nine removable weeks but checks three candidates instead of eight. The final-selection audit checks three idle candidates instead of nine. Both retain zero promotions and zero hash changes.
- Runtime: the final-selection audit takes 1.220 seconds with a 0.515-second maximum case, essentially unchanged because independent rescoring and closure checks dominate. The accepted claim is lower candidate/file volume, not wall-time speedup.
- Regression status: 99 tests pass. Official scores, hashes, and portal quotas are unchanged.

### E122: Complete final post-processing passes the 120-activity scale audit

- Timestamp: 2026-09-19 09:32:13 +08
- Method: run the production final Scenario C post-processor on both frozen 120-activity scale sources, independently rescore its selection, and reapply the strict buffered closure screen.
- Zero-floor result: C=`0` remains byte-identical and generates zero idle and ECLO candidates.
- Positive result: C=`2,880,360` improves to dual-scored, strict-clean C=`2,864,830`; exact score ordering checks one ECLO candidate and prunes 119. No idle candidate is applicable.
- Runtime: 0.56 seconds combined in this local run. This is evidence against prohibitive overhead for this fixture, not a guarantee for unknown competition instances.
- Regression status: all 100 tests pass. No official attempt was used.

### E123: Fault-injected idle predictions retain the safe tie rule

- Timestamp: 2026-09-19 09:34:09 +08
- Adversarial setup: on the frozen C=`2,730` equal-gap fixture, inject wrong predicted scores that rank leading week 1 before internal week 5 and trigger prediction distrust.
- Preserved failure: the old exhaustive fallback compared tied checked candidates by week number and would keep week 1, despite internal week 5 being the ECLO-unlocking choice.
- Correction: checked equal-score candidates now retain the internal-before-leading ranking key after prediction mismatch.
- Result: exhaustive fallback selects week 5 at checked C=`1,820`; the unmodified predictor audits and all retained final selections preserve their scores and hashes.
- Regression status: all 101 tests pass.
- Official protection: no official attempt was used.

### E124: Final cleanup survives a 59-gap scale stress

- Timestamp: 2026-09-19 09:36:38 +08
- Precondition: a generated 60-activity, 240-week reverse-order source has 59 internal idle weeks, standard feasibility, strict-buffer cleanliness, and matching source score C=`1,116,689` under both scorers.
- Result: final post-processing checks and promotes 59 idle deletions with zero prediction mismatches, then checks and promotes one ECLO candidate. The selected result is dual-scored C=`733,120`, strict-clean, for a decrease of `383,569`.
- Runtime: 1.537 seconds in this local run. The accepted claim is measured practicality at this scale, not asymptotic safety or an unknown-instance guarantee.
- Regression status: all 102 tests pass.
- Official protection: no portal interaction or attempt was used.

### E125: Two-line normalization branching finds no greedy counterexample

- Timestamp: 2026-09-19 09:39:00 +08
- Search space: all 256 ways to omit one week from each of four ordered four-week activity blocks across two independent lines. Each case exposes multiple internal-gap orders; the largest reachable non-worsening normalization graph has 16 states.
- Oracle: enumerate every strict-clean non-worsening normalization state, run exhaustive repeated ECLO compaction from each, and compare the best score with the production greedy path. Independently rescore every production result.
- Result: 256/256 final scores match the full branching oracle; mismatch count is zero.
- Boundary: planned starts are common and block order is fixed, so this is bounded falsification rather than a completeness proof.
- Regression status: all 103 tests pass.
- Official protection: no portal interaction or attempt was used.

### E126: Constrained branching finds no greedy counterexample

- Timestamp: 2026-09-19 09:40:56 +08
- Search: repeat the complete 256 two-line gap-pattern family under three data variants: staggered planned starts, a four-activity precedence chain, and both together.
- Oracle: compare production greedy normalization plus exhaustive repeated ECLO with all reachable strict-clean non-worsening normalization states and their exhaustive ECLO compositions; independently rescore each production result.
- Result: 768/768 final scores match; no mismatch example exists. The largest reachable state count is five for each staggered-start family and 16 for the precedence-only family.
- Interpretation: planned-start and precedence feasibility checks are active and did not expose a choice-order defect in this bounded family. This is not a proof for arbitrary schedules.
- Regression status: all 104 tests pass.
- Official protection: no portal interaction or attempt was used.

### E127: Final release archives are separated from stale validator history

- Timestamp: 2026-09-19 09:44:00 +08
- Finding: historical `deliverables/validator/A.zip` is the infeasible A-001 artifact; unnumbered B/C ZIPs also have different archive bytes from the confirmed B-001/C-001 uploads. These remain historical evidence, not release files.
- Packaging: deterministic ZIPs are now generated under `deliverables/final-submission` from the hash-pinned protected public A/B/C directories only. Each archive contains exactly `RESULTS.csv`, `SCHEDULE_ACCESS.csv`, and `SCHEDULE_OCCUPANCY.csv` at its root.
- Verification: every archived member hash matches the official-incumbent public manifest. The final manifest records archive hashes `d003c6f1…` (A), `25b87dc9…` (B), and `a3e3419f…` (C), plus run IDs and scores.
- Test correction: the first archive regression required the same member order as an unrelated tuple and failed all three archives. ZIP member order is not a submission rule; the corrected assertion requires exactly three unique required root names and preserves byte-hash verification.
- Regression status: all 105 tests pass.
- Authorization boundary: packaging is local and reversible; no portal interaction or attempt was used.

### E128: Local pre-upload readiness passes for all official incumbents

- Timestamp: 2026-09-19 09:44:18 +08
- Audit: reload the current public dataset; verify each protected source and final ZIP using archive/member hashes, submission hash, exact root membership, primary score, independent score, hard feasibility, and strict buffered closure screening.
- Result: every check is true for A=`137.9`/A-002, B=`30.0`/B-001, and C=`62.7`/C-001; aggregate `all_ready` is true.
- Boundary: this is a local drift and packaging check, not an official validator call or a new score claim.
- Regression status: all 106 tests pass.
- Official protection: no portal interaction or attempt was used.

### E129: Organizer specification remains unchanged upstream

- Timestamp: 2026-09-19 09:45:36 +08
- Read-only check: `git ls-remote` reports organizer repository `main` at full commit `966c976005db2e3e40a691cff268fdb8f396a5df`.
- Result: this equals the commit already recorded for the locally verified PS1 pack. No new upstream problem-statement change requires reconciliation.
- Boundary: this checks the public Git branch only; portal-only notices would require separate evidence.
- Official protection: no validator or submission attempt was used.

### E130: Correct stale Scenario C excess weight in idle prediction

- Timestamp: 2026-09-19 09:47:48 +08
- Finding: `idle_compact._predicted_objective` used `20 × excess_access_nights_total`; the official and dual-scorer coefficient is `7`.
- Impact analysis: idle deletion cannot change the excess total. Full serialized evaluation gates every candidate, and the first discrepancy disables pruning, so no protected score, selected hash, or official artifact was wrong. The defect caused avoidable prediction distrust and exhaustive candidate checks when excess and removable gaps coexist.
- Correction and test: coefficient `7` makes the no-shift prediction on the real excess-bearing irregular C incumbent equal both scorers at C=`31.0` with excess total 3. Fault-injected mismatch fallback still preserves the internal-gap tie rule.
- Replay: retained, 59-gap scale, 120-activity scale, 256-case multiline, and 768-case constrained audits preserve all scores and mismatch counts after the correction.
- Regression status: all 107 tests pass.
- Official protection: no portal interaction or attempt was used.

### E131: Centralize production scoring without accepting a runtime regression

- Timestamp: 2026-09-19 09:53:31 +08
- Change: move official production weights, nudges, excess/ECLO unit costs, contract cost curves, and point delay scoring into `objective.py`; keep the independent raw-CSV scorer separate. Remove the unused activity-completion helper that encoded the obsolete scoring shape. Reject incomplete/extra contract completion mappings rather than silently omitting delay.
- Rejected path: the first point-score implementation generated a full horizon cost vector per contract and candidate. It preserved all semantic results but slowed the 59-gap audit from about 1.50 to 6.93 seconds, ranked ECLO from 0.25 to 1.27 seconds, and final positive-scale post-processing from 0.39 to 1.45 seconds.
- Correction: point scoring now calculates only the requested contract/week value. Measured runtime returns to 1.54 seconds, 0.25 seconds, and 0.39 seconds respectively.
- Verification: all 108 tests pass; every public contract cost curve matches the compatibility alias and the official A delay equals the independent scorer. Full replay preserves 256/256 unconstrained and 768/768 constrained branching matches, zero retained-corpus promotions/hash changes, and final readiness for A/B/C.
- Official protection: no portal interaction or attempt was used.

### E132: Final packages match exact confirmed-upload contents

- Timestamp: 2026-09-19 09:58:04 +08
- Reference chain: A-002 archive SHA-256 `76bf26e1…`, B-001 `1ef95698…`, and C-001 `ee6b09cc…` match the append-only upload ledger.
- Result: every preserved reference archive contains exactly the three required root CSVs, and every member hash equals the corresponding deterministic final-package member. All ten readiness checks pass for each scenario; aggregate `all_ready` remains true.
- Interpretation: different final ZIP hashes come only from deterministic repacking metadata/compression. The evaluated CSV bytes are unchanged.
- Regression status: all 108 tests pass.
- Official protection: no portal interaction or attempt was used.

### E133: Exact-commit upstream byte audit passes

- Timestamp: 2026-09-19 10:03:45 +08
- Reference: organizer `main` and the locally recorded specification commit both resolve to `966c976005db2e3e40a691cff268fdb8f396a5df`.
- Failed diagnostic: a shallow clone stalled for more than two minutes, was interrupted, and ended with `fetch-pack: unexpected disconnect while reading sideband packet`. It is retained as a failed acquisition path, not positive evidence.
- Fallback method: enumerate every local PS1 file except `.DS_Store`, fetch its raw counterpart from the exact commit, and compare complete file bytes.
- Result: 14/14 files match; the README SHA-256 is `e7d8f9457e62a1732fc7986cea57ad5fbd595e7cabe2e8b789e673c8335bd253`.
- Boundary: public-repository equality does not reveal portal-only notices or invoke the official validator.
- Official protection: no portal interaction or attempt was used.

### E134: Fourteen boundary mutations exercise the core hard constraints

- Timestamp: 2026-09-19 10:08:29 +08
- Method: clone the protected public A/B/C CSVs into isolated temporary directories, change one boundary condition at a time, and run the full evaluator. The protected sources are never edited.
- Legal mix: merge accepted boundary groups into `5C` and `PC + 4C`; both are rejected with the exact mix counts.
- Capacity: split one possession into extra local groups. A rejects supply + 1; C does not capacity-reject supply + 1 but rejects supply + 2; B records three soft excess groups without a capacity hard failure.
- Other boundaries: a one-half-unit workload deficit, predecessor overlap, workfront overflow, out-of-range access-night index, Scenario A ECLO, pre-start placement, horizon overflow, and Scenario B deadline overrun each trigger the intended diagnostic.
- Correlated-risk note: this validates our evaluator against direct mutations and published thresholds, not against an unused official run. Some capacity mutations deliberately retain unrelated closure conflicts, so the assertions inspect rule-specific diagnostics rather than claiming whole-submission feasibility.
- Regression status: all 109 tests pass.
- Official protection: no portal interaction or attempt was used.

### E135: Zero-supply mutation falsifies incomplete ECLO score prediction

- Timestamp: 2026-09-19 10:11:21 +08
- Finding: the Scenario C ECLO ranker included delay and ECLO cost but omitted excess cost. This is invisible on the positive-supply fixtures used so far, but the input loader and solver permit a location with supply zero.
- Safety analysis: serialized candidates were still evaluated in full; an actual/predicted mismatch disabled pruning. No wrong incumbent or official artifact resulted.
- Mutation: copy the two-line multipass fixture, change one used location from supply one to zero, and leave the source submission unchanged. It remains within Scenario C's one-extra-group allowance and has six excess nights.
- Result: after adding exact excess arithmetic, ranked and exhaustive modes report zero prediction mismatches and select the same score and submission hash.
- Performance guard: precomputing zero-supply footprint units restores the 120-activity ranked benchmark to 0.244 seconds; exhaustive checks all 120 candidates in 8.381 seconds. Scores, hashes, and mismatch counts are unchanged.
- Regression status: all 110 tests pass.
- Official protection: no portal interaction or attempt was used.

### E136: Exhaustive legal-mix equivalence finds no divergence

- Timestamp: 2026-09-19 10:12:40 +08
- Search space: every non-empty `(PM, PC, C)` count triple from zero through five, 215 combinations total.
- Oracle comparison: the evaluator's explicit legal-mix predicate versus the solver inequalities `PM ≤ 1`, `PC ≤ 1`, `C ≤ 4 − PC`, and `PC + C ≤ 4(1 − PM)`.
- Result: 215/215 acceptance decisions match. This extends the artifact mutations beyond `5C` and `PC + 4C` to multiple-PM, multiple-PC, and every mixed boundary in the enumerated range.
- Regression status: all 111 tests pass.
- Official protection: no portal interaction or attempt was used.

### E137: Scenario capacity-domain enumeration finds no off-by-one error

- Timestamp: 2026-09-19 10:13:50 +08
- Search space: every supply value zero through five crossed with zero through ten candidate activities, 66 pairs.
- Result: A equals `min(candidates, supply)`; C equals `min(candidates, supply + 1)`; bridge-safe B equals `candidates`; direct-heuristic B equals `min(candidates, supply + 1)`.
- Integrity boundary: only unrestricted bridge-safe B represents the published unlimited paid-excess domain. The smaller direct domain remains a non-certifying construction heuristic, and its comment and tests now state that boundary explicitly.
- Regression status: all 112 tests pass.
- Official protection: no portal interaction or attempt was used.

### E138: Ten malformed-output mutations fail closed

- Timestamp: 2026-09-19 10:17:49 +08
- Method: mutate one schema/consistency boundary at a time in a temporary copy of the officially accepted A files and run the complete evaluator.
- Access/occupancy results: duplicate activity-week, invalid chronological sequence, missing footprint row, duplicate footprint row, extra footprint row, and empty group label all emit their intended hard diagnostic.
- RESULTS results: missing contract, false date/overrun, scenario mismatch, and duplicate contract all emit their intended hard diagnostic. The evaluator derives score/completion from the schedule and does not trust submitted summary values.
- Integrity: tests match rule-specific messages, preventing a different incidental violation from masquerading as coverage. The protected source is unchanged.
- Regression status: all 113 tests pass.
- Official protection: no portal interaction or attempt was used.

### E139: Week-local screening preserves a 360-activity replay

- Timestamp: 2026-09-19 10:31:32 +08
- Frozen-before-change fixture: `independent_scaled_m40`, dataset hash `52caa8f38fc6ee7851fbe038ca6d0e3e8dd40a3b5deabfcbadb2492803fda4f2`, with 360 activities, 320 contracts, 2,236 locations, 640 oracle access rows, and 2,240 oracle occupancy rows. The oracle is hard-feasible at A=`280.0`.
- Fixed policy: seed 1, one worker, one two-second heuristic attempt, one-second local repair, one three-second fallback, two-second verification, 500 closure rounds, production-C enabled.
- Baseline: A=`280.0` in 110.705 seconds, B=`400.0` in 118.942, C=`280.0` in 232.015; all succeed with zero strict conflicts.
- Diagnosis: solver telemetry consumed only about 0.6–1.6 seconds per solve. Structural-hint construction repeatedly screened the complete growing multiweek schedule even though closure conflicts occur within one week.
- Correction: maintain provisional access and occupancy indexes by week and screen the complete affected-week state for each new candidate. Existing accepted weeks remain unchanged and already clean.
- Replay: A=`280.0` in 15.140 seconds, B=`400.0` in 15.162, C=`280.0` in 39.090. Every score, selected stage, strict-conflict count, and submission hash is identical to baseline; aggregate elapsed time falls 461.662→69.392 seconds, or 6.65×.
- Regression and boundary: the stored before/after comparison re-evaluates all optimized outputs with both scorers and requires at least 5× recorded improvement per scenario. All 114 tests and all 30 local readiness checks pass. This is one local seed and does not establish universal runtime behavior.
- Official protection: no portal interaction or attempt was used.

### E140: Incremental closure decisions match under full and week-local screening

- Timestamp: 2026-09-19 10:34:39 +08
- Source: all 192 activity-week occurrences in the preserved failed A-001 artifact, whose conflicts are already independently pinned.
- Protocol: replay forward, reverse, and SHA-256-derived occurrence orders under standard and strict buffer-overlap policies. After each candidate, compare complete accumulated screening with screening of every accumulated row in only the candidate week; accept only conflict-free candidates.
- Result: 1,152/1,152 conflict tuples match. Standard replays reject 4, 6, and 6 candidates; strict replays reject 5, 6, and 6. This includes both clean and conflicting branches while preserving the clean-provisional invariant required by structural-hint construction.
- Regression status: all 115 tests pass in 16.965 seconds.
- Boundary: this proves equivalence of the implemented screen on these incremental states, not hidden-validator semantics or universal runtime gains.
- Official protection: no portal interaction or attempt was used.

### E141: A second 360-activity replay is byte-reproducible

- Timestamp: 2026-09-19 10:37:00 +08
- Protocol: repeat the exact E139 one-worker policy with solver seed 2 before any footprint-cache change.
- Result: A/B/C again succeed at `280/400/280`, zero strict conflicts, the same selected stages, and the exact E139 hashes. Recorded times are 14.776, 14.873, and 38.586 seconds versus 15.140, 15.162, and 39.090.
- Interpretation: the second run supports timing stability and deterministic construction under this complete-hint, one-worker regime. Identical hashes mean it is not independent schedule diversity and must not be presented as such.
- Official protection: no portal interaction or attempt was used.

### E142: Per-instance footprint caching removes the new dominant bottleneck

- Timestamp: 2026-09-19 10:39:35 +08
- Pre-change profile: a 360-activity A run made 21,450,928 calls in 23.306 profiled seconds. `activity_footprint` was invoked 544,500 times and consumed 18.875 cumulative seconds; CP-SAT consumed 1.164.
- Change: memoize the pure footprint result per loaded instance and frozen `Activity`. The cache is private, excluded from instance equality, and initialized fresh on construction or `dataclasses.replace`.
- Post-change profile: identical A score, stage, hash, and strict status in 4.488 profiled seconds with 8,175,832 calls. `activity_footprint` is absent from the top 25 cumulative sites; CP-SAT remains 1.163 seconds.
- Full replay: A=`280.0` in 3.014 seconds, B=`400.0` in 1.308, C=`280.0` in 11.218. Against E141 this is 4.90×, 11.37×, and 3.44× faster; aggregate time falls 68.235→15.540 seconds. Against the original E139 pre-week-local baseline, aggregate improvement is 29.7×.
- Integrity gates: every output hash and stage matches E139/E141, both scorers agree, strict conflicts are zero, all 115 tests pass, and all 30 local readiness checks remain true.
- Boundary: local deterministic timing is not an official score or universal performance guarantee; mutable in-place edits to a loaded instance are outside the solver's data contract.
- Official protection: no portal interaction or attempt was used.

### E143: The 720-activity holdout succeeds but trips the direct-A budget

- Timestamp: 2026-09-19 10:42:15 +08
- Frozen-before-solve input: `independent_scaled_m80`, dataset hash `d006732ff7e879edcbaace50b04058da23045197380ed86ff2b0d031cc4b6fbf`, with 720 activities, 640 contracts, and 4,476 locations. Its separately generated A oracle has 1,280 access rows, 4,480 occupancy rows, zero hard violations, and dual-scored A=`560.0`.
- Policy: identical to E139/E141/E142: one worker, seed 1, 2/1/3/2-second heuristic/repair/fallback/verification budgets, one attempt each, 500 closure rounds, production C.
- Results: A=`560.0` in 13.395 seconds, B=`800.0` in 4.782, C=`560.0` in 27.517; 3/3 succeed, both scorers agree, and strict conflicts are zero.
- Stage evidence: A's complete-hint direct model has 148,402 variables and 344,881 constraints but returns `UNKNOWN` after 2.048 seconds. The unrestricted fallback then returns `OPTIMAL` at `560.0` in 2.905 seconds; verification preserves it. B verification reaches matching score/bound `800.0`. C safely selects its A-derived fallback at `560.0`.
- Scaling boundary: compared with the cached 360-activity replay, elapsed time grows 4.44× for A, 3.65× for B, 2.45× for C, and 2.94× overall when activities double. This modular fixture does not cover dense cross-module coupling.
- Regression status: all 116 tests pass in 13.348 seconds, including independent re-evaluation of the oracle and all three generated submissions.
- Official protection: no portal interaction or attempt was used.

### E144: Checked complete-hint promotion recovers the dense scale failure

- Timestamp: 2026-09-19 10:48:00 +08
- Frozen failure: `independent_dense_m20`, hash `51177bef3a23a307c8710e1dfbb5452a9e2f867d2f773e5fa043e712cb15dacf`, has 164 activities sharing two bottleneck corridors over 47 weeks. Its independent A oracle is hard-feasible and dual-scored at `0.0`. Under the unchanged fixed policy, A/B/C failed 0/3 after 5.906/14.036/12.318 seconds; every direct and fallback stage returned `UNKNOWN` and no output was promoted.
- Diagnosis: every direct stage reported a complete 164-activity structural hint. The failure was delivery: CP-SAT did not emit the already constructed assignment within the short budget.
- Correction: canonicalize each complete hint's sequences, serialize it in a temporary directory, run the full evaluator and selected closure screen, and install it only as a checked incumbent. CP-SAT then searches strictly below its measured score.
- Replay: A/B/C succeed 3/3 at `0.0`, zero strict conflicts, in 1.070/12.321/2.596 seconds. A and B validate their complete hint in about 0.03 seconds; later sound verification reports matching zero bounds. Every final is independently scored.
- Anti-copy evidence: candidate access sets differ from the independently generated oracle by swapping `DXLIVE` and `DYLIVE` between weeks 41 and 42 while retaining score zero.
- Fault injection: delete one occupancy row only during temporary structural-candidate serialization, use a near-zero solve budget, and verify `complete=true`, `checked=true`, `feasible=false`, score absent, and no submission CSV emitted.
- Integrity gates: all 118 tests pass in 9.371 seconds and all 30 local readiness checks remain true. The original 0/3 run and input/oracle were committed before implementation.
- Boundary: B's 12.321-second end-to-end time remains unexplained by its 0.033-second hint and 0.460-second verification; profile before optimizing.
- Official protection: no portal interaction or attempt was used.

### E145: Checked zero-floor fast path removes dense verification overhead

- Timestamp: 2026-09-19 10:50:41 +08
- Profile: dense B after E144 makes 19,238,451 calls in 14.095 seconds. Two full flexible-model constructions consume 13.322 seconds; `_add_sample_hints` adds 1,805,398 entries and consumes 3.651 seconds, while both CP-SAT solves total 0.481 seconds.
- Rule: all official primary objective components are nonnegative. A complete hint that passes the evaluator and requested closure screen at exactly `0.0` is globally primary-optimal; only the subordinate row-count tie remains unproved.
- Implementation: perform that complete check before model creation, rewrite the same rows and derived results, and return telemetry with score/bound zero, `primary_score_proven_optimal=true`, zero model variables/constraints/solve rounds, and explicit no-tie-proof scope.
- Replay: A/B/C remain exact hashes `a524ccfd…`, `c6a153f4…`, and `a3cd3733…`, with scores zero and no strict conflicts. Runtime falls 1.070→0.580, 12.321→0.679, and 2.596→1.407 seconds; aggregate 15.988→2.666, or 6.00×.
- Integrity gates: all 119 tests pass in 7.513 seconds; the dedicated fast-path test re-runs both scorers and asserts no model was built. All 30 local readiness checks remain true.
- Boundary: positive-score public and synthetic cases cannot enter this path; no official score or artifact changed.
- Official protection: no portal interaction or attempt was used.

### E146: Positive-score scale replays survive checked-hint promotion

- Timestamp: 2026-09-19 10:52:43 +08
- 360 activities: fresh seed 5 returns A=`280.0` in 2.501 seconds, B=`400.0` in 1.414, and C=`280.0` in 10.885. All are dual-scored and strict-clean. A/C use different checked equal-score hashes (`3b9ad8a3…`, `eecc5dbc…`); B preserves `70fbd577…`.
- 720 activities: fresh seed 2 returns A=`560.0` in 9.686 seconds, B=`800.0` in 5.214, and C=`560.0` in 24.715, again dual-scored and strict-clean. A now selects `heuristic_incumbent` from its checked complete constructor instead of the historical `bridge_safe_fallback`; B remains byte-identical, while A/C hashes change.
- Integrity interpretation: score, feasibility, and strict-policy results are preserved; byte identity is not claimed across a deliberate incumbent-source change. Protected official A/B/C bytes remain untouched.
- Regression status: all 119 tests pass in 7.634 seconds and re-evaluate the six fresh outputs.
- Official protection: no portal interaction or attempt was used.

### E147: Current controller reconstructs the public optima without displacing cleaner artifacts

- Timestamp: 2026-09-19 10:56:07 +08.
- Policy: public input, seed 6, eight workers, 30/10/30/10-second heuristic/repair/fallback/verification limits, one attempt per stage, production C, and the published-rule closure policy.
- Result: A=`137.9` in 32.666 seconds, B=`30.0` in 22.567, and C=`62.7` in 74.875; 3/3 succeed, the full evaluator has zero hard violations, and both scorers reproduce every score.
- Selection: A uses `heuristic_incumbent`, B `strict_score_preserving_hedge`, and C `scenario_c_heuristic`. New hashes are `e952613a…`, `6dc4db90…`, and `49e9d875…`.
- Adversarial boundary: the separate strict-buffer audit reports A=`4`, B=`0`, C=`9` conflicts. This optional hedge is not a confirmed official hard rule, but the protected official files are equal-score, strict-clean, and official-validator-confirmed. The new files are therefore retained only as current-code replay evidence.
- Integrity gates: all 120 tests pass in 7.880 seconds, including dual rescoring, dataset-hash equality, exact score equality, and explicit non-replacement assertions.
- Official protection: no portal interaction or attempt was used; remaining quotas stay A=`3/5`, B=`4/5`, C=`4/5`.

### E148: Doubled dense holdout succeeds and exposes model-assembly overhead

- Timestamp: 2026-09-19 11:01:53 +08.
- Frozen-before-solve input: `independent_dense_m40`, dataset hash `b5e18c49…`, has 324 activities, 324 contracts, 44 locations, and an 87-week horizon. Its independent oracle has 644 access and 1,932 occupancy rows, is hard-feasible, and is dual-scored A=`0.0`.
- Policy and result: the unchanged one-worker 2/1/3/2-second fixed policy succeeds A/B/C at `0.0` in 2.363/2.774/5.478 seconds; selected stages are heuristic/heuristic/C-fallback. Every output is dual-scored and strict-clean.
- Anti-copy check: all three candidates swap the two Live activities' weeks 81/82 relative to the independent oracle. The solver did not receive the oracle directory.
- Scale profile: direct A constructs 284,048 variables and 457,994 constraints. In a fresh profile, two flexible-solver calls consume 2.900 of 3.479 seconds; CP-SAT itself takes 0.130 seconds, while 225,330 hint additions consume 0.496 seconds. Full model construction is now the dominant avoidable cost after the constructor has already produced a checked score-zero candidate.
- Integrity gates: the dedicated regression and all 121 tests pass in 8.736 seconds. The fixture and oracle were committed before the first solve.
- Boundary: repeated dense structure and a zero lower bound remain easier than unknown coupled positive-score instances. No official artifact or score changed, and no portal attempt was used.

### E149: Pre-model structural validation removes zero-floor model assembly

- Timestamp: 2026-09-19 11:10:59 +08.
- Change: extract the deterministic structural constructor from CP-SAT. When it is complete, serialize and run the full evaluator and requested closure policy before building any model. Return early only at exact score zero; otherwise reuse the same rows as ordinary model hints.
- Dense results: the 164-activity A/B/C replay preserves hashes `a524ccfd…`/`c6a153f4…`/`a3cd3733…` while improving 0.580/0.679/1.407 to 0.084/0.090/0.224 seconds. The 324-activity replay preserves `1dd716d0…`/`48cd2b2a…`/`3a574f82…` while improving 2.363/2.774/5.478 to 0.199/0.220/0.536.
- Rejected intermediate: a first implementation duplicated constructor work before the unchanged model path. The 720-activity positive replay remained correct but slowed to 11.648/6.802/28.860 seconds. The duplication was removed; this run remains retained as contradictory performance evidence.
- Positive-score guard: post-refactor 360-activity scores/hashes remain `280/400/280` and 720-activity scores/hashes remain `560/800/560`, all strict-clean. These cases cannot take the zero-floor return and continue through the full solver.
- Fault injection: deleting occupancy prevents promotion; a synthetic strict-only conflict under strict mode forces model construction. A separate test patches model construction to raise and proves a valid strict-clean zero candidate returns first with zero variables, constraints, or solve rounds.
- Integrity gates: all 123 tests pass in 7.932 seconds and all 30 final-readiness checks remain true. No protected artifact changed and no portal attempt was used.
