"""
Support and resistance levels from recent price action.
"""
from typing import List, Tuple

import numpy as np
import pandas as pd


def compute_support_resistance(
    df: pd.DataFrame,
    lookback: int = 100,
    num_levels: int = 5,
    proximity_pct: float = 0.002,
) -> Tuple[List[float], List[float]]:
    """
    Compute support and resistance levels using local minima/maxima
    and cluster nearby levels within proximity_pct.
    """
    if df.empty or len(df) < lookback:
        return [], []

    recent = df.tail(lookback)
    high = recent["high"].values
    low = recent["low"].values
    close = recent["close"].iloc[-1]

    # Local maxima (resistance): peak if higher than neighbors
    window = max(3, lookback // 20)
    resistances = []
    for i in range(window, len(high) - window):
        if high[i] == np.max(high[i - window : i + window + 1]):
            resistances.append(high[i])

    # Local minima (support)
    supports = []
    for i in range(window, len(low) - window):
        if low[i] == np.min(low[i - window : i + window + 1]):
            supports.append(low[i])

    def cluster_levels(levels: List[float], ref: float) -> List[float]:
        if not levels:
            return []
        levels = sorted(set(levels))
        clustered = []
        for lvl in levels:
            if lvl <= 0:
                continue
            found = False
            for c in clustered:
                if abs(lvl - c) / c <= proximity_pct:
                    found = True
                    break
            if not found:
                clustered.append(lvl)
        # Sort by distance from current price, take top num_levels
        clustered.sort(key=lambda x: abs(x - ref))
        return clustered[:num_levels]

    supports = cluster_levels(supports, close)
    resistances = cluster_levels(resistances, close)
    return supports, resistances
