# Expected Scenario B infeasibility

This is a fail-closed run, not a solver regression. `MPAMX1` and `MPAMX2`
each require three workload units and have only week 1 available before
Scenario B's hard planned-completion deadline. An activity may have at most one
access row per week; even an ECLO row supplies only 1.5 units. Each activity can
therefore receive at most 1.5 of three required units.

The component solver reports `INFEASIBLE` and the decomposed controller emits no
submission or proof report. No portal interaction occurred.
