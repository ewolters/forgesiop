"""Demand forecasting — pure Python implementations.

No external dependencies for core methods (SMA, WMA, SES, Holt).
statsmodels optional for Holt-Winters and ARIMA.
"""

from __future__ import annotations


def simple_moving_average(data: list[float], periods: int = 3) -> float:
    """Simple moving average forecast."""
    if len(data) < periods:
        return sum(data) / len(data) if data else 0.0
    return sum(data[-periods:]) / periods


def weighted_moving_average(data: list[float], weights: list[float]) -> float:
    """Weighted moving average forecast."""
    n = len(weights)
    if len(data) < n:
        return simple_moving_average(data, len(data))
    recent = data[-n:]
    return sum(v * w for v, w in zip(recent, weights)) / sum(weights)


def single_exponential_smoothing(data: list[float], alpha: float = 0.3) -> list[float]:
    """Simple exponential smoothing. Returns full smoothed series."""
    if not data:
        return []
    result = [data[0]]
    for i in range(1, len(data)):
        result.append(alpha * data[i] + (1 - alpha) * result[-1])
    return result


def holt_trend_corrected(
    data: list[float],
    alpha: float = 0.3,
    beta: float = 0.1,
    periods_ahead: int = 1,
) -> float:
    """Holt's trend-corrected exponential smoothing.

    Returns forecast for `periods_ahead` beyond the last data point.
    """
    if len(data) < 2:
        return data[0] if data else 0.0

    level = data[0]
    trend = data[1] - data[0]

    for i in range(1, len(data)):
        new_level = alpha * data[i] + (1 - alpha) * (level + trend)
        new_trend = beta * (new_level - level) + (1 - beta) * trend
        level = new_level
        trend = new_trend

    return level + periods_ahead * trend


def croston_intermittent(
    data: list[float],
    alpha: float = 0.3,
) -> float:
    """Croston's method for intermittent demand.

    Separately smooths demand size and inter-arrival interval.
    """
    if not data or all(d == 0 for d in data):
        return 0.0

    # Initialize with first non-zero
    demand_sizes = []
    intervals = []
    gap = 0
    for d in data:
        gap += 1
        if d > 0:
            demand_sizes.append(d)
            intervals.append(gap)
            gap = 0

    if not demand_sizes:
        return 0.0

    # Smooth demand size
    z = demand_sizes[0]
    for d in demand_sizes[1:]:
        z = alpha * d + (1 - alpha) * z

    # Smooth interval
    p = intervals[0]
    for i in intervals[1:]:
        p = alpha * i + (1 - alpha) * p

    return z / p if p > 0 else 0.0
