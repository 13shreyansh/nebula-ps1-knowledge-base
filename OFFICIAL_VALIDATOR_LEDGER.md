# Official Validator Ledger

Append-only record of participant-portal results. The portal keeps only the latest score, so every run is preserved here before another upload.

**Latest verified status: A=0.0, B=0.0, C=0.0, all feasible. Remaining attempts A=1, B=1, C=2.** See the controlled-submission entries at the end and `deliverables/official-zero/MANIFEST.json`. Earlier positive-score optimum claims in this file are superseded.

## A-001

- Timestamp: 2026-09-19 02:47:43 +08
- Portal: NEBULA X team CSV Validator (PS1)
- Scenario: A
- Uploaded ZIP SHA-256: `51f984fb6d2711c99494d7976bd7b4bb3728f75b0d22f15810bf48fb920289bf`
- Local candidate: protected A, internal score `32.2`, submission hash pinned in `deliverables/public/MANIFEST.json`
- Official result: **Infeasible**, five violations, four of five A runs left.
- Violations:
  1. `Activity inside another group's closure zone`: week 18, A058 inside closure of A035 at `PLAT:ALP:S03:WB`, `PLAT:ALP:S04:WB`, `SEC:ALP:S03_S04:WB`.
  2. `Activity inside another group's closure zone`: week 18, A035 inside closure of A058 at the same three locations.
  3. `Activity inside another group's closure zone`: week 21, A001 inside closure of A074 at `PLAT:BET:S15:EB`, `PLAT:BET:S16:EB`, `SEC:BET:S15_S16:EB`.
  4. `Activity inside another group's closure zone`: week 21, A011 inside closure of A074 at the same three locations.
  5. `Activity inside another group's closure zone`: week 29, A023 inside closure of A075 at `PLAT:ALP:S03:WB`, `PLAT:ALP:S04:WB`, `SEC:ALP:S03_S04:WB`.
- Immediate inference: co-sharing exemption is local to an exact location/group rather than a transitive week-level possession component. Live interchange closure also propagates buffered sectors and their platforms onto the other line; the internal checker omitted that propagation.

### A-001 inference correction — 2026-09-19 02:52:41 +08

The first inference above was falsified. Direct-pair-only co-sharing creates ten extra conflicts among activities that are connected through valid co-sharing bridges. The supported interpretation retains transitive possession components, includes each component's occupied work footprint in its closure, and propagates a Live interchange closure plus buffer onto the other line. Under that interpretation, the local checker reproduces the five official directional violations exactly. This agreement is evidence from one run, not proof of complete validator equivalence.

## A-002

- Timestamp: 2026-09-19 02:56:30 +08
- Scenario: A
- Uploaded ZIP SHA-256: `76bf26e19161337daf4f186d2a678aeb23bcb8613bc3bba42d00451d30325437`
- Local candidate: seven-activity partially frozen repair of A-001, with zero standard or strict closure conflicts and exact-three-file byte verification.
- Official result: **Feasible**, all constraints passed, three of five A runs left.
- Official score: `137.9`.
- Official diagnostics: 28 overrun days across 3 contracts, 0 excess access nights, 0 ECLO nights.
- Score discrepancy: the pre-upload local scorer reported `32.2`. The exact official `137.9` equals the final contract overrun charged to every activity in that contract, with each activity's priority nudge: C006 `85.4` + C010 `45.5` + C014 `7.0`. Both local scorers and the solver objective were corrected immediately; they now reproduce `137.9` on the uploaded bytes.

## B-001

- Timestamp: 2026-09-19 03:03:19 +08
- Scenario: B
- Uploaded ZIP SHA-256: `1ef95698cc456f5a037bcd3939a6ee6a6ea06bd32fc4c74c0ff403eb3d00b76c`
- Local candidate: four-activity partially frozen repair, strict-pruned and protected by a full bridge-safe verification that proved no score below `30.0`.
- Official result: **Feasible**, all constraints passed, four of five B runs left.
- Official score: `30.0`.
- Official diagnostics: 0 overrun days, 0 excess access nights, 6 ECLO nights.
- Agreement: both local scorers predicted exactly `30.0`.

## C-001

- Timestamp: 2026-09-19 03:03:19 +08
- Scenario: C
- Uploaded ZIP SHA-256: `ee6b09ccf0584cf4d3dfb6b825669c39491329a9f756ca50dc1879fd5e274f43`
- Local candidate: seven-activity partially frozen repair of the superseded C artifact, strict-pruned and protected by a full bridge-safe verification that proved no score below `62.7`.
- Official result: **Feasible**, all constraints passed, four of five C runs left.
- Official score: `62.7`.
- Official diagnostics: 7 overrun days across 1 contract, 0 excess access nights, 4 ECLO nights.
- Agreement: both local scorers predicted exactly `62.7` (`42.7` contract delay + `20.0` ECLO).

## Current official incumbents

- A: `137.9` (3/5 runs left)
- B: `30.0` (4/5 runs left)
- C: `62.7` (4/5 runs left)
- Combined public penalty: `230.6`

## Later read-only portal snapshot — 2026-09-19

The user reported that their friend had uploaded A/B/C. The live portal was inspected without uploading files or consuming an attempt. Exact uploaded CSVs, archive hashes and upload timestamps are pending, so these are observed latest results rather than hash-identified runs.

- A: **Infeasible**, 54 displayed closure-zone violations, 2/5 runs left.
- B: **Infeasible**, 67 displayed closure-zone violations, 3/5 runs left.
- C: **Feasible**, score **98.2**, 14 overrun days across two contracts, zero excess, two ECLO accesses, 3/5 runs left.
- The portal retains the latest result, not the best. The previous accepted A-002/B-001/C-001 CSVs remain preserved locally; the earlier 'Current official incumbents' section describes historical best accepted files, not the latest portal display.
- Full visible diagnostics and analysis: `artifacts/friend-portal-audit-2026-09-19/REPORT.md`, `portal-visible-report.txt`, and `analysis.json`.
- New substantive evidence: own-line Live buffer endpoint platforms appear in official violations that our current closure expansion omits. A candidate expansion plus the apparent four-location display limit reproduces B 67/67 and A 52/54 diagnostics, conditional on the printed components. Two A messages need full occupancy/component reconstruction. No production checker or submitted file was changed during this audit.
- A's week-27 A036-inside-A075 message directly supports that specific exclusion; it does not independently certify the complete public optimality claim.

### Exact uploaded-file replay after user supplied ZIPs

- Supplied A archive SHA-256: `97c75c656976f5c8c5870aa09d3a6182560ea62d9e45748140c1643370cd7127`.
- Supplied B archive SHA-256: `37d488d78553d49e54fb9ac056dc3dd005a626d558f922217461431092e41f67`.
- Supplied C archive SHA-256: `694984c9d53d3cf4ddd0c400833b03e7fcf68a4fd81705e628855099991434fc`.
- With the isolated own-line Live buffer endpoint-platform correction, all A 54/54 and B 67/67 diagnostics exactly match after reproducing the portal's first-three-member/first-four-location display formatting. No extra local hard violations. C reproduces feasible 98.2.
- Both remaining A messages were explained by fourth component member A042, omitted from the displayed list.
- The two extra B failures beyond the baseline checker's 65 are A059 inside A074 at ALP:S06:WB in week 19 and A021 inside A075 at BET:S13:WB in week 28, both platform-only.
- Exact C files confirm C006 and C010 seven days late, with ECLO only on A036 weeks 22-23. The officially accepted C schedule has four overlaps under our additional strict buffer-only screen, establishing that screen is stricter than observed portal acceptance.
- A minimal C repair adds ECLO to A059 weeks 18-19, removes its week-20 visit, and locally scores 62.7 with no new strict findings. This NEW candidate was NOT submitted and has no official acceptance. Production code was not modified during the replay.
- Full findings: `artifacts/friend-portal-audit-2026-09-19/REPLAY_REPORT.md`.

## User-authorized controlled submissions — 19 September 2026

Authorization: user requested controlled B/C experiments followed by applying the result to A, limited the experimental budget to four submissions, and reserved the final attempt of each scenario. Exactly four uploads were performed, with none of the final reserved attempts consumed.

| Probe | Scenario | Uploaded SHA-256 | Official outcome |
|---|---|---|---|
| B1 | B | `6ebfd269e20a0f11f94e0a5e5853e93d65a83a7739446cd2188a711de8e8d570` | Feasible 30.0, no violations; A008 uses two distinct nights in week 16. |
| C1 | C | `f51c63885185ec043f41b673dd7aaad00c80af32b3f6267a503499443de151e2` | Feasible **0.0**, zero overrun, zero excess, zero ECLO. |
| A1 | A | `f1cbe372bcf2e6c4b2c686dc1c78e2f23c665aef6f448a4364492f71b3f2c414` | Feasible **0.0**, zero overrun, zero excess, zero ECLO. |
| B2 | B | `7afa56e561cde540db63f21d0bfa8d896bab3cec918a305bc0fa4831a39c3938` | Feasible **0.0**, zero overrun, zero excess, zero ECLO. |

C1 adds repeat standard accesses to replace all ECLO work in the historical accepted B schedule. A1 and B2 reuse its exact schedule CSVs, changing only RESULTS scenario labels. The portal's final current state is all three zero scores with A=1/B=1/C=2 attempts left. The 137.9/30.0/62.7 restricted-model optimality claims are retracted as claims about the official public problem. Zero is an attained lower bound because published score terms are nonnegative.

Live report snapshots, exact probe changes, and the scoring proof are in `artifacts/controlled-probes-2026-09-19/`. The exact accepted ZIPs are preserved at `deliverables/official-zero/` with SHA-256 manifests. Remaining semantic and implementation limitations are explicit in the probe report: this does not certify all hidden-instance rules, and the legacy local checker still rejects repeated activity/weeks.
