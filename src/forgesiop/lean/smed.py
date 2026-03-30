"""SMED (Single Minute Exchange of Die) — changeover analysis and reduction."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SMEDElement:
    """One element in a changeover analysis."""

    name: str
    time_minutes: float
    element_type: str  # "internal" or "external"
    convertible: bool = False  # can this internal be made external?


@dataclass
class SMEDResult:
    """SMED analysis result."""

    total_time: float = 0.0
    internal_time: float = 0.0
    external_time: float = 0.0
    target_time: float = 0.0  # internal only (goal state)
    reduction_pct: float = 0.0
    elements: list[SMEDElement] = field(default_factory=list)
    n_internal: int = 0
    n_external: int = 0
    n_convertible: int = 0


def classify_elements(elements: list[dict]) -> SMEDResult:
    """Classify changeover elements as internal/external.

    Args:
        elements: [{name, time_minutes, type: "internal"|"external", convertible: bool}]

    Returns:
        SMEDResult with time breakdown and reduction potential.
    """
    classified = []
    internal = 0.0
    external = 0.0
    n_int = 0
    n_ext = 0
    n_conv = 0

    for e in elements:
        etype = e.get("type", "internal")
        conv = e.get("convertible", False)
        t = e["time_minutes"]

        if etype == "internal":
            internal += t
            n_int += 1
        else:
            external += t
            n_ext += 1

        if conv:
            n_conv += 1

        classified.append(SMEDElement(
            name=e["name"],
            time_minutes=t,
            element_type=etype,
            convertible=conv,
        ))

    total = internal + external
    target = internal  # goal: only internal remains (external done while running)
    reduction = ((total - target) / total * 100) if total > 0 else 0

    return SMEDResult(
        total_time=total,
        internal_time=internal,
        external_time=external,
        target_time=target,
        reduction_pct=reduction,
        elements=classified,
        n_internal=n_int,
        n_external=n_ext,
        n_convertible=n_conv,
    )


def smed_reduction(
    current_elements: list[dict],
    proposed_elements: list[dict],
) -> dict:
    """Compare current vs proposed changeover times.

    Args:
        current_elements: Current state [{name, time_minutes, type}].
        proposed_elements: Proposed state after SMED improvements.

    Returns:
        Dict with time savings, percentage reduction, annual impact estimate.
    """
    current = classify_elements(current_elements)
    proposed = classify_elements(proposed_elements)

    time_saved = current.total_time - proposed.total_time
    pct_reduction = (time_saved / current.total_time * 100) if current.total_time > 0 else 0

    return {
        "current_total": current.total_time,
        "proposed_total": proposed.total_time,
        "time_saved_minutes": time_saved,
        "pct_reduction": pct_reduction,
        "current_internal": current.internal_time,
        "proposed_internal": proposed.internal_time,
    }
