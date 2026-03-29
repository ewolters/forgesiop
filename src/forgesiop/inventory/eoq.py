"""Economic Order Quantity — classic and extended models.

No external dependencies. Pure Python + math stdlib.
"""

from __future__ import annotations

import math


def economic_order_quantity(
    annual_demand: float,
    ordering_cost: float,
    holding_cost_rate: float,
    unit_cost: float,
) -> float:
    """Classic EOQ (Wilson formula).

    Args:
        annual_demand: Total demand per year (units)
        ordering_cost: Fixed cost per order ($)
        holding_cost_rate: Annual holding cost as fraction of unit cost (e.g., 0.25 = 25%)
        unit_cost: Cost per unit ($)

    Returns:
        Optimal order quantity (units)
    """
    holding_cost = holding_cost_rate * unit_cost
    if holding_cost <= 0 or annual_demand <= 0:
        return 0.0
    return math.sqrt(2 * annual_demand * ordering_cost / holding_cost)


def eoq_with_quantity_discount(
    annual_demand: float,
    ordering_cost: float,
    holding_cost_rate: float,
    price_breaks: list[tuple[float, float]],
) -> dict:
    """EOQ with quantity discounts.

    Args:
        price_breaks: [(min_quantity, unit_price), ...] sorted ascending by quantity

    Returns:
        {quantity, unit_price, total_cost, method}
    """
    best = None

    for i, (min_qty, price) in enumerate(price_breaks):
        # Compute EOQ at this price
        q = economic_order_quantity(annual_demand, ordering_cost, holding_cost_rate, price)

        # Adjust to feasible range
        max_qty = price_breaks[i + 1][0] - 1 if i + 1 < len(price_breaks) else float("inf")
        q = max(min_qty, min(q, max_qty))

        # Also check at the minimum quantity for each break
        for check_qty in [q, min_qty]:
            if check_qty < min_qty:
                continue
            # Find the applicable price for this quantity
            applicable_price = price
            for mq, mp in price_breaks:
                if check_qty >= mq:
                    applicable_price = mp

            total = _total_cost(annual_demand, check_qty, ordering_cost, holding_cost_rate, applicable_price)

            if best is None or total < best["total_cost"]:
                best = {
                    "quantity": check_qty,
                    "unit_price": applicable_price,
                    "total_cost": total,
                    "method": "eoq_discount",
                }

    return best or {"quantity": 0, "unit_price": 0, "total_cost": 0, "method": "none"}


def eoq_total_cost(
    annual_demand: float,
    order_quantity: float,
    ordering_cost: float,
    holding_cost_rate: float,
    unit_cost: float,
) -> float:
    """Total annual cost for a given order quantity."""
    return _total_cost(annual_demand, order_quantity, ordering_cost, holding_cost_rate, unit_cost)


def _total_cost(demand, quantity, ordering_cost, holding_rate, unit_cost):
    if quantity <= 0:
        return float("inf")
    ordering = (demand / quantity) * ordering_cost
    holding = (quantity / 2) * holding_rate * unit_cost
    purchasing = demand * unit_cost
    return ordering + holding + purchasing
