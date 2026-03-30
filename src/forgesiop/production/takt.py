"""Takt time, cycle time analysis, line balancing (Yamazumi)."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class TaktResult:
    """Takt time computation result."""

    takt_seconds: float = 0.0
    takt_minutes: float = 0.0
    available_seconds: float = 0.0
    demand: float = 0.0


@dataclass
class StationBalance:
    """One station in a line balance."""

    name: str
    cycle_time: float
    utilization: float = 0.0
    free_capacity: float = 0.0
    over_takt: bool = False


@dataclass
class LineBalanceResult:
    """Line balancing (Yamazumi) result."""

    takt: float = 0.0
    stations: list[StationBalance] = field(default_factory=list)
    rto: float = 0.0  # required team operators
    staff: int = 0
    line_efficiency: float = 0.0
    bottleneck: str = ""


def takt_time(available_minutes: float, demand: float, breaks_minutes: float = 0) -> TaktResult:
    """Takt time = net available time / customer demand.

    Args:
        available_minutes: Total available time in minutes.
        demand: Units required per period.
        breaks_minutes: Break time to subtract.
    """
    net = available_minutes - breaks_minutes
    if demand <= 0:
        return TaktResult(available_seconds=net * 60, demand=demand)

    takt_min = net / demand
    return TaktResult(
        takt_seconds=takt_min * 60,
        takt_minutes=takt_min,
        available_seconds=net * 60,
        demand=demand,
    )


def line_balance(
    stations: list[dict],
    takt_seconds: float,
    cov_pct: float = 0,
) -> LineBalanceResult:
    """Line balance analysis (Yamazumi chart data).

    Args:
        stations: [{name, cycle_time}] — cycle time in seconds.
        takt_seconds: Takt time in seconds.
        cov_pct: Coefficient of variation % for staffing margin.

    Returns:
        LineBalanceResult with per-station utilization and overall efficiency.
    """
    if not stations or takt_seconds <= 0:
        return LineBalanceResult()

    total_ct = sum(s["cycle_time"] for s in stations)
    rto = total_ct / takt_seconds
    margin = rto * (cov_pct / 100) if cov_pct > 0 else 0
    staff = max(1, int(rto + margin + 0.999))  # ceil

    balance = []
    bottleneck_name = ""
    max_ct = 0

    for s in stations:
        ct = s["cycle_time"]
        util = min(100, (ct / takt_seconds) * 100)
        free = max(0, takt_seconds - ct)
        over = ct > takt_seconds

        if ct > max_ct:
            max_ct = ct
            bottleneck_name = s["name"]

        balance.append(StationBalance(
            name=s["name"],
            cycle_time=ct,
            utilization=util,
            free_capacity=free,
            over_takt=over,
        ))

    efficiency = (rto / staff) * 100 if staff > 0 else 0

    return LineBalanceResult(
        takt=takt_seconds,
        stations=balance,
        rto=rto,
        staff=staff,
        line_efficiency=efficiency,
        bottleneck=bottleneck_name,
    )
