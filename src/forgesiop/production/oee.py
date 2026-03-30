"""OEE (Overall Equipment Effectiveness) and TEEP.

OEE = Availability × Performance × Quality.
TEEP = OEE × Loading (utilization of calendar time).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class OEEResult:
    """OEE computation result with loss breakdown."""

    oee: float = 0.0
    availability: float = 0.0
    performance: float = 0.0
    quality: float = 0.0
    runtime: float = 0.0
    good_units: int = 0
    availability_loss: float = 0.0  # downtime minutes
    performance_loss: float = 0.0  # speed loss equivalent minutes
    quality_loss: float = 0.0  # defect equivalent minutes
    teep: float | None = None


def oee(
    planned_minutes: float,
    downtime_minutes: float,
    ideal_cycle_minutes: float,
    produced: int,
    defects: int = 0,
    loading_pct: float | None = None,
) -> OEEResult:
    """Calculate OEE with loss decomposition.

    Args:
        planned_minutes: Scheduled production time.
        downtime_minutes: Unplanned downtime.
        ideal_cycle_minutes: Ideal cycle time per unit (in minutes).
        produced: Total units produced (good + defective).
        defects: Defective units.
        loading_pct: Equipment loading % of calendar time (for TEEP).

    Returns:
        OEEResult with A×P×Q breakdown and losses.
    """
    if planned_minutes <= 0:
        return OEEResult()

    runtime = planned_minutes - downtime_minutes
    good = max(0, produced - defects)

    avail = runtime / planned_minutes if planned_minutes > 0 else 0
    perf = min(1.0, (produced * ideal_cycle_minutes) / runtime) if runtime > 0 else 0
    qual = good / produced if produced > 0 else 1.0

    oee_val = avail * perf * qual

    # Losses in minutes
    avail_loss = downtime_minutes
    perf_loss = runtime - (produced * ideal_cycle_minutes) if runtime > produced * ideal_cycle_minutes else 0
    qual_loss = defects * ideal_cycle_minutes

    teep = oee_val * (loading_pct / 100) if loading_pct is not None else None

    return OEEResult(
        oee=oee_val,
        availability=avail,
        performance=perf,
        quality=qual,
        runtime=runtime,
        good_units=good,
        availability_loss=avail_loss,
        performance_loss=perf_loss,
        quality_loss=qual_loss,
        teep=teep,
    )
