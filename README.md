---
document_id: NH-PS1-KB
version: 0.8.64
last_verified: 2026-09-19
research_status: reconciled
implementation_status: active
official_spec: https://github.com/aochinwen/NebulaX-Hackathon-ProblemStatement/blob/main/PS1/PS1_README.md
---

# Nebula Hack PS1: Team Knowledge Base

This document records the team’s verified clarifications, interpretations, and decisions for Problem Statement 1. It complements the [official PS1 specification](https://github.com/aochinwen/NebulaX-Hackathon-ProblemStatement/blob/main/PS1/PS1_README.md); it does not repeat its rules, schemas, formulas, or deliverables.

If the two conflict, the current official specification and reference validator govern. Record the conflict before changing implementation.

<a id="index"></a>

## Index

| Topic | Section |
|---|---|
| What problem we are solving | [`CORE`](#core) |
| Real operational conflict | [`OPERATIONS`](#operations) |
| Users and product role | [`USERS`](#users) |
| Organiser Q&A clarifications | [`QNA`](#qna) |
| Meaning of “same data” | [`DATA`](#data) |
| Optimisation, AI, and human roles | [`SYSTEM`](#system) |
| Product direction | [`PRODUCT`](#product) |
| Algorithm and constraint model | [`ALGORITHM`](#algorithm) |
| Score improvement loop | [`IMPROVEMENT`](#improvement) |
| Build order | [`BUILD`](#build) |
| Judging and evidence | [`JUDGING`](#judging) |
| Demo narrative | [`DEMO`](#demo) |
| Decisions | [`DECISIONS`](#decisions) |
| Open questions | [`OPEN`](#open) |
| Sources and transcription quality | [`SOURCES`](#sources) |
| Maintenance rules | [`MAINTENANCE`](#maintenance) |

### Confidence labels

- **Official:** stated in the current specification or demonstrated by the current validator.
- **Q&A:** clearly stated in the organiser conversation and not contradicted by the official source.
- **Decision:** chosen by the team.
- **Derived:** a reasoned consequence, not a direct organiser statement.
- **Open:** requires evidence or a team decision.

<a id="core"></a>

## 1. Core understanding

PS1 is a railway track-access and possession-scheduling problem. Maintenance and project programmes compete for limited nighttime access to railway locations. The system must produce a complete, safe, validator-compliant schedule and explain significant trade-offs to a works controller.

The activities’ required corridors are inputs. Optimisation selects timing and compatible co-sharing; it does not choose alternative railway routes.

The mandatory scope is scheduling for the three official scenarios. Disruption-driven replanning is a bonus.

<a id="operations"></a>

## 2. Real operational conflict

The core difficulty is not entering work into a calendar. It is prioritising several legitimate claims on the same access window:

- Operator maintenance may be driven by defects, inspections, safety, or asset condition.
- LTA and project work may be driven by renewal programmes, dependencies, contract milestones, and completion dates.
- Contractors need predictable access to deliver committed work.
- Physical and possession rules make many combinations illegal.
- Late changes can invalidate an otherwise optimal plan.

The planner must decide:

> When maintenance, project delivery, safety, capacity, and contractual considerations collide, which work receives access, which work moves, and how can that decision be defended?

### Recurring conflict types

| Conflict | Required answer |
|---|---|
| Competing access | Which activity receives the constrained location or possession opportunity? |
| Safety or compatibility | Why can apparently efficient work not coexist? |
| Programme dependency | What is blocked, and what is the downstream effect? |
| Schedule versus access cost | Which trade-off is correct for the active scenario? |
| Unexpected change | What breaks, what can remain unchanged, and what is the best recovery? |

The organiser’s concrete disruption example was a thunderstorm preventing planned work on an exposed viaduct. This is the strongest evidence for a replanning bonus.

<a id="users"></a>

## 3. Users and product role

The intended users are railway access planners and works controllers within or supporting:

- Public Transport Operators (PTOs)
- Operators such as SMRT and SBS Transit
- LTA and project teams

Contractors are affected stakeholders and potential consumers of allocation explanations. Judges evaluate the product but are not its operational persona.

The product should help a controller:

1. Generate and validate a schedule.
2. See conflicts, bottlenecks, delays, and displaced work.
3. Understand why an allocation was made.
4. Compare the official scenarios without mixing their policies.
5. Export the required files.
6. Optionally assess and recover from a disruption.

The interface should use professional operational language while remaining usable by someone who did not build the solver.

<a id="qna"></a>

## 4. Organiser Q&A clarifications

| ID | Clarification | Consequence |
|---|---|---|
| `Q1` | The base task is to solve the official scheduling problem for all three scenarios. Replanning is bonus innovation. | Finish static scheduling and validation before disruption recovery. |
| `Q2` | Likely users include PTOs, SMRT, SBS Transit, LTA, and project stakeholders who need a holistic schedule view. | Build decision support for planners and controllers, not a commuter product. |
| `Q3` | Contractor negotiation, depot or engineering-train logistics, digital twin, and similar items are examples, not required subproblems. | Choose a focused bonus instead of covering every example. |
| `Q4` | Contractor negotiation support means giving an operator or authority better evidence or leverage in discussions with contractors. It is not central to the core solver. | Treat it as an optional use of schedule evidence. |
| `Q5` | Digital twin means modelling and resolving clashes before physical execution: “design twice, build once.” | A truthful what-if and conflict sandbox is sufficient; 3D/BIM is not implied. |
| `Q6` | Maintenance and project work have different constraints and considerations. The practical challenge is prioritising them when access conflicts. | Explanations must expose the binding reason and displaced alternative. |
| `Q7` | A perfect plan can fail after unexpected change; thunderstorm disruption of viaduct work was the example. | Prefer impact assessment and minimal-change replanning as the first bonus. |
| `Q8` | The organiser said judging would use the same validator available to participants. | Validator results are the shared evidence boundary. |
| `Q9` | No cross-problem-statement prize formula was provided. The organiser redirected the team to the published rubric. | Do not optimise for an invented cross-track threshold. |

<a id="data"></a>

## 5. Meaning of “same data”

The Q&A contains a brief “same” after a question about final data. The team interprets this as the same **input contract**: schemas, semantics, rule system, and validator expectations. It does not mean identical public rows.

This interpretation is required because the current official specification describes hidden or undisclosed instances.

### Engineering consequence

The application must:

- Parse any valid instance following the official contract.
- Derive topology, horizon, demand, and constraints from uploaded data.
- Avoid hard-coded IDs, row counts, dates, names, or public-sample answers.
- Report malformed inputs clearly.
- Remain reproducible enough to diagnose hidden-instance failures.

<a id="system"></a>

## 6. Optimisation, AI, and human roles

| Layer | Responsibility |
|---|---|
| Constraint or optimisation engine | Feasibility, complete scheduling, scenario objectives, and reproducible output. |
| Reference validator | Independent evidence of compliance and score. |
| AI assistance | Evidence-grounded explanations, questions over the schedule, impact summaries, and comparison of solver-generated alternatives. |
| Human controller | Final operational judgment and acceptance of trade-offs. |

An LLM must not invent the possession schedule or claim feasibility. Any explanation presented as fact must trace to input data, solver state, or validator output.

Useful AI functions include:

- Explain why an activity moved.
- Identify the binding rule or bottleneck.
- Summarise downstream effects of lost access.
- Produce a handover or contractor discussion brief.
- Compare validated alternatives.

<a id="product"></a>

## 7. Product direction

### Product thesis

> An explainable, human-supervised railway access decision-support system that converts competing programmes into validated schedules and makes the consequences of each allocation understandable.

### Four questions the product must answer

1. Is this schedule feasible?
2. Why did this allocation or delay occur?
3. Where is the plan congested or fragile?
4. What changes when an access opportunity is lost?

### Product principles

- Feasibility before novelty.
- Complete workload before visual polish.
- Validator evidence before claims.
- Explanation alongside the schedule.
- General input handling rather than sample-specific logic.
- One strong bonus after the core works.

### Preferred bonus

Impact assessment and minimal-change replanning after a late disruption.

A credible implementation should show:

1. A validated baseline.
2. A specific disruption.
3. Direct and downstream effects.
4. A revised validated schedule.
5. Which work changed and which remained stable.
6. Why the recovery was selected.

### Digital-twin interpretation

If used, “digital twin” means a what-if planning layer over real solver state: network and timeline views, possession overlays, conflicts, capacity, and disruption comparison. Do not imply physical simulation or BIM integration unless implemented.

<a id="algorithm"></a>

## 8. Algorithm and constraint model

### Solver choice

Use **OR-Tools CP-SAT** as the primary optimiser.

The problem is discrete and dominated by assignment, precedence, packing, conditional compatibility, and cardinality constraints. CP-SAT supports these directly, returns feasible incumbents and bounds under a time limit, accepts hints, and contains portfolio and large-neighbourhood-search machinery.

This is a benchmarked choice, not a permanent assumption. Keep a small MILP comparison model and consider weighted MaxSAT only if the Boolean model scales better on generated hidden-style instances. Recent possession research has found CP, structure-aware ALNS, and MaxSAT effective in different settings; no solver family dominates every scale.

### Precomputed structures

Before solving, derive:

- Week indices for every date.
- Ordered sectors and platforms for every activity corridor.
- Each access occurrence’s physical work footprint.
- Buffer and mirrored closure footprints by nature of work.
- Pairwise co-sharing and closure compatibility.
- Predecessor graph, cycle check, earliest feasible week, and critical-chain slack.
- Location-week capacity and contract/type weekly limits.

For a corridor containing `n` tunnel sectors, occupancy contains those `n` sectors plus `n+1` platforms. This expansion reproduces the public sample’s 928 occupancy rows exactly.

### Primary formulation

| Variable | Meaning |
|---|---|
| `access[a,w]` | Activity `a` has one access in week `w`. |
| `eclo[a,w]` | That access uses ECLO; it implies `access[a,w]`. |
| `night[a,w,n]` | The access uses contract-local `access_night` index `n`. |
| `member[a,w,l,g]` | The activity belongs to local possession group `g` at occupied location `l`. Groups can differ by location. |
| `used[w,l,g]` | Local group `g` exists and counts against location supply. |
| `completion[a/c]` | Last scheduled week for an activity or contract. |
| `overrun[c]` | Contract completion beyond its planned completion date; the validator charges that delay through every activity-priority nudge in the contract. |
| `excess[l,w]` | Possession groups above nominal location capacity. |
| `eclo_window[line]` | Scenario C’s two-week ECLO window position. |

Use half-units for workload: `2 × sum(access) + sum(eclo) >= 2 × total_accesses`. The independent checker must retain the official `>=` rule. The optimiser should remove dominated extra rows with a post-score row-count tie-break rather than incorrectly replacing the rule with equality.

Local group membership must be indexed by location. The public sample contains activity pairs that share at one common location and use different groups at another in the same week, so one global group per activity-week is invalid.

Start with direct local slots and symmetry breaking:

- Use consecutive labels only: `used[g+1] <= used[g]`.
- Canonically renumber labels in exported files.
- Let CP-SAT detect remaining matrix symmetry; benchmark stronger value-precedence constraints before retaining them.
- Restrict access variables to eligible weeks and group variables to the activity footprint.

Do not pre-enumerate every legal batch initially. On the public instance, week-filtered batch enumeration creates about 72,683 candidates, while direct local slots require under 16,000 membership booleans in the largest scenario. Retain batch columns as a fallback for weak-propagation hotspots.

### Hard-constraint encoding

| Area | Encoding requirement |
|---|---|
| Workload | Schedule every activity to at least its required half-unit workload; allow at most one activity access per week. |
| Sequence | Derive consecutive `access_seq` values deterministically after sorting selected weeks. |
| Start and horizon | No occurrence precedes the planned start week or exceeds the declared horizon. |
| Predecessor | The successor’s first week is strictly later than the predecessor’s final week. |
| Occupancy | Every scheduled occurrence occupies all tunnel and platform locations in its corridor. |
| Closures | Apply same-bound buffers, Live opposite-bound mirroring, and Live cross-line interchange effects. |
| Possession mix | Each occupied location/week/group is exactly one PM, one PC with at most three C, or at most four C. |
| Co-sharing | Closure exemption applies only within the same location, week, and group. |
| Capacity | Count occupied groups per location/week, then apply the scenario’s hard or soft capacity policy. |
| Weekly allocation | Distinct local night indices stay within the contract/type weekly allowance. |
| Workfront | Activities sharing a contract/type/night stay within the workfront count. |
| ECLO | Forbidden in A; permitted in B; restricted to each line’s continuous two-week window in C. Cross-line Live ECLO must fit both windows. |
| Results | Contract completion is the latest activity finish; overrun is measured against planned completion. |

Official run A-001 established two missing closure details: a possession closure includes its occupied work footprint, and a Live interchange closure plus its configured buffer propagates onto the other line. Co-sharing remains transitive through same-location/group bridges. The corrected checker reproduced all five A-001 violations exactly; A-002 and the first B/C runs then passed officially. Protected outputs also pass the stricter buffer-to-buffer screen.

### Scenario objectives

Optimise the validator’s exact penalty, after achieving feasibility:

| Scenario | Hard policy | Primary objective |
|---|---|---|
| A | Nominal capacity; no ECLO | Priority-weighted activity overrun |
| B | No planned-completion overrun | `7 × excess access-nights + 5 × ECLO nights` |
| C | At most one excess group per location/week; two-week ECLO windows | A’s overrun term plus B’s excess and ECLO terms |

The prose ordering of ECLO versus excess access can disagree with the arithmetic because ECLO yields only half an additional work unit per access. The optimiser must compare complete counterfactual schedules using the formula, not encode a fixed “ECLO first” heuristic. Confirm the validator’s implementation before freezing this logic.

When all scenarios use the same input, solve A first and use its validated schedule as C’s guaranteed hard-feasible incumbent. Use targeted compression of A’s late activities to seed B. Do not transfer B directly into C because B can violate C’s excess and ECLO-window limits.

### Symmetry control and scale

Possession groups and local nights are interchangeable labels. Break symmetry by using the lowest available label first and ordering equivalent groups. Build conflict cliques and aggregate possession lower bounds instead of relying only on pairwise implications. If one monolithic model stalls, decompose week assignment from local packing, but never accept a master incumbent until detailed packing passes the independent checker.

### Public-instance benchmark

The supplied instance contains:

| Measure | Value |
|---|---:|
| Horizon | 30 weeks |
| Contracts | 14 |
| Activities | 54 |
| Access workload | 192 standard-night units |
| Locations | 76 |
| Predecessor links | 6 |
| Access-week Boolean upper bound after planned starts | 994 |
| Activity-location-week presences | 4,908 |
| Direct group-membership Boolean upper bound | 10,966 in A; 15,874 in C |

The tightest raw tunnel demand is around Beta eastbound `H01–H02`, `H02–S15`, and `S15–S16`. Raw demand does not account for timing or co-sharing, so use it to seed search and diagnostics, not as a feasibility conclusion.

The supplied Scenario A schedule is a feasible regression fixture with 192 accesses and no ECLO. Under the validator-confirmed contract-completion aggregation, its score is `137.9`.

Resource-independent workload timing plus the confirmed closure interaction give exact public-instance lower bounds:

| Scenario | Lower bound | Cause |
|---|---:|---|
| A | `137.9` | C006 contributes `85.4`, C010 `45.5`, and the unavoidable A036/A075 closure trade-off adds C014 `7.0`. |
| B | `30.0` | Six ECLO nights are necessary to meet every hard date; the full model proves no lower score. |
| C | `62.7` | Two ECLO nights each for A036/A059 cost `20.0`; A036 still forces seven days of C006 delay worth `42.7`. |

Each protected public answer matches its bound and has passed the official validator.

### Current executable evidence

- The schema-driven footprint expander reproduces all 928 public activity-location-week occupancy keys without activity-specific rules.
- **A-002:** officially feasible at `137.9`; 28 overrun days across three contracts, zero excess, zero ECLO. It reaches the structural lower bound.
- **B-001:** officially feasible at `30.0`; zero overrun/excess and six ECLO nights. The full bridge-safe model proves `<30.0` infeasible.
- **C-001:** officially feasible at `62.7`; seven overrun days in C006, zero excess, four ECLO nights. The full model and workload argument prove the same lower bound.
- The organizer's upstream `main` was rechecked at 2026-09-19 10:03 +08 and remains commit `966c976`. All 14 public PS1 files, excluding `.DS_Store`, are byte-identical to the files fetched directly from that exact commit.
- Combined public penalty is `230.6`. Lower is better; the portal does not publish a cross-scenario combined metric.
- The current controller reconstructed all three optimum scores from scratch in 15/15 fixed-policy runs across five seeds: A 15.425–25.742 seconds, B 9.902–23.039, and production C 17.360–37.354. Every schedule hash differed and only local validation applies, so the official ZIPs remain the release artifacts.
- Both local scorers reproduce every official score exactly. The earlier activity-completion proxy was rejected after A-002 exposed the correct contract-completion aggregation.
- The corrected closure checker reproduces the five A-001 violations exactly and accepts all three official incumbents under both standard and strict buffer screens.
- All 115 regressions pass. They pin official scores/hashes, A-001 violations, contract aggregation, arbitrary-line topology-derived interchange crossover, workload, packing, ECLO windows, pruning, incumbent protection, full heuristic-portfolio execution, guarded B/C cost-contributor repair, Scenario C delay-only, alternating contract/precedence/footprint dependency repairs, both production integrations of the terminal precedence revisit, two-tier repair escalation, its five-seed irregular matrix, three identifier-permuted irregular recoveries with explicit no-proof and strict-conflict boundaries, equal-score strict-hedge promotion, higher-score hedge rejection, selected-artifact conflict reporting, exact no-op behavior on all official incumbents, conditional-bound scope telemetry, independent C construction behind a protected A fallback, complete-versus-partial structural-hint policy, independently constructed two- and three-line oracles, dense no-hint construction, guarded dense C fallback, additive, coupled, irregular, and cross-module nonzero trade-offs, checked idle-week and ECLO compaction with incumbent-state preservation, duplicate elimination, exact score ordering including zero-supply excess, multi-activity contract aggregation, exhaustive legal-mix and scenario-capacity equivalence, malformed-submission rejection, repeated independent-line gains, exhaustive ECLO-window filter falsification, access-length generalization through seven rows, equal-score normalization composition, internal-gap tie handling, constrained exhaustive normalization comparisons, confirmed Scenario C prediction arithmetic, core constraint boundary mutations, final-selection post-processing in both production controllers, exact official-C no-op behavior, retained-corpus hash preservation, final archive byte integrity, aggregate pre-upload readiness, the exact-output 360-activity scale replay, and incremental full-versus-week-local closure equivalence, plus recomputation of the benchmark matrix.
- On a frozen 360-activity, 320-contract independent fixture, one-worker A/B/C construction preserves the exact scores, stages, hashes, and zero strict conflicts after week-local structural-hint screening. Recorded runtime falls from 110.705/118.942/232.015 seconds to 15.140/15.162/39.090 seconds, a 5.94–7.84× speed-up. This is one local seed, not an official or general runtime guarantee.
- A second replay before footprint caching reproduces the same hashes in 14.776/14.873/38.586 seconds. Caching immutable activity footprints per loaded instance then preserves the same A/B/C outputs in 3.014/1.308/11.218 seconds, another 3.44–11.37× improvement. Profiling reduces 544,500 footprint calls and 18.875 cumulative seconds to below the top-25 call sites; the original-to-current aggregate replay improves 29.7×. These are local timings, not score changes.
- On the altered-capacity/priority fixture, no-hint standard construction reaches A=`4599.7` with a 0.87% bound gap, and proves B=`30.0` and C=`59.9`. The stricter buffer-to-buffer hedge fails to construct B after 240 seconds while the validator-confirmed standard rule solves it in 18.7 seconds; strict overlap is therefore audit-only on unseen inputs.
- On a separately generated two-line topology with novel identifiers and no public-submission input, the staged solver reconstructs and proves A=`7.0`, B=`10.0`, and C=`7.0`. The independent oracle is generated with separate footprint/result logic; B pays two necessary ECLO nights while C rationally accepts seven points of delay instead.
- Experimental `solve-flexible-relaxation` flags expose per-solve deterministic time and OR-Tools interleaved search. Two structural-B repetitions were byte-identical at `30.0`, but took 98.8–104.9 seconds versus 16.6–21.2 seconds for successful ordinary portfolio seeds. Keep this as an audit mode, not the default score path.
- [`BENCHMARK_MATRIX.json`](BENCHMARK_MATRIX.json) is the machine-readable cross-regime evidence table. All 46 retained A/B/C cases are hard-feasible, dual-scored, and match recorded proof bounds; 40 are full-instance proofs, six are frozen-neighborhood proofs, and only the three public rows are reference-validator-confirmed. A three-line fixture and three adjacent-bridge fixtures test topology-derived Live crossover without public identifiers. The compact congested case proves A=`700.0`, B=`10.0`, C=`10.0`; the eight-job scaled case proves A=`273.0`, B=`80.0`, and enumerated C=`262.0` after a generic checked ECLO compaction closes the blind controller's C=`273.0` gap. The largest independent fixture has 180 activities; five one-worker seeds per scenario all reached the same proved A=`140.0`, B=`200.0`, and C=`140.0` scores under a two-second heuristic budget. A compact 84-activity shared-bottleneck fixture initially failed 15/15 runs; generic legal-batch and closure-screened chain hints then reached proved score `0.0` in all 15 runs without oracle input. A 106-activity held-out dense variant first exposed multi-contract and direct-C gaps; after preserving that blind result, generic workfront-aware chain placement plus the intended A-as-C controller reached proved `0.0` in all 15 production-path runs. A pre-generated additive trade-off reached A=`7.0`, B=`10.0`, C=`7.0` blindly. A coupled follow-up first exposed poor A/C timing and complete B failure; deadline-aware non-binding hints plus a reported ten-second repair budget then reached analytical A=`1820.0`, B=`20.0`, C=`920.0` in all 15 runs. An irregular partial-hint fixture exposed workfront, nondeterminism, and A-seed suppression errors; the corrected eight-worker controller reaches proved B=`30.0` and C=`31.0`. C recovered `31.0` across five seeds with the 30-second production repair budget; the 10-second compressed policy failed at `63.0` on fresh seed 5. A frozen 72-activity cross-module holdout reached and proved C=`76.0` blindly. Four successive alternating dependency holdouts reached C=`0.0` after preserving their narrower conditional-proof failures.
- A production-budget irregular seed-5 replay exercised the guarded-A failure branch end to end. Narrow repair recovered C=`31.0` from C=`63.0`; expanded repair preserved it. Both scorers and both closure screens accept hash `18b6eee516d8239407a52172ae7c5f66bbd0f53bd59a526284bdd22c4079711c`.
- A serial five-seed repair matrix independently repeated the same narrow-then-expanded policy from the checked C=`63.0` incumbent. All five narrow tiers reached C=`31.0`; all expanded tiers retained it; every final was dual-scored and clean under both closure policies. Five distinct hashes show schedule diversity, not one copied answer.
- Generalisation remains the main risk: timed no-hint construction varies across seeds and hidden topology/scale are unknown. No official run is spent on an unvalidated candidate.

The append-only evidence, hashes, parameters, failures, and limitations are in `EXPERIMENT_LEDGER.md`. Executable code is under `src/nebula_ps1`; regression tests are under `tests`.

The protected public answer keys are in `deliverables/public/A`, `B`, and `C`. Each directory contains exactly the three required CSV files. `deliverables/public/MANIFEST.json` pins their official scores, run IDs, and hashes.

Upload-ready copies are generated only in `deliverables/final-submission`. Its manifest proves that every archived member matches the protected official incumbent bytes. Do not use the historical generic ZIPs under `deliverables/validator`: `A.zip` is the failed A-001 artifact, and the unnumbered B/C archives are not the confirmed uploads. Packaging does not authorize or perform a portal submission.

Before any user-authorized upload, run `PYTHONPATH=src .venv/bin/python scripts/audit_final_submission_readiness.py` and require `deliverables/final-submission/READINESS.json` to report `all_ready: true`. The gate also verifies the preserved official-upload archive hashes and proves that their contained CSV bytes equal the final package. This is local verification only and consumes no portal attempt.

<a id="improvement"></a>

## 9. Score improvement loop

### Solve in stages

1. **Feasibility:** ignore soft score and find any complete valid schedule.
2. **Primary score:** optimise the exact scenario objective.
3. **Tie-break:** after fixing the best primary score, minimise unnecessary churn, fragmented work, and arbitrary label use. Tie-breakers must not weaken the official score.

The executable staged path uses the fast direct-component formulation only to generate candidates. It runs every requested heuristic attempt, suppresses those models' bounds, and rejects candidates that fail the full checker or requested strict screen. When complete candidates remain unsafe, the controller ranks them by conflict count and score, derives the best candidate's conflict activities, freezes unaffected access decisions, and tries a bounded bridge-safe local repair. Local failure is inconclusive and falls through to repair-hinted and unhinted broad construction. Every safe candidate is pruned and fully checked before protected bridge-safe improvement. Scenario B then repairs direct ECLO/excess contributors. Scenario C first repairs the narrower neighborhood formed by overdue contracts, ECLO/excess contributors, same-contract activities, precedence components, and footprint competitors. It then runs a separately reported ten-second expansion that revisits precedence after footprint expansion, adds contract peers only for newly reached dependencies, and closes precedence once more around those peers. This preserves the narrow search's measured recovery power while covering three precommitted conditional-proof failures. Unrelated access decisions remain frozen, and failure is inconclusive. Telemetry labels bounds from these repairs as neighborhood-conditional rather than full-instance proofs. Scenario C protects an A-derived fallback but tests its first C construction independently so a feasible, poor A schedule cannot suppress C-specific trade-offs. Checked idle-week normalization may seed repeated ECLO compaction before verification and once more after the final solver/repair/hedge selection. An equal-score normalization is never itself promoted, and only a strictly lower checked final result can replace the incumbent. Audit artifacts stay outside the final three-CSV directory.

The first candidate-generation attempt also receives a deterministic structural hint: interchangeable same-footprint C/PC work is packed into legal possession batches, and remaining singleton predecessor chains are placed backward only when the closure screen stays clean. The hint never constrains the model or establishes feasibility. Incomplete hints are cleared for A but retained for B/C; complete hints remain available in every scenario. Later heuristic attempts remain unhinted to preserve search diversity.

### Initial solution

Construct a warm start using the following signals:

- Earliest feasible week and predecessor criticality.
- Contract priority and activity priority.
- Deadline slack.
- Buffer size and Live/PM restrictiveness.
- Corridor scarcity and hotspot demand.
- PC anchors that can host compatible C work.
- Access demand and workfront limits.

Use the public sample schedule as a regression fixture, not as a template for hidden rows.

### Improvement operators

Run multiple time-bounded CP-SAT searches with different seeds and worker counts. Keep the best independently validated incumbent and its best bound. Use targeted large-neighbourhood search around:

- Late or high-penalty activities.
- Congested location-weeks.
- Predecessor chains.
- Poor PC/C packing.
- Weeks using excess capacity.
- ECLO selections and Scenario C window placement.

Destroy only the affected assignments and repair with the exact model. A hint is only a starting suggestion; it does not require the solver to stay close.

Let the search adapt online. Track each destroy/repair operator’s feasibility result, score gain, bound gain, and deterministic time. Use a simple multi-armed-bandit policy to balance exploration and exploitation within the current instance. Normalise rewards within each scenario, because A, B, and C have different score scales. This is the first self-improvement mechanism; it needs no offline training corpus.

### Validator-guided self-improvement

For every candidate:

1. Run the internal checker.
2. Generate all three output files deterministically.
3. Run the reference validator.
4. Reject any hard violation.
5. Compare score components with the internal calculation.
6. Convert every mismatch into a regression test.
7. Store the best feasible result by dataset hash, scenario, code commit, seed, time limit, score, and validator version.

Prioritise the largest validated penalty contributor when choosing the next neighbourhood. Never modify rules to fit one public result.

### Training decision

Do not train a scheduling model initially. We have one public instance, no representative labelled corpus, and hard constraints that require guarantees.

Self-improvement should first mean:

- Better feasible warm starts.
- CP-SAT portfolio, parameter, seed, and worker-count comparison.
- Validator-driven regression repair.
- Structure-aware large-neighbourhood search with online operator selection.
- Synthetic instances for robustness and performance testing.

A learned heuristic may be considered only after the exact solver and checker are stable and a diverse synthetic corpus exists. Its permissible role is to predict branching order, promising weeks, or neighbourhoods. Every learned proposal must still pass the exact model and validator.

The training gate is representative generalisation: held-out seeds are insufficient. Hold out topology, scale, priority mix, supply pressure, predecessor density, and hotspot concentration. Do not train an end-to-end schedule generator on the single public instance.

### Benchmark protocol

For every formulation or search change, use fixed time budgets and record:

- Internal and reference-validator feasibility.
- Time to first feasible solution.
- Best validated score over time.
- Best bound, optimality gap, and gap integral when available.
- Deterministic time, wall time, worker count, seed, solver version, model size, and peak memory.

Compare medians and tail behaviour across seeds and generated structural regimes. Use the best validated run for submission, but do not choose the method from one lucky seed.

### Verification suite

- One minimal passing and failing case for each hard rule.
- Boundary tests for dates, capacities, workfronts, legal mixes, and ECLO windows.
- Cross-contract predecessor and cycle tests.
- Exact corridor-expansion comparison with the supplied occupancy file.
- Property and metamorphic tests: row order and consistent ID/group renaming must not change results; increased supply cannot invalidate a fixed schedule.
- Differential tests between the internal checker and reference validator.
- Determinism tests for output generation.
- Performance tests at increasing synthetic sizes.

The full controlled validator experiment matrix is preserved in `RESEARCH_LEDGER.md`. Run one semantic question per case so one hard failure cannot mask another.

### Replanning objective

Warm-starting is not minimal-change replanning. For a disruption, use a lexicographic recovery objective:

1. Restore hard feasibility and minimise the official scenario penalty.
2. Minimise the number of moved activity accesses.
3. Minimise total week displacement.
4. Minimise changed ECLO and local-night decisions.
5. Compare possession changes by membership, not arbitrary group-label strings.

<a id="build"></a>

## 10. Build order

| Gate | Required outcome |
|---|---|
| `P0: Semantics` | Parse arbitrary valid input, reproduce all 928 public activity-location-week occupancy keys, build an independent checker and deterministic serializer, and retain explicit tests for every uncertain rule. |
| `P1: Core solver` | Implement week-indexed CP-SAT with location-specific groups for A/B/C; generate complete output without manual editing and preserve incumbent/bound telemetry. |
| `P2: Validator closure` | Run the reference validator, eliminate hard violations, record scores, and preserve regressions. |
| `P3: Score engine` | Establish lower bounds, A-to-C/B warm starts, multi-start LNS, online operator selection, and fair score-versus-time benchmarks. |
| `P4: Controller experience` | Provide upload, solve, inspect, explain, validate, and export in one usable flow. |
| `P5: Replanning bonus` | Apply a disruption, identify impact, produce a lexicographically low-churn recovery, and validate it. |
| `P6: Extensions` | Add natural-language analysis, negotiation briefs, fragility views, or richer simulation only if earlier gates are secure. |

Current gate: P0–P3 are complete for the public instance. All scenarios are officially feasible and match proved lower bounds. Current engineering priority is hidden-instance construction reliability, runtime benchmarking, and the controller experience.

### Required product states

The interface must distinguish:

`input loaded → solving → files generated → validating → feasible/infeasible → exported`

Producing files is not the same as passing validation.

### Explanation structure

For a significant decision, show:

`decision → binding reason → evidence → displaced alternative → consequence`

<a id="judging"></a>

## 11. Judging and evidence

The official judging dimensions are **Problem Fit**, **Technical Execution**, and **Ease of Use**.

| Dimension | Evidence we should present |
|---|---|
| Problem Fit | Correct scenario handling, complete outputs, understandable trade-offs, and a bonus tied to the real disruption problem. |
| Technical Execution | Reference-validator results, hidden-instance-ready ingestion, reproducible solving, and regression tests. |
| Ease of Use | A complete upload-to-export flow, clear schedule inspection, explanations, and honest failure states. |

### Claim boundary

Do not claim that the solver is feasible, hidden-instance-ready, faster, or operationally effective until the corresponding test exists. Public-instance validation proves only that result on that instance.

<a id="demo"></a>

## 12. Demo narrative

### Core

1. Upload an instance that is not hard-coded.
2. Generate one official scenario.
3. Run the reference validator.
4. Inspect a contested location or delayed programme.
5. Explain the trade-off from real evidence.
6. Export the official output files.

### Bonus

1. Begin with a validated baseline.
2. Remove a viaduct access opportunity because of a thunderstorm.
3. Show affected work and downstream risk.
4. Generate a low-churn recovery.
5. Compare changed and unchanged work.
6. Validate the recovered schedule.

Any activity count, score, time saving, or improvement stated in the demo must come from the implemented run.

<a id="decisions"></a>

## 13. Decision register

| ID | Date | Decision |
|---|---|---|
| `D1` | 2026-09-18 | Keep one canonical, complementary knowledge document; the official specification and validator remain authoritative. |
| `D2` | 2026-09-18 | Design for works controllers, operator planners, and LTA/project stakeholders. |
| `D3` | 2026-09-18 | Treat A/B/C scheduling as core and disruption replanning as bonus. |
| `D4` | 2026-09-18 | Interpret “same data” as the same schema, semantics, and validator contract, not identical public rows. |
| `D5` | 2026-09-18 | Use formal optimisation for scheduling; restrict AI to evidence-grounded assistance. |
| `D6` | 2026-09-18 | Use disruption impact assessment and minimal-change replanning as the preferred first bonus. |
| `D7` | 2026-09-18 | Treat digital twin as a truthful what-if and conflict-planning layer, not a required 3D replica. |
| `D8` | 2026-09-18 | Do not describe a generated schedule as feasible until the reference validator passes. |
| `D9` | 2026-09-18 | Keep the repository private during active development unless the team deliberately changes visibility. |
| `D10` | 2026-09-18 | Use OR-Tools CP-SAT as the primary scheduling optimiser. |
| `D11` | 2026-09-18 | Optimise the validator’s exact objective; use prose guidance only as a search hint. |
| `D12` | 2026-09-18 | Use staged feasibility, score optimisation, and tie-breaking rather than one blended objective. |
| `D13` | 2026-09-18 | Use validator-guided regression, multi-start search, and large-neighbourhood search for self-improvement. |
| `D14` | 2026-09-18 | Do not train a scheduling model until the exact solver, checker, and diverse benchmark corpus exist. |
| `D15` | 2026-09-18 | Use week-indexed optional access rows and location-specific possession membership as the first formulation. |
| `D16` | 2026-09-18 | Start with canonical direct group slots; retain set-partitioning columns, MILP, and MaxSAT as measured fallbacks. |
| `D17` | 2026-09-18 | Use an online bandit over structure-aware LNS operators before any offline learned heuristic. |
| `D18` | 2026-09-18 | Use A as C’s warm start on shared inputs and compress A’s late work to seed B. |
| `D19` | 2026-09-18 | Benchmark feasibility and score over time across seeds and structural regimes; never select a method from one final run. |
| `D20` | 2026-09-18 | Define replanning churn explicitly; a solution hint alone is not a stability guarantee. |
| `D21` | 2026-09-19 | Protect A as Scenario C's fallback, but always test an independent C construction and repair checked ECLO/excess contributors before selection. |
| `D22` | 2026-09-19 | Use no remaining official portal attempt unless the user explicitly authorizes that specific validator run. Continue improvement with local checks, independent scoring, and frozen synthetic holdouts. |

<a id="open"></a>

## 14. Open questions

| ID | Priority | Question | Resolution |
|---|---:|---|---|
| `O1` | Resolved | Where is the reference validator? | The authenticated participant portal exposes five runs per scenario; exact results are preserved in `OFFICIAL_VALIDATOR_LEDGER.md`. No local executable was released. Remaining attempts are A=`3/5`, B=`4/5`, C=`4/5`, frozen under `D22`. |
| `O2` | High | What runtime and instance-size limits apply to hidden evaluation? | Find official limits; otherwise benchmark generated scale cases. |
| `O3` | Resolved | How is overrun aggregated? | Contract completion delay is charged through every activity-priority nudge in that contract. A-002, B-001, and C-001 exactly match the corrected scorers. |
| `O5` | Medium | Which controller view is most useful in the short demo? | Decide after real solver conflict data is available. |
| `O7` | Low | What is the final product name? | Decide after the core direction is stable. |
| `O8` | Resolved for public data | What closure model matches the validator? | Transitive possession components, footprint-inclusive closure, and topology-derived cross-line Live buffering reproduce A-001 exactly and pass A-002/B-001/C-001. |
| `O9` | High | Is the declared horizon a validator-enforced hard bound, and what does `access_seq` enforce? | Run `V002` and `V009`. |
| `O10` | High | Are all scenarios evaluated against one shared instance or scenario-specific input rows? | Confirm from the released validator/portal; condition cross-scenario warm starts on shared input hashes. |

<a id="sources"></a>

## 15. Sources and transcription quality

| ID | Source | Use | Limitation |
|---|---|---|---|
| `E1` | [Official PS1 repository](https://github.com/aochinwen/NebulaX-Hackathon-ProblemStatement/tree/main/PS1), locally verified against commit `966c976` | Technical specification and public fixture | Recheck for upstream updates. |
| `E2` | `AUDIO-2026-09-18-19-50-30.m4a`, approximately 10m31s | Organiser intent and clarification | Room audio and overlapping speech reduce verbatim accuracy. |
| `E3` | User-supplied Wispr Flow transcript | Improved recovery of the full conversation | Speaker numbers are inconsistent; several domain terms are mistranscribed. |
| `E4` | Independent local transcription passes | Cross-check of Q&A meaning | One failed middle-section pass was discarded and reprocessed. |
| `E5` | [`RESEARCH_LEDGER.md`](RESEARCH_LEDGER.md), 91 research entries plus failure and validator-test registers | Full paper trail, experiments, alternatives, and limitations | Evidence archive; this README contains the reconciled decisions. |

Combined confidence:

- Substantive meaning: approximately 90–95%.
- Exact wording: approximately 80–85%.
- Speaker labels: unreliable.

Corrections that affect interpretation:

| Transcript | Intended term |
|---|---|
| `LTE` | `LTA` |
| distorted `SBST` | `SBS Transit` |
| `by that` / `VyDAT` | `viaduct` |
| `valid data` | `validator` |
| `README work` | likely `renewal work` |
| `digital prism` | `digital twin` |
| final garbled judging phrase | use the official rubric names |

<a id="maintenance"></a>

## 16. Maintenance protocol

Add information only when it changes understanding, implementation, evidence, or a likely future ambiguity.

For each material update:

1. Identify its confidence label and source.
2. State the consequence, not the full thought process.
3. Update an existing section instead of adding a parallel explanation.
4. Add a decision only when the team commits to a direction.
5. Keep an open question only when resolving it could change the work.
6. Remove stale detail that no longer prevents confusion.

When sources conflict:

1. Prefer the current official specification, then validator behaviour, then current written organiser clarification, then recorded Q&A, then team interpretation.
2. Check whether an update date explains the conflict.
3. Record only the resolution and any ambiguity likely to recur.

### Handoff instruction

> Use this document as the team’s interpretation and decision layer. Use the official PS1 README as the technical specification. Before changing implementation, identify the relevant decision and open question. Do not claim feasibility without validator evidence, and do not convert an inference into an official rule.

## Revision history

| Version | Date | Change |
|---|---|---|
| `0.1.0` | 2026-09-18 | Initial comprehensive draft. |
| `0.2.0` | 2026-09-18 | Removed low-value branches and repetition; retained only actionable knowledge and likely ambiguity guards. |
| `0.3.0` | 2026-09-18 | Added the CP-SAT model, constraint encoding, validator-guided improvement loop, benchmark facts, and training decision. |
| `0.4.0` | 2026-09-18 | Reconciled the research ledger into the formulation, lower bounds, adaptive-search plan, benchmark protocol, validator risks, and revised build order. |
| `0.5.0` | 2026-09-18 | Added executable evidence, the quarantined `25.2` relaxation, the protected `32.2` Scenario A repair, and the remaining validator boundary. |
| `0.6.0` | 2026-09-18 | Added exact B/C objectives, iterative inferred-closure separation, protected A=`32.2`, B=`30.0`, C=`26.1` incumbents, and cross-seed evidence. |
| `0.7.0` | 2026-09-19 | Added strict buffer-overlap hedging, dual-policy release checks, validator-gated pruning, and exact three-file answer-key packaging. |
| `0.8.0` | 2026-09-19 | Added official A/B/C validation, corrected contract-completion scoring and Live cross-line closure, official-score manifests, exact lower bounds, and 39 passing regressions. |
| `0.8.1` | 2026-09-19 | Added full heuristic portfolios, a guarded Scenario B cost-contributor repair, prefix-40 A/B/C proofs, wall-time instability evidence, and 42 passing regressions. |
| `0.8.2` | 2026-09-19 | Added a fully synthetic two-line oracle and no-hint A/B/C proof benchmark, plus explicit separation between independent and public-derived metamorphic evidence. |
| `0.8.3` | 2026-09-19 | Added the reproducible 12-case benchmark matrix, strict-hedge diagnostics, and a regression that recomputes every retained score and feasibility result. |
| `0.8.4` | 2026-09-19 | Added a public-independent 180-activity scale fixture, unfiltered five-seed A/B/C distributions, 15-case proof matrix, and 45 passing regressions. |
| `0.8.5` | 2026-09-19 | Added the dense shared-bottleneck falsification, generic legal-batch and closure-screened chain hints, 18-case proof matrix, and 46 passing regressions. |
| `0.8.6` | 2026-09-19 | Preserved the frozen-hint holdout failure, added workfront-aware multi-contract chains and production-C benchmarking, and expanded to 21 proved cases with 47 regressions. |
| `0.8.7` | 2026-09-19 | Added a pre-generated nonzero dense trade-off, blind 15/15 A/B/C transfer at analytical optima, 24 proof cases, and 48 regressions. |
| `0.8.8` | 2026-09-19 | Preserved the coupled-window blind failure, added deadline-aware structural hints and budget-sensitivity evidence, and expanded to 27 proof cases with 49 regressions. |
| `0.8.9` | 2026-09-19 | Added hint-coverage telemetry, rejected two plausible but harmful fixes, gated incomplete hints by scenario, and validated 15/15 public optimum reconstructions with 51 regressions. |
| `0.8.10` | 2026-09-19 | Added the irregular partial-hint falsification, full-budget UNKNOWN handling, independent Scenario C construction, guarded B/C cost repair, 29 proof cases, and 53 regressions. |
| `0.8.11` | 2026-09-19 | Preserved the seed-3 narrow-neighborhood failure, expanded Scenario C repair through affected footprint competitors without dense or coupled regressions, and added a 54th regression. |
| `0.8.12` | 2026-09-19 | Recorded the one/two/four-worker construction boundary and five-seed irregular C recovery, including the seed-5 ten-second budget failure and existing 30-second production-budget success. |
| `0.8.13` | 2026-09-19 | Added a frozen cross-module workfront holdout, preserved the spatial-only repair failure, expanded Scenario C repair through direct contributors' contract peers, and reached 30 proof cases with 56 regressions. |
| `0.8.14` | 2026-09-19 | Preserved a delay-only empty-neighborhood failure, seeded Scenario C repair from overdue contracts, and added a 57th regression with cross-regime checks. |
| `0.8.15` | 2026-09-19 | Preserved a cross-contract predecessor failure, expanded Scenario C repair through precedence components, and reached 59 regressions without widening existing benchmark neighborhoods. |
| `0.8.16` | 2026-09-19 | Made the scope of frozen-access bounds and optimality claims explicit, documented fixed-point neighborhood growth, and reached 60 regressions. |
| `0.8.17` | 2026-09-19 | Preserved a footprint-introduced dependency failure, added a bounded post-footprint precedence pass, and reached 32 proof cases with 62 regressions. |
| `0.8.18` | 2026-09-19 | Preserved a post-precedence contract failure and a broader-neighborhood recovery regression, then replaced one broad default with a protected narrow-plus-expanded repair portfolio. |
| `0.8.19` | 2026-09-19 | Verified the two-tier controller end to end on irregular seed 5 and normalized repair telemetry across guarded-A success and failure report branches. |
| `0.8.20` | 2026-09-19 | Added a reproducible serial five-seed two-tier repair matrix; all seeds reached the analytical C=`31.0` optimum with distinct checked schedules. |
| `0.8.21` | 2026-09-19 | Preserved a predecessor-of-final-contract-peer failure, added one terminal precedence closure with zero retained-regime growth, and reached 34 proof cases with 67 regressions. |
| `0.8.22` | 2026-09-19 | Pinned the terminal precedence revisit in both Scenario C production controllers, completed fallback prune aliases, and reached 69 regressions. |
| `0.8.23` | 2026-09-19 | Rejected search-weak fixed-point repair, added a residual-frontier audit, and retained a no-oracle identifier-permutation recovery with 70 regressions. |
| `0.8.24` | 2026-09-19 | Extended identifier permutation to three runs, preserved a strict-only conflict, and added a score-preserving final strict hedge with 72 regressions. |
| `0.8.25` | 2026-09-19 | Audited broad hedge runtime, rejected a strict-clean C=`112` candidate behind C=`31`, corrected selected-state reporting, and reached 73 regressions. |
| `0.8.26` | 2026-09-19 | Pinned strict-hedge no-op behavior on all three official incumbents and reached 74 regressions without changing any protected hash. |
| `0.8.27` | 2026-09-19 | Added a public-independent three-line topology, proved A/B/C from scratch, expanded the matrix to 37 cases, and reached 75 regressions. |
| `0.8.28` | 2026-09-19 | Added a frozen two-adjacent-bridge topology, proved A/B/C from scratch, expanded the matrix to 40 cases, and reached 76 regressions. |
| `0.8.29` | 2026-09-19 | Added a precommitted congested two-bridge trade-off, proved its A/B/C optima from scratch, expanded the matrix to 43 cases, and reached 77 regressions. |
| `0.8.30` | 2026-09-19 | Preserved the scaled multi-bridge C failure, added checked single-lane ECLO compaction to both production controllers, proved C=`262.0` by enumeration, expanded the matrix to 46 cases, and reached 81 regressions. |
| `0.8.31` | 2026-09-19 | Corrected non-target ECLO preservation, deduplicated equivalent compaction candidates, replayed the real controller and all retained C cases, and reached 82 regressions. |
| `0.8.32` | 2026-09-19 | Added a 120-job scale audit, nonnegative-floor exit, exhaustive score-prediction check, and exact candidate ordering that preserves C=`262.0` while validating one candidate. |
| `0.8.33` | 2026-09-19 | Falsified exact compaction score ordering against a precommitted multi-activity, mixed-priority contract holdout; all six predictions matched serialized evaluation. |
| `0.8.34` | 2026-09-19 | Repeated checked Scenario C compaction across independent line windows, reducing the frozen two-line case from `23,660` to `18,220`, and froze all remaining portal attempts pending explicit approval. |
| `0.8.35` | 2026-09-19 | Differentially falsified repeated compaction across all 24 two-line activity orders and a cross-line Live case; ranked results matched unfiltered exhaustive search and no filtered candidate was feasible. |
| `0.8.36` | 2026-09-19 | Generalized checked ECLO compaction beyond three-row activities; a precommitted four-access two-line holdout improved from `32,760` to `27,320` with ranked/exhaustive agreement. |
| `0.8.37` | 2026-09-19 | Swept serialized activities from three through seven accesses; ranked and exhaustive compaction matched at every length with dual scoring and zero prediction mismatches. |
| `0.8.38` | 2026-09-19 | Added checked idle-week normalization before ECLO compaction, including an equal-score seed that unlocks a frozen C=`910` schedule to C=`10` without promoting the intermediate. |
| `0.8.39` | 2026-09-19 | Extended checked idle-week normalization to leading empty weeks; a precommitted delayed source now composes from C=`27,300` through `23,660` to strict-clean C=`18,220`. |
| `0.8.40` | 2026-09-19 | Corrected equal-score idle-gap tie ordering after a frozen counterexample; preferring an internal gap unlocks a checked C=`920` result instead of stopping at `1,820`. |
| `0.8.41` | 2026-09-19 | Compared greedy idle normalization plus ECLO against every reachable non-worsening normalization state on 16 controlled schedules; all final scores matched exhaustive composition. |
| `0.8.42` | 2026-09-19 | Added a shared final-selection Scenario C post-processing gate to both controllers; a frozen verification winner now improves from `23,660` to checked `22,760`. |
| `0.8.43` | 2026-09-19 | Audited final post-processing on all 19 retained C incumbents; nine idle candidates were checked, no score/hash changed, and total runtime was 1.21 seconds. |
| `0.8.44` | 2026-09-19 | Added a sound zero-objective floor exit to idle normalization; retained candidate generation falls from nine to three with every score and hash preserved. |
| `0.8.45` | 2026-09-19 | Stress-tested the complete final Scenario C post-processor on 120 activities: zero-score input remains byte-identical, while a reverse-order source improves by `15,530` through one checked candidate. |
| `0.8.46` | 2026-09-19 | Preserved internal-gap tie preference even after a score-prediction mismatch forces exhaustive idle-candidate checking. |
| `0.8.47` | 2026-09-19 | Added a 60-activity, 59-gap scale audit; final checked post-processing lowers C=`1,116,689` to `733,120` in about 1.54 seconds with zero prediction mismatch or strict conflict. |
| `0.8.48` | 2026-09-19 | Exhaustively compared greedy normalization plus ECLO against every reachable normalization state across all 256 four-activity, two-line gap patterns; every final score matched. |
| `0.8.49` | 2026-09-19 | Extended full branching comparison to 768 cases with staggered starts, a precedence chain, and both constraints together; every greedy final score matched the oracle. |
| `0.8.50` | 2026-09-19 | Added deterministic final A/B/C ZIPs whose archived bytes match the protected, officially confirmed incumbents; explicitly quarantined stale historical validator archives. |
| `0.8.51` | 2026-09-19 | Added a one-command local pre-upload audit covering archive structure and hashes, both scorers, hard feasibility, strict closures, official run IDs, and official scores. |
| `0.8.52` | 2026-09-19 | Rechecked the organizer's upstream specification; `main` remains the locally verified commit `966c976` with no pending rule update. |
| `0.8.53` | 2026-09-19 | Corrected the idle-normalization predictor's stale Scenario C excess coefficient from `20` to the confirmed `7`; full candidate validation had prevented score corruption, while the fix restores trusted pruning. |
| `0.8.54` | 2026-09-19 | Centralized production scoring constants and contract-delay arithmetic, removed the dead per-activity scorer, retained the independent scorer, and rejected an initially correct but 4–5× slower implementation. |
| `0.8.55` | 2026-09-19 | Extended final readiness to verify the exact A-002/B-001/C-001 archive SHA-256 values and byte-for-byte equality between their CSV members and the final packages. |
| `0.8.56` | 2026-09-19 | Verified all 14 local PS1 files byte-for-byte against the exact upstream commit after the shallow-clone path failed, without contacting the portal. |
| `0.8.57` | 2026-09-19 | Added 14 public-artifact mutations around legal-mix, capacity, workload, precedence, allocation, workfront, start, horizon, deadline, and ECLO boundaries; all expected checks fire. |
| `0.8.58` | 2026-09-19 | Corrected ECLO candidate predictions to include Scenario C excess cost on zero-supply locations, with ranked/exhaustive equality and restored 120-activity runtime. |
| `0.8.59` | 2026-09-19 | Exhaustively matched evaluator legal-mix acceptance to the solver inequalities across all 215 non-empty PM/PC/C count triples through five of each. |
| `0.8.60` | 2026-09-19 | Exhaustively pinned A/B/C solver group domains across 66 supply/candidate pairs, preserving unrestricted exact B and explicitly bounded heuristic B. |
| `0.8.61` | 2026-09-19 | Added ten complete-submission mutations proving rejection of duplicate/gapped access, missing/extra/duplicate occupancy, empty groups, and missing/false/mismatched results. |
| `0.8.62` | 2026-09-19 | Added a frozen 360-activity scale replay and exact-output regression; week-local structural-hint screening preserves all A/B/C results while reducing recorded runtime 5.94–7.84×. |
| `0.8.63` | 2026-09-19 | Differentially matched full-schedule and affected-week closure decisions across 1,152 incremental candidates, including conflicting standard and strict-buffer rejections. |
| `0.8.64` | 2026-09-19 | Added per-instance activity-footprint caching after profiling 544,500 repeated calls; the 360-activity A/B/C replay remains byte-identical and gains another 3.44–11.37×. |
