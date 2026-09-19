# Rejected report-generation run

The merged schedule was not promoted. Decomposition report generation crashed
because a component used a proven nonnegative zero-floor path whose final-verifier
telemetry is correctly null. The aggregator incorrectly assumed every proof came
from the final verifier.

The input and component outputs are retained for regression. No portal interaction
occurred.
