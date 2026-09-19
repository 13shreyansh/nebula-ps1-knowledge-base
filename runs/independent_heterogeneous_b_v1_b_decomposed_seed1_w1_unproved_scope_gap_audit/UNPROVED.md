# Valid schedule, incomplete aggregate proof

The merged B=`349` schedule is valid and dual-scored, but this run is not a
global proof. Six components used the explicit full-instance Scenario B
workload/ECLO lower-bound proof scope, which the decomposition aggregator did
not yet recognize. It therefore reported
`global_optimality_proved_by_additivity=false`.

The report is retained unchanged as the pre-correction boundary. No portal
interaction occurred.
