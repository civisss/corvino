"""
OHLCV data model for in-memory / normalized bars.
"""
from pydantic import BaseModel
from datetime import datetime


class OHLCVRow(BaseModel):
    """Single OHLCV bar, normalized for analysis."""

    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float

    class Config:
        from_attributes = True
