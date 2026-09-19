# Nebula PS1 Research Ledger

| Field | Value |
|---|---|
| Status | Active continuous improvement through the competition deadline |
| Started | 2026-09-18 |
| Scope | Railway possession scheduling, optimisation, validation, failure modes, robustness, and competition execution |
| Canonical decisions | `README.md` |

This is the evidence-preserving research record. It intentionally retains competing methods, limitations, failures, and unresolved interpretations. Reconciled decisions are in `README.md`; no evidence entry was deleted during reconciliation.

## Recording protocol

Each entry records the source, direct finding, relevance to PS1, limitations, and confidence. Numerical results are never transferred between unlike problem instances as expected PS1 performance. Search failures and negative results are retained when they affect what should be tried next.

Confidence labels:

- **High:** direct statement or result in a primary paper, official source, code, or reproducible experiment.
- **Medium:** supported inference from primary evidence, or a result whose full experimental conditions have not yet been inspected.
- **Low:** promising lead requiring verification.

## Search log

| Pass | Date | Focus | Coverage |
|---|---|---|---|
| `P001` | 2026-09-18 | Field taxonomy and established solution families | Possession scheduling, grouping, CP, MILP, decomposition, LNS, uncertainty |
| `P002` | 2026-09-18 | Real deployments and computational failure modes | Hong Kong MTR, Dutch railways, South African case, Viennese tram network |
| `P003` | 2026-09-18 | Online self-improvement and exact score trade-offs | ALNS, multi-armed bandits, CP-SAT status semantics, PS1 objective arithmetic |
| `P004` | 2026-09-18 | Current 2025–2026 railway methods | Urban-rail network ALNS, negotiation models, robust rescheduling, monitoring-informed maintenance |

## Evidence entries

### `R001` The problem belongs to fixed-timetable, variable-possession scheduling

- **Source:** Sedghi et al., [A taxonomy of railway track maintenance planning and scheduling](https://doi.org/10.1016/j.ress.2021.107827), 2021.
- **Finding:** The literature distinguishes three interactions: fixed timetable with variable possessions, fixed possessions with variable timetable, and joint optimisation. PS1 supplies the access opportunities and asks us to allocate work, so it is closest to the first category.
- **Relevance:** Methods that jointly redesign passenger timetables solve a larger problem than PS1 and should not be copied unless a future bonus introduces train service decisions.
- **Limitation:** PS1 has bespoke C, PC, PM, buffer, ECLO, and scoring rules absent from the taxonomy.
- **Confidence:** High.

### `R002` Constraint programming has a direct real-world possession-assignment precedent

- **Source:** Cheung et al., [Railway track possession assignment using constraint satisfaction](https://doi.org/10.1016/S0952-1976(99)00025-1), 1999.
- **Finding:** Hong Kong MTR used a constraint-based system with a rule base of conflict rules and constraint relaxation to assign track possessions to engineering work. The paper reports that the resulting system entered daily use.
- **Relevance:** This is unusually close to PS1 and supports the choice of CP-SAT. It also suggests separating rule representation, hard conflicts, and controlled relaxation instead of burying all logic in a heuristic.
- **Limitation:** The implementation used CHIP and a historical MTR rule set. It does not establish that the same search strategy is optimal for PS1.
- **Confidence:** High.

### `R003` Grouping compatible maintenance is a primary optimisation lever

- **Sources:** Budai and Dekker, [A Dynamic Approach for Planning Preventive Railway Maintenance Activities](https://doi.org/10.2495/CR040331), 2004; Sedghi et al. 2021 review.
- **Finding:** The cited numerical study reported a 33% reduction in possession time and cost from combining routine work with projects or other routine work. Later studies reviewed by Sedghi et al. also report savings from grouping activities or adjacent segments.
- **Relevance:** PS1 explicitly rewards legal C sharing and PC plus C packing. Search should treat group construction as a central combinatorial decision, not a formatting step after assigning weeks.
- **Limitation:** The 33% is instance-specific and must not be presented as an expected PS1 improvement.
- **Confidence:** High for the qualitative result; Medium for transferring the magnitude.

### `R004` Spatial and temporal aggregation can make integrated models tractable

- **Source:** Lidén and Joborn, [An optimization model for integrated planning of railway traffic and network maintenance](https://doi.org/10.1016/j.trc.2016.11.016), 2017.
- **Finding:** Their MIP uses spatial and temporal aggregation and limited train scheduling windows. Multi-day to weekly instances were reported solvable to optimality within one hour.
- **Relevance:** PS1 already works at weekly granularity. Further restriction of each occurrence to an eligibility window, corridor footprint, and feasible group range should materially reduce search.
- **Limitation:** Their model and objective differ from PS1, and the reported scale does not predict our runtime.
- **Confidence:** High.

### `R005` Exact monolithic models can fail at realistic scale

- **Source:** Fuchs et al., [Scheduling of maintenance work of a large-scale tramway network](https://doi.org/10.1016/j.ejor.2018.04.027), 2019.
- **Finding:** A comprehensive MIP was useful for limited horizons, but its limitations appeared on large real-life networks and long horizons. A specialised large-neighbourhood-search method was introduced for those cases.
- **Relevance:** We should retain one exact feasibility model while adding repair neighbourhoods rather than assuming a single long CP-SAT run will dominate every hidden instance.
- **Limitation:** The paper studies strategic multi-decade maintenance, not PS1's 30-week sample.
- **Confidence:** High.

### `R006` Microscopic MILP can be practical when scope is tightly bounded

- **Source:** Cillie and Bekker, [Development of a maintenance possession scheduler for a railway](https://doi.org/10.7166/34-2-2750), 2023.
- **Finding:** A microscopic 24-hour South African possession scheduler reportedly found optimal solutions in under nine minutes for its application case.
- **Relevance:** Exact optimisation is operationally plausible, but only when the model's scope and dimensions are controlled. We need scaling tests rather than arguments based solely on NP-hardness or a small public instance.
- **Limitation:** One corridor and 24 hours are substantially different from multi-line weekly PS1 scheduling.
- **Confidence:** High.

### `R007` Decomposition is useful, but cut quality changes over the run

- **Source:** Zomer et al., [The Maintenance Scheduling and Location Choice Problem for Railway Rolling Stock](https://arxiv.org/abs/2103.00454), 2021.
- **Finding:** Logic-based Benders decomposition separated assignment from capacity feasibility. Min-cut cuts were faster and helped early progress; a binary-search heuristic produced better later convergence. Some large tests did not reach optimality within two hours, and remaining candidate schedules could still contain capacity violations.
- **Relevance:** If PS1's group and closure variables make one model too large, decompose week assignment from possession packing. Always validate the combined incumbent because a good master score can conceal an infeasible packing subproblem. A portfolio can change strategy as search matures.
- **Limitation:** The paper concerns rolling-stock maintenance locations and teams rather than track possession groups.
- **Confidence:** High.

### `R008` Dynamic restriction of candidate paths or time windows can beat an unrestricted solver

- **Source:** Zhang et al., [A heuristic approach to integrate train timetabling, platforming, and railway network maintenance scheduling decisions](https://doi.org/10.1016/j.trb.2022.02.002), 2022.
- **Finding:** The authors repeatedly solved a binary program while dynamically modifying candidate train time windows. Their approach found near-optimal solutions and outperformed a direct commercial-solver approach on the tested networks. Integrated decisions improved results by as much as 30% in those experiments.
- **Relevance:** Use restricted candidate-week sets, then expand them around bottlenecks or incumbent conflicts. This is safer than instantiating every possible week/group combination from the beginning.
- **Limitation:** The numerical improvement concerns an integrated train problem and is not transferable to PS1.
- **Confidence:** High.

### `R009` Feasibility must feed back from detailed packing to high-level planning

- **Source:** Su et al., [Integrated condition-based track maintenance planning and crew scheduling of railway networks](https://doi.org/10.1016/j.trc.2018.11.003), 2019.
- **Finding:** A high-level maintenance plan is checked by a detailed crew-scheduling level. When detailed scheduling is infeasible because resources or possession time are insufficient, feedback changes the high-level decision and resolves it again.
- **Relevance:** A PS1 decomposition must never accept a week assignment until location, group, buffer, Live-work, weekly allocation, and workfront feasibility are confirmed. Infeasible subsets should generate cuts or neighbourhood repairs.
- **Limitation:** The feedback rule in the paper changes maintenance thresholds, which PS1 does not permit.
- **Confidence:** High.

### `R010` Realistic objectives and model boundaries matter as much as solver choice

- **Source:** Sedghi et al., 2021 taxonomy and research agenda.
- **Finding:** Oversimplified cost functions can produce inadequate maintenance decisions. The literature also underrepresents resource dependencies, contractor workload, materials, procurement, safety, and interactions among track components.
- **Relevance:** For the competition, the official validator objective must be the primary score. Operational qualities outside that objective belong in tie-breakers, explanations, or bonuses and must not silently distort the official score.
- **Limitation:** PS1 intentionally abstracts many operational resources, so adding them as hard constraints would contradict the input contract.
- **Confidence:** High.

### `R011` Uncertainty belongs in a separate replanning layer

- **Sources:** Zhan et al., [Handling uncertainty in train timetable rescheduling](https://doi.org/10.1016/j.tre.2024.103429), 2024; Wang et al., [A data-driven optimization approach for integrated train scheduling and maintenance planning](https://doi.org/10.1016/j.cor.2025.106958), 2025.
- **Finding:** Recent work treats disruption and uncertain duration through robust, stochastic, or distributionally robust formulations. These approaches require uncertainty sets, distributions, or scenario data rather than a single deterministic instance.
- **Relevance:** The core PS1 solver should remain deterministic and validator-exact. Replanning can later use scenario sampling or robust buffers, but only with explicit assumptions and a separate objective such as feasibility preservation and minimal churn.
- **Limitation:** The current PS1 data does not provide probability distributions or duration uncertainty.
- **Confidence:** Medium pending full-paper inspection of the latest DRO study.

### `R012` A good score is not evidence of feasibility

- **Evidence:** Zomer et al. report attractive master-level progress while detailed capacity violations can remain; the PS1 organiser separately identifies the validator as the final checker.
- **Finding:** Objective optimisation and complete constraint validation are distinct processes.
- **Relevance:** Maintain an independent checker, run the reference validator on every retained incumbent, and compare score components. Never rank an invalid candidate above a feasible one.
- **Limitation:** The exact PS1 validator has not yet been obtained.
- **Confidence:** High.

### `R013` Feasible possession groups can be modelled as columns rather than arbitrary labels

- **Source:** Yang et al., [Scheduling a single parallel-batching machine with non-identical job sizes and incompatible job families](https://arxiv.org/abs/2102.02002), 2021.
- **Finding:** For compatible-job batching, a set-partitioning formulation in which each column represents one feasible batch outperformed the studied assignment and time-indexed alternatives. Column generation and branch-and-price extended the method to larger instances.
- **Relevance:** At a PS1 location and week, each legal PM, PC+C, or C-only possession group is a feasible batch. Pre-enumerating legal groups can remove group-label symmetry and make capacity equal to the number of selected columns. If enumeration becomes large, generate promising groups on demand.
- **Limitation:** A PS1 access spans multiple locations and may belong to different groups at each location. Cross-location consistency and closure rules still couple the local set-partitioning problems.
- **Confidence:** High for the formulation pattern; Medium until benchmarked against direct CP-SAT labels.

### `R014` Batch membership must be synchronised explicitly

- **Source:** Huertas and Van Hentenryck, [Parallel Batch Scheduling With Incompatible Job Families Via Constraint Programming](https://arxiv.org/abs/2410.11981), 2024.
- **Finding:** Existing CP batching models could create interrupted batches because job and batch timing were not synchronised strongly enough. The paper introduces redundant synchronisation to prevent those invalid schedules and improve search.
- **Relevance:** In PS1, a possession group is not valid merely because its pairwise composition is legal. Membership must be tied to the exact location and week, and every selected activity must contribute to the same group count and closure exemption there. Redundant equalities and checker assertions may improve both correctness and propagation.
- **Limitation:** The source models continuous processing intervals, while PS1 uses discrete weekly access and location-specific groups.
- **Confidence:** High.

### `R015` Competition-winning rail replanning used priority ordering plus LNS, not an end-to-end learned policy

- **Source:** Chen et al., [Scalable Rail Planning and Replanning with Soft Deadlines](https://arxiv.org/abs/2306.06455), 2023.
- **Finding:** The winning Flatland 3 system combined a new priority order for initial planning with large-neighbourhood search for quality improvement and partially replanned only trains affected by malfunction.
- **Relevance:** For PS1, build a strong deterministic priority order, then reopen a targeted neighbourhood. For the disruption bonus, preserve unaffected assignments and repair the impacted activities and dependency closure.
- **Limitation:** Flatland is multi-agent train routing, not possession grouping, so only the search architecture transfers.
- **Confidence:** High.

### `R016` LNS works best when destroy and repair operators encode problem structure

- **Sources:** Shaw et al., [Improved Local Search for CP Toolkits](https://doi.org/10.1023/A:1021241117280), 2002; recent railway applications including [operational-level centralised maintenance scheduling](https://doi.org/10.1016/j.cie.2026.111838), 2026.
- **Finding:** CP can search a neighbourhood formed by fixing most of an incumbent. Recent railway ALNS work continues to outperform generic ALNS or direct commercial-solver runs by using domain-specific destroy and repair operators, sometimes with adaptive operator selection.
- **Relevance:** Candidate PS1 destroy operators should target a predecessor chain, a congested corridor-week, one contract, one line/ECLO window, or one poorly packed PC/C group. Random removal should be only a diversity operator.
- **Limitation:** The 2026 railway paper includes crew routing and depot selection and has not yet been inspected in full. Q-learning operator selection is not justified until simpler score-based adaptation is benchmarked.
- **Confidence:** High for structure-aware LNS; Low for Q-learning as a PS1 improvement.

### `R017` Full feasible-group enumeration is possible on the public instance but concentrated at hotspots

- **Evidence:** Local enumeration over the official public CSVs, using every activity's tunnel-plus-platform footprint and the published PM, PC+C, and C-only legal mixes.
- **Finding:** Sixty-seven locations are touched. Ignoring week eligibility, there are 5,906 distinct legal activity groups. One platform, `PLAT:BET:S15:EB`, contributes 1,470 groups because 13 C activities and one PC activity touch it. Repeating every static group across all 30 weeks would create an upper bound of 177,180 group-week candidates before date filtering.
- **Relevance:** Full column enumeration is feasible enough to prototype, but most columns arise from a few hotspots. A hybrid should enumerate sparse locations and generate, restrict, or lazily activate groups at hotspots.
- **Limitation:** These are activity-level combinations, not occurrence-specific assignments. They ignore eligible weeks, predecessors, closures, and contract weekly limits, so they measure formulation size rather than feasible schedules.
- **Confidence:** High for the public instance.

### `R018` CP-SAT already uses a multi-worker portfolio and LNS, while hints are not guarantees

- **Sources:** Perron et al., [The CP-SAT-LP Solver](https://doi.org/10.4230/LIPIcs.CP.2023.3), 2023; current [OR-Tools CP-SAT model protocol](https://github.com/google/or-tools/blob/stable/ortools/sat/cp_model.proto) and [solver parameters](https://github.com/google/or-tools/blob/stable/ortools/sat/sat_parameters.proto).
- **Finding:** Multi-threaded CP-SAT is a portfolio of different subsolvers and includes LNS workers. A solution hint may help but is not guaranteed to accelerate search, be used, or produce a nearby final solution. The solver exposes objective bounds, gap information, solution pools, LNS controls, and assumption-based infeasibility cores.
- **Relevance:** Benchmark worker counts and hints instead of assuming they help. Store both incumbent score and best bound. For infeasibility explanations, group optional requirements under assumption literals and request a sufficient core.
- **Limitation:** A returned assumption core is sufficient, not guaranteed irreducible or minimal. Multi-threaded runs can be nondeterministic.
- **Confidence:** High.

### `R019` Minimal-change replanning requires an explicit objective

- **Evidence:** OR-Tools states that a solution hint does not guarantee a solution close to the hint; the Flatland 3 winner explicitly replanned affected agents through an LNS neighbourhood.
- **Finding:** Warm-starting the disrupted model from the baseline is not a minimal-churn guarantee.
- **Relevance:** Replanning should lexicographically minimise: baseline feasibility and official score degradation first, then the number of moved access occurrences, then total week displacement, then changes to ECLO/access-night decisions. Arbitrary `co_share_group` strings must not be compared; semantic group membership or selected possession columns should be compared instead.
- **Limitation:** The exact churn hierarchy remains a product decision and must not override the official scenario score unless the bonus is presented as a separate recovery mode.
- **Confidence:** High for the need for an explicit metric; Medium for the proposed hierarchy.

### `R020` Online bandit selection is a practical self-improvement mechanism without a training corpus

- **Source:** Cai, Kadioglu, and Dilkina, [Balans: Multi-Armed Bandits-based Adaptive Large Neighborhood Search for Mixed-Integer Programming](https://arxiv.org/abs/2412.14382), 2024.
- **Finding:** Balans chooses among destroy and repair neighbourhoods online for the current instance. It requires neither labelled examples nor offline training, and the authors report gains over the default MIP solver, a fixed best neighbourhood, and an earlier MIP-LNS method on their benchmark suite.
- **Relevance:** PS1 can improve during each solve by learning which neighbourhoods work on that scenario and instance. This is a stronger near-term fit than training a neural model before we have a diverse corpus.
- **Limitation:** The paper benchmarks generic MIPs, not PS1 or CP-SAT. Its performance claims must be reproduced on our instances.
- **Confidence:** High for the method and reported experiments; Medium for PS1 transfer.

### `R021` Adaptive operator rewards must include time and feasibility, not only raw score gain

- **Sources:** Ropke and Pisinger, [An Adaptive Large Neighborhood Search Heuristic for the Pickup and Delivery Problem with Time Windows](https://doi.org/10.1016/j.trb.2005.05.001), 2006; Cai et al. 2024.
- **Finding:** ALNS maintains competing operators and updates their selection probabilities from observed performance. Newer bandit variants frame this as online exploration versus exploitation.
- **Relevance:** Record every PS1 neighbourhood attempt with operator, variables released, time limit, feasibility, starting score, ending score, best bound, and improvement. A candidate reward is feasible objective improvement per deterministic time budget, with separate credit for repairing an infeasible incumbent. Normalise within each scenario because A, B, and C have different score scales.
- **Limitation:** The reward definition above is a PS1 design proposal, not a result established by either paper. Wall-clock reward is noisy when parallel CP-SAT is nondeterministic.
- **Confidence:** High for adaptive selection; Medium for the proposed instrumentation and reward.

### `R022` The README's qualitative lever ordering is not a safe optimisation rule

- **Evidence:** Current official `PS1_README.md` objective formulas and the definitions of `excess_access_nights_total` and `eclo_nights_total`.
- **Finding:** Scenario C charges delay per day with contract and activity weighting, excess at 7 per excess location-week access-night, and ECLO at 5 per ECLO activity access. The prose compares examples with different quantities, then suggests a fixed order of actions. Actual marginal cost depends on how many activities, locations, and weeks each action changes. For example, one week of Priority-3 delay costs 7 or 9.1 for one affected activity under the stated weights, while an added possession can create excess at several occupied locations and an ECLO decision can change the required count of access rows.
- **Relevance:** Never encode “delay P3, then ECLO, then excess” as a hard search policy. Generate alternatives and evaluate the complete stated objective exactly. Use the prose ordering only as a branching hint when the computed marginal costs agree.
- **Limitation:** The executable validator is still unavailable, so activity-level lateness aggregation and ECLO counting need controlled confirmation.
- **Confidence:** High that fixed ordering is mathematically unsafe; Medium on exact validator aggregation.

### `R023` Activity lateness, not only the submitted contract result, appears to drive the weighted score

- **Evidence:** `PS1_README.md` describes `RESULTS.csv` at contract level, defines `priority_overrun` from contract overrun-days, but says `priority_weighted_score` is summed per overrunning activity and uses each activity's priority nudge.
- **Finding:** A contract can contain activities with different priorities and completion weeks, while `RESULTS.csv` exposes only one completion and overrun per contract. The prose says the weighted score is summed per overrunning activity. Applying that rule to the sample schedule produces 48.3: late activities A035, A036, A038, A059, and A075 contribute 9.1, 18.2, 7, 7, and 7 respectively. This resolves the most likely intended local calculation: derive each activity's finish from `SCHEDULE_ACCESS.csv`, compare it with its contract planned date, and apply that activity's priority nudge.
- **Relevance:** Model and locally report activity-level lateness even though `RESULTS.csv` is contract-level. Still construct a two-activity controlled validator test to confirm that the result file is cross-checked rather than used as the score's only source.
- **Limitation:** The 48.3 is a reproducible derivation from the sample files and prose, not executable-validator output.
- **Confidence:** Medium until validator-confirmed.

### `R024` Resource-independent lower bounds expose unavoidable score before any packing conflict

- **Evidence:** Reproducible local earliest-start calculation using planned starts, one access per activity per week, workload, FS+0 predecessors, and the 2027-01-04 horizon start.
- **Finding:** In Scenario A, even with unlimited location and workfront capacity, A036 cannot finish before 2027-07-18, 14 days after C006's planned date, and A059 cannot finish before 2027-05-23, 7 days after C010's planned date. Under the activity-weighted interpretation, this gives an objective lower bound of 25.2 before resource conflicts. The sample score is 48.3, so 23.1 comes from other late activity occurrences. In Scenario B, hard dates require at least four ECLO accesses for A036 and two for A059, for a resource-independent lower bound of six ECLO rows and score 30. In Scenario C, the two-ECLO-per-activity cap can reduce A036 to seven days late, but 10 ECLO penalty plus 9.1 delay exceeds its no-ECLO cost of 18.2; the same comparison for A059 is 10 versus 7. Thus the same 25.2 remains the isolated objective lower bound.
- **Relevance:** These are immediate regression checks and search targets. If a local bound exceeds a returned incumbent, the local implementation is wrong. The gap from 25.2 or 30 separates intrinsic date pressure from avoidable conflicts.
- **Limitation:** These bounds deliberately ignore locations, closures, possession mixes, line-wide ECLO-window coupling, weekly allocation, and workfronts. They cannot prove the global optimum unless matched by a fully feasible schedule.
- **Confidence:** High for the calculation under the published rules; Medium for weighted-score semantics until validator-confirmed.

### `R025` Metamorphic tests can validate the checker even when the true optimum is unknown

- **Source:** Alzahrani, Spichkova, and Harland, [Application of property-based testing tools for metamorphic testing](https://arxiv.org/abs/2211.12003), 2022.
- **Finding:** Metamorphic testing addresses the oracle problem by checking relations between transformed inputs and outputs instead of requiring the exact answer to every generated case. Property-based tools can generate and verify those transformations automatically.
- **Relevance:** Build two test layers. Boundary fixtures should exercise PM alone, PC+3C, illegal PC+4C, 4C, illegal 5C, buffer exemption only within the same group, Live mirroring, strict-later-week predecessors, weekly access-night counts, workfronts, C's +1 excess limit, and two-week ECLO windows. Metamorphic tests should verify that row reordering, consistent ID renaming, and bijective `co_share_group` renaming do not alter feasibility or score; increased supply cannot invalidate a schedule; and tightening a deadline cannot improve the optimum. Any violation exposes a checker, serializer, or model bug without needing a known optimum.
- **Limitation:** The PS1 relations are proposed from the published rules. Only the official validator can resolve undocumented behaviour, and monotonicity tests apply to the optimum or a fixed schedule, not necessarily to a time-limited heuristic's returned score.
- **Confidence:** High for the testing method; Medium until each relation is validator-confirmed.

### `R026` Clique and aggregate constraints can replace large sets of pairwise conflicts

- **Source:** Grimm et al., [A decomposition approach for integrated locomotive scheduling and driver assignment in rail freight transport](https://doi.org/10.1016/j.ejtl.2024.100145), 2024.
- **Finding:** The authors construct conflict graphs and replace many pairwise conflict inequalities with clique-cover inequalities. Their formulation uses fewer constraints and a tighter feasible-region description.
- **Relevance:** Precompute PS1 conflict cliques for activities that cannot occupy the same possession or access-night, then compare clique constraints with pairwise implications. At one location-week, a useful aggregate lower bound on possession count is `PM + PC + ceil(max(0, C - 3*PC)/4)` before buffer conflicts; selected columns are an exact strengthening when activity identities matter.
- **Limitation:** The aggregate expression assumes every C can join every PC or C batch at that location and therefore is only a lower bound. Buffers, multi-location footprints, contract access nights, and cross-line rules can require more possessions.
- **Confidence:** High for clique tightening; High for the stated local counting lower bound.

### `R027` A learned optimiser is justified only after representative-instance evaluation

- **Sources:** Chen et al., [Learning to Optimize: A Primer and A Benchmark](https://www.jmlr.org/papers/v23/21-0308.html), 2022; Balcan et al., [Learning to Branch](https://proceedings.mlr.press/v80/balcan18a.html), 2018.
- **Finding:** Learning can improve repeated optimisation over an instance distribution, including branching decisions, but learned optimisers commonly fail outside the training distribution. The benefit depends on having representative samples from the target distribution.
- **Relevance:** Do not train an end-to-end schedule generator on one public instance. If hidden-instance-style generation becomes available, first log exact-solver trajectories and operator outcomes. Evaluate on held-out seeds plus held-out topology, scale, priority mix, supply pressure, and predecessor density. Keep every learned choice inside an exact feasibility-and-score shell. Until that gate is passed, online bandit selection over hand-designed operators is the safer self-improvement layer.
- **Limitation:** The JMLR benchmark focuses mainly on continuous optimisation, and learning-to-branch targets MIP tree search. They establish the distribution requirement, not expected PS1 gains.
- **Confidence:** High.

### `R028` Possession membership is location-specific, not one global group per activity occurrence

- **Evidence:** Reproducible comparison of the public `SCHEDULE_OCCUPANCY.csv` rows.
- **Finding:** The sample contains 129 location-week groups with multiple activities and 100 activity pairs that share at least one such group. Many pairs share at one common location but use different groups at another common location in the same week. For example, A001 and A011 in week 23 share four of their five common locations but not `PLAT:BET:S15:EB`.
- **Relevance:** A model with one possession-group variable per activity-week is wrong. Membership must be indexed by activity, week, and occupied location, or represented by a selected local batch column at each location-week. Closure exemption must be tested at the exact location/group granularity used by the validator.
- **Limitation:** The sample proves location-specific labels, but not every undocumented closure-exemption edge case.
- **Confidence:** High.

### `R029` Week-indexed access booleans avoid pre-guessing the number of ECLO rows

- **Evidence:** Published workload rule: standard rows yield 1.0, ECLO rows 1.5, at most one access per activity-week, and total yield must be at least demand.
- **Finding:** The number of output rows for an activity is a decision because ECLO can replace some standard rows. A direct formulation can use `x[a,w]` for an access and `e[a,w] <= x[a,w]` for ECLO, with integer half-unit workload `2*sum(x) + sum(e) >= 2*demand`. Any redundant row that can be removed while preserving workload is dominated because removal cannot worsen capacity, closures, dates, or ECLO penalty. An inclusion-minimal workload has at most two half-units of oversupply.
- **Relevance:** Prefer week-indexed booleans over allocating a fixed list of `total_accesses` occurrence variables. Add a secondary row-count minimisation or a dominance bound, while keeping the official `>=` rule in the independent checker.
- **Limitation:** A dominance restriction must be proved and regression-tested before entering the hard model; the validator may accept redundant rows even though they are never score-improving.
- **Confidence:** High.

### `R030` Benchmark score-versus-time and variability, not one lucky final run

- **Sources:** Gleixner et al., [MIPLIB 2017: data-driven compilation of the 6th mixed-integer programming library](https://doi.org/10.1007/s12532-020-00194-3), 2021; current OR-Tools [`CpSolverResponse`](https://github.com/google/or-tools/blob/stable/ortools/sat/cp_model.proto) and [`SatParameters`](https://github.com/google/or-tools/blob/stable/ortools/sat/sat_parameters.proto).
- **Finding:** MIPLIB deliberately selects structurally diverse instances for fair solver comparison. CP-SAT reports wall time, deterministic time, objective, best bound, and a gap integral, while its search exposes seeds and worker counts. Search performance can vary with random choices and parallel portfolios.
- **Relevance:** Benchmark each formulation and search policy on a matrix spanning activity count, horizon, topology, access-type mix, buffer severity, predecessor density, deadline slack, hotspot concentration, and supply pressure. Under fixed budgets, record validator feasibility, time to first feasible, best validated score over time, best bound, gap or gap integral, deterministic time, wall time, workers, seed, solver version, model size, and memory. Report median and tail behaviour across seeds; keep best score only for the submission portfolio.
- **Limitation:** MIPLIB's exact instance-selection process is not a PS1 generator. Deterministic time improves comparability but does not replace the competition's actual wall-clock limit.
- **Confidence:** High.

### `R031` The latest close urban-rail work still relies on structure-aware ALNS

- **Source:** [Operational-level centralized maintenance scheduling optimization for urban rail transit infrastructure under network conditions](https://doi.org/10.1016/j.cacaie.2026.100035), 2026.
- **Finding:** The study integrates task allocation, crew scheduling, and depot choice in a time-space network, then uses problem-specific destroy/repair operators and Q-learning operator selection. Its Beijing Subway experiments report better efficiency and solution quality than traditional ALNS and Gurobi on the tested instances.
- **Relevance:** This reinforces the exact-model plus domain-neighbourhood architecture. Crew routing and depot choice are omitted from PS1 inputs and therefore belong only in a future extension. Q-learning should be tested only after the simpler online-bandit baseline.
- **Limitation:** The accessible abstract does not expose enough experimental detail to transfer gains or hyperparameters. The problem is richer than PS1.
- **Confidence:** High for the published method and reported comparison; Low for direct PS1 performance transfer.

### `R032` Contractor negotiation can be evidence from alternatives, not an extra scheduling constraint

- **Source:** Schaeffer et al., [A bilevel programming and bargaining game approach to negotiations regarding time on track for railway maintenance](https://doi.org/10.1016/j.jrtpm.2025.100552), 2025.
- **Finding:** The paper models infrastructure-manager and contractor negotiation over track-work duration, including urgency, leverage, and strategic behaviour. Its central result is that cooperative negotiation can improve combined utility in the studied setting.
- **Relevance:** A credible optional negotiation feature would present validated alternatives and marginal costs: the score and affected work if a contractor receives one more access, changes duration, or accepts a later window. It should not invent unprovided contractor utility or bargaining parameters.
- **Limitation:** PS1 supplies no utility curves, prices, or negotiation behaviour, so implementing the paper's bilevel game would require unsupported assumptions.
- **Confidence:** High.

### `R033` Robust plans need explicit uncertainty data and should be judged by recovery frequency

- **Source:** Wei et al., [Robust Optimization of High-Level Maintenance Scheduling for High-Speed Trains under Uncertainty](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6568962), 2026 working paper.
- **Finding:** The authors combine min-max robust optimisation with ALNS and evaluate adjustment frequency across 10,000 simulated scenarios. They report fewer adjustment days than a deterministic plan in their case study.
- **Relevance:** If a disruption bonus later gains scenario data, evaluate not only expected score but frequency and magnitude of rescheduling. Without calibrated scenarios, present weather or asset failure as a user-selected what-if, not a probability claim.
- **Limitation:** This is a working paper on high-speed train-set maintenance, not track possession, and its uncertainty model is unavailable in PS1.
- **Confidence:** Medium for the reported result; High for the data requirement.

### `R034` A 2026 national-scale possession problem favoured MaxSAT over MIP

- **Source:** Reisch, Großmann, and Weiß, [A MaxSAT model for solving the track maintenance possession problem for the railway network in Germany](https://doi.org/10.1016/j.jrtpm.2026.100569), 2026.
- **Finding:** The study schedules German maintenance demands into predefined containers with machine and traffic restrictions. On the large whole-country instances, its MaxSAT encoding outperformed the MIP formulation after a 24-hour limit and fulfilled about 95% of demands, close to a reported upper bound. Neither method proved the large instances optimal. On two smaller regional instances both reached the optimum, with neither solver uniformly faster.
- **Relevance:** Keep CP-SAT as the primary solver because it uses SAT-style reasoning plus integer constraints, but add a pure weighted-MaxSAT formulation as a later benchmark if the problem can be cleanly Booleanised. Preserve bounds and anytime curves. Do not assume MIP, MaxSAT, or CP-SAT dominates at every scale.
- **Limitation:** The German objective permits unfulfilled demand, whereas PS1 requires every activity to complete and minimises lateness, excess, and ECLO. It also includes machine tours absent from PS1.
- **Confidence:** High.

### `R035` The current public repository still does not contain the promised validator or expander

- **Evidence:** GitHub tree and issue audit at upstream commit `966c976005db2e3e40a691cff268fdb8f396a5df` on 2026-09-18.
- **Finding:** PS1 contains eight input CSVs, three sample output CSVs, the README, and two diagram files. There is no validator executable, package metadata, or `trackaccess` implementation, and the public issue list is empty. Upstream `main` remains at the same commit previously inspected.
- **Relevance:** The internal checker and controlled test plan are urgent, but all validator-dependent semantics must remain marked unconfirmed. Continue monitoring the portal and upstream rather than reverse-engineering a nonexistent public executable.
- **Limitation:** The organiser portal or a private release may contain files absent from the public repository.
- **Confidence:** High for the public repository state.

### `R036` Direct local group slots are smaller than full batch enumeration on the public instance

- **Evidence:** Reproducible variable-count experiment over the public data and exact corridor footprints.
- **Finding:** Planned-start domains create 994 activity-week access booleans and 4,908 activity-location-week presences. Full legal local batch columns after week filtering still create about 72,683 group-week candidates, with 1,470 at the single worst location-week. Direct membership in canonical local slots needs about 10,966 booleans in A using nominal supply slots, 15,874 in C using supply+1 slots, or 9,875 under a static dominance cap. The dominance cap at a location is `PM + PC + ceil(max(0, C - 3*PC)/4)` over all activities that can touch it; its public maximum is four.
- **Relevance:** Start with direct local group slots plus strong symmetry breaking, not full set-partitioning columns. Retain columns as a benchmark or generate them only where the label model propagates poorly. In B, “unlimited” soft excess does not require unbounded labels: merging legally compatible groups cannot increase excess, closures, or ECLO, so an objective-optimal solution should exist within the dominance cap.
- **Limitation:** The B dominance argument assumes the validator's closure exemption is monotone under legal merging. Confirm with `V007` before making the cap irreversible.
- **Confidence:** High for counts; Medium for the validator-dependent dominance cap.

### `R037` Group-label symmetry should be broken as interchangeable values

- **Sources:** Walsh, [Symmetry Breaking Using Value Precedence](https://arxiv.org/abs/0903.1136), 2009; current OR-Tools [`SymmetryProto`](https://github.com/google/or-tools/blob/stable/ortools/sat/cp_model.proto).
- **Finding:** Value-precedence constraints remove symmetry among interchangeable labels by requiring lower labels to appear before higher labels. CP-SAT can also detect permutation symmetries and orbitopes, including the Boolean-matrix pattern used in graph colouring.
- **Relevance:** For every location-week, enforce contiguous use `used[g+1] <= used[g]`. Order activities deterministically and benchmark explicit first-use/value-precedence constraints against CP-SAT's automatic symmetry detection. Present group labels only after canonical renumbering in the serializer.
- **Limitation:** Overly elaborate manual symmetry constraints can enlarge the model or interfere with search. The comparison must use identical feasible spaces and fixed budgets.
- **Confidence:** High.

### `R038` Scenario dominance gives safe warm starts when the input instance is shared

- **Evidence:** Published scenario policies.
- **Finding:** Any Scenario A feasible schedule is also hard-feasible in C on the same input because C relaxes capacity by one group per location-week and permits ECLO without requiring it. Its C score equals its A delay score when it uses neither excess nor ECLO. A B schedule is not necessarily C-feasible because B has unlimited soft excess and no ECLO continuity window. A C schedule is not necessarily A-feasible, and A/C schedules may violate B's hard planned dates.
- **Relevance:** Solve A first and inject its validated schedule as C's guaranteed incumbent. Build B by targeted compression of late A activities rather than from scratch, while allowing extra groups and ECLO. Maintain separate models and objectives; share only derived structures and eligible incumbents.
- **Limitation:** This transfer holds only when A, B, and C are evaluated on the same eight input CSVs. If organisers provide scenario-specific instances, only the architecture transfers.
- **Confidence:** High under a shared instance.

### `R039` The sample contradicts a simplistic weekly buffer-conflict rule

- **Evidence:** Public sample access and occupancy rows inspected before research stopped.
- **Finding:** A003 and A041 are both `Non-live (Consist)` C activities, occupy `SEC:BET:S15_S16:EB` in weeks 11 and 12, and use different local groups there. Their contract-local access-night indices also differ. Similar buffered overlaps appear elsewhere. Therefore the sample cannot be reproduced by simply forbidding every pair of buffered activities that share a corridor location in one week unless they use the same group at every common location.
- **Relevance:** Closure logic is the highest-risk unverified semantic. Reproduce sample grouping, then use the official expander and minimal validator cases to determine whether buffers are tied to nights, selected locations, group construction, or another rule. Do not encode the simplistic pairwise interpretation as settled fact.
- **Limitation:** The public sample shows which interpretation is wrong, not the complete correct algorithm.
- **Confidence:** High.

### `R040` The sample specifically permits buffer-to-buffer overlap

- **Evidence:** Recomputed work footprints and external buffers from the public input, then matched them to the organizer's sample access rows. The three sample CSV hashes are unchanged from upstream's initial commit `3ea7744`; that same initial README already contained both “buffers never overlap” and the claim that the sample has zero hard violations. This is an original specification inconsistency, not a later sample drift introduced by the predecessor update.
- **Finding:** The sample schedules A069 and A046 in week 12. Their work footprints are disjoint and neither activity's buffer intersects the other's work, but both external buffers contain `SEC:ALP:H02_S05:WB`. A rule that forbids buffer-to-buffer overlap would therefore reject the organizer's stated feasible sample. Four such buffer-only collisions occur under the current topology derivation, including another ALP case in week 11 and BET cases in weeks 17 and 20.
- **Relevance:** Keep closure screening narrow: reject another possession's work inside a component's blocked area, but do not reject buffer-only overlap. Preserve this exact case as a regression. Treat it as sample-derived evidence, not proof that the full inferred closure semantics match the hidden validator.
- **Limitation:** A topology or buffer-expansion error could produce the apparent overlap. Only the official expander or validator can resolve that remaining possibility.
- **Confidence:** High that the derived sample contradiction is reproducible; Medium that the derivation matches the organizer's intended expander.

### `R041` Possession closure exemption must propagate through local group links

- **Evidence:** Public week-13 occupancy and derived closure footprints.
- **Finding:** A003 and A060 share group `b1` at `PLAT:BET:S15:EB`; A060 and A019 share group `b2` at `PLAT:BET:S16:EB`; A003 and A019 never directly share a local group. A pairwise-only exemption nevertheless reports A003/A019 colliding at `SEC:BET:S16_S17:EB`, while the organizer calls the complete sample feasible. The shared activity therefore links the local groups into one transitive possession component for closure exemption.
- **Relevance:** Build possession components as the connected components of same-location/week/group membership, then apply closure interactions between components. Do not require one global group label across a corridor and do not limit exemption to directly co-grouped pairs.
- **Limitation:** This validates the component construction needed to reproduce the sample under our topology expansion; it does not independently validate the expansion or hidden validator.
- **Confidence:** High.

### `R042` `access_night` is accounting-local, not a possession identity

- **Evidence:** Official output schema and public sample week 16.
- **Finding:** A003 and A007 belong to the same contract C001 and directly co-share group `b1` at both BET interchange platforms and the connecting sector, yet their `access_night` values are 3 and 1. The organizer still describes the sample as feasible. Therefore equal possession membership does not require equal `access_night`, even within one contract.
- **Relevance:** Use `access_night` only for the published contract/type weekly allocation and workfront counts. Do not link it across contracts, equate it with `co_share_group`, or use it as a global physical-night identifier.
- **Limitation:** This settles the invalid equality constraint; it does not reveal any unlisted validator checks on night indices.
- **Confidence:** High.

### `R043` Superseded: activity-completion scoring suggested a 26.1 C bound

- **Evidence:** Public activity/project rows, week calendar, workload rule, ECLO yield/cost, activity-delay weights, and derived Live mirror/buffer footprint.
- **Finding:** A036 has seven units, starts in week 22, and costs `18.2` if completed in week 28 or `9.1` in week 27. A059's seven units from week 14 make its week-20 `7.0` delay unavoidable without spending a more expensive pair of ECLOs. A075 is a one-night Live PM starting week 24 with an on-time limit of week 28; its mirrored closure blocks A036's BET `S14_H01:EB` location, and PM cannot co-share. With no ECLO, A036 occupies every week 22–28, so A075 must either be delayed to week 29, raising the total to at least `32.2`, or A036 must be compressed. Six A036 access rows need two ECLO bonuses, cost `10`, and can finish in week 27 at `9.1` delay. Adding A059's `7.0` gives `26.1`, achieved by the protected schedule.
- **Relevance:** Historical falsification record only. A-002 proved that the validator charges the contract's final overrun through every activity-priority nudge, so `26.1` is not the official C score.
- **Limitation:** The scoring premise was wrong; do not use this bound or its activity-level costs for selection.
- **Confidence:** Rejected by official differential evidence.

### `R044` Official scoring, closure semantics, and public optima

- **Evidence:** Official portal runs A-001, A-002, B-001, and C-001; exact uploaded ZIPs; corrected dual scorers; bridge-safe solver proofs; workload and closure lower bounds.
- **Finding:** A possession closure contains its work footprint. Live interchange closure and its configured buffer propagate onto the other line. Same-location/group links form transitive possession components. Overrun is based on final contract completion and is charged once through every activity-priority nudge in that contract. The portal confirms A=`137.9`, B=`30.0`, and C=`62.7`.
- **Relevance:** These are the protected public incumbents. A reaches its workload-plus-A036/A075 trade-off bound; B and C have bridge-safe `< incumbent` infeasibility proofs, and C also has a workload/ECLO bound.
- **Limitation:** Four successful public validations do not establish hidden-instance construction speed or reliability. The portal does not label solutions globally optimal; optimality follows from our independently stated bounds.
- **Confidence:** Very high for public feasibility and score; high for public optimality; medium for hidden-instance transfer.

### `R045` Wall time, seed, and worker count are not a reproducibility contract

- **Evidence:** OR-Tools' current SAT parameter definition distinguishes wall-clock `max_time_in_seconds` from `max_deterministic_time`; it also describes experimental interleaved search as deterministic across worker counts. The installed OR-Tools 9.15 exposes both controls. Our prefix-40 one-worker staged repetitions ranged from checked `34.0` to `186.0`, and the full structural fixture failed with one worker while an eight-worker run reached and proved `30.0`.
- **Finding:** A fixed random seed and one worker do not make a sequence of separately wall-time-limited CP-SAT solves reproducible. Iterative cut timing changes which incumbents and cuts survive. Worker count is part of the benchmark contract. [OR-Tools parameters](https://github.com/google/or-tools/blob/stable/ortools/sat/sat_parameters.proto)
- **Relevance:** Record worker count, wall and deterministic time, per-stage budgets, seed, incumbent, bound, and conflicts. Evaluate score distributions and fail-closed rates, not one lucky run. Experiment with deterministic-time or interleaved search only as an explicit non-default policy until it is benchmarked.
- **Limitation:** OR-Tools marks interleaved search experimental, and a 2026 upstream issue reports that deterministic batches can still have highly uneven wall duration on large models. Determinism can therefore trade away deadline predictability. [OR-Tools issue 5199](https://github.com/google/or-tools/issues/5199)
- **Confidence:** High.

### `R046` Separate incumbent generation, neighbourhood improvement, and proof

- **Evidence:** Recent hybrid CP/SAT scheduling work describes a division of labour in which large-neighbourhood search supplies high-quality schedules and exhaustive/failure-directed search proves optimality. Our own B experiments mirror this: fast candidate generation, conflict-neighbourhood repair, cost-contributor repair, then a sound protected verifier. [Bit-Monnot, Enhancing Hybrid CP-SAT Search for Disjunctive Scheduling](https://journals.sagepub.com/doi/pdf/10.3233/FAIA230278)
- **Finding:** A single monolithic timed solve is not the most reliable architecture. Preserve a checked incumbent, use multiple structurally meaningful neighbourhoods, and run a separate sound phase for improvement/proof. Neighbourhood failure is never infeasibility evidence.
- **Relevance:** Keep conflict-participant and objective-contributor repairs as bounded LNS operators. Add new operators only when their free set is derived generically and benchmarked against the same protected incumbent and budget.
- **Limitation:** Job/open-shop benchmarks are not the PS1 formulation. The paper supports the architecture, not a guaranteed score gain or the exact neighbourhood definitions used here.
- **Confidence:** Medium-to-high.

### `R047` Decomposition should separate schedule choice from detailed possession feasibility only when scale requires it

- **Evidence:** Railway logic-based Benders work separates high-level timetable decisions from microscopic feasibility and reports improved scalability on real Swiss railway cases. A 2023 set-covering/Benders variant reports up to 20× faster solutions with small gaps, while a 2025 geographic-decomposition study finds that decomposition shape and coordination overhead interact non-trivially. [Leutwiler and Corman](https://www.research-collection.ethz.ch/handle/20.500.11850/535049), [set-covering Benders](https://doi.org/10.1016/j.cor.2023.106339), [geographic decomposition study](https://fis.tu-dresden.de/portal/en/publications/geographic-decompositions-in-railway-timetable-planning%284aa12519-e138-4fa1-b9f4-11465a5f3fcc%29.html)
- **Finding:** PS1 has a natural decomposition: a master chooses activity weeks, ECLO, and coarse capacity; per-week/location subproblems test legal possession grouping and closure compatibility; infeasible subsets return aggregated cuts. Our iterative closure separator is a partial version of this idea, but it still keeps all group variables in the master.
- **Relevance:** Keep the current formulation while it proves public and synthetic optima quickly. Switch to a true master/subproblem design only if hidden-scale benchmarks show group-variable or cut-growth failure. Premature decomposition can add coordination overhead and weaken bounds.
- **Limitation:** Timetabling decomposition results do not transfer numerically to PS1, whose co-sharing and closure rules differ. “Up to 20×” is paper-specific and is not an expected gain here.
- **Confidence:** Medium.

### `R048` Independent size scaling is not a substitute for interaction-density scaling

- **Evidence:** A public-independent 20-module fixture with 180 activities solved 15/15 fixed-budget one-worker A/B/C runs to matching bounds, yet the modules are spatially separated and contract-independent. C took 5.35–5.59 seconds while A/B remained near two seconds or below.
- **Finding:** Variable count alone is not the current failure mode. Closure density, shared bottlenecks, predecessor coupling, and ECLO-window interaction are more likely to trigger cut growth and unstable construction than additional separable modules.
- **Relevance:** Retain the current monolithic-plus-separator architecture. Benchmark dense shared corridors before implementing Benders, learning, or another solver family; otherwise a rewrite would optimize an unobserved bottleneck.
- **Limitation:** The 180-activity result is not a hidden-runtime guarantee. It is an authored, decomposable fixture and has no reference-validator confirmation.
- **Confidence:** High for this fixture; medium for the prioritization inference.

### `R049` A feasibility-oriented structural hint can remove combinatorial symmetry without weakening validation

- **Evidence:** The dense independent fixture failed 15/15 fixed-budget runs. A non-binding hint that forms legal same-footprint C/PC batches and closure-screens backward singleton-chain placement changed the same policy to 15/15 proved zero-score results. A group-label cap and start-order symmetry alone both failed.
- **Finding:** Dense PS1 construction benefits from separating a domain-specific feasible pattern proposal from exact optimization. The proposal should encode published generic structure, not IDs or answer rows; CP-SAT may ignore it, and every output must still pass the independent checker and bridge-safe phase.
- **Relevance:** Use the structural hint as one portfolio operator, not the model. Preserve unhinted attempts and failed telemetry. Expand the operator only after held-out dense generators show benefit.
- **Limitation:** The first decisive success is on a co-developed generator with identical footprints and deadlines. This is vulnerable to structural overfitting even though it is not sample memorization.
- **Confidence:** High in the measured before/after; medium in transfer.

### `R050` Benchmark the deployed controller, while retaining component failures separately

- **Evidence:** On the dense holdout, direct Scenario C construction failed every seed, while the designed A-as-C guarded controller reached the proved zero lower bound in every seed. The distinction was hidden until the seed harness exposed an explicit `production_c` policy field.
- **Finding:** A component benchmark and a deployment benchmark answer different questions. Direct C failure reveals search weakness; production C success establishes current end-to-end fallback reliability. Neither result should replace the other.
- **Relevance:** Encode controller choice in every benchmark contract. Preserve direct-construction failures, but measure submission readiness through the same staged path the live system will call.
- **Limitation:** A-as-C is safe only when A and C share the same input hash and C accepts A's capacity/ECLO policy. The controller already checks its generated fallback; hidden scenario-specific inputs must not be silently cross-used.
- **Confidence:** High.

### `R051` Non-binding construction hints can coexist with exact ECLO and delay trade-offs

- **Evidence:** On a dense holdout with a provable A=`7`, B=`10`, C=`7` extension, the standard-only structural hint could not schedule B's tight activity by its deadline. The exact model nevertheless found the required two ECLO rows in all five seeds, while guarded C retained the cheaper seven-point delay.
- **Finding:** A partial feasibility hint need not encode every policy lever. Keeping ECLO, excess, and timing as free exact decisions allows CP-SAT to repair or ignore the hint. This is safer than a constructive algorithm that commits to one lever order.
- **Relevance:** Continue treating hints as portfolio operators and keep the exact objective dominant. Add specialized ECLO hints only if coupled trade-off benchmarks show a measured need; do not assume “ECLO first.”

### `R052` Search budget is part of the algorithm, and a proof bound is not an incumbent

- **Status:** Locally demonstrated; external generality unverified.
- **Finding:** On the coupled ECLO-window fixture, the corrected construction exposed the exact B lower bound `20.0`, but one second of repair returned `48.0`. Ten seconds reached `20.0` in all five seeds, with wall time varying from 6.068 to 20.025 seconds and five different optimal hashes.
- **Relevance:** Record stage budgets with every score. A bound-incumbent gap should trigger continued protected repair when budget remains; never report the bound as achieved until a dual-scored feasible incumbent matches it. Compare policies by complete score/runtime distributions, not one seed or one output hash.
- **Limitation:** This evidence comes from one locally authored family. An adaptive continuation rule still needs fixed-budget cross-regime testing so it does not starve hard feasibility construction or exploit case-specific stopping behavior.

### `R053` Equal score and local feasibility do not transfer official artifact status

- **Status:** Confirmed by public reconstruction; release policy fixed.
- **Finding:** The current controller reconstructed A=`137.9`, B=`30.0`, C=`62.7` with new hashes and both local scorers agreeing. The new schedules were not submitted to the reference validator, and their strict diagnostic conflicts differ from the protected official artifacts.
- **Relevance:** Keep official validation attached to an exact artifact hash, not a score or algorithm version. Never replace an officially accepted incumbent with an equal-scoring local reconstruction. Treat unconfirmed strict-buffer semantics as an audit dimension, not a hard constraint.

### `R054` Objective stability can coexist with structural and runtime instability

- **Status:** Confirmed on five public seeds per scenario.
- **Finding:** Fifteen fixed-policy reconstructions all reached the same optimum, yet all hashes differed, strict conflicts ranged from 3 to 8, and scenario wall times varied by up to roughly twofold.
- **Relevance:** Report objective, feasibility, artifact hash, strict diagnostics, selected stage, and runtime separately. Use repeated-seed distributions for deployment claims. Deterministic-time or interleaved search is worth comparing only under the same end-to-end budget and protected-incumbent gates.

### `R055` Portfolio diversity cannot compensate for a systematically unsafe construction hint

- **Status:** Demonstrated on the public one-worker policy.
- **Finding:** Three 30-second A trajectories retained 27, 12, and 14 closure conflicts, while one attempt retained 24. B stayed at `149.0` with one or three attempts. Additional seeds increased runtime without changing the failure class.
- **Relevance:** Diagnose repeated violation structure before allocating more attempts. Construction hints should be transactionally screened across interacting footprint classes, while remaining non-binding and independently checked. Use portfolio diversity after structural feasibility improves, not as a substitute for it.

### `R056` A cleaner partial hint can worsen timed exact search

- **Status:** Demonstrated and rejected on the public one-worker case.
- **Finding:** Cross-footprint closure screening made the provisional packing more conservative, yet final A conflicts worsened from 24/15 to 27/22 and B stayed at `149.0`.
- **Relevance:** Evaluate hints by checked end-to-end outcomes, not local plausibility. Measure hint coverage and run matched hint-on/off ablations before adding more construction rules; revert changes that do not improve the fixed-policy distribution.

### `R057` Hint completeness matters differently by objective regime

- **Status:** Confirmed on public A/B and four independent dense A regimes; hidden transfer unverified.
- **Finding:** A partial public warm start harmed delay-minimizing A, while removing the same packing information made fixed-deadline B lose feasibility. Complete hints solved every independent dense regime tested.
- **Relevance:** Record coverage explicitly. Clear incomplete hints for A, where neutral search can trade delay against placement; retain them for B/C, where packing can establish hard-date feasibility. Validate any scenario-specific policy on full score/feasibility/runtime distributions and preserve an unhinted portfolio path.
- **Limitation:** This rule is selected from known fixtures and may not dominate on every hidden distribution. Later unhinted attempts and fail-closed verification remain necessary safeguards.

### `R058` Local conflict counts do not identify a sufficient repair neighborhood

- **Status:** Demonstrated negatively on public one-worker A.
- **Finding:** Dependency closure, pre-seeded sound cuts, and activities blocking the least-conflicted alternative weeks all failed to remove a two-conflict residual. Some expansions increased final conflicts despite appearing locally favorable.
- **Relevance:** Closure repair is globally coupled through transitive possession groups, frozen access timing, workfronts, and capacity. Do not select neighborhoods from pairwise conflict counts alone. Validate repair operators end to end, preserve failed outputs, and move to an independent fixture or different formulation before further tuning a solved public instance.
- **Limitation:** The tight activity is spatially isolated, so the result does not cover ECLO decisions coupled to possession conflicts or C's global two-week line window.
- **Confidence:** High for the tested trade-off; medium for coupled cases.

### `R059` Count possession capacity by compatible batches, not surplus rows

- **Status:** Confirmed on the independent irregular fixture.
- **Finding:** The first lower-bound argument assigned two surplus C rows to two excess possessions and predicted C=`52.0`. The rows can co-share one legal additional possession. The correct count is two mandatory ECLO rows (`10`) plus one excess group across three occupied locations (`21`), giving `31`.
- **Relevance:** Lower bounds must combine workload compression, weekly/workfront limits, legal batch size, nominal group capacity, and footprint width. Counting rows without maximum compatible packing can materially overstate the bound.
- **Confidence:** High; a strict-clean schedule attains `31.0` and a focused exact repair returns the same bound.

### `R060` A feasible cross-scenario seed can suppress the intended search

- **Status:** Demonstrated on guarded Scenario C.
- **Finding:** A valid but poor A=`13160.0` schedule became C's protected hint and prevented the structural C constructor from running. The controller returned the same poor C score even though independent C construction plus repair reaches `31.0`.
- **Relevance:** Preserve cross-scenario incumbents as fallbacks, not exclusive initialisations. At least one scenario-native challenger must run without the inherited sample hint, and selection must compare only fully checked candidates.
- **Confidence:** High for the observed architecture failure and correction; transfer remains to be tested across more fixtures.

### `R061` Cost-contributor neighborhoods can turn a weak safe incumbent into a proof

- **Status:** Confirmed for B and C under implemented rules.
- **Finding:** Freezing unrelated access decisions while releasing every activity participating in ECLO or an excess location-week reduced irregular C from `38.0` to `31.0` in 0.645 seconds and from `52.0` to `31.0` in 0.296 seconds. Both repairs returned matching bounds.
- **Relevance:** Once any checked incumbent exists, derive the neighborhood from actual objective contributors rather than identifiers or pairwise conflict counts. Keep the incumbent protected because an empty or insufficient neighborhood remains possible, especially when cost is delay-only.
- **Confidence:** High for the two irregular repairs and public B regression; medium for broad C transfer.

### `R062` Per-round retry caps must not silently discard total search budget

- **Status:** Corrected and regression-tested.
- **Finding:** Repeated `UNKNOWN` responses stopped once the active solve cap reached 30 seconds even when the caller requested 120 seconds. The corrected loop expands into the remaining authorized time. A protected verification then consumed the full 120 seconds instead of stopping near 75.
- **Relevance:** Treat total and per-round budgets as separate contracts. Telemetry must expose both, and an exhausted retry cap must not be reported as an exhausted caller budget or evidence of optimality.
- **Confidence:** High for budget accounting; no public score gain is attributed to this change.

### `R063` Objective participants are too narrow when competitors occupy the same footprint in other weeks

- **Status:** Confirmed on irregular Scenario C seed 3.
- **Finding:** Releasing only ECLO and excess-group participants left a checked `52.0` local optimum. Releasing every incumbent activity that touched any of those participants' costly locations reached the global `31.0` bound, because competing rows in other weeks could move.
- **Relevance:** Derive C large neighborhoods in two steps: direct objective contributors, then the incumbent footprint competitors that consume their alternative slots. Preserve the checked incumbent and keep B's smaller neighborhood unless B evidence justifies expansion.
- **Limitation:** Footprint expansion can become large on network-spanning activities and may consume the whole repair budget. Cap and benchmark it by affected component size rather than assuming it is always superior.
- **Confidence:** High for the failure and recovery; medium for transfer.

### `R064` Improvement operators cannot compensate for failure to construct one checked incumbent

- **Status:** Confirmed on irregular Scenario C with one worker.
- **Finding:** The expanded neighborhood repairs 8-worker incumbents to `31.0`, but a 120-second one-worker construction never became safe and therefore never reached that stage. Local conflict repair also worsened 56 residual conflicts to 57.
- **Relevance:** Separate construction reliability from incumbent improvement. Benchmark time to first checked incumbent by worker count; retain a feasibility-oriented decomposition or portfolio branch before tuning score neighborhoods.
- **Limitation:** This is one authored fixture and one seed. It establishes a failure, not a universal worker threshold.
- **Confidence:** High for the observed run; low for the exact worker-count boundary.

### `R065` Repair neighborhoods must follow shared scheduling constraints, not only space

- **Status:** Confirmed by a precommitted cross-module fixture and controlled incumbent.
- **Finding:** Spatial expansion froze four standard-only activities in the same one-workfront contract as an ECLO contributor and conditionally proved C=`101.0`, although C=`76.0` was feasible. Adding the direct contributor's contract peers before footprint expansion recovered and proved `76.0`.
- **Relevance:** ECLO, excess, and delay trade-offs propagate through contract workfront and weekly-access limits even when activities occupy disjoint locations. Scenario C repair now includes those direct contract peers; Scenario B remains narrow.
- **Limitation:** Contract-plus-footprint expansion can approach the full instance, as 43/54 public activities did. Preserve a checked incumbent, cap time, report neighborhood size, and do not interpret a frozen-neighborhood bound as global.
- **Confidence:** High for the mechanism and tested correction; medium for runtime transfer.

### `R066` An improvement neighborhood must seed every objective component

- **Status:** Confirmed on a checked delay-only Scenario C incumbent.
- **Finding:** Selecting only ECLO and excess participants produced an empty neighborhood for C=`126.0`, whose entire avoidable loss was delay. Adding activities from overdue contracts allowed the same guarded repair to prove C=`76.0`.
- **Relevance:** Scenario C has three objective sources: delay, ECLO, and excess. Neighborhood discovery must start from all three before following contract and footprint dependencies; otherwise a valid incumbent can suppress a known improvement.
- **Limitation:** Delayed-contract expansion can make the neighborhood broad when many projects are late. The protected incumbent and time cap preserve correctness, not runtime.
- **Confidence:** High for the omission and correction; medium for scale transfer.

### `R067` Frozen precedence neighbors can create false local proofs

- **Status:** Confirmed on a precommitted two-contract fixture.
- **Finding:** Freeing a delayed successor while freezing its on-time predecessor proved score `7.0` optimal inside the neighborhood, although moving both gives `0.0`. Transitive predecessor/successor closure recovered and proved zero.
- **Relevance:** Dependency-aware repair must follow precedence in both directions: predecessors may need to move earlier, while successors may need to move when a contributor shifts later. Bounds remain conditional whenever linked activities are frozen.
- **Limitation:** A long precedence chain can widen repair substantially. Current tested public and synthetic neighborhoods did not grow, but hidden graphs may differ.
- **Confidence:** High for the mechanism and correction; medium for scale transfer.

### `R068` Recursive dependency closure is safer but can double repair size

- **Status:** Measured on four retained regimes; not adopted as the default.
- **Finding:** Repeating contract, precedence, and footprint expansion to a fixed point grew the public C neighborhood from `43/54` to `54/54`, irregular from `27/106` to `53/106`, coupled from `23/102` to `49/102`, and cross-module delay from `18/72` to `18/72`. Convergence took two or three rounds.
- **Relevance:** A one-pass neighborhood can miss dependencies introduced by its final footprint expansion, while unconditional recursion can erase the runtime advantage of local repair. Use a measured escalation tier rather than silently claiming the one-pass conditional bound is global.
- **Integrity control:** Frozen-access telemetry now records `primary_bound_scope` and states the conditional scope in plain language. A proven neighborhood optimum is evidence about that neighborhood only.
- **Confidence:** High in the measured set growth; medium in the recommended two-tier policy; low in hidden-instance runtime transfer.

### `R069` A second precedence pass closes the measured ordering gap cheaply

- **Status:** Confirmed on a precommitted holdout and four retained regimes.
- **Finding:** One-pass repair froze a footprint competitor's successor and proved C=`10.0` inside the wrong neighborhood despite a checked C=`0.0` oracle. Re-running only precedence closure after footprint expansion freed one additional activity and proved zero.
- **Scale evidence:** The targeted pass changed public `43→45`, irregular `27→29`, coupled `23→25`, and cross-module delay `18→18`. This is materially smaller than recursive fixed-point closure (`54`, `53`, `49`, `18`). Scores remained public `62.7`, irregular `31.0`, coupled `920.0`, and cross-module `76.0`; all outputs were dual-scored and clean under both closure policies.
- **Relevance:** Dependency ordering should be repaired at the boundary that produced the omission, not by automatically consuming the whole connected scheduling graph. Bounds remain neighborhood-conditional unless an independent lower bound makes the score globally decisive.
- **Limitation:** The second pass does not recursively add contract peers or footprint competitors of newly added dependencies. A future counterexample may justify another bounded tier, but this evidence does not justify fixed-point expansion.
- **Confidence:** High in the failure and correction; high in measured neighborhood growth; medium in hidden-instance transfer.

### `R070` Logical neighborhood coverage and search power require separate tiers

- **Status:** Confirmed by two opposing precommitted regimes.
- **Finding:** An expanded dependency neighborhood fixed a C=`10.0` conditional optimum, but replacing the narrower neighborhood caused two 30-second irregular repairs to remain at C=`63.0`; the narrower 27-activity repair reached C=`31.0` under the same production seed and budget.
- **Relevance:** Neighborhood inclusion is not monotonic in time-limited solution quality. A broader subproblem contains the better schedule mathematically but may fail to find it. Run narrow and expanded repairs as protected portfolio members rather than treating breadth as an upgrade.
- **Method:** Tier one keeps objective, contract, precedence, and footprint expansion. Tier two revisits precedence after footprints, then adds contract peers only for activities newly reached in that revisit. Tier two uses a distinct seed and at most ten seconds. Each result is pruned, fully checked, and promoted only if strictly better.
- **Scope evidence:** Targeted contract revisit grows public `45→46`, irregular `29→29`, coupled `25→25`, cross-module `18→18`, and the contract holdout `3→4`; broad all-current-contract expansion would grow public to `52`.
- **Limitation:** Two tiers add runtime and still do not close every alternating dependency chain. The protected incumbent controls score risk, not runtime risk.
- **Confidence:** High in current dominance evidence; medium in hidden-instance and runtime transfer.

### `R071` Evidence schemas must remain stable across fallback branches

- **Status:** Confirmed by an end-to-end production run.
- **Finding:** When guarded A fails, the Scenario C wrapper returned valid output but nested repair telemetry under `direct_c_staged_report`; the normal path exposed analogous fields at the top level. A summary consumer expecting one shape failed after the solve completed.
- **Relevance:** Branch-dependent audit schemas can hide which optimizer ran, lose conditional-bound context, or create false missing-result alarms. Keep the complete nested report and expose stable top-level narrow/expanded activity and telemetry fields on both paths.
- **Confidence:** High.

### `R072` Portfolio order stabilizes a broader stochastic neighborhood

- **Status:** Confirmed on five serial seeds from one checked irregular incumbent.
- **Finding:** Narrow-first repair reached analytical C=`31.0` in 5/5 30-second runs. Each subsequent expanded ten-second repair retained C=`31.0`. All five finals were dual-scored and clean under both closure policies, with five distinct hashes.
- **Relevance:** The expanded neighborhood failed twice when started directly from C=`63.0`, but behaved safely after the narrow tier supplied C=`31.0`. Portfolio order changes search reliability even when both tiers use protected hints.
- **Limitation:** This is one instance, source incumbent, machine, worker count, and serial-load regime. Neither tier proved a bound; optimality comes from the independent analytical lower bound.
- **Confidence:** High for this regime; medium for transfer.

### `R073` A terminal precedence pass closes the measured alternating chain

- **Status:** Confirmed on a precommitted five-activity holdout.
- **Finding:** The expanded tier added a contract peer but left its cross-contract predecessor frozen, then conditionally proved C=`10.0` despite a checked C=`0.0` oracle. One final transitive precedence pass freed the predecessor and proved zero.
- **Scale evidence:** The final pass adds zero activities to current public, irregular, coupled, and cross-module neighborhoods. It therefore covers the observed contract-to-precedence boundary without approaching the much larger fixed-point closures measured in R068.
- **Limitation:** A dependency introduced by the terminal pass can still have unexpanded contract or footprint neighbors. The method is intentionally bounded; another tier requires a new failure and runtime comparison.
- **Confidence:** High in the failure and correction; medium in hidden transfer.

### `R074` Residual dependency closure is real, but fixed-point repair is search-weak

- **Status:** Confirmed by a reproducible frontier audit and two matched irregular repairs.
- **Finding:** After the bounded expanded selector, dependency frontiers contain 8 activities on public, 24 on irregular, 24 on coupled, and 0 on the cross-module holdout. Full alternating closure grows the irregular repair from 29 to 53 activities.
- **Falsification:** A ten-second, eight-worker fixed-point repair from the protected irregular C=`31.0` incumbent returned the identical schedule. The same repair from its C=`63.0` predecessor returned a worse checked C=`84.0` candidate with bound `12.8`; protected selection rejects it.
- **Decision:** Do not add unconditional fixed-point recursion as a production tier. Retain the narrow-first bounded portfolio. Use `scripts/audit_cost_repair_frontier.py` to measure residual exposure and require a matched recovery result before adding another dependency pass.
- **Limitation:** Failure on one irregular regime does not show that fixed-point repair can never help. It shows that logical closure alone is insufficient evidence for spending the runtime budget.
- **Confidence:** High in counts and outcomes; medium in hidden transfer.

### `R075` Final repair quality survives complete identifier permutation

- **Status:** Confirmed on one public-independent irregular regime.
- **Finding:** Bijectively permuting line, station, contract, activity, sector, and location identifiers and shuffling every input table changed the seed-5 construction result from the original run to C=`147.0`, but the same 27-activity narrow repair recovered C=`31.0`; the 29-activity expanded tier retained it.
- **Evidence:** Both scorers agree on C=`31.0` with zero delay, two ECLO nights, three excess access-nights, no hard violations, and clean standard and strict closure screens. No translated incumbent or oracle was supplied.
- **Interpretation:** CP-SAT search order is label-sensitive under wall-time limits, while the protected controller recovered the same semantic optimum. This is evidence against identifier memorization in the final method, not proof of distribution-wide invariance.
- **Confidence:** High in the metamorphic result; medium in generalization beyond this fixture and seed.

### `R076` Strict closure is useful as a score-preserving hedge, not a default law

- **Status:** Confirmed by the third identifier permutation and constrained repair.
- **Finding:** Three independently renamed and shuffled irregular fixtures all reached standard-feasible C=`31.0`, but the third retained one conflict under the stricter buffer-to-buffer screen. Freeing only the two conflicting activities and one precedence successor produced a standard-clean and strict-clean C=`31.0` schedule in 0.282 seconds.
- **Relevance:** The strict rule contradicts four cases in the organizer's stated-feasible sample, so enforcing it throughout search can reject validator-feasible schedules. A final protected repair can nevertheless select an equal-score schedule accepted by both interpretations when one exists.
- **Integrity rule:** Never replace the official-rule incumbent with a higher-score hedge. Report strict status separately from official feasibility, preserve the original candidate, and label any repair proof as conditional on its frozen neighborhood.
- **Confidence:** High in the counterexample and repair; medium in general usefulness; low that strict overlap is the official hidden rule.

### `R077` Strict-hedge dependency closure can be broad but remains fail-safe

- **Status:** Confirmed across six retained strict-conflicted outputs.
- **Finding:** Contract/precedence closure from strict conflicts freed `[11,19,34,41,45,36]` activities out of 40–54. Four cases found equal-score strict-clean schedules in 0.29–2.68 seconds; two consumed the full ten-second cap and retained their original strict-conflicted incumbents.
- **Relevance:** Describe the method as conflict-seeded, not necessarily small. A hard time cap and protected selection control runtime and score risk; they do not guarantee strict cleanliness.
- **Confidence:** High for these six cases; medium for runtime transfer.

### `R078` Post-attempt telemetry must describe the selected artifact

- **Status:** Confirmed by a higher-score strict-clean counterexample.
- **Finding:** A rejected hedge can be strict-clean while the retained lower-score incumbent remains strict-conflicted. Reporting the candidate's conflict count as the final “after” state falsely describes the selected output.
- **Protection:** Keep candidate telemetry and prune evidence, but compute selected-state fields from the promoted artifact only. If promotion fails, final conflict status remains the incumbent's status.
- **Confidence:** High.

### `R079` Line cardinality is data-driven, including Live crossover propagation

- **Status:** Confirmed on a public-independent three-line fixture.
- **Finding:** A Live bridge on one line maps to 12 affected locations across two other lines. No-hint staged solving then proves A=`7.0`, B=`10.0`, and C=`7.0` on the full three-line instance.
- **Relevance:** Production topology and Scenario C ECLO-window logic iterate instance lines rather than assuming the public two-line shape.
- **Limitation:** One compact third-line extension does not cover arbitrary interchange graphs or large multi-line density.
- **Confidence:** High in cardinality handling; medium in larger-network transfer.

### `R080` Adjacent interchange bridges compose without public identifiers

- **Status:** Confirmed on a precommitted public-independent fixture.
- **Finding:** A Live activity spanning two adjacent interchange-to-interchange sectors derives ten unique cross-line locations on the other line: both sectors and all three platforms in both bounds. A Live activity on only the second bridge derives six. The production controller proves score `0.0` for A, B, and C from raw input with one worker.
- **Relevance:** Crossover propagation is applied to every worked interchange bridge and deduplicated at their shared station; it is not hard-coded to one public endpoint pair.
- **Limitation:** The fixture is compact, has only two lines, and does not test a branching interchange graph or simultaneous interacting Live jobs.
- **Confidence:** High for adjacent bridge composition; medium for dense multi-bridge transfer.

### `R081` Cross-line Live congestion changes the optimal lever by scenario

- **Status:** Confirmed on a precommitted public-independent two-bridge trade-off.
- **Finding:** Two opposing Live PM activities each span both adjacent bridges and cannot work in the same week. The urgent three-unit activity needs three standard weeks, forcing seven days of Priority-1 delay in A (`700.0`), but two ECLO weeks cover its workload in B/C (`10.0`) while preserving the later activity's deadline.
- **Relevance:** The production formulation jointly handles crossover closure, one-access-per-activity-week, hard B dates, A's ECLO prohibition, and C's two-week per-line ECLO window. It does not apply a fixed qualitative lever order.
- **Limitation:** Two activities make the analytical lower bound simple; this does not measure large congested search performance.
- **Confidence:** High for the encoded interaction and full-instance proofs; medium for scaled transfer.

### `R082` A safe Scenario C fallback can conceal a valuable global ECLO move

- **Status:** Confirmed failure on a precommitted eight-activity interacting-Live fixture.
- **Finding:** The protected controller returns safe C=`273.0` with a full-instance lower bound of `21.0` after ten seconds. Its first direct C candidate scores `115.0` but has 14 closure conflicts; two later candidates merely reproduce `273.0`. The bounded cost repair frees all eight activities yet also retains `273.0` after five seconds.
- **Relevance:** Contributor-based neighborhood selection is no longer the bottleneck when every activity is selected. Search needs a structurally meaningful ECLO-window move or more effective full-instance sequencing, not further dependency expansion.
- **Limitation:** The exact optimum is not yet known. A constructive one-week compression argument gives a feasible target below `273.0`, but it must be serialized and checked before becoming an incumbent.
- **Confidence:** High in the measured controller failure and bound gap; medium in the proposed compression trajectory until file-validated.

### `R083` Checked ECLO compaction closes the scaled Scenario C gap

- **Status:** Confirmed and integrated on the precommitted eight-activity fixture.
- **Finding:** A data-derived operator enumerates every way to replace one activity's three standard rows with two adjacent ECLO rows in a gap-free, one-activity-per-week incumbent, shifts later work one week earlier, regenerates `RESULTS.csv`, and promotes only a strictly lower fully checked candidate. The unmocked strict-screened controller improves C from `273.0` to `262.0`; both scorers agree and both closure policies are clean.
- **Lower bound:** All 28 activity pairs conflict as separate PM possessions, so at most one activity can work per week. Every activity needs three standard weeks. Because each Live activity affects both lines, Scenario C's shared two-week ECLO window can shorten at most one activity from three weeks to two. Enumerating all `8!` activity orders with each of the nine choices of compressed activity or none gives minimum `262.0`, matching the candidate.
- **Integrity:** The fixture and blind C=`273.0` failure were committed before the operator was implemented. Candidate generation uses schema properties and checked files, not identifiers, oracle rows, or expected scores. The official public C artifact does not satisfy the operator's structural precondition and remains byte-identical.
- **Limitation:** The operator is intentionally narrow. It does not solve schedules with simultaneous compatible work, idle gaps, dispersed ECLO windows, or multiple compressible lanes. The sound CP-SAT verifier retains `262.0` but still reports bound `21.0`; the exact proof here is the independent finite enumeration.
- **Confidence:** High for this fixture and fail-safe integration; medium for transfer to other serialized bottlenecks; low outside the stated preconditions.

### `R084` Candidate validation must preserve incumbent ECLO state

- **Status:** Confirmed defect, fail-safe impact, corrected and replayed.
- **Finding:** The first compactor implementation set every non-target access to standard while testing a target activity. Full workload and ECLO-window validation rejected the affected candidates, so no invalid schedule could be promoted, but a valid second compaction could be hidden. Non-target ECLO flags are now preserved exactly.
- **Efficiency:** Equivalent removals inside one consecutive three-week block can produce identical files. Signature deduplication reduces the real scaled run from 20 materialized candidate directories to eight while retaining the same selected C=`262.0` hash; audit-directory size falls from 580 KB to 432 KB.
- **Cross-regime result:** A reproducible strict-screen audit of all 19 retained Scenario C incumbents finishes in 0.19 seconds: 17 are structurally inapplicable, one has no legal candidate, and the already-optimal scaled case remains unchanged. No candidate is falsely promoted.
- **Limitation:** Deduplication reduces redundant work but worst-case file generation remains proportional to the number of unique eligible transformations times submission size. Large serialized hidden instances still need a specific runtime stress test.
- **Confidence:** High in state preservation, deduplication, and fail-safe selection; medium in worst-case scale.

### `R085` Exact score ordering removes serialized-compaction scale overhead

- **Status:** Confirmed on a precommitted 120-activity, 360-week fixture.
- **Finding:** A zero-score serialized incumbent initially spent 8.34 seconds checking 120 candidates although Scenario C's objective cannot be negative. A nonnegative-floor exit reduces this to 0.035 seconds. On a separately frozen reverse ordering with score `2,880,360`, exhaustive validation checks 120 unique candidates in 8.29 seconds; exact in-memory score ordering checks the best-ranked candidate in 0.24 seconds and selects the same `2,864,830` result.
- **Safety:** The ranker recomputes contract completion, official priority weights and activity nudges, and ECLO count under the exact transformation. The one-activity-per-week precondition proves excess access remains zero. Exhaustive mode reports zero prediction mismatches over all 120 candidates and remains available for audits. Every promoted candidate is still serialized and passed through the full evaluator and requested strict closure screen.
- **Production replay:** The unmocked eight-job controller checks one of eight unique transformations, prunes seven only after its predicted and serialized scores agree, and returns the same strict-clean C=`262.0` hash. Sound verification retains the incumbent.
- **Limitation:** Ranking is exact only under the operator's serialization preconditions. Signature generation and score calculation remain quadratic in the number of access rows, although measured overhead is small at 120 activities.
- **Confidence:** High in the score-order equivalence and measured speedup; medium beyond the tested scale.

### `R086` Exact ordering survives contract-level aggregation and mixed priorities

- **Status:** Confirmed on a precommitted three-contract, six-activity holdout.
- **Finding:** Each contract contains two activities, contract priorities span 1–3, and activity priorities span 1–3. The feasible strict-clean source scores C=`23,765`. Exhaustive evaluation of all six unique ECLO transformations reports zero prediction mismatches; ranked and exhaustive modes choose the same hash at C=`21,990`.
- **Safety:** The source fixture and its activity order were committed as `0e0c6c1` before the ranking operator saw them. Both source and selected output agree under the main and independent scorers; the strict closure screen is clean. Production ranking checks one candidate and prunes five only after its predicted score matches serialized evaluation.
- **Limitation:** This falsifies errors in contract maximum-completion aggregation and priority nudges for the covered combinations. It does not independently confirm the locally reconstructed formula against the portal on hidden data.
- **Confidence:** High in implementation equivalence under the operator preconditions; low-to-medium in untested official-validator semantics.

### `R087` Scenario C serialized compaction must iterate across line windows

- **Status:** Confirmed on a precommitted two-line holdout and integrated into both production controllers.
- **Finding:** A one-pass controller lowers the strict-clean source from C=`23,660` to `20,030` but leaves a legal independent-line compaction. Repeating checked improvements reaches C=`18,220`; ranked and exhaustive sequences select the same hash with zero prediction mismatches.
- **Safety:** Every round writes a complete candidate and requires a strict score decrease after full validation. The sequence is bounded by the original access-row count. Activities whose affected lines already contain ECLO are skipped because disjoint serialized activity blocks cannot share that line's two-week window; cross-line Live work marks every affected line.
- **Efficiency:** Ranked mode checks two candidates across three rounds; exhaustive mode checks six. Both promote twice and stop when the remaining lines are occupied.
- **Limitation:** This operator still requires a globally gap-free one-activity-per-week incumbent. It is a safe targeted improvement, not a general Scenario C optimiser.
- **Confidence:** High in checked multipass behavior; medium in how often hidden schedules meet the narrow structural precondition.

### `R088` Existing-window filtering survives unfiltered sequence enumeration

- **Status:** Confirmed on all 24 block orders of both the three-access and four-access two-line holdouts, plus a cross-line Live case.
- **Finding:** An independent audit materializes every structural transformation without applying the existing-window filter and recursively visits every improving state. The ranked production sequence matches the best reachable score in all 48 orders. Across the three-access graphs, all 288 unique candidates that production would filter are infeasible; across the four-access graphs, all 1,920 are infeasible. On the eight-job Live final, all seven unique filtered candidates are also infeasible and the exhaustive best remains C=`262`.
- **Consequence:** The filter removes only candidates that violate the already occupied two-week line window in the tested serialized regimes. It cuts repeated file generation without changing the reachable result.
- **Limitation:** This is exhaustive for four activities and one retained eight-job Live state, not a formal proof over arbitrary topology. Full candidate validation remains the acceptance gate for every unfiltered line.
- **Confidence:** High for serialized three- and four-access Non-live independent lines and the tested all-line Live crossover; medium beyond these structures.

### `R089` Two ECLO upgrades can remove one row from longer activities

- **Status:** Confirmed on a precommitted four-access, two-line holdout.
- **Finding:** The three-row-only operator checks nothing on the strict-clean C=`32,760` source. The generalized transformation removes one standard row from an all-standard activity and marks exactly two retained adjacent rows as ECLO, preserving total workload. Repeated production compaction reaches C=`27,320` after two line-local promotions.
- **Audit:** Exhaustive mode checks 12 unique candidates and reports zero predicted-versus-serialized score mismatches. Ranked mode checks two and prunes ten after exact agreement. Both select hash `ce83a1d4…`; main and independent scorers agree and the strict screen is clean.
- **Order falsification:** Across all 24 activity-block permutations, ranked repeated compaction matches unfiltered exhaustive sequence search. The largest state graph visits 25 schedules and materializes 480 candidates; none of 1,920 candidates skipped by existing-window filtering is feasible.
- **Transfer relevance:** Public activities require up to seven accesses, so limiting the operator to exactly three scheduled rows was not schema-general even though the protected public C artifact is structurally inapplicable.
- **Limitation:** The transformation removes only one row per affected line window and still requires a globally serialized incumbent. Full validation remains the acceptance gate for workload, windows, deadlines, and closures.
- **Confidence:** High in four-access behavior and backward compatibility; medium for longer or irregular access patterns until separately exercised.

### `R090` Generalized compaction remains exact through seven accesses

- **Status:** Confirmed on a deterministic two-line sweep for access counts 3, 4, 5, 6, and 7.
- **Finding:** At every length, ranked mode checks two serialized candidates and reaches the same final score and hash as exhaustive per-round evaluation. The main and independent scorers agree, strict conflicts remain zero, and all predicted scores match serialized scores.
- **Scale:** Exhaustive unique checks grow linearly from 6 at length 3 to 30 at length 7; duplicate transformations grow from 12 to 180. Exact ordering keeps ranked checks fixed at two. The length-7 source falls from C=`60,060` to `54,620` in under 0.01 seconds in ranked mode.
- **Relevance:** The covered lengths include every `total_accesses` value greater than two in the public data, including the previously untested five- and seven-access activities.
- **Limitation:** Rows are contiguous within serialized activity blocks. Irregular interleaving is outside the current operator's global one-activity-per-week use case.
- **Confidence:** High for access-length arithmetic, workload preservation, and candidate ranking through seven rows.

### `R091` Non-worsening idle normalization can unlock a strict compound gain

- **Status:** Confirmed on two precommitted idle-week holdouts and integrated before ECLO compaction in both production controllers.
- **Finding:** Deleting a globally empty week preserves access rows, ECLO flags, possession groups, workload, and relative order while shifting later work left. On the delayed holdout it strictly improves C=`26,390` to `23,660`, after which ECLO reaches `18,220`. On the counterexample, deleting week 4 leaves C=`910` unchanged but makes the schedule contiguous; ECLO then reaches strict-clean C=`10`.
- **Selection rule:** A fully checked equal-score normalization may be used only as an internal ECLO seed. It is not promoted by itself. The protected incumbent changes only when the composed final artifact is strictly better and fully checked.
- **Predictor hardening:** The ranker always serializes at least the first gap on every affected schedule. Any predicted-versus-serialized mismatch disables early stopping and forces evaluation of all remaining gaps.
- **Limitation:** Only globally empty weeks before the last occupied week are removed. Local idle capacity and partial left shifts remain solver responsibilities.
- **Confidence:** High in the two compound cases, retained-corpus no-regression result, and fail-safe selection boundary.

### `R092` Leading idle time is a removable checked normalization

- **Status:** Confirmed on a precommitted leading-idle holdout and audited against all 19 retained Scenario C incumbents.
- **Finding:** A source delayed by a globally empty week 1 scores C=`27,300`. Removing that week produces the exact previously audited C=`23,660` state; two checked ECLO promotions then reach C=`18,220`.
- **Evidence:** The main and independent scorers agree at `18,220`; the strict closure screen reports zero conflicts. The intermediate hash equals the independently frozen gap-free source hash, so the transformation restores a known state rather than exploiting score-only coincidence.
- **No-regression audit:** The generalized operator sees nine removable weeks across eight retained schedules, serializes one best-ranked candidate for each affected schedule, reports zero prediction mismatches, and promotes none.
- **Integrity:** The delayed source was committed before the operator was widened. Candidate acceptance still depends on complete-file validation, and the official incumbents and portal quotas remain unchanged.
- **Limitation:** The evidence covers global empty-week deletion, not left-shifting one activity into capacity that is only locally idle.
- **Confidence:** High in leading-gap detection, composition, and incumbent preservation.

### `R093` Equal-score normalization ties require structural ordering

- **Status:** A frozen counterexample disproved the original gap-number tie-break; a generic correction is implemented and regression-tested.
- **Failure:** The source has a leading gap at week 1 and an internal gap at week 5. Either deletion lowers C=`2,730` to `1,820`. Choosing week 1 first leaves an internal gap; the remaining shift violates the second activity's planned start, so ECLO never runs and the controller stops at `1,820`.
- **Correction:** For equal predicted scores, checked internal-gap deletions rank before leading-gap deletions. Choosing week 5 makes occupied weeks contiguous without moving the first activity, after which one checked ECLO promotion reaches C=`920`.
- **Evidence:** Source, intermediate, and final artifacts are fully evaluated; the final main and independent scores agree at `920`, and the strict closure screen is clean. The source fixture was committed before the ranker was changed.
- **Scope:** This is a structure-derived tie-break, not an identifier rule or expected-score branch. Score remains the primary ordering key, and every candidate remains subject to full validation.
- **Limitation:** The correction does not exhaustively branch over equal-score internal gaps. If several internal deletions are individually valid but cannot all compose, downstream outcomes could still differ.
- **Confidence:** High in this failure and correction; medium in completeness over more complex equal-score normalization graphs.

### `R094` Corrected idle ordering matches exhaustive small-state composition

- **Status:** Confirmed on all 16 controlled six-row schedules over the frozen eight-week tie fixture.
- **Method:** For every combination of three first-activity weeks from 1–4 and three second-activity weeks from 5–8, an independent audit enumerates every reachable fully valid non-worsening idle-deletion state. It runs exhaustive per-round ECLO compaction from every state and compares the best composed score with the production greedy pipeline.
- **Result:** Production and exhaustive composition match in 16/16 cases. Each selected score also agrees with the independent scorer. The largest normalization graph contains three unique states.
- **Protection:** The audit compares scores, not only chosen hashes, because equal-score normalization paths can legitimately produce different files. It uses full evaluation and the strict closure screen for every retained state.
- **Limitation:** This finite audit fixes one line, two activities, six rows, and an eight-week horizon. It does not prove greedy completeness for larger branching normalization graphs.
- **Confidence:** High for the enumerated state space; medium for transfer to larger multi-line schedules.

### `R095` Final solver winners require the same checked post-processing

- **Status:** A frozen counterexample disproved the assumption that pre-verification compaction is sufficient; the correction is integrated into both production controllers.
- **Failure:** The heuristic branch normalizes from C=`26,390` to `25,480` but remains non-serialized because two different-line activities share week 7. Verification then selects a distinct strict-clean C=`23,660` serialization. The prior pipeline copied it immediately, never applying the compactor that could lower it to `22,760`.
- **Correction:** After verification, targeted cost repair, expanded repair, and any strict hedge have selected the final incumbent, a shared fail-closed function reruns checked idle normalization and repeated ECLO compaction. It promotes only a strict score decrease.
- **Evidence:** Both production controllers are exercised on the frozen branch. They finish at dual-scored C=`22,760`, zero strict conflicts, from a C=`23,660` final-selection source. The early post-processor still cannot improve the deliberately non-serialized heuristic beyond `25,480`.
- **Integrity:** The input and invalid/valid fixture corrections were committed before the production change. The final gate has no expected-score or identifier branch, writes complete artifacts, and does not touch A or B.
- **Limitation:** The post-processor remains deliberately narrow; it does not replace general solver search for non-serialized selections.
- **Confidence:** High in the identified pipeline gap, shared implementation, and fail-closed promotion boundary.

### `R096` Final post-processing is a no-op on every retained C incumbent

- **Status:** Confirmed across all 19 Scenario C rows in the executable benchmark matrix.
- **Result:** The strict audit checks nine idle-shift candidates and zero ECLO candidates. It promotes nothing and preserves every submission hash. Main and independent scores agree for every selected artifact.
- **Official protection:** Public C remains exactly `62.7` with hash `30247f57…`, zero strict conflicts, and no generated replacement.
- **Runtime:** The complete retained audit takes 1.21 seconds; the slowest case takes 0.49 seconds on the current machine.
- **Scope correction:** Two historical benchmark incumbents begin with strict-only diagnostic conflicts and remain byte-identical. This does not represent an unsafe promotion; production strict mode would not admit those sources as final incumbents.
- **Confidence:** High in retained-corpus safety and measured overhead; medium in unseen large serialized candidates.

### `R097` Zero-score normalization cannot unlock a strict gain

- **Status:** Confirmed by the nonnegative Scenario C objective and retained-corpus replay.
- **Reasoning:** Idle deletion can be useful as an equal-score seed only when a later transformation can make the final score strictly lower. From score zero, no legitimate Scenario C result can be lower, so serializing any idle candidate is provably unnecessary.
- **Implementation:** The idle normalizer still records the number of removable gaps, but emits no candidate when the current score is zero. This applies after any earlier strict promotion also reaches zero.
- **Replay:** The retained C corpus still exposes nine removable weeks, but fully checked idle files fall from eight to three in the dedicated idle audit and from nine to three in the final-selection audit. Promotions, hashes, independent scores, and strict results are unchanged.
- **Runtime note:** Total retained-audit wall time remains about 1.22 seconds because source loading, dual scoring, and closure checks dominate these small cases; the benefit is reduced file generation rather than a claimed timing speedup.
- **Confidence:** Very high in soundness; high in candidate-count reduction.

### `R098` Full final post-processing scales safely to 120 activities

- **Status:** Confirmed on the independent 120-activity, 360-week scale fixture.
- **Method:** Run the same checked idle-normalization-plus-ECLO sequence used after final production selection, then independently rescore and apply the strict buffered closure screen.
- **Floor case:** A C=`0` source emits no idle or ECLO candidate and remains byte-identical.
- **Positive case:** A reverse-order C=`2,880,360` source has no removable idle week; exact score ordering checks one ECLO candidate, prunes 119, and selects strict-clean C=`2,864,830`, a decrease of `15,530` confirmed by both scorers.
- **Runtime:** The two cases complete in about 0.56 seconds combined on this machine. Treat timing as local evidence, not a competition runtime guarantee.
- **Confidence:** High for this scale regime; medium for denser multi-line inputs with many removable gaps.

### `R099` Prediction distrust must not restore the harmful idle-gap tie rule

- **Status:** Confirmed by fault injection on the frozen equal-score gap counterexample.
- **Failure:** Once any predicted idle score disagreed with serialized evaluation, the normalizer correctly checked every candidate but broke equal actual-score ties by the smallest week number. That could reselect a leading gap and lose the later ECLO improvement the internal-gap rule was introduced to preserve.
- **Correction:** Candidate selection now uses the same `(internal before leading, then week)` tie key as initial ranking, including after prediction distrust activates.
- **Falsification:** Deliberately false predictions rank leading week 1 first and force exhaustive checking. The checked tie still selects internal week 5 at C=`1,820`, preserving the path that can reach C=`920`.
- **Scope:** This changes only equal-score tie handling under a predictor mismatch. All retained audits keep the same scores and hashes.
- **Confidence:** High.

### `R100` Many-gap final post-processing remains practical in the measured scale regime

- **Status:** Confirmed on an independent 60-activity, 240-week schedule with 59 internal idle weeks.
- **Construction:** Reverse the activity order and separate consecutive three-week activity blocks by one globally idle week. The source is standard-feasible, strict-buffer clean, and scored identically by both implementations before production post-processing sees it.
- **Result:** The checked normalizer performs 59 promotions with 59 serialized candidates and zero prediction mismatches; the resulting contiguous schedule enables one checked ECLO promotion. C falls from `1,116,689` to dual-scored, strict-clean `733,120`, a decrease of `383,569`.
- **Runtime:** About 1.54 seconds locally for the complete final helper. This falsifies an immediate runtime failure at this size, but the one-gap-per-round implementation still scales with gap count and submission size.
- **Integrity:** The generator uses only schema-derived activity ordering and complete candidate validation. This is a synthetic robustness result, not an official score change.
- **Confidence:** High for the measured case; medium for much larger dense inputs.

### `R101` Greedy normalization matches full branching search on two independent lines

- **Status:** Confirmed on a complete 256-case family with four activities, two ECLO lines, and up to 16 reachable non-worsening normalization states per case.
- **Method:** In each activity's four-week block, omit one of four positions, covering all `4^4` gap patterns. For every valid source, compare production's greedy checked normalization plus exhaustive ECLO sequence against every reachable strict-clean non-worsening normalization state followed by exhaustive ECLO composition.
- **Result:** Production and full branching search return the same final score in 256/256 cases; both local scorers agree on every production result. No counterexample was found.
- **Boundary:** Activities retain the fixture's common planned start and fixed block order. This materially widens the earlier one-line, two-activity audit but does not prove arbitrary precedence or planned-start structures.
- **Confidence:** High for this bounded family; medium beyond it.

### `R102` Planned starts and precedence did not break greedy normalization in 768 cases

- **Status:** Confirmed across three complete 256-pattern variants of the two-line, four-activity branching family.
- **Variants:** Staggered planned starts at block boundaries; a four-activity precedence chain; and both constraints together.
- **Oracle:** For every source, enumerate every reachable strict-clean non-worsening normalization state and exhaustive repeated ECLO composition, then compare with the checked production greedy path and independently rescore it.
- **Result:** Final scores match in 768/768 cases. Staggered starts reduce the largest reachable graph from 16 to five states, demonstrating that infeasible earlier shifts are actually excluded rather than ignored.
- **Boundary:** Fixed activity block order and one omitted week per block remain controlled simplifications. Arbitrary overlapping access patterns are outside the normalizer's serialized ECLO precondition.
- **Confidence:** High for the tested constrained family.

### `R103` Historical validator ZIP names are unsafe release selectors

- **Status:** Confirmed by archive hashes and the append-only official ledger.
- **Risk:** `deliverables/validator/A.zip` is the failed A-001 upload, while A-002 is the confirmed A=`137.9` file. The unnumbered B/C ZIPs also differ from the confirmed B-001/C-001 upload archives. Selecting by the generic filenames could silently submit stale bytes.
- **Control:** `scripts/package_final_submissions.py` deterministically archives only the protected `deliverables/public/{A,B,C}` files into `deliverables/final-submission`. Its manifest records archive hashes, member hashes, official run IDs, scores, and protected submission hashes.
- **Verification:** Each final ZIP has exactly the three required root members; every archived member hash equals the protected public manifest. A regression recomputes both archive and member hashes.
- **Boundary:** These are ready-to-inspect local packages. No portal upload is authorized or performed.
- **Confidence:** Very high.

### `R104` Pre-upload readiness must be recomputed, not inferred from filenames

- **Status:** Implemented and currently passing for A/B/C.
- **Control:** `scripts/audit_final_submission_readiness.py` reloads the current public dataset and protected artifacts, checks hard feasibility and strict closures, compares the primary and independent scores with the official scores, and verifies submission, archive, and per-member hashes plus the exact three-file root structure.
- **Result:** All eight checks pass independently for A, B, and C; the machine-readable readiness report marks every scenario and the aggregate `all_ready` true.
- **Boundary:** This detects local drift and packaging errors. It does not emulate undocumented validator behavior and does not contact the portal.
- **Confidence:** Very high for artifact integrity; high for known validated semantics.

### `R105` Idle score prediction retained an obsolete excess coefficient

- **Status:** Confirmed and corrected.
- **Failure:** The idle normalizer predicted Scenario C with `20 × excess`, while the published and officially confirmed objective uses `7 × excess`. On excess-bearing schedules every predicted candidate would differ from full evaluation by `13 × excess`.
- **Safety boundary:** Global idle deletion preserves the excess count, and every serialized candidate is fully evaluated. The first mismatch already disabled prediction-based early stopping, so the error caused exhaustive fallback rather than an invalid promotion or wrong protected score.
- **Correction:** Use coefficient `7`. On the retained irregular C incumbent with three excess nights, the predictor now reproduces evaluated C=`31.0` exactly. Every idle/ECLO retained, branching, constrained, and scale audit preserves its scores and hashes.
- **Confidence:** Very high.

### `R106` Shared production arithmetic needs an O(contracts) point-score path

- **Status:** Implemented after rejecting the first performance-regressing refactor.
- **Motivation:** The active evaluator, solver, and two compaction predictors duplicated contract weights, activity nudges, and B/C unit costs. An unused per-activity cost helper also preserved the superseded pre-A-002 scoring shape and could be reused accidentally.
- **Correction:** `objective.py` is now the single production definition for official constants, contract-completion cost curves, and point delay scores. The evaluator, solver, flexible solver, and both predictors consume it. Point scoring rejects incomplete or extra contract mappings instead of silently undercounting. The raw-CSV independent scorer intentionally keeps separate arithmetic.
- **Rejected implementation:** The first shared point scorer rebuilt every contract's full horizon vector for each candidate. Semantics passed, but 59-gap runtime rose from about 1.50 to 6.93 seconds and ranked 120-activity ECLO runtime from 0.25 to 1.27 seconds.
- **Accepted implementation:** Compute only the requested contract/week cost for prediction. Rerun timings return to about 1.54 seconds for 59 gaps and 0.25 seconds for ranked 120-activity ECLO; scores, hashes, candidate counts, and mismatch counts remain unchanged.
- **Confidence:** Very high in arithmetic equivalence; high in restored measured performance.

### `R107` Final bytes are traceable to the exact confirmed portal uploads

- **Status:** Confirmed locally from preserved immutable archives and official ledger hashes.
- **Chain:** Final A/B/C members equal the protected public files; those same bytes equal every member in A-002, B-001, and C-001 respectively. Each preserved upload archive itself matches the SHA-256 recorded at upload time.
- **Readiness:** Ten checks per scenario now cover final archive structure/hash, protected member/submission hashes, confirmed-upload archive/member hashes, both scores, hard feasibility, and strict closure cleanliness. All 30 checks pass.
- **Boundary:** Repacking changes ZIP metadata and therefore the final ZIP hash, but not any CSV byte. The preserved numbered archives remain the evidence of what the portal evaluated.
- **Confidence:** Very high.

### `R108` The local PS1 pack is byte-identical to the exact upstream commit

- **Status:** Confirmed for every public PS1 file available in the repository, excluding `.DS_Store`.
- **Reference:** Organizer `main` resolves to `966c976005db2e3e40a691cff268fdb8f396a5df`; the locally retained README SHA-256 is `e7d8f9457e62a1732fc7986cea57ad5fbd595e7cabe2e8b789e673c8335bd253`.
- **Method:** A shallow clone stalled and ended with a sideband disconnect, so it was not accepted as evidence. The fallback enumerated the local PS1 files, fetched each corresponding raw file from the exact commit, and compared bytes directly.
- **Result:** All 14/14 files match. This excludes silent local drift in the available public pack.
- **Boundary:** The comparison cannot observe portal-only notices, validator code, runtime limits, or unpublished changes.
- **Confidence:** Very high for public repository bytes; none for portal-only state.

### `R109` Core hard-constraint thresholds survive boundary mutation

- **Status:** Confirmed locally with 14 complete-submission mutations derived from the officially accepted A/B/C artifacts.
- **Accepted edges:** The protected schedules already exercise legal `PC + 3C`, legal `4C`, exact workload, zero-lag predecessor separation, and nominal capacity. Scenario C's one-extra-group mutation is not tagged as a capacity breach; the next group is. Scenario B counts three added groups as soft excess without a capacity hard failure; Scenario A rejects one.
- **Rejected edges:** `5C`, `PC + 4C`, half a workload unit missing, successor starting in its predecessor's completion week, workfront overflow, out-of-range allocation index, Scenario A ECLO, pre-start work, week 31, and Scenario B late completion each trigger the intended hard-rule diagnostic.
- **Boundary:** Some group-splitting mutations also create closure conflicts. The assertions isolate the capacity and legal-mix diagnostics; they do not misreport those mutated submissions as globally feasible.
- **Confidence:** High in the local evaluator's thresholds and their agreement with the published rules; official hidden-validator equivalence remains unproved.

### `R110` ECLO ranking must include excess even under global serialization

- **Status:** Corrected and falsified on a zero-supply Scenario C mutation.
- **Finding:** The ECLO ranker described its prediction as exact but omitted the `7 × excess` term. One-activity-per-week serialization normally makes excess zero when supply is positive, but the schema permits supply zero; removing one access can then reduce paid excess.
- **Safety boundary:** Every materialized candidate was fully evaluated. The first mismatch disabled pruning, so the omission caused exhaustive fallback rather than a false promotion. It could still waste runtime or invalidate the exact-order claim.
- **Correction:** Add the exact per-activity zero-supply footprint contribution to every remaining access. Precompute this value once per activity to avoid repeating topology expansion for every candidate.
- **Falsification:** On a copied two-line serialized fixture with one used location changed to supply zero, the source has six excess nights. Ranked and exhaustive selection now have zero prediction mismatches and identical selected score/hash. The 120-activity benchmark remains zero-mismatch and measures 0.244 seconds ranked versus 8.381 seconds exhaustive in the recorded rerun.
- **Confidence:** High in the corrected serialized precondition; candidate files remain the final authority.

### `R111` Evaluator and solver legal-mix rules are extensionally equivalent

- **Status:** Confirmed over every non-empty PM/PC/C count triple with zero through five activities of each type.
- **Method:** Compare the evaluator predicate with the independent algebraic form used by both CP-SAT models: at most one PM and one PC, `C ≤ 4 − PC`, and `PC + C ≤ 4(1 − PM)`.
- **Result:** All 215 combinations agree, covering valid `PM`, `PC + 0..3C`, and `1..4C` groups plus multi-PM, multi-PC, mixed-PM, and over-capacity rejections.
- **Boundary:** This proves equivalence of the implemented count rules, not the organizer's hidden validator. Input parsing still controls which access-type strings can reach either implementation.
- **Confidence:** Very high in solver/evaluator equivalence for the enumerated domain.

### `R112` Exact scenario capacity domains match the published policy

- **Status:** Confirmed over supply zero through five and zero through ten candidate activities.
- **Result:** Scenario A exposes at most nominal supply groups; C exposes at most supply plus one; exact bridge-safe B exposes one group per candidate and therefore cannot remove paid excess solutions.
- **Heuristic boundary:** Direct-heuristic B intentionally exposes at most supply plus one to control group-label symmetry. It cannot certify infeasibility or replace a protected incumbent without the unrestricted bridge-safe path.
- **Verification:** All 66 supply/candidate pairs match these four policies, including zero supply and candidate counts below the available group limit.
- **Confidence:** Very high in the domain calculation; solver search can still fail to find an incumbent within time.

### `R113` Malformed output cannot improve the protected result silently

- **Status:** Confirmed locally with ten isolated mutations of the protected A submission.
- **Rejected access/occupancy forms:** duplicate activity-week access, non-chronological `access_seq`, missing required occupancy, duplicate occupancy, unexpected footprint occupancy, and an empty possession-group label.
- **Rejected result forms:** missing contract, false completion date/overrun, scenario disagreement, and duplicate contract row.
- **Method:** Each mutation starts from a fresh complete copy; the protected source is never edited. Assertions require the rule-specific hard diagnostic rather than merely checking a generic failure flag.
- **Boundary:** CSV parser failures and unknown activity handling have separate tests. This is local evaluator evidence, not an official validator run.
- **Confidence:** High in the covered anti-exploit gates.

### `R114` Structural-hint closure screening is week-local

- **Status:** Confirmed on a precommitted 360-activity, 320-contract independent holdout.
- **Finding:** Re-screening the complete accumulated schedule for every candidate structural-hint row caused most elapsed time. Closure conflicts are week-local; an accepted provisional schedule cannot gain a conflict in another week when a row is added only to week `w`.
- **Correction:** Index accepted access and occupancy rows by week, then screen the complete existing-plus-candidate state only for `w`. This changes preprocessing scope, not the model or validation gate.
- **Evidence:** With identical input hash, one-worker policy, and budgets, A/B/C preserve scores `280/400/280`, stages, submission hashes, and zero strict conflicts. Recorded runtimes improve `110.705→15.140`, `118.942→15.162`, and `232.015→39.090` seconds, or 5.94–7.84×.
- **Boundary:** One generated fixture and one seed establish a real scale defect and exact replay, not universal speed-up or hidden-instance transfer. Per-step differential testing remains the next semantic falsification.
- **Confidence:** High in this replay; medium in general performance transfer.

### `R115` Incremental full and week-local closure decisions are equivalent

- **Status:** Confirmed for 1,152 realistic incremental decisions.
- **Method:** Replay all 192 occurrences from the failed public A-001 artifact in forward, reverse, and hashed orders under both published and strict buffer-overlap policies. Retain a candidate only when the accumulated schedule is clean, matching the structural-hint invariant.
- **Result:** Full accumulated screening and complete affected-week screening return identical conflict tuples for every decision. The six replays include 33 rejected candidates, so the comparison exercises both acceptance and conflict paths.
- **Interpretation:** This directly supports the semantic premise behind `R114`: with a previously clean schedule, adding one week-local occurrence cannot create a conflict outside its week.
- **Boundary:** The activity orders and topology come from one public artifact; this is differential local evidence, not an official validator result.
- **Confidence:** Very high in the week decomposition implemented by the closure checker.

### `R116` Activity footprints should be cached per immutable instance

- **Status:** Confirmed by before/after profiling and a complete A/B/C replay.
- **Finding:** After week-local screening, one profiled 360-activity A run still made 544,500 `activity_footprint` calls, consuming 18.875 of 23.306 profiled seconds; CP-SAT used only 1.164 seconds.
- **Correction:** Cache each derived footprint inside its loaded `Instance`, keyed by the frozen `Activity` value. The cache is excluded from equality and construction so `dataclasses.replace` receives a fresh cache rather than inheriting topology-derived state.
- **Evidence:** The post-cache A profile falls to 4.488 seconds and 8.18 million calls from 23.306 seconds and 21.45 million; footprint calculation leaves the top 25 cumulative sites. A/B/C retain exact scores `280/400/280`, stages, hashes, and zero strict conflicts while recorded unprofiled time falls `14.776→3.014`, `14.873→1.308`, and `38.586→11.218` seconds.
- **Boundary:** Inputs are treated as immutable after loading. The cache adds memory proportional to distinct activities queried. Timings compare consecutive deterministic local replays and remain host-specific.
- **Confidence:** Very high in semantic preservation across the current suite; high in the measured bottleneck removal.

### `R117` Doubled modular scale requires the sound fallback for Scenario A

- **Status:** Confirmed on a fixture frozen before solver execution.
- **Fixture:** 720 activities, 640 contracts, 4,476 locations, 1,280 oracle access rows, and 4,480 oracle occupancy rows; the independently built A oracle is dual-scored and hard-feasible at `560.0`.
- **Result:** Under the same one-worker fixed policy, A/B/C succeed at `560/800/560`, with zero strict conflicts, in 13.395/4.782/27.517 seconds. Total runtime is 2.94× the cached 360-activity replay for 2× the activities.
- **Failure signal:** A's complete structural hint reaches a 148,402-variable, 344,881-constraint model but returns `UNKNOWN` after its two-second direct-heuristic budget. The unrestricted fallback reaches and proves `560.0` within three seconds; the incumbent is never taken from the failed stage.
- **Boundary:** The fixture repeats independent modules and tests scale, not new topology or coupling. Its exact score scaling is not evidence for arbitrary hidden instances.
- **Confidence:** High in fail-safe behavior and measured scale; low in extrapolation beyond modular structure.

### `R118` A complete checked constructor output is an incumbent, not merely a solver hint

- **Status:** Confirmed after a precommitted dense failure and fault injection.
- **Finding:** The structural constructor placed all 164 dense activities, but CP-SAT returned `UNKNOWN` before emitting the same assignment; the fixed-budget portfolio failed 0/3 despite an available schedule.
- **Correction:** When the constructor is complete, rebuild chronological `access_seq`, serialize all rows temporarily, and require the full evaluator plus the requested closure policy. Only a fully checked candidate becomes a protected incumbent; incomplete or invalid constructions remain hints only.
- **Evidence:** The unchanged dense holdout recovers A/B/C=`0.0`, dual-scored with zero strict conflicts. The candidate is not copied from the independent oracle: both Live activities exchange weeks 41/42. Removing one occupancy row during temporary serialization sets `structural_hint_feasible=false` and emits no submission.
- **Boundary:** This improves feasible-incumbent delivery, not the constructor's completeness. Positive-score hints still require solver search for improvement, and local full-gate correctness remains bounded by implemented-rule coverage.
- **Confidence:** High after retained-suite, malformed-output, fault-injection, independent-oracle, and readiness checks.

### `R119` A checked zero objective needs no optimization model

- **Status:** Confirmed with exact-output replay and a dedicated regression.
- **Finding:** Dense Scenario B spent 14.095 profiled seconds after immediate hint recovery; two model builds dominated, including 1.8 million `add_hint` calls. The solver itself used 0.481 seconds.
- **Correction:** Before model construction, fully evaluate a supplied incumbent and apply the requested closure policy. If its score is exactly zero, emit it unchanged as primary-optimal because every delay, excess, and ECLO term is nonnegative. Do not claim row-count tie optimality.
- **Evidence:** Dense A/B/C retain exact hashes and scores while runtime improves `1.070→0.580`, `12.321→0.679`, and `2.596→1.407` seconds. A direct zero-floor test reports zero variables, constraints, and solve rounds, with both scorers agreeing.
- **Boundary:** Only score zero qualifies. Positive-score incumbents, malformed hints, and strict-conflicting hints continue through rejection or full model search.
- **Confidence:** Very high in primary-score optimality and gating; high in measured runtime removal.

### `R120` Checked complete hints preserve positive scores, not necessarily schedule bytes

- **Status:** Confirmed on fresh 360- and 720-activity A/B/C replays.
- **Result:** The current controller retains scores `280/400/280` and `560/800/560`, with both scorers agreeing and zero strict conflicts in all six cases. The 720-activity A stage now returns its fully checked constructor incumbent instead of waiting for the fallback.
- **Hash boundary:** B remains byte-identical. A and C select different equal-score checked schedules, so historical exact-hash claims apply to their recorded before/after experiments, not every future controller replay.
- **Interpretation:** Incumbent selection is score- and validity-based. Output-byte identity is required for protected official artifacts and controlled regression comparisons, not for independently reconstructed synthetic optima.
- **Confidence:** High in current positive-score safety; medium in transfer beyond tested structural regimes.

### `R121` A reconstructed optimum is evidence, not automatic release promotion

- **Status:** Confirmed on a fresh current-code public replay.
- **Result:** Seed 6 locally reconstructs A=`137.9`, B=`30.0`, and C=`62.7`; both scorers agree and the full evaluator reports no confirmed hard violation.
- **Promotion rule:** The audit-only strict-buffer screen reports A=`4`, B=`0`, C=`9` conflicts. Because the protected official artifacts have the same scores, zero strict conflicts, and official-validator confirmation, the fresh hashes are regression evidence only and cannot replace them.
- **Boundary:** The stricter screen is not a confirmed official hard rule. Its conflicts do not invalidate the fresh replay under the published rules, but equal-score artifact selection should preserve the stronger hedge when available.
- **Confidence:** Very high in non-replacement and score equality; high in local feasibility; no new official validation claim.

### `R122` Checked construction transfers to a doubled dense bottleneck, but model assembly dominates

- **Status:** Confirmed on a fixture committed before solving.
- **Result:** The 324-activity, 324-contract dense holdout succeeds in A/B/C at score zero, with both scorers agreeing and zero standard or strict conflicts. Candidate access weeks differ from the separately generated oracle for both Live activities.
- **Scale signal:** End-to-end times are 2.363/2.774/5.478 seconds. An A profile attributes 2.900 of 3.479 profiled seconds to two flexible-solver calls; the direct call builds 284,048 variables and 457,994 constraints even though its fully checked constructor already attains the nonnegative floor.
- **Consequence:** The next safe optimization is to validate a complete structural zero-floor candidate before materializing CP-SAT, while retaining full model construction for incomplete, invalid, or positive-score candidates.
- **Boundary:** This generator still has repeated dense modules and an easy zero optimum. It tests scale and trust gates, not arbitrary coupling or positive-score optimality.
- **Confidence:** High in measured transfer and diagnosis; medium in extrapolation beyond this family.

### `R123` Validate a complete structural zero-floor candidate before model assembly

- **Status:** Confirmed after fault injection and positive-score replay.
- **Finding:** Once a deterministic constructor has produced a complete candidate at objective zero, CP-SAT cannot improve the nonnegative primary objective. Building hundreds of thousands of variables only to rediscover that floor is avoidable.
- **Implementation:** The constructor is model-independent. A complete candidate is serialized and must pass the full evaluator plus the requested closure policy. Only an exact zero score returns before model construction; incomplete, invalid, strict-conflicting, or positive-score candidates continue to the original model path.
- **Evidence:** The 164-activity A/B/C aggregate falls `2.666→0.398` seconds and the 324-activity aggregate `10.615→0.955`, with every stage, score, strict count, and hash preserved. Positive-score 360/720 replays preserve all six hashes and scores.
- **Falsification:** A missing occupancy row is rejected. Patching model construction to raise proves a strict-clean zero candidate never builds a model; injecting a strict-only conflict under strict mode instead reaches the model path. An initial duplicated-constructor implementation slowed the 720-activity replay and was refactored rather than accepted.
- **Boundary:** The floor proof covers the primary score only, not row-count tie optimality. Wall timings are local, and zero-floor structure is not evidence for arbitrary positive-score dense cases.
- **Confidence:** Very high in the mathematical floor and validation gate; high in implementation safety across retained regimes.

### `R124` Dense positive-score construction fails when one activity requires ECLO

- **Status:** Confirmed on a holdout frozen before solving.
- **Finding:** Adding one independent three-unit activity with only two on-time weeks to the 324-activity dense case preserves analytical optima A/C=`7.0`, B=`10.0`. The fixed controller reaches A/C but fails B: its constructor emits all 324 standard-only activities and omits the one activity that needs two ECLO rows.
- **Failure mechanism:** The direct B model has 351,754 variables and returns `UNKNOWN`; the unrestricted fallback expands to 13,179,238 variables because every same-location candidate becomes a potential paid group, then also returns `UNKNOWN`.
- **Consequence:** Structural construction must represent workload with ECLO when dates are rigid. Expanding the unrestricted model is not an adequate fallback at this density.
- **Boundary:** The added trade-off is spatially independent of the dense corridor. This isolates ECLO construction but does not yet test an ECLO activity coupled into the bottleneck.
- **Confidence:** Very high in the recorded failure and analytical optimum; high in the diagnosis.

### `R125` Deadline compression gives a resource-independent Scenario B ECLO bound

- **Status:** Confirmed on the frozen positive dense holdout and pinned on the public instance.
- **Finding:** For an activity with workload `d` and `r` release-to-deadline weeks, at most one row can run per week and each ECLO row adds half a unit. Using the maximum useful `min(d, r)` rows therefore forces at least `max(0, 2d - 2r)` ECLO rows. Summing this nonnegative requirement across activities gives a valid resource-independent B lower bound; congestion can only make the true optimum higher.
- **Implementation:** The generic constructor applies that minimum ECLO count, preserves ECLO and access-night values in model hints, serializes any complete candidate, and runs the full evaluator plus requested closure policy. It skips CP-SAT verification and cost repair only when the checked score exactly equals the full-instance workload bound.
- **Evidence:** The precommitted 325-activity B failure recovers at its analytical `10.0` bound in 0.155 seconds with 646 rows, zero strict conflicts, and independent rescoring. A separate production-path replay reaches A/B/C=`7.0/10.0/7.0`. The public workload calculation returns `30.0`, matching the protected official B score without using public identifiers in the formula.
- **Falsification:** A proof-unaware intermediate constructed checked B=`10.0` in 0.445 seconds, then continued through a 13.18-million-variable verification path and later failed to terminate promptly; it was manually interrupted after more than two minutes. Two mock repair tests also exposed that a claimed global proof must be false whenever a lower later candidate exists.
- **Boundary:** Equality with this bound proves only the B primary objective. A candidate above it is not proved optimal and must continue through the model path. The current dense trade-off is spatially independent, so interacting ECLO/capacity/closure cases remain the next test.
- **Confidence:** High in the bound derivation and checked return; high in the recorded recovery; medium in construction reliability under coupled positive congestion.

### `R126` A workload bound must not absorb possession-capacity cost

- **Status:** Confirmed on a fixture committed before solver exposure.
- **Finding:** Three deadline-tight activities share one three-location footprint: two PC and one C. Each needs two ECLO rows in weeks 1–2, forcing `6 × 5 = 30`. The two PC activities cannot occupy one local possession group; the C activity legally bridges them into one transitive closure component using different local groups. Two groups against supply one at three locations over two weeks force `6 × 7 = 42` excess cost. The exact B optimum is therefore `72`.
- **Falsification result:** The structural hint is partial at two of three activities. The heuristic finds checked `72` but reports no proof; `verification_skipped_primary_proven=false`. The bridge-safe full model then proves score and bound `72`. Production therefore does not mistake the workload-only `30` for the resource-constrained optimum.
- **Anti-copy evidence:** The solver receives no oracle path and emits a different submission hash while matching both scorers and the strict closure screen. End-to-end time is 0.015 seconds under the fixed one-worker policy.
- **Boundary:** This is a compact exact case, not a scale result. It covers ECLO plus transitive local packing and excess capacity, but not Live buffers, predecessors, or multiple lines.
- **Confidence:** Very high in the counting proof, validation, and refusal behavior; medium in transfer to large coupled instances.

### `R127` A deliberately relaxed model can certify the public optima independently

- **Status:** Confirmed by an executable raw-CSV audit and an independent rerun.
- **Method:** Parse the eight public input files without importing production code. Model access weeks, ECLO workload, contract completion, predecessors, mandatory PM exclusions, and Scenario C's per-line two-week ECLO windows. Deliberately omit capacity/excess cost, possession packing, workfronts, allocation, and non-PM closures. Every officially feasible schedule therefore maps into this cheaper relaxation, so its optimum is a valid lower bound.
- **Result:** One-worker, no-hint, no-frozen-activity CP-SAT relaxations prove A=`137.9`, B=`30.0`, and C=`62.7`. Separate satisfaction models prove scores at most `137.8`, `29.9`, and `62.6` infeasible. The A certificate additionally enumerates all 5,842 within-horizon A036/A075 access-subset pairs, including oversupply, to compose the mandatory PM-conflict cost with independent contract bounds.
- **Upper-bound check:** The protected A-002/B-001/C-001 CSVs are re-read as feasible witnesses. Production, independent raw-CSV, and a third embedded score calculation agree; strict closures are clean; the bytes match both archived successful uploads and final packages.
- **Sensitivity:** Dropping mandatory PM exclusion lowers relaxed A from `137.9` to `130.9`; forcing A075 on time raises A to `173.6`; five or fewer B ECLO rows are infeasible. Dropping C's two-week ECLO windows lowers C to `30.0`; limiting C to three ECLO rows raises its relaxation to `98.2`, while forcing A036 on time is infeasible. These counterfactuals identify exactly which confirmed rules make the positive floors unavoidable.
- **Boundary:** The certificate covers the exact published bytes and confirmed semantics only. Because the model is intentionally relaxed, it does not construct general schedules or predict hidden-instance quality. Portal validation established witness feasibility and score, not optimality.
- **Confidence:** Very high after source inspection, byte-hash pinning, stored model exports/responses, and an independent successful rerun.

### `R128` A saved certificate is evidence only if its generator still reproduces it

- **Status:** Confirmed by isolated end-to-end regeneration.
- **Risk:** A regression that merely parses committed `CERTIFICATE.json` can pass after the proof script, dependencies, or input semantics drift. Stored solver summaries are inspectable but not self-refreshing.
- **Control:** The audit accepts a dedicated output directory while resolving repository inputs from its own fixed location. A regression launches the exact committed script in a fresh temporary directory, then compares input hashes, analytical contract curves, exhaustive A pair enumeration, relaxed scores/bounds, strict-better infeasibility, and all six sensitivity outcomes against the committed certificate. Nondeterministic timestamps and wall times are excluded.
- **Result:** Isolated regeneration succeeds in 1.340 seconds and reproduces every stable proof fact without altering committed artifacts or protected submissions.
- **Boundary:** This is reproducibility under the current Python, OR-Tools, platform, and input bytes; it is not a formally checked proof trace independent of the CP-SAT implementation.
- **Confidence:** Very high in local reproducibility and stale-certificate detection; high in the combined analytical/computational certificate.

### `R129` The unrestricted fallback recovers group counts beyond the heuristic domain

- **Status:** Confirmed on a fixture committed before solver exposure.
- **Finding:** Four incompatible PC activities share a three-location footprint and are connected into one legal closure component by three C bridges. Every activity needs two ECLO rows by week 2. Four local groups against supply one force three excess groups at each location/week, so the exact B lower bound is `14 × 5 + 18 × 7 = 196`.
- **Result:** The direct B heuristic has only `supply + 1 = 2` group labels, emits a partial 4/7-activity hint, and correctly returns `INFEASIBLE` without a candidate. The unrestricted bridge-safe fallback uses 2,200 variables and 6,027 constraints, constructs strict-clean B=`196`, and proves a matching full-instance bound in 0.085 seconds; the end-to-end staged run takes 0.127 seconds.
- **Anti-overfitting evidence:** The input and independent oracle were committed first. The solver receives no oracle path and returns a different submission hash. Both scorers agree and the later full verifier preserves the bound.
- **Boundary:** This is still seven activities, one footprint, two weeks, and a deliberately regular bridge chain. It validates fallback coverage, not large coupled scaling.
- **Confidence:** Very high in the exact result and path selection; high in fallback correctness for this group-count regime; medium in large-instance runtime transfer.

## Current method candidates

These are research candidates, not reconciled decisions:

| Candidate | When it may help | Main risk or test |
|---|---|---|
| Monolithic CP-SAT | Public-scale model and first exact implementation | Variable explosion from per-location grouping and pairwise closures |
| Restricted-domain CP-SAT | Most occurrences have narrow useful week ranges | Restriction can remove the true optimum; add controlled expansion |
| CP-SAT large-neighbourhood search | Strong feasible incumbent exists | Bad neighbourhood definitions create repeated local optima |
| Assignment/packing decomposition | Week assignment is easy but detailed grouping is hard | Weak cuts cause slow convergence or invalid master incumbents |
| MILP baseline | Objective bounds and formulation comparison | Big-M and symmetry may weaken the relaxation |
| Weighted MaxSAT baseline | Boolean week/group encoding or large hidden instances | Numeric objective and multi-location grouping may inflate clauses |
| Greedy constructive heuristic | Fast warm start and fallback | May paint later predecessor or hotspot activities into infeasibility |
| Learned search heuristic | Only after a large synthetic run corpus exists | Distribution shift and no feasibility guarantee |
| Online bandit over LNS operators | Learns per-instance operator performance without offline data | Noisy rewards and excess exploration under short time limits |

## Failure register

| ID | Observed failure pattern | Protection for PS1 |
|---|---|---|
| `F001` | Monolithic exact formulations stop scaling with horizon or integration depth. | Precompute aggressively, restrict domains, use decomposition or LNS, and benchmark scale early. |
| `F002` | A high-level assignment looks good but detailed resource packing is infeasible. | Validate each complete incumbent and feed infeasible subsets back as cuts or repairs. |
| `F003` | One cut or neighbourhood strategy works early but stalls later. | Use a timed portfolio and record improvement curves, not only final scores. |
| `F004` | Sequentially assigning work and grouping possessions loses the main sharing benefit. | Co-optimise week and compatible group composition, or iterate between them. |
| `F005` | A realistic-looking objective diverges from the official scoring function. | Optimise the validator score first; operational qualities are secondary tie-breakers. |
| `F006` | Instance-specific performance percentages are mistaken for expected gains. | Preserve experimental context and measure all claims on our own validated runs. |
| `F007` | Robust or learned methods are added without uncertainty data or training coverage. | Keep the core deterministic; introduce these methods only with explicit data and exact validation. |
| `F008` | Group labels create many mathematically identical solutions and waste search. | Compare direct labels against feasible-group columns and add canonical lowest-label symmetry breaking. |
| `F009` | Pairwise compatibility is enforced while batch membership or timing remains inconsistent. | Tie every membership variable to location, week, capacity count, and closure exemption; add redundant checker assertions. |
| `F010` | A warm start is mistaken for a minimal-change constraint. | Add explicit change variables and a lexicographic churn objective. |
| `F011` | Solver status `FEASIBLE` is reported as proven optimal. | Record incumbent, best bound, gap, wall time, worker count, and status separately. |
| `F012` | A fixed heuristic order is copied from qualitative scoring prose even when actions affect different numbers of rows and locations. | Compute the full marginal objective for every candidate move. |
| `F013` | Adaptive search overfits to one operator or rewards slow gains that consume the budget. | Retain exploration, normalise rewards by scenario, and benchmark score-versus-time curves. |
| `F014` | The prose objective is implemented despite unresolved aggregation semantics. | Differential-test controlled schedules against the official validator before trusting local scores. |
| `F015` | A checker passes only hand-written happy paths and shares the solver's same mistaken assumptions. | Add independent boundary, metamorphic, and differential tests; parse outputs independently. |
| `F016` | Pairwise conflicts create a large weak formulation. | Precompute maximal or covering cliques and add aggregate possession lower bounds. |
| `F017` | A model memorises the public topology or generator quirks and degrades on hidden instances. | Hold out structural regimes, compare against non-learned baselines, and preserve exact feasibility checks. |
| `F018` | One global possession group is assigned to an activity-week despite location-specific sample groups. | Index membership by location or use local batch columns linked to the same activity-week decision. |
| `F019` | The number of access occurrences is fixed before ECLO decisions. | Use optional week-indexed access rows and half-unit workload conservation. |
| `F020` | A method is selected from one lucky seed or only its final score. | Use fixed budgets, several seeds, score-over-time curves, feasibility rate, bounds, and held-out structural regimes. |
| `F021` | One solver family is assumed to dominate because of one paper or one instance size. | Benchmark CP-SAT, MIP, and MaxSAT formulations under the same validated objective and time budgets. |
| `F022` | Fixed seed or one worker is mistaken for deterministic output under wall-time-limited iterative solves. | Track deterministic time and complete telemetry; repeat full recipes, include worker count in the benchmark contract, and never replace a protected incumbent based on one run. |

## Validator experiment matrix

Run these minimal, single-purpose cases when the official validator becomes available. Do not combine them, because one hard failure can mask another semantic.

| ID | Question | Controlled comparison |
|---|---|---|
| `V001` | Is week completion the Sunday of the indexed week? | One one-access activity in weeks 1 and 2; compare derived completion dates. |
| `V002` | Is the horizon a hard upper bound? | Move an otherwise valid one-access activity from the final week to week `horizon+1`. |
| `V003` | How is weighted lateness aggregated? | Two activities in one contract, different activity priorities and finish weeks; vary one at a time. |
| `V004` | Does `RESULTS.csv` drive or merely report score? | Keep schedule fixed and alter only submitted completion/overrun values. |
| `V005` | What exactly counts as one ECLO night? | Compare one ECLO activity row with two co-shared ECLO activity rows in one possession. |
| `V006` | Is excess counted per local possession group? | Add one group at one occupied location, then one corridor group spanning several locations. |
| `V007` | What is the closure-exemption granularity? | Make two activities share only one of several common locations, then vary groups at the conflict location. |
| `V008` | Are group labels purely local and arbitrary? | Bijectively rename labels within location-week, then rename inconsistently across locations. |
| `V009` | What does `access_seq` enforce? | Permute rows, swap sequence labels, introduce a gap, and duplicate one sequence value. |
| `V010` | Is beneficial workload oversupply accepted? | Compare exact, +0.5, and +1.0 work-unit coverage using different standard/ECLO mixes. |
| `V011` | How are Scenario C line windows derived? | Place ECLO at both endpoints of a two-week span, then at three weeks; repeat with interchange Live work. |
| `V012` | Are access-night indices independent across contracts and locations? | Reuse the same index across contracts, then exceed distinct indices within one contract/type/week. |

## Active research queue

Research resumed under the user's continuous-improvement goal. Current evidence dependencies are:

1. Obtain the executable validator and official expander, then run `V001`–`V012` plus the buffered-overlap cases in `R039`.
2. Confirm runtime and hidden-instance limits.
3. Benchmark deterministic-time and experimental interleaved search against the current wall-time portfolio before changing defaults.
4. Scale the independent synthetic generator across density, topology, deadlines, and access-type regimes without public-oracle input.
