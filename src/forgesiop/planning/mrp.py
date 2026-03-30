"""Material Requirements Planning — time-phased explosion.

BOM traversal + gross-to-net + lot sizing + lead time offsetting.
No external dependencies beyond core types.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta

from ..core.bom import BOM
from ..core.types import BOMEntry, InventoryPosition, Item


@dataclass
class MRPRecord:
    """MRP time-phased record for one item."""

    item_id: str
    periods: list[date]
    gross_requirements: list[float]
    scheduled_receipts: list[float]
    projected_on_hand: list[float]
    net_requirements: list[float]
    planned_order_receipts: list[float]
    planned_order_releases: list[float]
    lead_time_days: int = 0


@dataclass
class PlannedOrder:
    """A single planned order from MRP."""

    item_id: str
    quantity: float
    release_date: date
    due_date: date
    order_type: str = "planned"  # planned, firm, released


def run_mrp(
    items: dict[str, Item],
    bom_entries: list[BOMEntry],
    master_schedule: dict[str, list[tuple[date, float]]],
    inventory: dict[str, InventoryPosition],
    lot_size_policy: str = "lot_for_lot",
    fixed_lot_size: float = 0,
    planning_horizon_days: int = 90,
    start_date: date | None = None,
) -> dict[str, MRPRecord]:
    """Run full MRP explosion.

    Args:
        items: {item_id: Item} — all items with lead times
        bom_entries: flat list of BOM relationships
        master_schedule: {item_id: [(date, quantity)]} — MPS for top-level items
        inventory: {item_id: InventoryPosition}
        lot_size_policy: "lot_for_lot", "fixed", "eoq"
        planning_horizon_days: how far out to plan
        start_date: planning start (defaults to today)

    Returns:
        {item_id: MRPRecord} for every item touched
    """
    if start_date is None:
        start_date = date.today()

    bom = BOM(bom_entries)
    llc = bom.low_level_codes()

    # Ensure MPS items have LLC 0 even if not in BOM
    for item_id in master_schedule:
        if item_id not in llc:
            llc[item_id] = 0

    # Generate weekly periods
    periods = []
    d = start_date
    end = start_date + timedelta(days=planning_horizon_days)
    while d <= end:
        periods.append(d)
        d += timedelta(days=7)

    n = len(periods)
    records: dict[str, MRPRecord] = {}

    # Initialize gross requirements from MPS
    gross: dict[str, list[float]] = defaultdict(lambda: [0.0] * n)
    for item_id, schedule in master_schedule.items():
        for sdate, qty in schedule:
            for i, p in enumerate(periods):
                if p <= sdate < p + timedelta(days=7):
                    gross[item_id][i] += qty
                    break

    # Process by low-level code (0 first)
    max_llc = max(llc.values()) if llc else 0
    for level in range(max_llc + 1):
        items_at_level = [iid for iid, llc_val in llc.items() if llc_val == level]

        for item_id in items_at_level:
            item = items.get(item_id)
            lt = int(item.lead_time_days / 7) if item else 0  # convert to periods (weeks)
            inv = inventory.get(item_id, InventoryPosition(item_id=item_id))
            on_hand = inv.on_hand

            gr = gross[item_id]
            sr = [0.0] * n  # scheduled receipts (existing orders)
            poh = [0.0] * n
            nr = [0.0] * n
            por = [0.0] * n  # planned order receipts
            porel = [0.0] * n  # planned order releases

            for i in range(n):
                available = (poh[i - 1] if i > 0 else on_hand) + sr[i] - gr[i]

                if available < 0:
                    net = abs(available)
                    nr[i] = net

                    # Lot sizing
                    if lot_size_policy == "fixed" and fixed_lot_size > 0:
                        import math
                        lot_qty = math.ceil(net / fixed_lot_size) * fixed_lot_size
                    else:
                        lot_qty = net  # lot-for-lot

                    por[i] = lot_qty
                    poh[i] = available + lot_qty

                    # Offset by lead time
                    release_period = i - lt
                    if 0 <= release_period < n:
                        porel[release_period] = lot_qty
                else:
                    poh[i] = available

            records[item_id] = MRPRecord(
                item_id=item_id,
                periods=periods,
                gross_requirements=gr,
                scheduled_receipts=sr,
                projected_on_hand=poh,
                net_requirements=nr,
                planned_order_receipts=por,
                planned_order_releases=porel,
                lead_time_days=int(item.lead_time_days) if item else 0,
            )

            # Explode planned order releases into child gross requirements
            for i, qty in enumerate(porel):
                if qty > 0:
                    for child_entry in bom.get_children(item_id):
                        child_qty = qty * child_entry.quantity_per
                        if child_entry.scrap_factor > 0:
                            child_qty /= (1 - child_entry.scrap_factor)
                        gross[child_entry.child_id][i] += child_qty

    return records


def extract_planned_orders(records: dict[str, MRPRecord]) -> list[PlannedOrder]:
    """Extract planned orders from MRP records."""
    orders = []
    for item_id, rec in records.items():
        for i, qty in enumerate(rec.planned_order_releases):
            if qty > 0:
                release = rec.periods[i]
                lt = rec.lead_time_days
                due = release + timedelta(days=lt)
                orders.append(PlannedOrder(
                    item_id=item_id,
                    quantity=qty,
                    release_date=release,
                    due_date=due,
                ))
    return orders
