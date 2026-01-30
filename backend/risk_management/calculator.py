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

    def compute_dynamic_levels(
        self,
        entry: float,
        atr: float,
        direction: str,
        supports: list[float],
        resistances: list[float],
    ) -> Tuple[float, float, float, float, float]:
        """
        Compute SL/TP based on S/R levels.
        - SL: placed beyond nearest Support (Long) or Resistance (Short).
        - TP: placed at next Resistance (Long) or Support (Short) levels.
        - Fallback: ATR-based if no relevant S/R found.
        """
        if atr <= 0:
            atr = entry * 0.02

        # Min distance to avoid noise (0.5 ATR)
        min_dist = 0.5 * atr

        sl = 0.0
        tps = []

        if direction.upper() == "LONG":
            # SL: Find highest support BELOW entry (minus buffer)
            # supports are typically sorted? Let's assume passed list can be any order.
            # Filter supports < entry
            valid_supports = sorted([s for s in supports if s < entry], reverse=True) # Descending (nearest first)
            
            # Find first support at least min_dist away
            chosen_support = None
            for s in valid_supports:
                if (entry - s) >= min_dist:
                    chosen_support = s
                    break
            
            if chosen_support:
                sl = chosen_support - (0.2 * atr) # Small buffer below support
            else:
                sl = entry - (self.atr_mult_sl * atr) # Fallback

            # TP: Find resistances ABOVE entry
            valid_resistances = sorted([r for r in resistances if r > entry]) # Ascending (nearest first)
            
            for r in valid_resistances:
                if (r - entry) >= min_dist:
                    tps.append(r)
                if len(tps) >= 3:
                    break
            
            # Fill missing TPs with ATR logic relative to Entry
            while len(tps) < 3:
                last_tp = tps[-1] if tps else entry
                # Add 1.5 ATR spacing for subsequent TPs if S/R exhausted
                tps.append(last_tp + (1.5 * atr))

        else: # SHORT
            # SL: Find lowest resistance ABOVE entry (plus buffer)
            valid_resistances = sorted([r for r in resistances if r > entry]) # Ascending (nearest first)
            
            chosen_resistance = None
            for r in valid_resistances:
                if (r - entry) >= min_dist:
                    chosen_resistance = r
                    break
            
            if chosen_resistance:
                sl = chosen_resistance + (0.2 * atr) # Small buffer above resistance
            else:
                sl = entry + (self.atr_mult_sl * atr) # Fallback

            # TP: Find supports BELOW entry
            valid_supports = sorted([s for s in supports if s < entry], reverse=True) # Descending (nearest first)
            
            for s in valid_supports:
                if (entry - s) >= min_dist:
                    tps.append(s)
                if len(tps) >= 3:
                    break
            
            while len(tps) < 3:
                last_tp = tps[-1] if tps else entry
                tps.append(last_tp - (1.5 * atr))

        # Risk/Reward Calc
        risk = abs(entry - sl)
        # Average reward
        tp1, tp2, tp3 = tps[0], tps[1], tps[2]
        reward_avg = (abs(entry - tp1) + abs(entry - tp2) + abs(entry - tp3)) / 3
        risk_reward = reward_avg / risk if risk > 0 else 0.0

        return sl, tp1, tp2, tp3, risk_reward
