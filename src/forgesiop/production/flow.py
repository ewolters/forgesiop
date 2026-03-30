"""Flow analysis — Little's Law, throughput, bottleneck identification, value ratio."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class LittlesLawResult:
    """Little's Law computation."""

    wip: float = 0.0
    throughput: float = 0.0
    lead_time: float = 0.0
    solved_for: str = ""  # which variable was computed


@dataclass
class StationData:
    """One station in bottleneck analysis."""

    name: str
    cycle_time: float
    utilization: float = 0.0
    is_bottleneck: bool = False


@dataclass
class BottleneckResult:
    """Bottleneck analysis result."""

    constraint: str = ""
    constraint_cycle_time: float = 0.0
    system_throughput: float = 0.0  # units/hour
    stations: list[StationData] = field(default_factory=list)


def littles_law(
    wip: float | None = None,
    throughput: float | None = None,
    lead_time: float | None = None,
) -> LittlesLawResult:
    """Little's Law: L = λW. Provide any 2, get the 3rd.

    Args:
        wip: Work in process (L).
        throughput: Units per time period (λ).
        lead_time: Time in system (W).

    Returns:
        LittlesLawResult with all three values.
    """
    given = sum(1 for v in [wip, throughput, lead_time] if v is not None)
    if given < 2:
        raise ValueError("Provide at least 2 of: wip, throughput, lead_time")

    if wip is None:
        wip = throughput * lead_time
        solved = "wip"
    elif throughput is None:
        throughput = wip / lead_time if lead_time > 0 else 0
        solved = "throughput"
    else:
        lead_time = wip / throughput if throughput > 0 else 0
        solved = "lead_time"

    return LittlesLawResult(wip=wip, throughput=throughput, lead_time=lead_time, solved_for=solved)


def throughput_rate(completed: int, elapsed_seconds: float) -> float:
    """Throughput = completed units / elapsed time (units/hour).

    Args:
        completed: Number of completed units.
        elapsed_seconds: Elapsed time in seconds.

    Returns:
        Units per hour.
    """
    if elapsed_seconds <= 0:
        return 0.0
    return (completed / elapsed_seconds) * 3600


def bottleneck_analysis(stations: list[dict]) -> BottleneckResult:
    """Identify the constraint station (highest cycle time).

    System throughput is limited by the bottleneck.

    Args:
        stations: [{name, cycle_time}] — cycle time in seconds.

    Returns:
        BottleneckResult with constraint identified and system throughput.
    """
    if not stations:
        return BottleneckResult()

    max_ct = 0.0
    bottleneck_name = ""
    results = []

    for s in stations:
        ct = s["cycle_time"]
        if ct > max_ct:
            max_ct = ct
            bottleneck_name = s["name"]

    system_tput = 3600 / max_ct if max_ct > 0 else 0

    for s in stations:
        ct = s["cycle_time"]
        util = (ct / max_ct) * 100 if max_ct > 0 else 0
        results.append(StationData(
            name=s["name"],
            cycle_time=ct,
            utilization=util,
            is_bottleneck=s["name"] == bottleneck_name,
        ))

    return BottleneckResult(
        constraint=bottleneck_name,
        constraint_cycle_time=max_ct,
        system_throughput=system_tput,
        stations=results,
    )


def value_ratio(value_add_time: float, total_lead_time: float) -> float:
    """Process cycle efficiency = value-add time / total lead time.

    World-class target: > 25%. Most processes: 1-5%.

    Returns:
        Ratio as percentage (0-100).
    """
    if total_lead_time <= 0:
        return 0.0
    return (value_add_time / total_lead_time) * 100
