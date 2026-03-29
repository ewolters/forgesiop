"""Yield modeling from process capability — THE DIFFERENTIATOR.

Nobody else does this. Takes Cpk/Ppk from SPC data and computes
yield distribution, not a point estimate. Feeds into production
planning as probabilistic yield instead of fixed assumption.
"""

from __future__ import annotations

import math


def yield_from_cpk(cpk: float) -> float:
    """Compute expected yield (fraction conforming) from Cpk.

    Uses the relationship: P(defect) = 2 * Phi(-3 * Cpk)
    where Phi is the standard normal CDF.

    Args:
        cpk: Process capability index

    Returns:
        Yield as fraction (0-1). E.g., 0.9973 for Cpk=1.0
    """
    if cpk <= 0:
        return 0.5  # centered on spec limit

    try:
        from scipy.stats import norm

        defect_rate = 2 * norm.cdf(-3 * cpk)
    except ImportError:
        # Approximate with error function
        defect_rate = 2 * _normal_cdf(-3 * cpk)

    return 1.0 - defect_rate


def yield_distribution(
    cpk: float,
    cpk_std: float = 0.0,
    n_samples: int = 1000,
) -> dict:
    """Compute yield distribution from uncertain Cpk.

    If Cpk itself has uncertainty (e.g., from small sample size),
    propagate that uncertainty through the yield calculation.

    Returns:
        {mean, std, p5, p25, p50, p75, p95, samples}
    """
    import random

    if cpk_std <= 0:
        # No uncertainty — deterministic
        y = yield_from_cpk(cpk)
        return {
            "mean": y,
            "std": 0.0,
            "p5": y,
            "p25": y,
            "p50": y,
            "p75": y,
            "p95": y,
            "samples": [y],
        }

    # Monte Carlo: sample Cpk from its distribution, compute yield each time
    samples = []
    for _ in range(n_samples):
        cpk_sample = random.gauss(cpk, cpk_std)
        y = yield_from_cpk(max(0, cpk_sample))
        samples.append(y)

    samples.sort()
    n = len(samples)

    return {
        "mean": sum(samples) / n,
        "std": _std(samples),
        "p5": samples[int(0.05 * n)],
        "p25": samples[int(0.25 * n)],
        "p50": samples[int(0.50 * n)],
        "p75": samples[int(0.75 * n)],
        "p95": samples[int(0.95 * n)],
        "samples": samples,
    }


def required_input_quantity(
    desired_output: float,
    cpk: float,
    confidence: float = 0.95,
) -> float:
    """How many units to start to get desired_output good units.

    Accounts for yield loss from process capability.

    Args:
        desired_output: How many conforming units you need
        cpk: Process capability index
        confidence: Confidence level for the estimate

    Returns:
        Required input quantity
    """
    y = yield_from_cpk(cpk)
    if y <= 0:
        return float("inf")

    # For point estimate, just divide
    base = desired_output / y

    # Add safety margin based on confidence
    if confidence > 0.5:
        # Approximate: higher confidence = more input
        z = 1.645 if confidence >= 0.95 else 1.282 if confidence >= 0.90 else 0.842
        margin = z * math.sqrt(desired_output * (1 - y) / y)
        return base + margin

    return base


def _normal_cdf(x: float) -> float:
    """Approximate standard normal CDF without scipy."""
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def _std(values: list[float]) -> float:
    """Standard deviation."""
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    variance = sum((v - mean) ** 2 for v in values) / (len(values) - 1)
    return math.sqrt(variance)
