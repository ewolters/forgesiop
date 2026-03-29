"""Multi-echelon inventory optimization.

Uses stockpyl for GSM/SSM algorithms when available.
Falls back to single-echelon approximation otherwise.
"""

from __future__ import annotations


def base_stock_newsvendor(
    demand_mean: float,
    demand_std: float,
    lead_time: float,
    holding_cost: float,
    stockout_cost: float,
) -> dict:
    """Single-echelon base stock from newsvendor model.

    Critical ratio: Cu / (Cu + Co) where Cu = stockout cost, Co = holding cost.
    """
    import math

    critical_ratio = stockout_cost / (stockout_cost + holding_cost)

    # z-score from critical ratio
    try:
        from scipy.stats import norm
        z = norm.ppf(critical_ratio)
    except ImportError:
        # Approximate
        from ..inventory.safety_stock import _z_score
        z = _z_score(critical_ratio)

    demand_during_lt = demand_mean * lead_time
    std_during_lt = demand_std * math.sqrt(lead_time)
    base_stock = demand_during_lt + z * std_during_lt

    return {
        "base_stock_level": round(base_stock, 1),
        "safety_stock": round(z * std_during_lt, 1),
        "critical_ratio": round(critical_ratio, 4),
        "service_level": round(critical_ratio, 4),
    }


def guaranteed_service_model(
    stages: list[dict],
) -> list[dict]:
    """Guaranteed Service Model (GSM) for multi-echelon.

    Each stage: {name, demand_mean, demand_std, lead_time, holding_cost, service_time_to_customer}

    Requires stockpyl for full optimization. This is a simplified version.
    """
    try:
        # Try stockpyl for rigorous optimization
        import stockpyl
        # TODO: wire stockpyl.ssm or stockpyl.gsm when API stabilizes
        pass
    except ImportError:
        pass

    # Simplified: treat each stage independently with adjusted lead time
    results = []
    for i, stage in enumerate(stages):
        # Net lead time = processing LT - guaranteed service time from upstream
        upstream_service = stages[i - 1].get("service_time_to_customer", 0) if i > 0 else 0
        net_lt = max(0, stage["lead_time"] - upstream_service)

        bs = base_stock_newsvendor(
            demand_mean=stage["demand_mean"],
            demand_std=stage["demand_std"],
            lead_time=net_lt,
            holding_cost=stage.get("holding_cost", 1),
            stockout_cost=stage.get("stockout_cost", 10),
        )
        results.append({
            "stage": stage["name"],
            "net_lead_time": net_lt,
            **bs,
        })

    return results
