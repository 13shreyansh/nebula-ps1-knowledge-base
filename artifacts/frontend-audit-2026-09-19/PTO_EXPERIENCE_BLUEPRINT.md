# NightShift PTO experience: inspection and build blueprint

Inspected 19 September 2026: http://127.0.0.1:8501, served by
`/Users/shreyansh/Documents/ChatGPT/Yash nebula/streamlit_app.py`.
This is an inspection and proposed implementation specification, not a report that
voice or the redesigned interface has been implemented. Neither application source
nor the deployed service was changed during this inspection.

## Product direction

Give the operator one connected workflow: understand the active plan, report a
change by speaking or typing, inspect affected work, calculate a recovery, compare
it with the baseline, and adopt or discard it. Scope the bonus to disruption
replanning and natural-language querying. Leave additional speculative features
out of the first demo.

The official PS1 rubric explicitly values usability by a works controller.
The two named bonus directions cover disruption recovery with limited changes to
unaffected work and questions grounded in schedule evidence.
Source: https://github.com/aochinwen/NebulaX-Hackathon-ProblemStatement/blob/main/PS1/PS1_README.md

## What the teammate intended and what exists

| Capability | Observed implementation | Treatment in NightShift |
|---|---|---|
| New planning run | Public demo or eight-file upload; A/B/C selection; time budget | Keep with an explicit active dataset and plan version; advanced solve settings out of the normal flow |
| Operating overview | Score, overdue contracts, scheduled accesses, horizon, activity/week chart, attention list | Keep; make current week, affected work, next decision and plan status prominent |
| Analytics | Contract delay/workload; activity priorities and leverage; weekly/network load; CSV export | Keep the useful calculations, connect all views through common filters and selected entities |
| Timeline | Searchable activity/week table and separate overview chart | Combine into one zoomable view with visible repeated-visit counts and activity details |
| Capacity | Location pressure chart and occupancy ledger | Link a selected location/week to its actual scheduled work and incident action |
| Explanations | Activity schedule, access type, work requirement and predecessor facts | Put these in a contextual drawer; answer why only when supported by constraints or a solver experiment |
| What-if | Earlier completion for an activity, with no-worse-score or mandatory policy | Secondary advanced action; not another separate headline demo feature |
| Manual disruption | Lower one location's supply, optionally lock activities, run a real replan, compare rows, export or activate | Retain the workflow, add affected dates/weeks and completed-work preservation |
| Natural language | Responses API with structured JSON; two supported proposals: reduce capacity or accelerate activity | Reuse the constrained-action concept, connect tools to the current scheduler |
| Voice | No microphone, speech playback, WebRTC or voice implementation found in the running app/source | Build genuine GPT-Live interaction |
| Plan adoption | Activate a validated alternative; preserve a previous-plan snapshot | Keep with an explicit comparison and undo action |
| Technical proof | Bounds, solver status, validation checks, exact ZIP export and refinement | Keep in an expandable evidence panel for judges and technical users |

## Verified findings

1. The initial screen loaded a stored Scenario A reference at 137.9, with a
   displayed bound of 130.9 and gap of 5.1%. This is the older formulation, not the
   current NightShift zero-score result. Do not carry its bound or proof claims
   into the current model.
2. The AI panel was disabled and displayed a missing OPENAI_API_KEY message.
   Source uses `client.responses.create` and defaults OPENAI_MODEL to
   `gpt-5.6-terra`; it is not a GPT-4 live-voice implementation. No paid AI call or
   microphone session was attempted during inspection.
3. A manual replan was executed in the inspection browser session: default
   `SEC:BET:S15_S16:EB`, supply 4 to 3, no locked activities. The UI returned
   OPTIMAL, score 137.9, zero changed row signatures, zero hard violations, and
   an enabled replan export. It was not adopted as the active plan.
4. Capacity reduction modifies the location's static supply value. There is no
   affected-week interval in the proposal schema or this UI. The change therefore
   applies throughout the horizon, not just during an incident.
5. Whole-activity locks exist, but the replan API has no current-week cutoff or
   automatic freeze of completed visits. Real mid-horizon recovery needs both.
6. The old solver's reference map is keyed by (activity, week), and its tie-break
   compares one reference visit for that key. It cannot simply be transplanted
   onto the new repeated-access model.
7. Old churn counts the symmetric difference of access-row signatures. Moving
   one visit can count twice (one removal and one addition). Show moved activities
   and changed visits separately from this technical measure.
8. Eight top-level tabs, additional analytics subtabs, truncated raw location
   identifiers and solver jargon spread one task across several screens. The
   floating AI popover also separates the conversation from the affected work.
9. The default tested disruption changed nothing. Select a demo incident by
   inspecting actual scheduled occupancy, then rehearse a real solver run that
   produces visible effects; do not manufacture the outcome.

## Proposed operator workspace

Use a restrained, high-contrast layout with an operational hierarchy:

- Top bar: dataset, scenario, active plan version, selected planning week, plan
  status, New plan and Export. Keep the score visible but secondary to the
  operational consequences.
- Main area: linked network and schedule. Selecting a location, contract or
  activity updates both; use readable labels with exact IDs in details. Support
  horizontal timeline scrolling, clear visit counts, selection and keyboard use.
- Attention panel: affected activities, delayed contracts, capacity constraints
  and required decisions. Every item opens the relevant schedule context.
- Persistent assistant panel: Talk to NightShift, transcript, typed input,
  microphone/mute/end controls, and actual listening/thinking/solving states.
  Its answers can select/highlight the corresponding work.
- Recovery comparison: original and proposed placements, changed activities,
  unchanged work, completion-date differences, ECLO/excess use and score change.
  Two clear actions: Use revised plan and Keep current plan.
- Evidence drawer: validation, input/output hashes, solver status, bounds,
  exported CSVs and the basis for each explanation.

Keep setup, execution, candidate comparison and active-plan adoption visibly
separate. A completed solve should not silently replace the current plan.

## Voice and natural-language implementation

Use GPT-Live (`gpt-live-1`, subject to the project's actual model access) over
WebRTC with a backend that performs typed application actions. The long-lived
OpenAI key stays in server configuration/Secret Manager; the browser receives
only the session connection response. No keys in source bundles, browser storage
or screenshots. Confirm real project access before declaring voice operational.

Official sources:
- https://developers.openai.com/api/docs/guides/live
- https://developers.openai.com/api/docs/guides/voice-webrtc

The voice layer handles conversation while backend tools query the plan and run
CP-SAT. Provide the same actions through text and direct UI controls:

- `get_plan_summary(plan_id)`
- `get_activity(plan_id, activity_id)`
- `get_capacity(plan_id, location_id, from_week, to_week)`
- `preview_disruption(plan_id, location_id, from_week, to_week, capacity)`
- `run_replan(plan_id, proposal_id)`
- `compare_plans(baseline_id, candidate_id)`
- `activate_plan(candidate_id)` after operator selection

Resolve exact entities and time windows. If someone says a train broke down,
ask which work/location is affected and for how long: the supplied instance has
no rolling-stock fault model that could justify inventing that mapping.
Answers must cite active plan entities and versions. The assistant may explain
observations immediately; a claim that a particular constraint caused a move
requires recorded evidence or a tested counterfactual.

## Solver integration required

Extend the currently deployed repeated-access solver, not the legacy reference
solver. Store the baseline, disruption overlay, proposal, candidate and validation
as separate versioned records. Cloud Run can route consecutive requests to
separate containers; in-memory Python state alone is not sufficient for this.

Model capacity overrides by location and week. Keep all completed visit tuples
fixed, prohibit introducing new work in the past, and honour explicit future
locks. Preserve the existing objective as primary and minimise disruption to
unaffected visits as secondary, with a documented visit-level metric supporting
multiple accesses per activity/week. A time-limited feasible result is not a proof
of minimum change.

Validate a recovery against the original instance plus its declared disruption
and frozen history. Provide the three standard result CSVs, and keep the incident
and comparison evidence alongside them. Do not imply that a changed-input replan
is an organizer-certified output for the unmodified input pack.

## Focused demo

1. Load and solve the public dataset with the current engine; show real results.
2. Choose a location/week with actual scheduled work.
3. Say, for example: "BET eastbound between S15 and S16 has only one access slot
   during week 22. Keep earlier work unchanged." This is a proposed test input,
   not a claim that this particular reduction will force a change.
4. Assistant shows the interpreted incident and affected work, clarifies anything
   ambiguous, and starts the actual recovery when requested.
5. Show real solver progress, then a before/after comparison and validation.
6. Ask which contracts changed and why; highlight the supporting activities.
7. Adopt the candidate or retain the baseline; download the validated result.

## Fastest build order and acceptance checks

1. Reuse the existing Cloud Run app, input loader, repeated-access CP-SAT solver,
   independent scorer and result schema. Add versioned plan/incident state and a
   real replan endpoint first; verify scope, locks and repeated visits.
2. Rebuild the operator workspace around the shared plan state and comparison.
   Port useful analytics concepts without importing legacy bounds or assumptions.
3. Connect natural-language tools, then GPT-Live audio to those same tools.
4. Rehearse one meaningful incident and one no-impact incident end to end.

Acceptance: baseline still passes; disruption affects only selected weeks;
completed work cannot move; locked visits stay fixed; all required work remains;
changed and unchanged counts reconcile with exported data; infeasible recovery
leaves the baseline usable; failed/ended voice session leaves text/manual tools
available; interruptions cannot accidentally adopt a plan; all charts and assistant
answers refer to the same active plan version; API credentials never reach the
client. A live microphone test and an actual authenticated API exchange are
required before calling voice verified.

Source pointers inspected: teammate `streamlit_app.py` lines 94, 475, 510, 579,
772, 875, 917, 1070, 1239 and 1530; `assistant.py` lines 10, 99 and 167;
`workflow.py` line 108; `solver.py` lines 387 and 855.
