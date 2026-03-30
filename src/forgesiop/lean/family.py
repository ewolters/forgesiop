"""Product Family Analysis (PFA) and Workload Family Analysis (WFA).

Groups products by routing similarity (PFA) or workload pattern (WFA).
From the Protzman/TIPS methodology.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ProcessStep:
    """One step in a process flow analysis."""

    name: str
    category: str  # P=Process, T=Transport, I=Inspect, S-B/S-L/S-W=Storage
    time_minutes: float = 0.0
    distance_meters: float = 0.0


@dataclass
class PFAResult:
    """Process Flow Analysis result."""

    total_time: float = 0.0
    total_distance: float = 0.0
    process_time: float = 0.0  # value-add (P only)
    transport_time: float = 0.0
    inspect_time: float = 0.0
    storage_time: float = 0.0
    process_ratio: float = 0.0  # value-add / total (%)
    n_steps: int = 0
    category_counts: dict[str, int] = field(default_factory=dict)


@dataclass
class FamilyGroup:
    """A product family group."""

    name: str
    products: list[str] = field(default_factory=list)
    common_steps: list[str] = field(default_factory=list)
    similarity: float = 0.0  # 0-1


def process_flow_analysis(steps: list[dict]) -> PFAResult:
    """Analyze process flow — categorize steps and compute value ratio.

    Args:
        steps: [{name, category, time_minutes, distance_meters}]
            Categories: P (process/VA), T (transport), I (inspect),
            S-B (storage-buffer), S-L (storage-lot), S-W (storage-wait)

    Returns:
        PFAResult with time breakdown and process ratio.
    """
    totals = {"P": 0.0, "T": 0.0, "I": 0.0, "S-B": 0.0, "S-L": 0.0, "S-W": 0.0}
    counts = {"P": 0, "T": 0, "I": 0, "S-B": 0, "S-L": 0, "S-W": 0}
    total_time = 0.0
    total_dist = 0.0

    for step in steps:
        cat = step.get("category", "P")
        t = step.get("time_minutes", 0)
        d = step.get("distance_meters", 0)

        totals[cat] = totals.get(cat, 0) + t
        counts[cat] = counts.get(cat, 0) + 1
        total_time += t
        total_dist += d

    process_time = totals.get("P", 0)
    transport_time = totals.get("T", 0)
    inspect_time = totals.get("I", 0)
    storage_time = sum(totals.get(k, 0) for k in ("S-B", "S-L", "S-W"))

    ratio = (process_time / total_time * 100) if total_time > 0 else 0

    return PFAResult(
        total_time=total_time,
        total_distance=total_dist,
        process_time=process_time,
        transport_time=transport_time,
        inspect_time=inspect_time,
        storage_time=storage_time,
        process_ratio=ratio,
        n_steps=len(steps),
        category_counts=counts,
    )


def product_family_analysis(
    products: dict[str, list[str]],
) -> list[FamilyGroup]:
    """Group products by routing similarity.

    Args:
        products: {product_name: [step1, step2, ...]} — sequence of process step names.

    Returns:
        List of FamilyGroup — products with similar routings grouped together.
    """
    names = list(products.keys())
    n = len(names)
    if n <= 1:
        return [FamilyGroup(name="Family 1", products=names, similarity=1.0)]

    # Jaccard similarity between each pair
    def _jaccard(a: list, b: list) -> float:
        sa, sb = set(a), set(b)
        inter = len(sa & sb)
        union = len(sa | sb)
        return inter / union if union > 0 else 0

    # Simple agglomerative: merge most similar pairs
    groups = {name: [name] for name in names}
    routings = {name: products[name] for name in names}

    while len(groups) > 1:
        best_sim = 0
        best_pair = None
        group_names = list(groups.keys())

        for i in range(len(group_names)):
            for j in range(i + 1, len(group_names)):
                gi, gj = group_names[i], group_names[j]
                sim = _jaccard(routings[gi], routings[gj])
                if sim > best_sim:
                    best_sim = sim
                    best_pair = (gi, gj)

        if best_sim < 0.3 or best_pair is None:
            break

        # Merge
        gi, gj = best_pair
        merged_name = f"{gi}+{gj}"
        groups[merged_name] = groups.pop(gi) + groups.pop(gj)
        # Combined routing = union
        routings[merged_name] = list(set(routings.pop(gi)) | set(routings.pop(gj)))

    result = []
    for i, (gname, members) in enumerate(groups.items()):
        common = set(products[members[0]]) if members else set()
        for m in members[1:]:
            common &= set(products[m])

        result.append(FamilyGroup(
            name=f"Family {i + 1}",
            products=members,
            common_steps=sorted(common),
            similarity=1.0 if len(members) == 1 else best_sim,
        ))

    return result
