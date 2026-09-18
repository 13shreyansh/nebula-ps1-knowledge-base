# Official Validator Ledger

Append-only record of participant-portal results. The portal keeps only the latest score, so every run is preserved here before another upload.

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
