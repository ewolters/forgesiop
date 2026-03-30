"""Cost of quality and production cost accounting."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class CostOfQualityResult:
    """Cost of quality (CoQ) breakdown."""

    prevention: float = 0.0
    appraisal: float = 0.0
    internal_failure: float = 0.0
    external_failure: float = 0.0
    total_coq: float = 0.0
    conformance_cost: float = 0.0  # prevention + appraisal
    nonconformance_cost: float = 0.0  # internal + external failure
    coq_revenue_pct: float | None = None


@dataclass
class ProductionCostResult:
    """Production cost accounting breakdown."""

    labor: float = 0.0
    overtime: float = 0.0
    material: float = 0.0
    scrap: float = 0.0
    holding: float = 0.0
    total: float = 0.0
    cost_per_unit: float | None = None


def cost_of_quality(
    prevention: float = 0,
    appraisal: float = 0,
    internal_failure: float = 0,
    external_failure: float = 0,
    revenue: float | None = None,
) -> CostOfQualityResult:
    """Cost of quality decomposition.

    Args:
        prevention: Training, planning, process improvement costs.
        appraisal: Inspection, testing, audit costs.
        internal_failure: Scrap, rework, retest costs.
        external_failure: Warranty, returns, complaint handling costs.
        revenue: Total revenue (for CoQ as % of revenue).
    """
    conformance = prevention + appraisal
    nonconformance = internal_failure + external_failure
    total = conformance + nonconformance
    pct = (total / revenue * 100) if revenue and revenue > 0 else None

    return CostOfQualityResult(
        prevention=prevention,
        appraisal=appraisal,
        internal_failure=internal_failure,
        external_failure=external_failure,
        total_coq=total,
        conformance_cost=conformance,
        nonconformance_cost=nonconformance,
        coq_revenue_pct=pct,
    )


def cost_accounting(
    worker_count: int = 0,
    labor_cost_per_hour: float = 0,
    hours_worked: float = 0,
    ot_worker_count: int = 0,
    ot_hours: float = 0,
    overtime_premium: float = 1.5,
    material_cost: float = 0,
    scrap_cost: float = 0,
    avg_wip: float = 0,
    holding_cost_per_unit_hour: float = 0,
    units_produced: int | None = None,
) -> ProductionCostResult:
    """Production cost accounting.

    Args:
        worker_count: Regular shift workers.
        labor_cost_per_hour: Wage rate.
        hours_worked: Regular hours.
        ot_worker_count: Overtime workers.
        ot_hours: Overtime hours.
        overtime_premium: OT multiplier (default 1.5x).
        material_cost: Raw material cost.
        scrap_cost: Scrap/waste cost.
        avg_wip: Average WIP units for holding cost.
        holding_cost_per_unit_hour: Inventory carrying cost.
        units_produced: For per-unit cost calculation.
    """
    labor = worker_count * labor_cost_per_hour * hours_worked
    overtime = ot_worker_count * labor_cost_per_hour * (overtime_premium - 1) * ot_hours
    holding = avg_wip * holding_cost_per_unit_hour * hours_worked
    total = labor + overtime + material_cost + scrap_cost + holding
    cpu = total / units_produced if units_produced and units_produced > 0 else None

    return ProductionCostResult(
        labor=labor,
        overtime=overtime,
        material=material_cost,
        scrap=scrap_cost,
        holding=holding,
        total=total,
        cost_per_unit=cpu,
    )


def payback_period(investment: float, annual_savings: float) -> float:
    """Simple payback period in years.

    Args:
        investment: Initial investment cost.
        annual_savings: Expected annual savings.

    Returns:
        Payback period in years. Returns inf if savings ≤ 0.
    """
    if annual_savings <= 0:
        return float("inf")
    return investment / annual_savings
