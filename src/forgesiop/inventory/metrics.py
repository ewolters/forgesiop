"""Inventory performance metrics."""

from __future__ import annotations


def inventory_turns(cogs: float, average_inventory_value: float) -> float:
    """Inventory turnover = COGS / average inventory value."""
    if average_inventory_value <= 0:
        return 0.0
    return cogs / average_inventory_value


def days_of_supply(on_hand: float, average_daily_demand: float) -> float:
    """Days of supply = on hand / average daily demand."""
    if average_daily_demand <= 0:
        return float("inf")
    return on_hand / average_daily_demand


def fill_rate(units_shipped: float, units_ordered: float) -> float:
    """Order fill rate = units shipped / units ordered."""
    if units_ordered <= 0:
        return 0.0
    return min(1.0, units_shipped / units_ordered)


def gmroi(gross_margin: float, average_inventory_cost: float) -> float:
    """Gross Margin Return on Inventory Investment."""
    if average_inventory_cost <= 0:
        return 0.0
    return gross_margin / average_inventory_cost


def stockout_rate(stockout_periods: int, total_periods: int) -> float:
    """Fraction of periods with stockout."""
    if total_periods <= 0:
        return 0.0
    return stockout_periods / total_periods


def weeks_of_supply(on_hand: float, average_weekly_demand: float) -> float:
    """Weeks of supply = on hand / average weekly demand."""
    if average_weekly_demand <= 0:
        return float("inf")
    return on_hand / average_weekly_demand
