"""Scenario engine — what-if analysis with distribution parameters.

Run a plan N times with perturbed inputs to understand sensitivity.
"""

from __future__ import annotations

import random
from dataclasses import dataclass


@dataclass
class ScenarioInput:
    """A single input parameter that can be varied."""

    name: str
    base_value: float
    low_value: float
    high_value: float
    distribution: str = "triangular"  # "triangular", "uniform", "normal"

    def sample(self) -> float:
        if self.distribution == "triangular":
            return random.triangular(self.low_value, self.high_value, self.base_value)
        elif self.distribution == "uniform":
            return random.uniform(self.low_value, self.high_value)
        elif self.distribution == "normal":
            std = (self.high_value - self.low_value) / 4  # 95% within range
            return random.gauss(self.base_value, std)
        return self.base_value


@dataclass
class ScenarioResult:
    """Result of a scenario analysis."""

    base_case: dict
    iterations: int
    output_distributions: dict[str, dict]  # {metric: {mean, std, p5, p50, p95}}
    sensitivity: list[dict]  # [{input, correlation, rank}] sorted by impact


def run_scenario(
    inputs: list[ScenarioInput],
    model_fn: callable,
    n_iterations: int = 1000,
) -> ScenarioResult:
    """Run scenario analysis.

    Args:
        inputs: list of variable inputs with distributions
        model_fn: function(input_dict) → output_dict
            Takes {input_name: value} → returns {metric_name: value}
        n_iterations: Monte Carlo iterations

    Returns:
        ScenarioResult with distributions and sensitivity ranking
    """
    # Base case
    base_inputs = {inp.name: inp.base_value for inp in inputs}
    base_output = model_fn(base_inputs)

    # Monte Carlo
    all_input_samples: dict[str, list[float]] = {inp.name: [] for inp in inputs}
    all_output_samples: dict[str, list[float]] = {k: [] for k in base_output}

    for _ in range(n_iterations):
        sampled = {}
        for inp in inputs:
            val = inp.sample()
            sampled[inp.name] = val
            all_input_samples[inp.name].append(val)

        output = model_fn(sampled)
        for k, v in output.items():
            all_output_samples[k].append(v)

    # Summarize outputs
    output_distributions = {}
    for metric, samples in all_output_samples.items():
        s = sorted(samples)
        n = len(s)
        mean = sum(s) / n
        variance = sum((x - mean) ** 2 for x in s) / max(n - 1, 1)
        import math
        std = math.sqrt(variance)

        output_distributions[metric] = {
            "mean": round(mean, 4),
            "std": round(std, 4),
            "p5": round(s[int(0.05 * n)], 4),
            "p50": round(s[int(0.50 * n)], 4),
            "p95": round(s[int(0.95 * n)], 4),
            "base": base_output[metric],
        }

    # Sensitivity — rank correlation between each input and primary output
    primary_output = list(base_output.keys())[0]
    sensitivity = []
    for inp_name, inp_samples in all_input_samples.items():
        corr = _rank_correlation(inp_samples, all_output_samples[primary_output])
        sensitivity.append({
            "input": inp_name,
            "correlation": round(corr, 4),
            "abs_correlation": round(abs(corr), 4),
        })

    sensitivity.sort(key=lambda s: s["abs_correlation"], reverse=True)
    for i, s in enumerate(sensitivity):
        s["rank"] = i + 1

    return ScenarioResult(
        base_case=base_output,
        iterations=n_iterations,
        output_distributions=output_distributions,
        sensitivity=sensitivity,
    )


def _rank_correlation(x: list[float], y: list[float]) -> float:
    """Spearman rank correlation coefficient."""
    n = len(x)
    if n < 3:
        return 0.0

    rx = _ranks(x)
    ry = _ranks(y)

    d_sq = sum((a - b) ** 2 for a, b in zip(rx, ry))
    return 1 - (6 * d_sq) / (n * (n**2 - 1))


def _ranks(data: list[float]) -> list[float]:
    """Compute ranks for a list of values."""
    indexed = sorted(enumerate(data), key=lambda x: x[1])
    ranks = [0.0] * len(data)
    for rank, (orig_idx, _) in enumerate(indexed):
        ranks[orig_idx] = rank + 1
    return ranks
