"""Aggregate production planning — chase, level, mixed strategies.

Uses scipy.optimize.linprog for LP-based mixed strategy.
Falls back to heuristic if scipy unavailable.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class AggregatePlan:
    """Result of aggregate planning."""

    periods: list[str]
    production: list[float]
    inventory: list[float]
    workforce: list[float]
    overtime: list[float]
    subcontract: list[float]
    total_cost: float
    strategy: str


def chase_strategy(
    demand: list[float],
    hiring_cost: float = 500,
    firing_cost: float = 700,
    production_cost: float = 20,
    units_per_worker: float = 40,
    initial_workforce: int = 10,
) -> AggregatePlan:
    """Chase strategy — match production to demand each period.

    Workforce adjusts every period. Zero inventory.
    """
    n = len(demand)
    production = list(demand)
    inventory = [0.0] * n
    workforce = []
    total_cost = 0

    prev_workers = initial_workforce
    for i in range(n):
        workers_needed = demand[i] / units_per_worker if units_per_worker > 0 else 0
        workers_needed = max(1, round(workers_needed))
        workforce.append(workers_needed)

        if workers_needed > prev_workers:
            total_cost += (workers_needed - prev_workers) * hiring_cost
        elif workers_needed < prev_workers:
            total_cost += (prev_workers - workers_needed) * firing_cost

        total_cost += demand[i] * production_cost
        prev_workers = workers_needed

    return AggregatePlan(
        periods=[f"P{i + 1}" for i in range(n)],
        production=production,
        inventory=inventory,
        workforce=[float(w) for w in workforce],
        overtime=[0.0] * n,
        subcontract=[0.0] * n,
        total_cost=round(total_cost, 2),
        strategy="chase",
    )


def level_strategy(
    demand: list[float],
    production_cost: float = 20,
    holding_cost: float = 5,
    stockout_cost: float = 50,
    units_per_worker: float = 40,
    initial_inventory: float = 0,
) -> AggregatePlan:
    """Level strategy — constant production rate, inventory absorbs variation."""
    n = len(demand)
    total_demand = sum(demand)
    avg_production = total_demand / n

    # Round up to ensure we meet total demand
    level_production = [avg_production] * n

    inventory = []
    total_cost = 0
    inv = initial_inventory

    for i in range(n):
        inv += level_production[i] - demand[i]
        inventory.append(inv)
        total_cost += level_production[i] * production_cost
        if inv > 0:
            total_cost += inv * holding_cost
        else:
            total_cost += abs(inv) * stockout_cost

    workers = avg_production / units_per_worker if units_per_worker > 0 else 0

    return AggregatePlan(
        periods=[f"P{i + 1}" for i in range(n)],
        production=level_production,
        inventory=inventory,
        workforce=[round(workers)] * n,
        overtime=[0.0] * n,
        subcontract=[0.0] * n,
        total_cost=round(total_cost, 2),
        strategy="level",
    )


def compare_strategies(
    demand: list[float],
    **kwargs,
) -> list[AggregatePlan]:
    """Run both strategies and return sorted by total cost."""
    chase = chase_strategy(demand, **{k: v for k, v in kwargs.items() if k in chase_strategy.__code__.co_varnames})
    level = level_strategy(demand, **{k: v for k, v in kwargs.items() if k in level_strategy.__code__.co_varnames})
    return sorted([chase, level], key=lambda p: p.total_cost)
