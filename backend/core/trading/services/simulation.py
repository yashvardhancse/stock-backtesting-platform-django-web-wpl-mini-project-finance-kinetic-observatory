from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class MonteCarloResult:
    final_values: list[float]
    mean: float
    variance: float
    median: float
    minimum: float
    maximum: float
    histogram: dict[str, list[float]]


def run_monte_carlo_simulation(
    returns: pd.Series,
    *,
    initial_capital: float = 100000.0,
    simulations: int = 150,
    bins: int = 12,
    seed: int | None = 42,
) -> dict:
    """Bootstrap daily returns to produce a terminal portfolio distribution."""

    clean_returns = pd.Series(returns).replace([np.inf, -np.inf], np.nan).dropna().to_numpy()
    if clean_returns.size == 0:
        empty_histogram = {"bins": [], "counts": []}
        return MonteCarloResult([], 0.0, 0.0, 0.0, 0.0, 0.0, empty_histogram).__dict__

    rng = np.random.default_rng(seed)
    final_values: list[float] = []

    for _ in range(simulations):
        sampled_returns = rng.choice(clean_returns, size=clean_returns.size, replace=True)
        equity_path = initial_capital * np.cumprod(1 + sampled_returns)
        final_values.append(float(equity_path[-1]))

    histogram_counts, histogram_edges = np.histogram(final_values, bins=bins)
    histogram = {
        "bins": [float(edge) for edge in histogram_edges.tolist()],
        "counts": [int(count) for count in histogram_counts.tolist()],
    }

    result = MonteCarloResult(
        final_values=[float(value) for value in final_values],
        mean=float(np.mean(final_values)),
        variance=float(np.var(final_values)),
        median=float(np.median(final_values)),
        minimum=float(np.min(final_values)),
        maximum=float(np.max(final_values)),
        histogram=histogram,
    )
    return result.__dict__
