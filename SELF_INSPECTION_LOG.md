# Nebula PS1 Self-Inspection Log

Append-only paranoid audits for the active score-improvement goal. All times use Asia/Singapore.

## 2026-09-18 22:31:33 +08

- Interval: first inspection in this goal.
- Current action: establish an executable semantics and scoring baseline before attempting optimisation. This is highest-value because the repository currently contains research documents but no parser, checker, solver, or reproducible score runner.
- Incumbents: Scenario A has only the organiser-supplied sample, described by the official README as feasible but not locally reference-validator confirmed. Scenarios B and C have no candidate outputs. No result is promoted as a protected validator-confirmed incumbent.
- Evidence since the previous turn: the reconciled knowledge base and research ledger were committed locally and uploaded to the private GitHub repository. This improved knowledge state, not solver score.
- Going well: the public instance, sample output, official constraints, research synthesis, and explicit uncertainty register are available locally.
- Going badly: no executable implementation exists. The official validator and `trackaccess expand` package remain unavailable. Closure and co-sharing semantics are therefore not fully closed.
- Weakest assumptions: exact closure expansion, co-sharing exemptions across a multi-location activity, validator scoring aggregation, horizon enforcement, and hidden-instance scale.
- Whole-approach challenge: CP-SAT may be the wrong first formulation if local possession packing produces weak propagation. A decomposed week-assignment plus packing checker, MILP, or MaxSAT model could outperform it. The smallest useful discriminator is an exact public-instance model with telemetry and an independently checked sample fixture.
- Cheating and overfit audit: no solver exists, so there is no candidate cheating result. The principal future risks are hard-coded public IDs, memorising the sample schedule, using public row counts as constraints, tuning on one seed, and treating inferred rules as validator facts.
- Wrong-signal audit: the official score is a penalty and lower is better. The README specifies contract-priority bands plus an activity-priority nudge; any earlier activity-only or contract-only approximation must not become executable truth.
- Regression risk: none from code yet. Documentation claims must remain labelled derived until validated.
- Next experiment: implement schema-driven parsing, topology and activity footprint expansion, deterministic sample-output loading, and score derivation. Require exact reproduction of the sample's 928 distinct activity-location-week occupancy keys before solver work.
- Abandon/revise trigger: if the independent expansion cannot reproduce the public fixture without sample-specific exceptions, stop solver formulation and isolate the semantic mismatch first.

## 2026-09-18 22:45:39 +08

- Interval: 14 minutes 6 seconds since the previous inspection. This early checkpoint follows the user-requested change to a 15-minute cadence.
- Current action: convert the organiser fixture into executable semantics, then use exact optimisation only behind an independent checker. This remains highest-value because a score is useless if the hidden validator rejects it.
- Current results: the organiser sample derives `48.3` and passes all implemented checks. E002 proves `25.2` optimal only for a closure-free relaxation and is quarantined after eight inferred closure conflicts. E003 scores `32.2`, changes only two late sample rows, and passes the implemented checker plus the sample-consistent closure screen. No score is reference-validator confirmed.
- Evidence of improvement: E003 removes A035's and A038's avoidable late rows while preserving every other activity and every already-on-time target row. CP-SAT proves `32.2` optimal under those repair restrictions. The output has 192 access rows, 928 occupancy rows, zero implemented hard violations, deterministic hashes, and six passing regressions.
- Noise and fairness check: the E003 optimum and bound match; the result appears under a fixed model in 0.066 seconds, so it is not a lucky-seed claim. The broader global-optimum claim remains unproven because closure semantics are inferred and only two activities were released.
- What worked: schema-driven parsing, exact public footprint reproduction, score calculation, mutation rejection, direct local group slots, sample-preserving repair, and a narrow closure screen that accepts the known-feasible sample while rejecting the optimistic `25.2` schedule.
- What failed or remains blocked: the public repository, local machine, and PyPI contain no reference validator or `trackaccess` package. The `25.2` schedule fails the inferred closure screen. Scenarios B and C are not implemented.
- Weak assumptions: co-sharing components are inferred from shared local groups; external buffers are treated as tunnel sectors only; buffer-buffer contact is allowed because the public sample requires it; Live cross-line closure is interpreted as affecting both bounds. Only the organiser validator can settle these points.
- Whole-approach challenge: the closure screen may be self-consistent yet wrong. A validator could treat group connectivity, platforms, or buffer propagation differently and reject E003. The smallest discriminator is the official validator on the unchanged sample, E003, and one mutation for each disputed semantic.
- Cheating and overfit audit: the implementation contains no hard-coded public activity IDs or fixed row counts. The command-line repair targets A035/A038 explicitly as a public-instance experiment, which is permitted for the required precomputed public output but cannot be used as the hidden-instance solver. E003 is not promoted as validator-confirmed. No hidden data, malformed output, proxy-score substitution, or validator exploit is used.
- Wrong-signal audit: no learning component exists. CP-SAT optimises the published penalty in integer tenths; the independent evaluator recomputes the score from CSV output. Feasibility is checked before promotion. The solver still shares topology code with the checker, so an independent fixture comparison remains essential.
- Regression check: row reordering leaves score unchanged; omitted work is rejected; the organiser sample remains accepted; E003 is accepted; E002 is rejected for closure conflicts.
- Lower-bound falsification: `32.2` depends on A036 occupying the H01 eastbound boundary in every week 22-28 and A075's Live PM closure excluding co-existence at the interchange. If the official validator allows a different possession-night interpretation, the additional A075 lower-bound term can fail.
- Next corrective experiment: encode the sample-consistent closure relations inside the optimizer, verify that the organiser sample remains feasible and E002 remains excluded, then solve unrestricted Scenario A. In parallel, keep validator acquisition as the critical external evidence task.
- Abandon/revise trigger: any official-validator rejection of the organiser sample under our regenerated occupancy, any acceptance of a controlled schedule our closure screen rejects, or any unrestricted closure-aware solution below `32.2` invalidates the present proof and requires a semantic/model revision.

## 2026-09-18 22:59:38 +08

- Interval: 13 minutes 59 seconds since the previous inspection; taken slightly early to remain safely inside the requested 15-minute cadence.
- Current action: extend the exact base model to B/C and iteratively separate inferred closure conflicts. This is higher-value than UI work because all three scenario outputs must first be feasible and low-scoring.
- Current incumbents: A=`32.2`; B=`30.0`; C=`32.2`. All three have zero violations under the independent checker and sample-consistent closure screen. None is reference-validator confirmed.
- Evidence of improvement: B reaches the closure-free lower bound of `30.0` with six ECLO rows, zero excess capacity, zero delay, and 189 access rows. Ninety-nine separation rounds removed every inferred closure conflict without raising score. C now has a safe `32.2` fallback obtained by changing only the scenario/result rows of the already checked A schedule.
- Failed path retained: C reached `29.1` after 180 seconds but still had five closure conflicts; its earlier `25.2` relaxation had five conflicts as well. Neither is an incumbent.
- What is going well: exact half-unit ECLO arithmetic, fixed-date enforcement for B, C's line-specific two-week ECLO window, lexicographically subordinate row minimisation, deterministic output generation, and post-generation independent scoring.
- What is going badly: iterative conflict cuts need many rounds and can end on an attractive but unsafe partition. C has not yet found a closure-feasible improvement over `32.2`. The reference validator remains unavailable.
- Whole-approach challenge: the separator proves only that the returned schedule passes the inferred screen; it does not encode the organiser's validator or prove that every unseen closure pattern has been separated. A native component/possession formulation may scale and propagate better.
- Cheating and overfit audit: no public activity ID is hard-coded in the generic B/C solver. The A-to-C fallback reuses a fully scheduled output unchanged and is mechanically rechecked; it does not exploit malformed files, omit work, or substitute a proxy score. Invalid 25.2/29.1 C results remain quarantined.
- Wrong-signal audit: B's 30 points are entirely `6 ECLO × 5`, not delay or excess capacity. C's fallback is entirely 32.2 delay. The row-count tie-breaker is bounded below one official tenth and cannot exchange against official score.
- Randomness audit: B currently uses one seed. Its objective is independently bounded by the closure-free optimum, but schedule reproducibility and closure feasibility still require cross-seed runs. C needs both a valid improvement and cross-seed confirmation.
- Hidden-assumption audit: closure component connectivity, buffer overlap semantics, and cross-line Live propagation remain inferred. The official validator could invalidate every internally feasible incumbent despite our public-fixture regression.
- Next corrective experiments: add regression coverage for B and the C fallback; warm-start C from the safe schedule; run multiple seeds; then replace repeated no-good separation with stronger possession-component constraints if convergence remains poor.
- Abandon/revise trigger: any cross-seed score discrepancy with a better valid result, any checker mutation that wrongly accepts omitted/illegal work, or any official-validator mismatch immediately supersedes current optimality claims.
