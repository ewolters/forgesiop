"""Changeover matrix optimization — sequence products to minimize total setup time."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ChangeoverResult:
    """Changeover matrix analysis result."""

    optimal_sequence: list[str] = field(default_factory=list)
    total_changeover: float = 0.0
    min_changeover: float = 0.0
    max_changeover: float = 0.0
    avg_changeover: float = 0.0


def changeover_matrix(
    products: list[str],
    times_matrix: dict[str, dict[str, float]],
) -> ChangeoverResult:
    """Optimize product sequence to minimize total changeover time.

    Uses greedy nearest-neighbor heuristic (same as SVEND calc-lean.js).

    Args:
        products: List of product names.
        times_matrix: {from_product: {to_product: changeover_minutes}}.

    Returns:
        ChangeoverResult with optimal sequence and total time.
    """
    if len(products) <= 1:
        return ChangeoverResult(optimal_sequence=products)

    # Greedy nearest-neighbor
    sequence = [products[0]]
    remaining = set(products[1:])

    while remaining:
        current = sequence[-1]
        best_next = None
        best_time = float("inf")

        for candidate in remaining:
            t = times_matrix.get(current, {}).get(candidate, float("inf"))
            if t < best_time:
                best_time = t
                best_next = candidate

        if best_next is not None:
            sequence.append(best_next)
            remaining.discard(best_next)
        else:
            # No path — append remaining in original order
            sequence.extend(sorted(remaining))
            break

    # Calculate total changeover for the sequence
    total = total_changeover_time(sequence, times_matrix)

    # Stats across all pairs in matrix
    all_times = []
    for from_p in products:
        for to_p in products:
            if from_p != to_p:
                t = times_matrix.get(from_p, {}).get(to_p, 0)
                if t > 0:
                    all_times.append(t)

    return ChangeoverResult(
        optimal_sequence=sequence,
        total_changeover=total,
        min_changeover=min(all_times) if all_times else 0,
        max_changeover=max(all_times) if all_times else 0,
        avg_changeover=sum(all_times) / len(all_times) if all_times else 0,
    )


def total_changeover_time(
    sequence: list[str],
    times_matrix: dict[str, dict[str, float]],
) -> float:
    """Sum changeover times for a given production sequence."""
    total = 0.0
    for i in range(len(sequence) - 1):
        total += times_matrix.get(sequence[i], {}).get(sequence[i + 1], 0)
    return total
