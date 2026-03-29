"""Seasonality — decomposition and seasonal indices."""

from __future__ import annotations


def seasonal_indices(data: list[float], period: int = 12) -> list[float]:
    """Compute seasonal indices using ratio-to-moving-average method.

    Args:
        data: historical demand (at least 2 full cycles)
        period: seasonality period (12 for monthly, 4 for quarterly)

    Returns:
        List of seasonal indices (one per period position, centered on 1.0)
    """
    n = len(data)
    if n < period * 2:
        return [1.0] * period

    # Centered moving average
    half = period // 2
    cma = [None] * n
    for i in range(half, n - half):
        window = data[i - half: i + half + (1 if period % 2 else 0)]
        cma[i] = sum(window) / len(window) if window else None

    # Ratio to CMA
    ratios_by_position: dict[int, list[float]] = {p: [] for p in range(period)}
    for i in range(n):
        if cma[i] and cma[i] > 0:
            pos = i % period
            ratios_by_position[pos].append(data[i] / cma[i])

    # Average ratio per position
    indices = []
    for p in range(period):
        ratios = ratios_by_position[p]
        idx = sum(ratios) / len(ratios) if ratios else 1.0
        indices.append(idx)

    # Normalize to sum to period
    total = sum(indices)
    if total > 0:
        factor = period / total
        indices = [idx * factor for idx in indices]

    return indices


def deseasonalize(data: list[float], indices: list[float]) -> list[float]:
    """Remove seasonality from data."""
    period = len(indices)
    return [d / indices[i % period] if indices[i % period] > 0 else d for i, d in enumerate(data)]


def reseasonalize(data: list[float], indices: list[float], start_position: int = 0) -> list[float]:
    """Apply seasonal indices to deseasonalized data."""
    period = len(indices)
    return [d * indices[(start_position + i) % period] for i, d in enumerate(data)]
