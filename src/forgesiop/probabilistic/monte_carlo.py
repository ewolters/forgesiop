"""Monte Carlo simulation for production plans.

Propagate distributions through the plan instead of point estimates.
THE DIFFERENTIATOR — nobody else does this.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field


@dataclass
class SimulationResult:
    """Result of a Monte Carlo plan simulation."""

    n_iterations: int
    metric_name: str
    mean: float
    std: float
    p5: float
    p25: float
    p50: float
    p75: float
    p95: float
    samples: list[float] = field(default_factory=list, repr=False)


def simulate_production(
    planned_quantity: float,
    yield_mean: float,
    yield_std: float,
    demand_mean: float,
    demand_std: float,
    lead_time_mean: float,
    lead_time_std: float,
    n_iterations: int = 5000,
) -> dict[str, SimulationResult]:
    """Monte Carlo simulation of a production plan.

    Samples from yield, demand, and lead time distributions to
    produce probabilistic output metrics.

    Returns dict of SimulationResult for each metric.
    """
    good_output_samples = []
    inventory_samples = []
    service_samples = []

    for _ in range(n_iterations):
        # Sample yield
        y = max(0, min(1, random.gauss(yield_mean, yield_std)))
        good_output = planned_quantity * y

        # Sample demand
        d = max(0, random.gauss(demand_mean, demand_std))

        # Sample lead time — demand accumulates over lead time
        lt = max(0.5, random.gauss(lead_time_mean, lead_time_std))
        demand_during_lt = d * lt

        # Ending inventory: good output minus demand over lead time
        inv = good_output - demand_during_lt
        inventory_samples.append(inv)
        good_output_samples.append(good_output)
        service_samples.append(1.0 if inv >= 0 else 0.0)

    return {
        "good_output": _summarize(good_output_samples, "good_output", n_iterations),
        "ending_inventory": _summarize(inventory_samples, "ending_inventory", n_iterations),
        "service_level": _summarize(service_samples, "service_level", n_iterations),
    }


def simulate_supply_chain(
    stages: list[dict],
    n_iterations: int = 5000,
) -> dict[str, SimulationResult]:
    """Monte Carlo simulation of a multi-stage supply chain.

    Each stage: {name, input_qty, yield_mean, yield_std, lead_time_mean, lead_time_std}
    Output of one stage feeds input of next.
    """
    final_outputs = []

    for _ in range(n_iterations):
        qty = stages[0].get("input_qty", 100)

        for stage in stages:
            y = max(0, min(1, random.gauss(stage["yield_mean"], stage.get("yield_std", 0))))
            qty *= y

        final_outputs.append(qty)

    return {
        "final_output": _summarize(final_outputs, "final_output", n_iterations),
    }


def _summarize(samples: list[float], name: str, n: int) -> SimulationResult:
    samples_sorted = sorted(samples)
    mean = sum(samples) / n
    variance = sum((s - mean) ** 2 for s in samples) / max(n - 1, 1)
    std = math.sqrt(variance)

    return SimulationResult(
        n_iterations=n,
        metric_name=name,
        mean=round(mean, 4),
        std=round(std, 4),
        p5=round(samples_sorted[int(0.05 * n)], 4),
        p25=round(samples_sorted[int(0.25 * n)], 4),
        p50=round(samples_sorted[int(0.50 * n)], 4),
        p75=round(samples_sorted[int(0.75 * n)], 4),
        p95=round(samples_sorted[int(0.95 * n)], 4),
        samples=samples,
    )
