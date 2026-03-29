"""S&OP / SIOP — demand/supply balancing over planning horizon.

Scenario comparison, constraint propagation, executive summary.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass
class SIOPScenario:
    """A single S&OP scenario with demand, supply, and constraints."""

    name: str
    periods: list[date]
    demand: list[float]
    supply: list[float]
    opening_inventory: float = 0
    target_service_level: float = 0.95
    target_inventory_days: float = 30
    notes: str = ""

    @property
    def balance(self) -> list[float]:
        """Cumulative supply - demand balance per period."""
        result = []
        cum = self.opening_inventory
        for d, s in zip(self.demand, self.supply):
            cum += s - d
            result.append(cum)
        return result

    @property
    def projected_inventory(self) -> list[float]:
        return self.balance

    @property
    def stockout_periods(self) -> list[int]:
        return [i for i, b in enumerate(self.balance) if b < 0]

    @property
    def total_demand(self) -> float:
        return sum(self.demand)

    @property
    def total_supply(self) -> float:
        return sum(self.supply)

    @property
    def service_level(self) -> float:
        """Fraction of periods with positive inventory."""
        bal = self.balance
        if not bal:
            return 0
        return sum(1 for b in bal if b >= 0) / len(bal)


def balance_scenario(scenario: SIOPScenario) -> dict:
    """Analyze a single S&OP scenario.

    Returns executive-level summary.
    """
    bal = scenario.balance
    n = len(bal)

    avg_daily_demand = scenario.total_demand / n if n else 0
    avg_inventory = sum(max(0, b) for b in bal) / n if n else 0
    dos = avg_inventory / avg_daily_demand if avg_daily_demand > 0 else 0
    excess = sum(max(0, b - avg_daily_demand * scenario.target_inventory_days) for b in bal)
    shortage = sum(abs(min(0, b)) for b in bal)

    return {
        "scenario": scenario.name,
        "total_demand": scenario.total_demand,
        "total_supply": scenario.total_supply,
        "gap": scenario.total_supply - scenario.total_demand,
        "service_level": round(scenario.service_level, 4),
        "meets_service_target": scenario.service_level >= scenario.target_service_level,
        "stockout_periods": len(scenario.stockout_periods),
        "average_inventory": round(avg_inventory, 1),
        "days_of_supply": round(dos, 1),
        "excess_inventory": round(excess, 1),
        "total_shortage": round(shortage, 1),
        "ending_inventory": round(bal[-1], 1) if bal else 0,
    }


def compare_scenarios(scenarios: list[SIOPScenario]) -> dict:
    """Compare multiple S&OP scenarios side by side.

    Returns ranked comparison with recommendation.
    """
    analyses = [balance_scenario(s) for s in scenarios]

    # Score each scenario
    for a in analyses:
        score = 0
        if a["meets_service_target"]:
            score += 40
        score += min(30, a["service_level"] * 30)
        # Penalize excess inventory
        if a["excess_inventory"] > 0:
            score -= min(15, a["excess_inventory"] / max(a["total_demand"], 1) * 100)
        # Penalize shortage
        if a["total_shortage"] > 0:
            score -= min(20, a["total_shortage"] / max(a["total_demand"], 1) * 100)
        a["score"] = round(max(0, score), 1)

    analyses.sort(key=lambda a: a["score"], reverse=True)

    return {
        "scenarios": analyses,
        "recommended": analyses[0]["scenario"] if analyses else None,
        "recommendation_reason": _recommendation_reason(analyses[0]) if analyses else "",
    }


def _recommendation_reason(analysis: dict) -> str:
    reasons = []
    if analysis["meets_service_target"]:
        reasons.append(f"meets {analysis['service_level']:.0%} service level")
    if analysis["stockout_periods"] == 0:
        reasons.append("no stockouts")
    if analysis["days_of_supply"] > 0:
        reasons.append(f"{analysis['days_of_supply']:.0f} days of supply")
    return "; ".join(reasons) if reasons else "best available option"
