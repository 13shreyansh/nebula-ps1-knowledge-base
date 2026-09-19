# Rejected decomposition proof

This run produced a hard-feasible, strict-clean C=`1659.2` schedule matching the
separately proved monolithic optimum, but its additivity proof is invalid.

The experimental component graph omitted the Scenario C rule that a Live
interchange activity's ECLO choice constrains the ECLO window on every line.
The eight location-disjoint copies were therefore not formally independent.
`DECOMPOSED.json` is retained as the original false-positive evidence and must
not be cited as a valid global proof or production result.

The graph was corrected immediately after discovery; the corrected partition
collapses this fixture to one component.
