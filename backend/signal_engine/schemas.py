"""
Internal signal representation before persistence.
"""
from typing import Optional, List
from pydantic import BaseModel


class RawSignal(BaseModel):
    """Full signal payload ready for DB/API."""

    asset: str
    timeframe: str
    direction: str
    entry_price: float
    stop_loss: float
    take_profit_1: float
    take_profit_2: Optional[float] = None
    take_profit_3: Optional[float] = None
    position_size_pct: Optional[float] = None
    risk_reward: Optional[float] = None
    invalidation_conditions: Optional[str] = None
    confidence_score: float
    explanation: Optional[dict] = None
