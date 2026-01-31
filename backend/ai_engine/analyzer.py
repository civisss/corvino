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
        risk_scenarios: Optional[Dict[str, Any]] = None,
    ) -> AIAnalysisResult:
        """
        Run LLM analysis and return confidence + structured explanation.
        If no API key, returns a rule-based fallback.
        """
        if self.client:
            return self._llm_analyze(
                asset, timeframe, indicators, patterns, supports, resistances, news_sentiment, risk_scenarios
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
        risk_scenarios: Optional[Dict[str, Any]] = None,
    ) -> str:
        scenarios_text = ""
        if risk_scenarios:
            long_s = risk_scenarios.get("LONG", {})
            short_s = risk_scenarios.get("SHORT", {})
            scenarios_text = f"""
Proposed Risk Setups (based on Support/Resistance/Order Blocks/FVG):
LONG:  SL {long_s.get('sl', 0):.2f} | TPs {[round(t, 2) for t in long_s.get('tps', [])]} | R:R {long_s.get('rr', 0):.2f}
SHORT: SL {short_s.get('sl', 0):.2f} | TPs {[round(t, 2) for t in short_s.get('tps', [])]} | R:R {short_s.get('rr', 0):.2f}
"""
        
        # BTC correlation warning for altcoins
        btc_check = ""
        if asset and "BTC" not in asset.upper():
            btc_check = """
6. BTC CORRELATION (CRITICAL for altcoins):
   - Before recommending LONG, ensure BTC is not showing bearish signals.
   - Before recommending SHORT, ensure BTC is not showing strong bullish momentum.
   - If BTC trend contradicts your signal, lower confidence significantly or output NEUTRAL.
"""

        return f"""You are a quantitative crypto trading analyst specializing in ICT (Inner Circle Trader) concepts. 
Based ONLY on the following data, output a trading signal analysis.

Asset: {asset}
Timeframe: {timeframe}

Technical indicators (latest):
{json.dumps(indicators, indent=2)}

Detected chart patterns (including Order Blocks and FVG):
{json.dumps(patterns, indent=2)}

Support levels (nearest): {supports[:5]}
Resistance levels (nearest): {resistances[:5]}
{f'News/macro sentiment: {news_sentiment}' if news_sentiment else ''}
{scenarios_text}

=== MANDATORY VALIDATION CHECKS ===

1. MARKET STRUCTURE (BOS/MSS):
   - Look for Break of Structure (BOS) or Market Structure Shift (MSS) in the data.
   - LONG is valid only after a bullish BOS (higher high breaking previous swing high).
   - SHORT is valid only after a bearish BOS (lower low breaking previous swing low).
   - If structure is unclear or ranging, prefer NEUTRAL.

2. LEVEL CONFLUENCE:
   - Check if SL/TP levels align with multiple factors (S/R + OB + FVG).
   - Higher confluence = higher confidence. Mention confluence in pattern_reasoning.
   - Single-factor levels are weaker; reduce confidence accordingly.

3. LIQUIDITY & STOP HUNT AWARENESS:
   - Identify nearby liquidity pools (equal highs/lows, round numbers like .000).
   - If price is near a liquidity zone, a "stop hunt" may occur before the real move.
   - Warn in risk_factors if SL could be swept by a wick before reversal.

4. NEWS/EVENTS CHECK:
   - If news_sentiment mentions FOMC, CPI, ETF decisions, or major events, warn in risk_factors.
   - Reduce confidence before high-impact events.
   - Prefer NEUTRAL if major event is imminent (within 24h).

5. RISK VALIDATION:
   - Only recommend a direction if R:R >= 1.5. Otherwise output NEUTRAL.
   - Verify SL is at a logical invalidation level.
   - TPs must be ordered: LONG (TP1 < TP2 < TP3), SHORT (TP1 > TP2 > TP3).
{btc_check}
Instructions:
1. Decide direction: LONG, SHORT, or NEUTRAL (if unclear, R:R < 1.5, or structure invalid).
2. Assign confidence 0-100. Factor in: R:R, confluence, structure, liquidity risk, BTC correlation.
3. Validate SL/TP levels - mention concerns in risk_factors.
4. Provide structured explanation: summary, technical_reasoning, pattern_reasoning, risk_factors, invalidation_conditions.

Respond with a single JSON object, no markdown:
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
        risk_scenarios: Optional[Dict[str, Any]] = None,
    ) -> AIAnalysisResult:
        prompt = self._build_prompt(
            asset, timeframe, indicators, patterns, supports, resistances, news_sentiment, risk_scenarios
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
