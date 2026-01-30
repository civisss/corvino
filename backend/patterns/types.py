"""
Types for pattern detection.
"""
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel


class PatternType(str, Enum):
    TRENDLINE_UP = "trendline_up"
    TRENDLINE_DOWN = "trendline_down"
    BREAKOUT_UP = "breakout_up"
    BREAKOUT_DOWN = "breakout_down"
    FAKEOUT_UP = "fakeout_up"
    FAKEOUT_DOWN = "fakeout_down"
    DOUBLE_TOP = "double_top"
    DOUBLE_BOTTOM = "double_bottom"
    HEAD_SHOULDERS = "head_shoulders"
    HEAD_SHOULDERS_INVERSE = "head_shoulders_inverse"
    CHANNEL_UP = "channel_up"
    CHANNEL_DOWN = "channel_down"
    RANGE = "range"


class PatternResult(BaseModel):
    pattern_type: str
    confidence: float  # 0-1
    level_or_price: Optional[float] = None
    description: Optional[str] = None
    metadata: Optional[dict] = None
