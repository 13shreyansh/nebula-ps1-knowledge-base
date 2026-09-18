from __future__ import annotations

import json
from pathlib import Path

from nebula_ps1.closure import screen_closures
from nebula_ps1.evaluate import evaluate_submission, load_submission
from nebula_ps1.independent_score import independently_score
from nebula_ps1.instance import load_instance


ROOT = Path(__file__).resolve().parents[1]

CASES = (
    ("public_A", "current-problem-statement/PS1/01_data", "deliverables/public/A", "A", None, "ANALYTIC_LOWER_BOUND_AND_OFFICIAL_VALIDATOR", 137.9),
    ("public_B", "current-problem-statement/PS1/01_data", "deliverables/public/B", "B", None, "MODEL_OPTIMAL_AND_OFFICIAL_VALIDATOR", 30.0),
    ("public_C", "current-problem-statement/PS1/01_data", "deliverables/public/C", "C", None, "MODEL_AND_ANALYTIC_LOWER_BOUND_AND_OFFICIAL_VALIDATOR", 62.7),
    ("prefix040_A", "fixtures/prefix_040", "runs/a_prefix040_corrected_w1", "A", "runs/a_prefix040_corrected_w1_audit/verification_raw/TELEMETRY.json", None, None),
    ("prefix040_B", "fixtures/prefix_040", "runs/b_prefix040_portfolio_costrepair_w1", "B", "runs/b_prefix040_portfolio_costrepair_w1_audit/verification_raw/TELEMETRY.json", None, None),
    ("prefix040_C", "fixtures/prefix_040", "runs/c_prefix040_corrected_w1", "C", "runs/c_prefix040_corrected_w1_audit/stages/scenario_c_verification_raw/TELEMETRY.json", None, None),
    ("structural_demand_A", "fixtures/structural_demand_seed_20260920", "runs/a_structural_demand_portfolio_w8", "A", "runs/a_structural_demand_portfolio_w8_audit/verification_raw/TELEMETRY.json", None, None),
    ("structural_demand_B", "fixtures/structural_demand_seed_20260920", "runs/b_structural_demand_portfolio_w8", "B", "runs/b_structural_demand_portfolio_w8_audit/verification_raw/TELEMETRY.json", None, None),
    ("structural_demand_C", "fixtures/structural_demand_seed_20260920", "runs/c_structural_demand_portfolio_w8", "C", "runs/c_structural_demand_portfolio_w8_audit/stages/scenario_c_verification_raw/TELEMETRY.json", None, None),
    ("independent_A", "fixtures/independent_synthetic_v1", "runs/a_independent_synthetic_v1", "A", "runs/a_independent_synthetic_v1_audit/verification_raw/TELEMETRY.json", None, None),
    ("independent_B", "fixtures/independent_synthetic_v1", "runs/b_independent_synthetic_v1", "B", "runs/b_independent_synthetic_v1_audit/verification_raw/TELEMETRY.json", None, None),
    ("independent_C", "fixtures/independent_synthetic_v1", "runs/c_independent_synthetic_v1", "C", "runs/c_independent_synthetic_v1_audit/stages/scenario_c_verification_raw/TELEMETRY.json", None, None),
    ("independent_scaled_m20_A", "fixtures/independent_scaled_m20", "runs/independent_scaled_m20_seed_matrix5_w1/a_seed_1", "A", "runs/independent_scaled_m20_seed_matrix5_w1/a_seed_1_audit/verification_raw/TELEMETRY.json", None, None),
    ("independent_scaled_m20_B", "fixtures/independent_scaled_m20", "runs/independent_scaled_m20_seed_matrix5_w1/b_seed_1", "B", "runs/independent_scaled_m20_seed_matrix5_w1/b_seed_1_audit/verification_raw/TELEMETRY.json", None, None),
    ("independent_scaled_m20_C", "fixtures/independent_scaled_m20", "runs/independent_scaled_m20_seed_matrix5_w1/c_seed_1", "C", "runs/independent_scaled_m20_seed_matrix5_w1/c_seed_1_audit/verification_raw/TELEMETRY.json", None, None),
    ("independent_dense_A", "fixtures/independent_dense_v1", "runs/independent_dense_v1_structural_matrix_w1/a_seed_1", "A", "runs/independent_dense_v1_structural_matrix_w1/a_seed_1_audit/verification_raw/TELEMETRY.json", None, None),
    ("independent_dense_B", "fixtures/independent_dense_v1", "runs/independent_dense_v1_structural_matrix_w1/b_seed_1", "B", "runs/independent_dense_v1_structural_matrix_w1/b_seed_1_audit/verification_raw/TELEMETRY.json", None, None),
    ("independent_dense_C", "fixtures/independent_dense_v1", "runs/independent_dense_v1_structural_matrix_w1/c_seed_1", "C", "runs/independent_dense_v1_structural_matrix_w1/c_seed_1_audit/verification_raw/TELEMETRY.json", None, None),
    ("independent_dense_holdout_A", "fixtures/independent_dense_holdout_v1", "runs/independent_dense_holdout_v1_production_matrix_w1/a_seed_1", "A", "runs/independent_dense_holdout_v1_production_matrix_w1/a_seed_1_audit/verification_raw/TELEMETRY.json", None, None),
    ("independent_dense_holdout_B", "fixtures/independent_dense_holdout_v1", "runs/independent_dense_holdout_v1_production_matrix_w1/b_seed_1", "B", "runs/independent_dense_holdout_v1_production_matrix_w1/b_seed_1_audit/verification_raw/TELEMETRY.json", None, None),
    ("independent_dense_holdout_C", "fixtures/independent_dense_holdout_v1", "runs/independent_dense_holdout_v1_production_matrix_w1/c_seed_1", "C", "runs/independent_dense_holdout_v1_production_matrix_w1/c_seed_1_audit/stages/scenario_c_verification_raw/TELEMETRY.json", None, None),
    ("independent_tradeoff_holdout_A", "fixtures/independent_tradeoff_holdout_v1", "runs/independent_tradeoff_holdout_v1_blind_w1/a_seed_1", "A", "runs/independent_tradeoff_holdout_v1_blind_w1/a_seed_1_audit/verification_raw/TELEMETRY.json", None, None),
    ("independent_tradeoff_holdout_B", "fixtures/independent_tradeoff_holdout_v1", "runs/independent_tradeoff_holdout_v1_blind_w1/b_seed_1", "B", "runs/independent_tradeoff_holdout_v1_blind_w1/b_seed_1_audit/verification_raw/TELEMETRY.json", None, None),
    ("independent_tradeoff_holdout_C", "fixtures/independent_tradeoff_holdout_v1", "runs/independent_tradeoff_holdout_v1_blind_w1/c_seed_1", "C", "runs/independent_tradeoff_holdout_v1_blind_w1/c_seed_1_audit/stages/scenario_c_verification_raw/TELEMETRY.json", None, None),
    ("independent_coupled_tradeoff_A", "fixtures/independent_coupled_tradeoff_v1", "runs/independent_coupled_tradeoff_v1_repair10_matrix_w1/a_seed_1", "A", "runs/independent_coupled_tradeoff_v1_repair10_matrix_w1/a_seed_1_audit/verification_raw/TELEMETRY.json", None, None),
    ("independent_coupled_tradeoff_B", "fixtures/independent_coupled_tradeoff_v1", "runs/independent_coupled_tradeoff_v1_repair10_matrix_w1/b_seed_1", "B", "runs/independent_coupled_tradeoff_v1_repair10_matrix_w1/b_seed_1_audit/verification_raw/TELEMETRY.json", None, None),
    ("independent_coupled_tradeoff_C", "fixtures/independent_coupled_tradeoff_v1", "runs/independent_coupled_tradeoff_v1_repair10_matrix_w1/c_seed_1", "C", "runs/independent_coupled_tradeoff_v1_repair10_matrix_w1/c_seed_1_audit/stages/scenario_c_verification_raw/TELEMETRY.json", None, None),
    ("independent_irregular_partial_B", "fixtures/independent_irregular_partial_v1", "runs/independent_irregular_partial_v1_corrected_production_w8/b_seed_1", "B", "runs/independent_irregular_partial_v1_corrected_production_w8/b_seed_1_audit/bridge_safe_cost_repair_raw/TELEMETRY.json", None, None),
    ("independent_irregular_partial_C", "fixtures/independent_irregular_partial_v1", "runs/independent_irregular_partial_v1_guarded_independent_c120_costrepair_w8", "C", "runs/independent_irregular_partial_v1_guarded_independent_c120_costrepair_w8_audit/stages/scenario_c_direct_after_a_failure_audit/bridge_safe_cost_repair_raw/TELEMETRY.json", None, None),
)


def main() -> None:
    rows: list[dict[str, object]] = []
    for name, data_rel, submission_rel, scenario, telemetry_rel, stated_proof, stated_bound in CASES:
        data = ROOT / data_rel
        submission = ROOT / submission_rel
        instance = load_instance(data)
        evaluation = evaluate_submission(instance, submission, scenario)
        independent = independently_score(data, submission)
        access, occupancy, _ = load_submission(submission)
        strict_conflicts = screen_closures(
            instance, access, occupancy, forbid_buffer_overlap=True
        )
        if evaluation.hard_violations:
            raise RuntimeError(f"{name}: hard violations: {evaluation.hard_violations}")
        if evaluation.objective_score != independent.objective_score:
            raise RuntimeError(
                f"{name}: scorer mismatch {evaluation.objective_score} != {independent.objective_score}"
            )
        telemetry = (
            json.loads((ROOT / telemetry_rel).read_text(encoding="utf-8"))
            if telemetry_rel is not None
            else None
        )
        rows.append(
            {
                "case": name,
                "scenario": scenario,
                "dataset_hash": evaluation.dataset_hash,
                "submission_hash": evaluation.submission_hash,
                "score": evaluation.objective_score,
                "delay_score": evaluation.priority_weighted_score,
                "eclo_nights": evaluation.eclo_nights_total,
                "excess_nights": evaluation.excess_access_nights_total,
                "standard_feasible": True,
                "strict_conflicts": len(strict_conflicts),
                "proof_status": telemetry["status"] if telemetry else stated_proof,
                "proof_bound": telemetry["best_bound"] if telemetry else stated_bound,
                "proof_matches_score": (
                    telemetry["best_bound"] == evaluation.objective_score
                    if telemetry
                    else stated_bound == evaluation.objective_score
                ),
                "reference_validator_confirmed": name.startswith("public_"),
            }
        )
    output = {
        "schema_version": 1,
        "integrity_rule": "main and independent scores must agree; hard violations abort generation",
        "cases": rows,
    }
    (ROOT / "BENCHMARK_MATRIX.json").write_text(
        json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
