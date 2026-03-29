"""Demand Driven MRP — buffer sizing, net flow, execution alerts.

First standalone pip-installable DDMRP engine. No ERP dependency.
Implements the Demand Driven Institute's core concepts.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class BufferZone(Enum):
    RED = "red"
    YELLOW = "yellow"
    GREEN = "green"


class AlertStatus(Enum):
    NORMAL = "normal"
    YELLOW = "yellow"  # net flow in yellow zone
    RED = "red"  # net flow in red zone
    CRITICAL = "critical"  # net flow below red base


@dataclass
class BufferProfile:
    """DDMRP buffer profile for a strategic decoupling point."""

    item_id: str
    average_daily_usage: float
    decoupled_lead_time_days: float
    lead_time_factor: float = 1.0  # variability factor (0.2-1.0)
    variability_factor: float = 0.5  # demand variability (0-1)
    order_frequency_days: float = 1.0

    @property
    def red_base(self) -> float:
        """Red base = ADU × DLT × lead time factor."""
        return self.average_daily_usage * self.decoupled_lead_time_days * self.lead_time_factor

    @property
    def red_safety(self) -> float:
        """Red safety = red base × variability factor."""
        return self.red_base * self.variability_factor

    @property
    def red_zone(self) -> float:
        """Total red zone = red base + red safety."""
        return self.red_base + self.red_safety

    @property
    def green_zone(self) -> float:
        """Green zone = max(ADU × DLT × lead time factor, ADU × order cycle, min order qty)."""
        return max(
            self.average_daily_usage * self.decoupled_lead_time_days * self.lead_time_factor,
            self.average_daily_usage * self.order_frequency_days,
        )

    @property
    def yellow_zone(self) -> float:
        """Yellow zone = ADU × DLT."""
        return self.average_daily_usage * self.decoupled_lead_time_days

    @property
    def top_of_green(self) -> float:
        """Top of buffer = red + yellow + green."""
        return self.red_zone + self.yellow_zone + self.green_zone

    @property
    def top_of_yellow(self) -> float:
        return self.red_zone + self.yellow_zone

    @property
    def top_of_red(self) -> float:
        return self.red_zone


def net_flow_position(
    on_hand: float,
    on_order: float,
    qualified_demand: float,
) -> float:
    """Net flow position = on hand + on order - qualified demand.

    Qualified demand = actual demand orders within the DLT horizon.
    """
    return on_hand + on_order - qualified_demand


def net_flow_equation(
    profile: BufferProfile,
    on_hand: float,
    on_order: float,
    qualified_demand: float,
) -> dict:
    """Full DDMRP net flow calculation.

    Returns order recommendation and zone status.
    """
    nfp = net_flow_position(on_hand, on_order, qualified_demand)
    tog = profile.top_of_green

    # Determine zone
    if nfp >= profile.top_of_yellow:
        zone = BufferZone.GREEN
        alert = AlertStatus.NORMAL
    elif nfp >= profile.top_of_red:
        zone = BufferZone.YELLOW
        alert = AlertStatus.YELLOW
    elif nfp >= profile.red_base:
        zone = BufferZone.RED
        alert = AlertStatus.RED
    else:
        zone = BufferZone.RED
        alert = AlertStatus.CRITICAL

    # Order recommendation: if NFP < TOG, order up to TOG
    recommended_order = max(0, tog - nfp) if nfp < tog else 0

    return {
        "net_flow_position": nfp,
        "top_of_green": tog,
        "top_of_yellow": profile.top_of_yellow,
        "top_of_red": profile.top_of_red,
        "red_base": profile.red_base,
        "zone": zone.value,
        "alert": alert.value,
        "recommended_order": recommended_order,
        "buffer_penetration": 1 - (nfp / tog) if tog > 0 else 1.0,
    }


def execution_alerts(
    profiles: list[BufferProfile],
    positions: dict[str, dict],
) -> list[dict]:
    """Generate execution alerts across all buffers.

    Args:
        profiles: list of BufferProfile
        positions: {item_id: {on_hand, on_order, qualified_demand}}

    Returns:
        list of alerts sorted by severity
    """
    alerts = []
    for profile in profiles:
        pos = positions.get(profile.item_id, {})
        result = net_flow_equation(
            profile,
            on_hand=pos.get("on_hand", 0),
            on_order=pos.get("on_order", 0),
            qualified_demand=pos.get("qualified_demand", 0),
        )

        if result["alert"] != "normal":
            alerts.append({
                "item_id": profile.item_id,
                "alert": result["alert"],
                "zone": result["zone"],
                "net_flow_position": result["net_flow_position"],
                "buffer_penetration": result["buffer_penetration"],
                "recommended_order": result["recommended_order"],
            })

    # Sort: critical first, then red, then yellow
    priority = {"critical": 0, "red": 1, "yellow": 2}
    alerts.sort(key=lambda a: priority.get(a["alert"], 3))
    return alerts
