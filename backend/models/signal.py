"""
Signal model: persistence and API schemas.
"""
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field
from sqlalchemy import Column, String, Float, DateTime, Enum as SQLEnum, Text, JSON

from .database import Base


class SignalStatus(str, Enum):
    ACTIVE = "active"
    CLOSED = "closed"
    INVALIDATED = "invalidated"


class Signal(Base):
    """SQLAlchemy model for a trading signal."""

    __tablename__ = "signals"

    id = Column(String(36), primary_key=True, index=True)
    asset = Column(String(20), nullable=False, index=True)
    timeframe = Column(String(10), nullable=False, index=True)
    direction = Column(String(10), nullable=False)  # LONG | SHORT
    entry_price = Column(Float, nullable=False)
    stop_loss = Column(Float, nullable=False)
    take_profit_1 = Column(Float, nullable=False)
    take_profit_2 = Column(Float, nullable=True)
    take_profit_3 = Column(Float, nullable=True)
    position_size_pct = Column(Float, nullable=True)
    risk_reward = Column(Float, nullable=True)
    invalidation_conditions = Column(Text, nullable=True)
    confidence_score = Column(Float, nullable=False)
    explanation = Column(JSON, nullable=True)
    status = Column(SQLEnum(SignalStatus), default=SignalStatus.ACTIVE, index=True)
    exit_price = Column(Float, nullable=True)
    pnl_pct = Column(Float, nullable=True)
    closed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# --- Pydantic schemas for API ---


class SignalCreate(BaseModel):
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
    confidence_score: float = Field(ge=0, le=100)
    explanation: Optional[dict] = None


class SignalUpdate(BaseModel):
    status: Optional[SignalStatus] = None
    exit_price: Optional[float] = None
    pnl_pct: Optional[float] = None
    closed_at: Optional[datetime] = None


class SignalResponse(BaseModel):
    id: str
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
    status: str
    exit_price: Optional[float] = None
    pnl_pct: Optional[float] = None
    closed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
