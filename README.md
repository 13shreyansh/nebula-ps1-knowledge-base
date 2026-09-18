---
document_id: NH-PS1-KB
version: 0.5.0
last_verified: 2026-09-18
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
| `overrun[a]` | Activity completion beyond its contract’s planned completion date. |
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

The closure and buffer row above is not implementation-complete until the official expander or validator is obtained. The README's literal “buffers never overlap” rule conflicts with four buffer-only overlaps in the unchanged organizer sample that the same README calls zero-violation. The solver therefore audits both the sample-consistent rule and the stricter published rule. Protected outputs must pass both, but only the reference validator can resolve the specification contradiction.

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

The supplied Scenario A schedule is described by the organiser as a feasible regression fixture. It schedules 192 access rows with no ECLO and delays only Priority-3 contracts. Applying the published activity-level weighting gives a derived score of `48.3`; confirm this number with the reference validator before calling it validator-proven.

Resource-independent earliest-finish calculations give useful lower bounds under the inferred activity-level score formula:

| Scenario | Lower bound | Cause |
|---|---:|---|
| A | `25.2` | A036 is intrinsically 14 days late and A059 7 days late before shared-resource conflicts. |
| B | `30` | At least four A036 and two A059 ECLO rows are needed to meet hard dates, before capacity costs. |
| C | `25.2` | ECLO is more expensive than accepting those two Priority-3 delays in isolation. |

These are regression bounds, not proofs of the global optimum. A feasible solution matching one would prove optimality only after all location, closure, allocation, and workfront rules pass validation.

### Current executable evidence

- The schema-driven footprint expander reproduces all 928 public activity-location-week occupancy keys without activity-specific rules.
- The independent partial checker reproduces the organiser sample's derived Scenario A penalty of `48.3` and rejects omitted workload.
- A closure-free CP-SAT relaxation proves its own optimistic `25.2` optimum but fails the inferred closure screen and is quarantined.
- **Scenario A:** an unrestricted solve scores `32.2` and passes all implemented checks; every activity, week, access night, and local group was free to move. It matches the earlier conservative two-row repair. Under the inferred closure semantics, `32.2` is also a lower bound because A036 occupies the H01 eastbound boundary in weeks 22–28 while A075's Live PM interchange closure forces a seven-day delay. Two seeds independently reproduced the optimum.
- **Scenario B:** the protected candidate scores `30.0`: six ECLO rows, zero excess access nights, zero delay, 189 access rows, and zero implemented violations. It matches the closure-free lower bound, so it is optimal under the inferred checker. A second seed reproduced the score and feasibility.
- **Scenario C:** the protected candidate scores `26.1`: `16.1` delay plus two ECLO rows, zero excess access nights, 191 access rows, and zero implemented violations. It matches a data-derived lower bound under the published workload and implemented closure rules: A036 needs weeks 22–28 without ECLO, while Live PM A075 must use one of weeks 24–28 and blocks A036's opposite-bound location. Reducing A036 to six weeks requires two ECLO nights, giving `9.1 + 10`, while A059 contributes an unavoidable `7.0`; total `26.1`. This is not reference-validator confirmation.
- All three protected candidates also satisfy a separate stricter screen that forbids buffer-to-buffer overlap. Strict A=`32.2`, B=`30.0`, and C=`26.1` are feasible at no public-instance score cost. Earlier matching bounds used an over-strong component cut and are not relied on as global proofs.
- A second score implementation independently re-parses the raw input and submission CSVs without importing the solver, topology, or main evaluator. It reproduces A=`32.2`, B=`30.0`, and C=`26.1` exactly.
- New solver telemetry records cumulative CP-SAT deterministic time across iterative closure rounds as well as wall time; older experiment artifacts remain wall-time-only.
- The same three optima are constructed with no schedule hint: A in 100 seconds and B in 102 seconds with one-second solve rounds, and C in 85 seconds with three-second rounds. A deterministic one-worker portfolio also reproduces every score. Search preserves the best safe incumbent so an invalid relaxation cannot consume the whole budget or overwrite a valid output.
- A bijectively renamed and row-shuffled input exposes direct-C search instability: two 180-second no-hint attempts fail to find a safe incumbent. A generic protected portfolio first solves A from that transformed input, verifies it as a C fallback, then improves C to `26.1`; a candidate replaces the fallback only after the checker accepts a strictly lower score.
- A stronger random permutation of line, station, contract, and activity identifier order also preserves A=`32.2`, B=`30.0`, and C=`26.1` under the eight-worker pipeline. This reduces identifier/order-overfit risk but does not substitute for different-topology hidden-instance tests.
- On a known-feasible structural fixture with 67 of 76 locations reduced to capacity 1 and contract/activity priorities permuted, the no-hint pipeline reaches A=`867.3`, B=`30.0`, and C=`29.1`, with both scorers agreeing and zero implemented violations. The guarded staged workflow independently reconstructed A=`867.3` from raw transformed input; its sound phase retained but did not prove that incumbent in 60 seconds. The C portfolio separates its exactly-three-CSV answer key from all audit artifacts.
- A second fixture changes 16 workloads, 37 starts, and 10 predecessor links; A/B/C each reach the `0.0` floor. A full-check pruning gate removes redundant access/occupancy rows without assuming that deletion preserves possession connectivity; it reduced one equal-score B result from 211 to 176 accesses and is applied before C portfolio selection.
- Interchange crossover is derived from station metadata rather than public station IDs; a renamed-interchange regression preserves the expected cross-line closure.
- All three protected candidates are internally checked, not reference-validator confirmed. The organiser sample remains the only organiser-described feasible artifact.

The append-only evidence, hashes, parameters, failures, and limitations are in `EXPERIMENT_LEDGER.md`. Executable code is under `src/nebula_ps1`; regression tests are under `tests`.

The protected public answer keys are in `deliverables/public/A`, `B`, and `C`. Each directory contains exactly the three required CSV files. `deliverables/public/MANIFEST.json` pins their scores and hashes and explicitly records that reference-validator confirmation is still absent.

<a id="improvement"></a>

## 9. Score improvement loop

### Solve in stages

1. **Feasibility:** ignore soft score and find any complete valid schedule.
2. **Primary score:** optimise the exact scenario objective.
3. **Tie-break:** after fixing the best primary score, minimise unnecessary churn, fragmented work, and arbitrary label use. Tie-breakers must not weaken the official score.

The executable staged path uses the fast direct-component formulation only to generate a candidate. It suppresses that heuristic model's bounds, rejects every candidate that fails the full checker or requested strict screen, then passes the first safe incumbent to the sound bridge-safe formulation and searches strictly below it. Multiple deterministic seed attempts protect against heuristic failure; if all fail, a bounded bridge-safe portfolio tries both repair-hinted and unhinted construction. Every safe fallback is pruned before comparison and only the best fully checked candidate reaches proof/improvement search. Only a strictly lower fully checked candidate can replace the incumbent; audit artifacts are stored outside the final three-CSV directory.

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

Current gate: P0 is partially complete. Parsing, footprint expansion, deterministic output loading, score calculation, mutation checks, and a sample-consistent closure screen exist. Reference-validator differential testing is still missing, so P0 is not closed.

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

<a id="open"></a>

## 14. Open questions

| ID | Priority | Question | Resolution |
|---|---:|---|---|
| `O1` | High | Where is the executable reference validator and `trackaccess expand` package? | Obtain them from the organiser portal or release and run them locally. |
| `O2` | High | What runtime and instance-size limits apply to hidden evaluation? | Find official limits; otherwise benchmark generated scale cases. |
| `O3` | High | Does validator scoring exactly match the inferred activity-level overrun and ECLO/excess formulas? | Run controlled cases `V003`–`V006` from the research ledger. |
| `O5` | Medium | Which controller view is most useful in the short demo? | Decide after real solver conflict data is available. |
| `O7` | Low | What is the final product name? | Decide after the core direction is stable. |
| `O8` | Critical | What exact closure and co-sharing exemption logic produced the public occupancy grouping? | Do not freeze pairwise closure constraints until the expander/validator passes `V007`, `V008`, and the sample-specific buffered-overlap cases. |
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
| `E5` | [`RESEARCH_LEDGER.md`](RESEARCH_LEDGER.md), 39 evidence entries plus failure and validator-test registers | Full paper trail, experiments, alternatives, and limitations behind version 0.4.0 | Evidence archive; this README contains the reconciled decisions. |

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
