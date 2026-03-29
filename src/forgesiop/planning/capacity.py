"""Capacity planning — RCCP, finite loading, bottleneck identification.

No external dependencies.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date

from ..core.types import CapacitySlot, Routing


@dataclass
class CapacityResult:
    """Result of capacity analysis for a work center."""

    work_center_id: str
    period: date
    available_hours: float
    loaded_hours: float
    utilization: float
    overloaded: bool
    overflow_hours: float


def rough_cut_capacity(
    planned_orders: list[dict],
    routings: dict[str, list[Routing]],
    capacity_slots: list[CapacitySlot],
) -> list[CapacityResult]:
    """Rough-cut capacity planning (RCCP).

    Loads planned orders against available capacity by work center and period.

    Args:
        planned_orders: [{item_id, quantity, release_date, due_date}]
        routings: {item_id: [Routing]} — operation sequence per item
        capacity_slots: available capacity per work center per period
    """
    # Build capacity lookup
    cap_lookup: dict[tuple[str, date], CapacitySlot] = {}
    for slot in capacity_slots:
        cap_lookup[(slot.work_center_id, slot.period)] = slot

    # Load each order
    load: dict[tuple[str, date], float] = defaultdict(float)
    for order in planned_orders:
        item_id = order["item_id"]
        qty = order["quantity"]
        release = order["release_date"]

        for routing in routings.get(item_id, []):
            hours = routing.setup_hours + routing.run_hours_per_unit * qty
            # Find the period this falls into
            for slot in capacity_slots:
                if slot.work_center_id == routing.work_center_id:
                    if slot.period <= release < date(slot.period.year, slot.period.month + 1 if slot.period.month < 12 else 1, 1) if slot.period.month < 12 else date(slot.period.year + 1, 1, 1):
                        load[(routing.work_center_id, slot.period)] += hours
                        break

    # Compute results
    results = []
    for slot in capacity_slots:
        key = (slot.work_center_id, slot.period)
        loaded = load.get(key, 0)
        effective = slot.available_hours * slot.efficiency
        util = loaded / effective if effective > 0 else 0
        overflow = max(0, loaded - effective)

        results.append(CapacityResult(
            work_center_id=slot.work_center_id,
            period=slot.period,
            available_hours=effective,
            loaded_hours=loaded,
            utilization=round(util, 4),
            overloaded=loaded > effective,
            overflow_hours=round(overflow, 2),
        ))

    return results


def identify_bottlenecks(results: list[CapacityResult], threshold: float = 0.85) -> list[dict]:
    """Identify bottleneck work centers.

    A bottleneck is any work center with utilization above threshold
    in any period.
    """
    bottlenecks = []
    for r in results:
        if r.utilization >= threshold:
            bottlenecks.append({
                "work_center_id": r.work_center_id,
                "period": r.period.isoformat(),
                "utilization": r.utilization,
                "overflow_hours": r.overflow_hours,
            })

    bottlenecks.sort(key=lambda b: b["utilization"], reverse=True)
    return bottlenecks
