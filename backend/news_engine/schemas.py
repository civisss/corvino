"""
News engine schemas.
"""
from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel


class SentimentLabel(str, Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"


class NewsItem(BaseModel):
    title: str
    url: Optional[str] = None
    source: Optional[str] = None
    published_at: Optional[datetime] = None
    summary: Optional[str] = None
    raw_text: Optional[str] = None


class NewsSentiment(BaseModel):
    sentiment: SentimentLabel
    impact_score: float  # 0-1
    summary: str
    regime_change_detected: bool = False
    raw_response: Optional[dict] = None
