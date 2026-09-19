from __future__ import annotations

from collections.abc import Mapping

from .instance import Instance


CONTRACT_WEIGHT = {1: 100.0, 2: 10.0, 3: 1.0}
ACTIVITY_NUDGE = {1: 0.3, 2: 0.2, 3: 0.0}
CONTRACT_WEIGHT_TENTHS = {
    1: {1: 1300, 2: 1200, 3: 1000},
    2: {1: 130, 2: 120, 3: 100},
    3: {1: 13, 2: 12, 3: 10},
}
EXCESS_COST = 7.0
ECLO_COST = 5.0
EXCESS_COST_TENTHS = 70
ECLO_COST_TENTHS = 50


def _combined_contract_weight_tenths(
    instance: Instance, contract_number: str
) -> int:
    project = instance.projects[contract_number]
    return sum(
        CONTRACT_WEIGHT_TENTHS[project.contract_priority][
            activity.activity_priority
        ]
        for activity in instance.activities.values()
        if activity.contract_number == contract_number
    )


def contract_cost_tenths_at_week(
    instance: Instance, contract_number: str, week: int
) -> int:
    project = instance.projects[contract_number]
    delay_days = max(
        0,
        (instance.completion_date(week) - project.planned_completion_date).days,
    )
    return delay_days * _combined_contract_weight_tenths(
        instance, contract_number
    )


def contract_costs_tenths(instance: Instance, contract_number: str) -> list[int]:
    """Return official contract-completion costs in score tenths by week."""

    return [
        contract_cost_tenths_at_week(instance, contract_number, week)
        for week in range(1, instance.horizon_weeks + 1)
    ]


def delay_score_from_completion_weeks(
    instance: Instance,
    completion_by_contract: Mapping[str, int],
) -> float:
    """Return official delay score for a complete contract-to-week mapping."""

    expected = set(instance.projects)
    observed = set(completion_by_contract)
    if observed != expected:
        raise ValueError(
            "contract completion mapping mismatch: "
            f"missing={sorted(expected - observed)}, "
            f"extra={sorted(observed - expected)}"
        )
    total_tenths = sum(
        contract_cost_tenths_at_week(instance, contract_number, week)
        for contract_number, week in completion_by_contract.items()
    )
    return total_tenths / 10.0
