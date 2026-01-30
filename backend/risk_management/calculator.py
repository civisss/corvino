"""
Position sizing, dynamic stop-loss and take-profit levels based on ATR/volatility.
"""
from typing import Tuple

import numpy as np


class RiskCalculator:
    """
    Compute:
    - Dynamic SL/TP (ATR-based)
    - TP1, TP2, TP3
    - Position size % (optional, based on risk per trade)
    - Risk/Reward ratio
    """

    def __init__(
        self,
        atr_mult_sl: float = 2.0,
        atr_mult_tp1: float = 1.5,
        atr_mult_tp2: float = 2.5,
        atr_mult_tp3: float = 4.0,
        max_risk_pct_per_trade: float = 2.0,
    ):
        self.atr_mult_sl = atr_mult_sl
        self.atr_mult_tp1 = atr_mult_tp1
        self.atr_mult_tp2 = atr_mult_tp2
        self.atr_mult_tp3 = atr_mult_tp3
        self.max_risk_pct_per_trade = max_risk_pct_per_trade

    def compute_levels(
        self,
        entry: float,
        atr: float,
        direction: str,  # LONG | SHORT
    ) -> Tuple[float, float, float, float, float]:
        """
        Returns (stop_loss, tp1, tp2, tp3, risk_reward).
        """
        if atr <= 0:
            atr = entry * 0.02  # fallback 2% of price
        sl_dist = self.atr_mult_sl * atr
        tp1_dist = self.atr_mult_tp1 * atr
        tp2_dist = self.atr_mult_tp2 * atr
        tp3_dist = self.atr_mult_tp3 * atr

        if direction.upper() == "LONG":
            stop_loss = entry - sl_dist
            tp1 = entry + tp1_dist
            tp2 = entry + tp2_dist
            tp3 = entry + tp3_dist
        else:
            stop_loss = entry + sl_dist
            tp1 = entry - tp1_dist
            tp2 = entry - tp2_dist
            tp3 = entry - tp3_dist

        risk = abs(entry - stop_loss)
        reward_avg = (tp1_dist + tp2_dist + tp3_dist) / 3
        risk_reward = reward_avg / risk if risk > 0 else 0.0

        return stop_loss, tp1, tp2, tp3, risk_reward

    def position_size_pct(
        self,
        entry: float,
        stop_loss: float,
        risk_pct: float,
    ) -> float:
        """
        Suggested position size as % of portfolio so that loss from SL = risk_pct.
        Assumes 1:1 notional; for leverage adjust externally.
        """
        risk_pct = min(risk_pct, self.max_risk_pct_per_trade)
        risk_per_unit = abs(entry - stop_loss)
        if risk_per_unit <= 0:
            return 0.0
        # size such that (size * risk_per_unit / entry) = risk_pct/100
        size_pct = (risk_pct / 100.0) * entry / risk_per_unit
        return min(100.0, max(0.5, round(size_pct, 1)))
