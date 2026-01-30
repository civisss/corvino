"""
Technical indicators computed on OHLCV DataFrame.
"""
from typing import Dict, Any

import pandas as pd
import numpy as np

# Use ta library for standard indicators
from ta.momentum import RSIIndicator
from ta.trend import MACD, EMAIndicator, SMAIndicator
from ta.volatility import AverageTrueRange


class IndicatorCalculator:
    """
    Compute RSI, MACD, EMA, SMA, ATR, and volume-based metrics.
    """

    def __init__(
        self,
        rsi_period: int = 14,
        macd_fast: int = 12,
        macd_slow: int = 26,
        macd_signal: int = 9,
        ema_periods: list[int] = [9, 21, 50],
        sma_periods: list[int] = [20, 50],
        atr_period: int = 14,
    ):
        self.rsi_period = rsi_period
        self.macd_fast = macd_fast
        self.macd_slow = macd_slow
        self.macd_signal = macd_signal
        self.ema_periods = ema_periods
        self.sma_periods = sma_periods
        self.atr_period = atr_period

    def compute_all(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add all indicator columns to df. Modifies in place and returns df."""
        if df.empty or len(df) < max(self.macd_slow, self.sma_periods[-1], self.atr_period):
            return df

        # RSI
        rsi = RSIIndicator(close=df["close"], window=self.rsi_period)
        df["rsi"] = rsi.rsi()

        # MACD
        macd = MACD(
            close=df["close"],
            window_slow=self.macd_slow,
            window_fast=self.macd_fast,
            window_sign=self.macd_signal,
        )
        df["macd"] = macd.macd()
        df["macd_signal"] = macd.macd_signal()
        df["macd_histogram"] = macd.macd_diff()

        # EMA
        for p in self.ema_periods:
            ema = EMAIndicator(close=df["close"], window=p)
            df[f"ema_{p}"] = ema.ema_indicator()

        # SMA
        for p in self.sma_periods:
            sma = SMAIndicator(close=df["close"], window=p)
            df[f"sma_{p}"] = sma.sma_indicator()

        # ATR
        atr = AverageTrueRange(
            high=df["high"], low=df["low"], close=df["close"], window=self.atr_period
        )
        df["atr"] = atr.average_true_range()

        # Volume: average and last
        df["volume_sma"] = df["volume"].rolling(window=20).mean()
        df["volume_ratio"] = df["volume"] / df["volume_sma"].replace(0, np.nan)

        return df

    def get_latest_metrics(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Return the latest values of all indicators as a dict."""
        if df.empty:
            return {}
        row = df.iloc[-1]
        out = {
            "rsi": float(row.get("rsi", 0)) if pd.notna(row.get("rsi")) else None,
            "macd": float(row.get("macd", 0)) if pd.notna(row.get("macd")) else None,
            "macd_signal": float(row.get("macd_signal", 0)) if pd.notna(row.get("macd_signal")) else None,
            "macd_histogram": float(row.get("macd_histogram", 0)) if pd.notna(row.get("macd_histogram")) else None,
            "atr": float(row.get("atr", 0)) if pd.notna(row.get("atr")) else None,
            "volume_ratio": float(row.get("volume_ratio", 0)) if pd.notna(row.get("volume_ratio")) else None,
        }
        for p in self.ema_periods:
            k = f"ema_{p}"
            out[k] = float(row[k]) if pd.notna(row.get(k)) else None
        for p in self.sma_periods:
            k = f"sma_{p}"
            out[k] = float(row[k]) if pd.notna(row.get(k)) else None
        out["close"] = float(row["close"])
        out["volume"] = float(row["volume"])
        return out
