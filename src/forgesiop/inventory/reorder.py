"""Reorder policies — ROP, (s,S), (s,Q)."""

from __future__ import annotations

import math

from .safety_stock import dynamic_safety_stock


def reorder_point(
    demand_mean: float,
    lead_time_mean: float,
    safety_stock: float,
) -> float:
    """Reorder point = demand during lead time + safety stock."""
    return demand_mean * lead_time_mean + safety_stock


def continuous_review_sQ(
    demand_mean: float,
    demand_std: float,
    lead_time_mean: float,
    lead_time_std: float,
    order_quantity: float,
    service_level: float = 0.95,
) -> dict:
    """(s, Q) continuous review policy.

    Order Q units when inventory position drops to s.
    """
    ss = dynamic_safety_stock(demand_mean, demand_std, lead_time_mean, lead_time_std, service_level)
    s = reorder_point(demand_mean, lead_time_mean, ss)

    return {
        "reorder_point_s": round(s, 1),
        "order_quantity_Q": round(order_quantity, 1),
        "safety_stock": round(ss, 1),
        "average_inventory": round(order_quantity / 2 + ss, 1),
        "policy": "(s, Q)",
    }


def periodic_review_sS(
    demand_mean: float,
    demand_std: float,
    review_period: float,
    lead_time_mean: float,
    lead_time_std: float,
    service_level: float = 0.95,
) -> dict:
    """(s, S) periodic review policy.

    Review every T periods. If position <= s, order up to S.
    """
    # Protection period = review period + lead time
    protection_period = review_period + lead_time_mean
    protection_std = math.sqrt(
        protection_period * demand_std**2 + demand_mean**2 * lead_time_std**2
    )
    ss = dynamic_safety_stock(demand_mean, demand_std, protection_period, lead_time_std, service_level)
    s = demand_mean * protection_period - ss  # reorder point
    S = demand_mean * protection_period + ss  # order-up-to level

    return {
        "reorder_point_s": round(max(0, s), 1),
        "order_up_to_S": round(S, 1),
        "safety_stock": round(ss, 1),
        "protection_std": round(protection_std, 2),
        "review_period": review_period,
        "average_inventory": round(demand_mean * review_period / 2 + ss, 1),
        "policy": "(s, S)",
    }
