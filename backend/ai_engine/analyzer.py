"""
LLM-based analysis via Perplexity: combine indicators, patterns, market structure; output confidence + JSON explanation.
"""
import json
import re
from typing import Any, Dict, List, Optional

from openai import OpenAI

from config import get_settings
from .schemas import AIAnalysisResult, SignalExplanation


class AIAnalyzer:
    """
    Uses Perplexity API (OpenAI-compatible) for:
    - Market and chart reading, indicators, patterns, support/resistance
    - Evaluate context and produce confidence 0-100
    - Return structured JSON explanation
    """

    def __init__(self):
        self.settings = get_settings()
        self._client: Optional[OpenAI] = None

    @property
    def client(self) -> Optional[OpenAI]:
        if self._client is None and self.settings.perplexity_api_key:
            self._client = OpenAI(
                api_key=self.settings.perplexity_api_key,
                base_url="https://api.perplexity.ai/v2",
            )
        return self._client

    def analyze(
        self,
        asset: str,
        timeframe: str,
        indicators: Dict[str, Any],
        patterns: List[Dict[str, Any]],
        supports: List[float],
        resistances: List[float],
        news_sentiment: Optional[str] = None,
    ) -> AIAnalysisResult:
        """
        Run LLM analysis and return confidence + structured explanation.
        If no API key, returns a rule-based fallback.
        """
        if self.client:
            return self._llm_analyze(
                asset, timeframe, indicators, patterns, supports, resistances, news_sentiment
            )
        return self._fallback_analyze(
            asset, timeframe, indicators, patterns, supports, resistances
        )

    def _build_prompt(
        self,
        asset: str,
        timeframe: str,
        indicators: Dict[str, Any],
        patterns: List[Dict[str, Any]],
        supports: List[float],
        resistances: List[float],
        news_sentiment: Optional[str],
    ) -> str:
        return f"""You are a quantitative crypto trading analyst. Based ONLY on the following data, output a trading signal analysis.

Asset: {asset}
Timeframe: {timeframe}

Technical indicators (latest):
{json.dumps(indicators, indent=2)}

Detected chart patterns:
{json.dumps(patterns, indent=2)}

Support levels (nearest): {supports[:5]}
Resistance levels (nearest): {resistances[:5]}
{f'News/macro sentiment: {news_sentiment}' if news_sentiment else ''}

Instructions:
1. Decide direction: LONG or SHORT (or NEUTRAL if unclear).
2. Assign a confidence score between 0 and 100.
3. Provide a structured explanation with: summary, technical_reasoning (list), pattern_reasoning (list), risk_factors (list), invalidation_conditions (list).

Respond with a single JSON object, no markdown, with this exact structure:
{{
  "confidence_score": <number 0-100>,
  "direction": "LONG" or "SHORT" or "NEUTRAL",
  "explanation": {{
    "summary": "<one-line summary>",
    "technical_reasoning": ["...", "..."],
    "pattern_reasoning": ["...", "..."],
    "risk_factors": ["...", "..."],
    "invalidation_conditions": ["...", "..."]
  }}
}}
"""

    def _llm_analyze(
        self,
        asset: str,
        timeframe: str,
        indicators: Dict[str, Any],
        patterns: List[Dict[str, Any]],
        supports: List[float],
        resistances: List[float],
        news_sentiment: Optional[str] = None,
    ) -> AIAnalysisResult:
        prompt = self._build_prompt(
            asset, timeframe, indicators, patterns, supports, resistances, news_sentiment
        )
        try:
            resp = self.client.chat.completions.create(
                model=self.settings.llm_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=800,
            )
            if not resp.choices or not resp.choices[0].message.content:
                return self._fallback_analyze(
                    asset, timeframe, indicators, patterns, supports, resistances
                )
            text = resp.choices[0].message.content.strip()
            # Extract JSON (handle markdown code blocks)
            json_str = re.sub(r"^```\w*\n?", "", text).strip()
            json_str = re.sub(r"\n?```\s*$", "", json_str).strip()
            data = json.loads(json_str)
            direction = data.get("direction", "NEUTRAL")
            if direction == "NEUTRAL":
                direction = "LONG"  # default for signal generation
            expl = data.get("explanation") or {}
            if not isinstance(expl, dict):
                expl = {}
            expl.setdefault("summary", f"{direction} bias from technical analysis")
            expl.setdefault("technical_reasoning", [])
            expl.setdefault("pattern_reasoning", [])
            expl.setdefault("risk_factors", [])
            expl.setdefault("invalidation_conditions", [])
            return AIAnalysisResult(
                confidence_score=float(data.get("confidence_score", 50)),
                direction=direction,
                explanation=SignalExplanation(**expl),
                raw_notes=text,
            )
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            return self._fallback_analyze(
                asset, timeframe, indicators, patterns, supports, resistances
            )

    def _fallback_analyze(
        self,
        asset: str,
        timeframe: str,
        indicators: Dict[str, Any],
        patterns: List[Dict[str, Any]],
        supports: List[float],
        resistances: List[float],
    ) -> AIAnalysisResult:
        """Rule-based fallback when LLM is unavailable."""
        rsi = indicators.get("rsi")
        macd_hist = indicators.get("macd_histogram")
        close = indicators.get("close", 0)
        direction = "LONG"
        reasons = []
        risks = []
        invalidation = []

        if rsi is not None:
            if rsi < 30:
                direction = "LONG"
                reasons.append(f"RSI oversold ({rsi:.1f})")
            elif rsi > 70:
                direction = "SHORT"
                reasons.append(f"RSI overbought ({rsi:.1f})")
        if macd_hist is not None:
            if macd_hist > 0:
                reasons.append("MACD histogram positive")
            else:
                reasons.append("MACD histogram negative")
                if direction == "LONG":
                    direction = "SHORT"

        if not reasons:
            reasons.append("No strong technical edge; neutral context")

        if supports:
            invalidation.append(f"Break below support {supports[0]:.2f}")
        if resistances:
            invalidation.append(f"Break above resistance {resistances[0]:.2f}")
        risks.append("Rule-based fallback; no LLM analysis")

        confidence = 45.0
        if rsi is not None and (rsi < 35 or rsi > 65):
            confidence = 55.0
        if patterns:
            confidence = min(75, confidence + 10 * len(patterns))

        return AIAnalysisResult(
            confidence_score=confidence,
            direction=direction,
            explanation=SignalExplanation(
                summary=f"{direction} bias on {asset} ({timeframe})",
                technical_reasoning=reasons,
                pattern_reasoning=[p.get("description", p.get("pattern_type", "")) for p in patterns[:3]],
                risk_factors=risks,
                invalidation_conditions=invalidation,
            ),
        )
