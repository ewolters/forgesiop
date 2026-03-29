"""Shared data types for ForgeSIOP.

Pure Python dataclasses. No Django. No ORM. These are the
interchange format between modules.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any


@dataclass
class Item:
    """A stockkeeping unit (SKU) or material."""

    id: str
    name: str
    unit: str = "ea"
    cost: float = 0.0
    lead_time_days: float = 0.0
    lead_time_std_days: float = 0.0
    classification: str = ""  # "A", "B", "C", "AX", "BY", etc.
    properties: dict[str, Any] = field(default_factory=dict)


@dataclass
class BOMEntry:
    """A single row in a bill of materials."""

    parent_id: str
    child_id: str
    quantity_per: float
    scrap_factor: float = 0.0  # 0.02 = 2% scrap allowance
    offset_days: int = 0  # lead time offset within parent


@dataclass
class DemandRecord:
    """A single demand observation (historical or forecast)."""

    item_id: str
    period: date  # typically month start
    quantity: float
    is_forecast: bool = False


@dataclass
class InventoryPosition:
    """Current inventory state for an item."""

    item_id: str
    on_hand: float = 0.0
    on_order: float = 0.0
    committed: float = 0.0
    safety_stock: float = 0.0
    reorder_point: float = 0.0

    @property
    def available(self) -> float:
        return self.on_hand + self.on_order - self.committed

    @property
    def net_position(self) -> float:
        return self.on_hand + self.on_order - self.committed


@dataclass
class CapacitySlot:
    """Available capacity for a work center in a period."""

    work_center_id: str
    period: date
    available_hours: float
    efficiency: float = 1.0  # 0.85 = 85% OEE
    loaded_hours: float = 0.0

    @property
    def remaining_hours(self) -> float:
        return (self.available_hours * self.efficiency) - self.loaded_hours

    @property
    def utilization(self) -> float:
        effective = self.available_hours * self.efficiency
        return self.loaded_hours / effective if effective > 0 else 0.0


@dataclass
class Routing:
    """A manufacturing routing step."""

    item_id: str
    operation: int  # sequence number
    work_center_id: str
    setup_hours: float = 0.0
    run_hours_per_unit: float = 0.0
    description: str = ""


@dataclass
class SupplyRisk:
    """Supply risk assessment for a supplier or item.

    Fed from SVEND's supplier quality data (claims, scores, detection rates).
    ForgeSIOP doesn't know about SVEND — it just takes these numbers.
    """

    supplier_id: str
    quality_score: float = 1.0  # 0-1, from supplier claim quality scoring
    open_claims: int = 0
    lead_time_reliability: float = 1.0  # 0-1, on-time delivery rate
    risk_level: str = "low"  # "low", "medium", "high", "critical"

    @property
    def risk_factor(self) -> float:
        """Multiplier for safety stock. Higher risk = more buffer."""
        if self.risk_level == "critical":
            return 2.0
        if self.risk_level == "high":
            return 1.5
        if self.risk_level == "medium":
            return 1.2
        return 1.0


@dataclass
class ProcessCapability:
    """Process capability data for an item/operation.

    Fed from SVEND's graph (Cpk from SPC, yield from evidence).
    ForgeSIOP doesn't know about the graph — it just takes these numbers.
    """

    item_id: str
    operation: int = 0
    cpk: float | None = None
    ppk: float | None = None
    yield_rate: float = 1.0  # 0-1, fraction conforming
    yield_std: float = 0.0  # variability in yield

    @property
    def expected_good_units(self) -> float:
        """Given 100 units in, how many good units out."""
        return self.yield_rate * 100


@dataclass
class PlanResult:
    """Result of a planning run (MRP, SIOP, etc.)."""

    planned_orders: list[dict] = field(default_factory=list)
    # [{item_id, quantity, release_date, due_date, order_type}]

    exceptions: list[dict] = field(default_factory=list)
    # [{type, item_id, message, severity}]

    metrics: dict[str, float] = field(default_factory=dict)
    # {total_cost, service_level, inventory_turns, ...}

    warnings: list[str] = field(default_factory=list)
