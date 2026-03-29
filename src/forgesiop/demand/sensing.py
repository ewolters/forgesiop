"""Demand sensing — short-horizon signal adjustment.

Adjusts statistical forecast with recent actual demand to
improve near-term accuracy.
"""

from __future__ import annotations


def demand_sensing(
    forecast: list[float],
    recent_actuals: list[float],
    alpha: float = 0.6,
    horizon: int = 4,
) -> list[float]:
    """Adjust forecast with recent actual demand signal.

    Blends forecast with actual demand trend over the sensing horizon.
    Near-term periods get more actual-influenced adjustment.

    Args:
        forecast: statistical forecast for upcoming periods
        recent_actuals: last N periods of actual demand
        alpha: weight toward actuals (0.6 = 60% actual, 40% forecast)
        horizon: how many periods to adjust (beyond this, forecast unchanged)

    Returns:
        Adjusted forecast
    """
    if not recent_actuals or not forecast:
        return list(forecast)

    # Compute recent trend
    if len(recent_actuals) >= 2:
        trend = (recent_actuals[-1] - recent_actuals[0]) / len(recent_actuals)
    else:
        trend = 0

    # Compute recent level
    level = sum(recent_actuals[-3:]) / min(3, len(recent_actuals))

    adjusted = list(forecast)
    for i in range(min(horizon, len(adjusted))):
        decay = alpha * (1 - i / horizon)  # fades out over horizon
        sensed = level + trend * (i + 1)
        adjusted[i] = decay * sensed + (1 - decay) * forecast[i]

    return adjusted
