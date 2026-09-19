# Expected Scenario B infeasibility

This is a fail-closed run, not a solver regression. `MPAMX1` and `MPAMX2`
each require three accesses, permit at most one access per week, and have a
planned-completion deadline in week 1. Scenario B treats planned completion as
a hard deadline, so each activity has capacity for only one of three required
accesses.

The component solver reports `INFEASIBLE` and the decomposed controller emits no
submission or proof report. No portal interaction occurred.
