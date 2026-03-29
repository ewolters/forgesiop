"""Available-to-Promise and Capable-to-Promise.

ATP: uncommitted inventory available for new orders.
CTP: ATP + capacity check + (optionally) capability check.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta


@dataclass
class ATPResult:
    """ATP result for a period."""

    period: date
    available: float
    cumulative: float


def available_to_promise(
    on_hand: float,
    master_schedule: list[tuple[date, float]],
    committed_orders: list[tuple[date, float]],
    planning_periods: list[date],
) -> list[ATPResult]:
    """Compute Available-to-Promise by period.

    ATP = MPS quantity - committed orders between this MPS and next MPS.
    First period ATP includes current on-hand.

    Args:
        on_hand: current inventory on hand
        master_schedule: [(date, quantity)] — production schedule
        committed_orders: [(date, quantity)] — customer orders already committed
    """
    # Sort inputs
    mps = sorted(master_schedule, key=lambda x: x[0])
    orders = sorted(committed_orders, key=lambda x: x[0])

    results = []
    cumulative = 0

    for i, period in enumerate(planning_periods):
        # MPS in this period
        mps_qty = sum(q for d, q in mps if _in_period(d, period, planning_periods, i))

        # Committed in this period
        committed = sum(q for d, q in orders if _in_period(d, period, planning_periods, i))

        if i == 0:
            atp = on_hand + mps_qty - committed
        else:
            atp = mps_qty - committed

        cumulative += atp
        results.append(ATPResult(
            period=period,
            available=max(0, atp),
            cumulative=max(0, cumulative),
        ))

    return results


def capable_to_promise(
    atp_results: list[ATPResult],
    capacity_available: dict[date, float],
    hours_per_unit: float,
    capability_ok: bool = True,
) -> list[dict]:
    """Capable-to-Promise — ATP constrained by capacity and capability.

    Args:
        atp_results: from available_to_promise()
        capacity_available: {period: remaining_hours}
        hours_per_unit: production time per unit
        capability_ok: whether process capability is sufficient (from Cpk check)

    Returns:
        [{period, atp, capacity_limited, capability_ok, ctp}]
    """
    results = []
    for atp in atp_results:
        cap_hours = capacity_available.get(atp.period, 0)
        cap_units = cap_hours / hours_per_unit if hours_per_unit > 0 else float("inf")

        ctp = min(atp.available, cap_units) if capability_ok else 0

        results.append({
            "period": atp.period.isoformat(),
            "atp": atp.available,
            "capacity_units": round(cap_units, 1),
            "capacity_limited": atp.available > cap_units,
            "capability_ok": capability_ok,
            "ctp": round(ctp, 1),
        })

    return results


def _in_period(d: date, period: date, periods: list[date], idx: int) -> bool:
    """Check if a date falls within a planning period."""
    next_period = periods[idx + 1] if idx + 1 < len(periods) else period + timedelta(days=7)
    return period <= d < next_period
