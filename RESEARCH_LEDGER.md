# Nebula PS1 Research Ledger

| Field | Value |
|---|---|
| Status | Active until the user explicitly asks to stop |
| Started | 2026-09-18 |
| Scope | Railway possession scheduling, optimisation, validation, failure modes, robustness, and competition execution |
| Canonical decisions | `README.md` |

This is the evidence-preserving working ledger. It may contain competing methods, unresolved interpretations, and findings that do not become team decisions. Reconciliation happens only when requested. The canonical README receives only conclusions that survive that process.

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

## Current method candidates

These are research candidates, not reconciled decisions:

| Candidate | When it may help | Main risk or test |
|---|---|---|
| Monolithic CP-SAT | Public-scale model and first exact implementation | Variable explosion from per-location grouping and pairwise closures |
| Restricted-domain CP-SAT | Most occurrences have narrow useful week ranges | Restriction can remove the true optimum; add controlled expansion |
| CP-SAT large-neighbourhood search | Strong feasible incumbent exists | Bad neighbourhood definitions create repeated local optima |
| Assignment/packing decomposition | Week assignment is easy but detailed grouping is hard | Weak cuts cause slow convergence or invalid master incumbents |
| MILP baseline | Objective bounds and formulation comparison | Big-M and symmetry may weaken the relaxation |
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

## Open research queue

1. Obtain the executable validator and official expander, then reverse-check every inferred rule with controlled cases.
2. Inspect recent work on adaptive LNS, matheuristics, and CP-SAT scheduling portfolios.
3. Study symmetry-breaking and clique/cumulative formulations for possession grouping.
4. Study exact conflict-graph and set-packing formulations for PC/C/PM groups.
5. Identify railway scheduling benchmark practices and honest optimality-gap reporting.
6. Study minimal-change and recoverable scheduling for the disruption bonus.
7. Compare deterministic, robust, and stochastic scheduling only where PS1 data supports them.
8. Investigate common implementation failures in date indexing, corridor expansion, buffers, and output generation.
9. Track changes to the organiser repository and portal.
