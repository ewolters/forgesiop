"""Safety stock calculations — dynamic, distribution-aware.

Uses scipy.stats for z-score lookup. Falls back to hardcoded
table for common service levels if scipy unavailable.
"""

from __future__ import annotations

import math

# Hardcoded z-scores for common service levels (fallback if scipy unavailable)
_Z_TABLE = {
    0.80: 0.842,
    0.85: 1.036,
    0.90: 1.282,
    0.95: 1.645,
    0.97: 1.881,
    0.98: 2.054,
    0.99: 2.326,
    0.995: 2.576,
    0.999: 3.090,
}


def _z_score(service_level: float) -> float:
    """Get z-score for a service level (0-1)."""
    try:
        from scipy.stats import norm

        return norm.ppf(service_level)
    except ImportError:
        # Fall back to table lookup with interpolation
        if service_level in _Z_TABLE:
            return _Z_TABLE[service_level]
        # Linear interpolation between nearest table entries
        levels = sorted(_Z_TABLE.keys())
        for i in range(len(levels) - 1):
            if levels[i] <= service_level <= levels[i + 1]:
                frac = (service_level - levels[i]) / (levels[i + 1] - levels[i])
                return _Z_TABLE[levels[i]] + frac * (_Z_TABLE[levels[i + 1]] - _Z_TABLE[levels[i]])
        return 1.645  # default to 95%


def dynamic_safety_stock(
    demand_mean: float,
    demand_std: float,
    lead_time_mean: float,
    lead_time_std: float = 0.0,
    service_level: float = 0.95,
) -> float:
    """Dynamic safety stock accounting for both demand and lead time variability.

    Formula: SS = z * sqrt(LT * sigma_d^2 + d_mean^2 * sigma_LT^2)

    Args:
        demand_mean: Average demand per period
        demand_std: Standard deviation of demand per period
        lead_time_mean: Average lead time in periods
        lead_time_std: Standard deviation of lead time in periods
        service_level: Target service level (0-1)

    Returns:
        Safety stock quantity (units)
    """
    z = _z_score(service_level)
    variance = lead_time_mean * demand_std**2 + demand_mean**2 * lead_time_std**2
    return z * math.sqrt(variance)


def demand_only_safety_stock(
    demand_std: float,
    lead_time: float,
    service_level: float = 0.95,
) -> float:
    """Safety stock from demand variability only (fixed lead time).

    Formula: SS = z * sigma_d * sqrt(LT)
    """
    z = _z_score(service_level)
    return z * demand_std * math.sqrt(lead_time)


def safety_stock_with_supply_risk(
    demand_mean: float,
    demand_std: float,
    lead_time_mean: float,
    lead_time_std: float,
    service_level: float,
    supply_risk_factor: float = 1.0,
) -> float:
    """Safety stock adjusted for supply risk.

    Args:
        supply_risk_factor: Multiplier from SupplyRisk.risk_factor (1.0 = no risk, 2.0 = critical)

    Returns:
        Adjusted safety stock
    """
    base = dynamic_safety_stock(demand_mean, demand_std, lead_time_mean, lead_time_std, service_level)
    return base * supply_risk_factor
