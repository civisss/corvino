"""
Feature extraction for ML: indicators + pattern flags from OHLCV DataFrame.
"""
from typing import List, Optional

import numpy as np
import pandas as pd


# Pattern types that suggest LONG vs SHORT (simplified)
BULLISH_PATTERNS = {
    "trendline_up", "breakout_up", "double_bottom",
    "head_shoulders_inverse", "channel_up", "range",
}
BEARISH_PATTERNS = {
    "trendline_down", "breakout_down", "double_top",
    "head_shoulders", "channel_down",
}


class FeatureBuilder:
    """
    Build numeric feature vector from OHLCV + indicators DataFrame and optional pattern list.
    Used for training and inference.
    """

    # Columns we need from df (after indicators are computed)
    INDICATOR_COLS = [
        "rsi", "macd", "macd_signal", "macd_histogram",
        "ema_9", "ema_21", "ema_50", "sma_20", "sma_50",
        "atr", "volume_ratio", "close", "volume",
    ]

    def __init__(self, normalize: bool = True):
        self.normalize = normalize
        self._feature_mean: Optional[np.ndarray] = None
        self._feature_std: Optional[np.ndarray] = None

    def build_from_df(
        self,
        df: pd.DataFrame,
        pattern_types: Optional[List[str]] = None,
    ) -> np.ndarray:
        """
        Build one feature vector from the last row of df + pattern counts.
        Returns 1D array of shape (n_features,). Missing cols filled with 0.
        """
        if df.empty or len(df) < 2:
            return np.zeros(self._n_features_static())

        row = df.iloc[-1]
        feats = []

        for col in self.INDICATOR_COLS:
            if col in df.columns and pd.notna(row.get(col)):
                val = float(row[col])
                if col in ("volume_ratio", "rsi") and self.normalize:
                    if col == "rsi":
                        val = (val - 50) / 50  # roughly [-1, 1]
                    elif col == "volume_ratio":
                        val = min(3.0, max(0, val)) / 3.0  # cap and scale
                feats.append(val)
            else:
                feats.append(0.0)

        # Returns (log) for last 1, 3, 5 bars
        close = row.get("close") or 0
        if close and close > 0:
            for k in [1, 3, 5]:
                if len(df) > k:
                    prev = df["close"].iloc[-1 - k]
                    if prev and prev > 0:
                        feats.append(np.log(close / prev))
                    else:
                        feats.append(0.0)
                else:
                    feats.append(0.0)
        else:
            feats.extend([0.0, 0.0, 0.0])

        # Pattern counts: bullish vs bearish
        if pattern_types is not None:
            bull = sum(1 for p in pattern_types if p in BULLISH_PATTERNS)
            bear = sum(1 for p in pattern_types if p in BEARISH_PATTERNS)
        else:
            bull, bear = 0, 0
        feats.append(float(bull))
        feats.append(float(bear))

        return np.array(feats, dtype=np.float64)

    def _n_features_static(self) -> int:
        return len(self.INDICATOR_COLS) + 3 + 2  # indicators + returns(3) + pattern_counts(2)

    def n_features(self) -> int:
        return self._n_features_static()

    def build_matrix(
        self,
        df: pd.DataFrame,
        pattern_results_per_row: Optional[List[List[str]]] = None,
    ) -> np.ndarray:
        """
        Build feature matrix for all rows (for training). Each row = one sample.
        pattern_results_per_row[i] = list of pattern_type strings for row i (if available).
        """
        n = len(df)
        if n < 2:
            return np.zeros((0, self._n_features_static()))

        rows = []
        for i in range(1, n):
            sub = df.iloc[: i + 1]
            patterns = pattern_results_per_row[i] if pattern_results_per_row and i < len(pattern_results_per_row) else None
            f = self.build_from_df(sub, pattern_types=patterns)
            rows.append(f)
        return np.array(rows)

    def set_normalization_params(self, mean: np.ndarray, std: np.ndarray):
        self._feature_mean = mean
        self._feature_std = std

    def get_normalization_params(self):
        return self._feature_mean, self._feature_std
