"""Kanban sizing, EPEI, pitch calculation."""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass
class KanbanResult:
    """Kanban quantity calculation."""

    base_quantity: float = 0.0
    safety_quantity: float = 0.0
    total_quantity: float = 0.0
    n_cards: int = 0
    container_size: float = 0.0


def kanban_quantity(
    daily_demand: float,
    lead_time_days: float,
    safety_factor: float = 0.1,
    container_size: float = 1,
) -> KanbanResult:
    """Toyota kanban formula: cards = (D × LT × (1 + SF)) / container.

    Args:
        daily_demand: Average daily demand.
        lead_time_days: Replenishment lead time in days.
        safety_factor: Safety factor as fraction (0.1 = 10%).
        container_size: Units per container/kanban.
    """
    base = daily_demand * lead_time_days
    safety = base * safety_factor
    total = base + safety
    cards = math.ceil(total / container_size) if container_size > 0 else 0

    return KanbanResult(
        base_quantity=base,
        safety_quantity=safety,
        total_quantity=total,
        n_cards=cards,
        container_size=container_size,
    )


def epei(
    changeover_time_minutes: float,
    available_minutes: float,
    num_products: int,
    target_pct: float = 10,
) -> float:
    """Every Part Every Interval — how often you can cycle through all products.

    EPEI = (products × changeover) / (available × budget%)

    Args:
        changeover_time_minutes: Average changeover time per product.
        available_minutes: Available production time.
        num_products: Number of different products to cycle through.
        target_pct: % of available time budgeted for changeovers (default 10%).

    Returns:
        EPEI in days (or same time unit as available_minutes).
    """
    budget = available_minutes * (target_pct / 100)
    if budget <= 0:
        return float("inf")
    total_co = num_products * changeover_time_minutes
    return total_co / budget


def pitch(takt_seconds: float, pack_size: int) -> float:
    """Pitch = takt × pack size. The heartbeat of material flow.

    Args:
        takt_seconds: Takt time in seconds.
        pack_size: Units per container/pack.

    Returns:
        Pitch time in seconds.
    """
    return takt_seconds * pack_size
