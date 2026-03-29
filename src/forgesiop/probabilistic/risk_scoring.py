"""Supply risk scoring — from quality data to planning adjustments.

Takes supplier quality metrics (claims, scores, detection rates)
and produces risk-adjusted parameters for planning.
"""

from __future__ import annotations

from ..core.types import SupplyRisk


def compute_risk_level(
    quality_score: float,
    open_claims: int,
    lead_time_reliability: float,
    overdue_evaluations: int = 0,
) -> SupplyRisk:
    """Compute supply risk level from quality metrics.

    Args:
        quality_score: 0-1 from supplier response quality scoring
        open_claims: number of unresolved quality claims
        lead_time_reliability: 0-1 on-time delivery rate
        overdue_evaluations: number of overdue supplier evaluations
    """
    # Weighted scoring
    score = (
        quality_score * 0.35
        + lead_time_reliability * 0.30
        + max(0, 1 - open_claims * 0.15) * 0.20
        + max(0, 1 - overdue_evaluations * 0.1) * 0.15
    )

    if score >= 0.8:
        level = "low"
    elif score >= 0.6:
        level = "medium"
    elif score >= 0.4:
        level = "high"
    else:
        level = "critical"

    return SupplyRisk(
        supplier_id="",
        quality_score=quality_score,
        open_claims=open_claims,
        lead_time_reliability=lead_time_reliability,
        risk_level=level,
    )


def risk_adjusted_lead_time(
    base_lead_time: float,
    lead_time_std: float,
    risk: SupplyRisk,
) -> tuple[float, float]:
    """Adjust lead time parameters for supply risk.

    Higher risk = longer expected lead time and more variability.

    Returns:
        (adjusted_mean, adjusted_std)
    """
    factor = risk.risk_factor
    return (
        base_lead_time * (1 + (factor - 1) * 0.3),  # mean increases moderately
        lead_time_std * factor,  # std increases proportionally
    )


def risk_adjusted_safety_stock_multiplier(risk: SupplyRisk) -> float:
    """Get safety stock multiplier based on supply risk.

    This is the factor applied to base safety stock calculation.
    """
    return risk.risk_factor
