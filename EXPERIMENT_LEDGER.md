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
