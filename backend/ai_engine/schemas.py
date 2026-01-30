"""
Pydantic schemas for AI analysis output.
"""
from typing import Optional, List
from pydantic import BaseModel, Field


class SignalExplanation(BaseModel):
    """Structured explanation of the signal for API/frontend."""

    summary: str = Field(description="One-line summary of the signal")
    technical_reasoning: List[str] = Field(default_factory=list)
    pattern_reasoning: List[str] = Field(default_factory=list)
    risk_factors: List[str] = Field(default_factory=list)
    invalidation_conditions: List[str] = Field(default_factory=list)


class AIAnalysisResult(BaseModel):
    """Full AI analysis result: confidence + explanation."""

    confidence_score: float = Field(ge=0, le=100)
    direction: str = Field(description="LONG or SHORT")
    explanation: SignalExplanation
    raw_notes: Optional[str] = None
