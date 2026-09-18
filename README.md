---
document_id: NH-PS1-KB
version: 0.2.0
last_verified: 2026-09-18
official_spec: current-problem-statement/PS1/PS1_README.md
---

# Nebula Hack PS1: Team Knowledge Base

This document records the team’s verified clarifications, interpretations, and decisions for Problem Statement 1. It complements the [official PS1 specification](current-problem-statement/PS1/PS1_README.md); it does not repeat its rules, schemas, formulas, or deliverables.

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

<a id="build"></a>

## 8. Build order

| Gate | Required outcome |
|---|---|
| `P0: Input` | Parse a valid arbitrary instance into a checked internal model; reject malformed input clearly. |
| `P1: Core solver` | Support all official scenarios, schedule the complete workload, and generate the required outputs without manual editing. |
| `P2: Validator closure` | Run the reference validator, eliminate hard violations, record scores, and preserve regressions. |
| `P3: Controller experience` | Provide upload, solve, inspect, explain, validate, and export in one usable flow. |
| `P4: Replanning bonus` | Apply a disruption, identify impact, produce a low-churn recovery, and validate it. |
| `P5: Extensions` | Add natural-language analysis, negotiation briefs, fragility views, or richer simulation only if earlier gates are secure. |

### Required product states

The interface must distinguish:

`input loaded → solving → files generated → validating → feasible/infeasible → exported`

Producing files is not the same as passing validation.

### Explanation structure

For a significant decision, show:

`decision → binding reason → evidence → displaced alternative → consequence`

<a id="judging"></a>

## 9. Judging and evidence

The official judging dimensions are **Problem Fit**, **Technical Execution**, and **Ease of Use**.

| Dimension | Evidence we should present |
|---|---|
| Problem Fit | Correct scenario handling, complete outputs, understandable trade-offs, and a bonus tied to the real disruption problem. |
| Technical Execution | Reference-validator results, hidden-instance-ready ingestion, reproducible solving, and regression tests. |
| Ease of Use | A complete upload-to-export flow, clear schedule inspection, explanations, and honest failure states. |

### Claim boundary

Do not claim that the solver is feasible, hidden-instance-ready, faster, or operationally effective until the corresponding test exists. Public-instance validation proves only that result on that instance.

<a id="demo"></a>

## 10. Demo narrative

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

## 11. Decision register

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

<a id="open"></a>

## 12. Open questions

| ID | Priority | Question | Resolution |
|---|---:|---|---|
| `O1` | High | Where is the executable reference validator and how is it invoked? | Recheck the current organiser repository or portal and run it locally. |
| `O2` | High | What runtime and instance-size limits apply to hidden evaluation? | Find official limits; otherwise benchmark generated scale cases. |
| `O3` | Medium | Which formal optimisation method should be the baseline? | Compare the smallest credible approaches on public and generated tests. |
| `O4` | Medium | How should “minimal churn” be measured? | Define the metric before building replanning. |
| `O5` | Medium | Which controller view is most useful in the short demo? | Decide after real solver conflict data is available. |
| `O6` | Medium | Should repository visibility remain private? | Team decision before collaboration or submission. |
| `O7` | Low | What is the final product name? | Decide after the core direction is stable. |

<a id="sources"></a>

## 13. Sources and transcription quality

| ID | Source | Use | Limitation |
|---|---|---|---|
| `E1` | Current files under `current-problem-statement/PS1/` | Official technical specification snapshot | Recheck for upstream updates. |
| `E2` | `AUDIO-2026-09-18-19-50-30.m4a`, approximately 10m31s | Organiser intent and clarification | Room audio and overlapping speech reduce verbatim accuracy. |
| `E3` | User-supplied Wispr Flow transcript | Improved recovery of the full conversation | Speaker numbers are inconsistent; several domain terms are mistranscribed. |
| `E4` | Independent local transcription passes | Cross-check of Q&A meaning | One failed middle-section pass was discarded and reprocessed. |

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

## 14. Maintenance protocol

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
