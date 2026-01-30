"""
Pattern detection: trendlines, breakout/fakeout, double top/bottom, H&S, channels, range.
"""
from typing import List

import numpy as np
import pandas as pd

from .types import PatternResult, PatternType


class PatternDetector:
    """
    Detect chart patterns from OHLCV + indicators.
    """

    def __init__(self, lookback: int = 100):
        self.lookback = lookback

    def detect_all(self, df: pd.DataFrame) -> List[PatternResult]:
        """Run all pattern checks and return list of PatternResult."""
        if df.empty or len(df) < 30:
            return []
        results: List[PatternResult] = []
        recent = df.tail(self.lookback)

        # Trend
        results.extend(self._trendlines(recent))
        # Breakout / Fakeout
        results.extend(self._breakout_fakeout(recent))
        # Double top / bottom
        results.extend(self._double_top_bottom(recent))
        # Head & Shoulders (simplified)
        results.extend(self._head_shoulders(recent))
        # Channel
        results.extend(self._channel(recent))
        # Range
        results.extend(self._range(recent))

        return results

    def _trendlines(self, df: pd.DataFrame) -> List[PatternResult]:
        out = []
        closes = df["close"].values
        n = len(closes)
        if n < 20:
            return out
        # Linear regression slope on last 20 and last 50
        x = np.arange(20)
        slope_20 = np.polyfit(x, closes[-20:], 1)[0]
        slope_50 = np.polyfit(np.arange(min(50, n)), closes[-min(50, n):], 1)[0] if n >= 50 else slope_20
        avg_price = np.mean(closes[-20:])
        if slope_20 > 0 and slope_50 > 0:
            out.append(
                PatternResult(
                    pattern_type=PatternType.TRENDLINE_UP.value,
                    confidence=min(0.9, 0.5 + abs(slope_20) / (avg_price * 0.01)),
                    level_or_price=float(closes[-1]),
                    description="Uptrend: higher lows and higher highs",
                )
            )
        elif slope_20 < 0 and slope_50 < 0:
            out.append(
                PatternResult(
                    pattern_type=PatternType.TRENDLINE_DOWN.value,
                    confidence=min(0.9, 0.5 + abs(slope_20) / (avg_price * 0.01)),
                    level_or_price=float(closes[-1]),
                    description="Downtrend: lower highs and lower lows",
                )
            )
        return out

    def _breakout_fakeout(self, df: pd.DataFrame) -> List[PatternResult]:
        out = []
        high = df["high"].values
        low = df["low"].values
        close = df["close"].values
        n = len(close)
        if n < 30:
            return out
        # Resistance = max of last 20 bars (excluding last 3)
        res = np.max(high[-25:-3]) if n >= 25 else np.max(high[:-3])
        sup = np.min(low[-25:-3]) if n >= 25 else np.min(low[:-3])
        last_close = close[-1]
        prev_close = close[-2]
        # Breakout above resistance
        if last_close > res and prev_close <= res:
            out.append(
                PatternResult(
                    pattern_type=PatternType.BREAKOUT_UP.value,
                    confidence=0.75,
                    level_or_price=float(res),
                    description=f"Breakout above resistance {res:.2f}",
                )
            )
        # Breakout below support
        if last_close < sup and prev_close >= sup:
            out.append(
                PatternResult(
                    pattern_type=PatternType.BREAKOUT_DOWN.value,
                    confidence=0.75,
                    level_or_price=float(sup),
                    description=f"Breakout below support {sup:.2f}",
                )
            )
        return out

    def _double_top_bottom(self, df: pd.DataFrame) -> List[PatternResult]:
        out = []
        high = df["high"].values
        low = df["low"].values
        close = df["close"].values
        n = len(close)
        if n < 40:
            return out
        # Find two comparable peaks in second half
        half = high[-n // 2 :]
        peak_idx = np.argsort(half)[-2:]
        peak_idx = np.sort(peak_idx)
        p1, p2 = half[peak_idx[0]], half[peak_idx[1]]
        if abs(p1 - p2) / max(p1, p2) < 0.01 and close[-1] < (p1 + p2) / 2:
            out.append(
                PatternResult(
                    pattern_type=PatternType.DOUBLE_TOP.value,
                    confidence=0.7,
                    level_or_price=float((p1 + p2) / 2),
                    description="Double top formation",
                )
            )
        # Double bottom
        half_low = low[-n // 2 :]
        trough_idx = np.argsort(half_low)[:2]
        trough_idx = np.sort(trough_idx)
        t1, t2 = half_low[trough_idx[0]], half_low[trough_idx[1]]
        if abs(t1 - t2) / max(t1, t2) < 0.01 and close[-1] > (t1 + t2) / 2:
            out.append(
                PatternResult(
                    pattern_type=PatternType.DOUBLE_BOTTOM.value,
                    confidence=0.7,
                    level_or_price=float((t1 + t2) / 2),
                    description="Double bottom formation",
                )
            )
        return out

    def _head_shoulders(self, df: pd.DataFrame) -> List[PatternResult]:
        out = []
        high = df["high"].values
        low = df["low"].values
        n = len(high)
        if n < 50:
            return out
        # Simplified: find three peaks where middle is highest
        window = n // 3
        p1 = np.max(high[0:window])
        p2 = np.max(high[window : 2 * window])
        p3 = np.max(high[2 * window :])
        if p2 > p1 and p2 > p3 and abs(p1 - p3) / max(p1, p3) < 0.02:
            out.append(
                PatternResult(
                    pattern_type=PatternType.HEAD_SHOULDERS.value,
                    confidence=0.65,
                    level_or_price=float(p2),
                    description="Head and shoulders (bearish)",
                )
            )
        # Inverse H&S
        t1 = np.min(low[0:window])
        t2 = np.min(low[window : 2 * window])
        t3 = np.min(low[2 * window :])
        if t2 < t1 and t2 < t3 and abs(t1 - t3) / max(t1, t3) < 0.02:
            out.append(
                PatternResult(
                    pattern_type=PatternType.HEAD_SHOULDERS_INVERSE.value,
                    confidence=0.65,
                    level_or_price=float(t2),
                    description="Inverse head and shoulders (bullish)",
                )
            )
        return out

    def _channel(self, df: pd.DataFrame) -> List[PatternResult]:
        out = []
        high = df["high"].values
        low = df["low"].values
        n = len(high)
        if n < 30:
            return out
        x = np.arange(n)
        slope_high = np.polyfit(x, high, 1)[0]
        slope_low = np.polyfit(x, low, 1)[0]
        avg = np.mean(df["close"].values)
        if slope_high > 0 and slope_low > 0 and abs(slope_high - slope_low) / avg < 0.001:
            out.append(
                PatternResult(
                    pattern_type=PatternType.CHANNEL_UP.value,
                    confidence=0.6,
                    description="Ascending channel",
                )
            )
        elif slope_high < 0 and slope_low < 0:
            out.append(
                PatternResult(
                    pattern_type=PatternType.CHANNEL_DOWN.value,
                    confidence=0.6,
                    description="Descending channel",
                )
            )
        return out

    def _range(self, df: pd.DataFrame) -> List[PatternResult]:
        out = []
        high = df["high"].values
        low = df["low"].values
        n = len(high)
        if n < 20:
            return out
        range_20 = np.max(high[-20:]) - np.min(low[-20:])
        avg = np.mean(df["close"].values)
        # Range if volatility band is tight relative to price
        if range_20 / avg < 0.05:
            out.append(
                PatternResult(
                    pattern_type=PatternType.RANGE.value,
                    confidence=0.7,
                    level_or_price=float(avg),
                    description="Sideways range; low volatility",
                )
            )
        return out
