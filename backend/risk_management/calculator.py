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
        order_blocks: list[dict] = None,
        fvg_zones: list[dict] = None,
    ) -> Tuple[float, float, float, float, float]:
        """
        Compute SL/TP based on S/R levels, Order Blocks, and FVG.
        - SL: placed at nearest OB/S/R level within 1.5 ATR max distance.
        - TP: placed at next R (Long) or S (Short) levels.
        - Target R:R >= 1.5 by adjusting TP if needed.
        """
        if atr <= 0:
            atr = entry * 0.02

        order_blocks = order_blocks or []
        fvg_zones = fvg_zones or []

        # Max SL distance = 1.5 ATR (tighter stops)
        max_sl_dist = 1.5 * atr
        min_dist = 0.3 * atr  # Min distance to avoid noise

        sl = 0.0
        tps = []

        if direction.upper() == "LONG":
            # Collect all potential SL levels: supports, bullish OBs, bullish FVGs
            sl_candidates = []
            
            # Supports below entry
            sl_candidates.extend([s for s in supports if s < entry])
            
            # Bullish Order Blocks (use ob_low as demand zone)
            for ob in order_blocks:
                if ob.get("type") == "bullish" and ob.get("low", 0) < entry:
                    sl_candidates.append(ob["low"])
            
            # Bullish FVGs (use fvg_low as support)
            for fvg in fvg_zones:
                if fvg.get("type") == "bullish" and fvg.get("low", 0) < entry:
                    sl_candidates.append(fvg["low"])
            
            # Sort descending (nearest first) and filter by distance
            sl_candidates = sorted([s for s in sl_candidates if min_dist <= (entry - s) <= max_sl_dist], reverse=True)
            
            if sl_candidates:
                sl = sl_candidates[0] - (0.1 * atr)  # Small buffer
            else:
                # Fallback: max allowed distance
                sl = entry - max_sl_dist

            # TP: Find resistances ABOVE entry
            valid_resistances = sorted([r for r in resistances if r > entry])
            
            for r in valid_resistances:
                if (r - entry) >= min_dist:
                    tps.append(r)
                if len(tps) >= 3:
                    break
            
            # Fill missing TPs with ATR logic
            while len(tps) < 3:
                last_tp = tps[-1] if tps else entry
                tps.append(last_tp + (1.0 * atr))

        else:  # SHORT
            # Collect all potential SL levels: resistances, bearish OBs, bearish FVGs
            sl_candidates = []
            
            # Resistances above entry
            sl_candidates.extend([r for r in resistances if r > entry])
            
            # Bearish Order Blocks (use ob_high as supply zone)
            for ob in order_blocks:
                if ob.get("type") == "bearish" and ob.get("high", 0) > entry:
                    sl_candidates.append(ob["high"])
            
            # Bearish FVGs (use fvg_high as resistance)
            for fvg in fvg_zones:
                if fvg.get("type") == "bearish" and fvg.get("high", 0) > entry:
                    sl_candidates.append(fvg["high"])
            
            # Sort ascending (nearest first) and filter by distance
            sl_candidates = sorted([r for r in sl_candidates if min_dist <= (r - entry) <= max_sl_dist])
            
            if sl_candidates:
                sl = sl_candidates[0] + (0.1 * atr)  # Small buffer
            else:
                # Fallback: max allowed distance
                sl = entry + max_sl_dist

            # TP: Find supports BELOW entry
            valid_supports = sorted([s for s in supports if s < entry], reverse=True)
            
            for s in valid_supports:
                if (entry - s) >= min_dist:
                    tps.append(s)
                if len(tps) >= 3:
                    break
            
            while len(tps) < 3:
                last_tp = tps[-1] if tps else entry
                tps.append(last_tp - (1.0 * atr))

        # Risk/Reward Calc
        risk = abs(entry - sl)
        tp1, tp2, tp3 = tps[0], tps[1], tps[2]
        
        # Adjust TP1 to ensure min R:R of 1.5 on first target
        min_reward = 1.5 * risk
        if abs(entry - tp1) < min_reward:
            if direction.upper() == "LONG":
                tp1 = entry + min_reward
            else:
                tp1 = entry - min_reward
        
        reward_avg = (abs(entry - tp1) + abs(entry - tp2) + abs(entry - tp3)) / 3
        risk_reward = reward_avg / risk if risk > 0 else 0.0

        return sl, tp1, tp2, tp3, risk_reward

