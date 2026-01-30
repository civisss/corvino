"""
Classify news impact (bullish/bearish/neutral) and detect regime change via Perplexity.
"""
import json
import re
from typing import List

from openai import OpenAI

from config import get_settings
from .schemas import NewsItem, NewsSentiment, SentimentLabel


class NewsClassifier:
    """
    Use Perplexity API to classify news sentiment and detect regime changes.
    """

    def __init__(self):
        self.settings = get_settings()
        self._client = None

    @property
    def client(self):
        if self._client is None and self.settings.perplexity_api_key:
            self._client = OpenAI(
                api_key=self.settings.perplexity_api_key,
                base_url="https://api.perplexity.ai/v2",
            )
        return self._client

    def classify_batch(self, news: List[NewsItem]) -> NewsSentiment:
        """
        Aggregate headlines and return overall sentiment + regime change flag.
        """
        if not news:
            return NewsSentiment(
                sentiment=SentimentLabel.NEUTRAL,
                impact_score=0.5,
                summary="No news available.",
                regime_change_detected=False,
            )
        text = "\n".join([f"- {n.title}" + (f" ({n.summary or ''})" if n.summary else "") for n in news[:15]])
        if self.client:
            try:
                resp = self.client.chat.completions.create(
                    model=self.settings.llm_model,
                    messages=[
                        {
                            "role": "user",
                            "content": f"""Classify the overall market sentiment from these crypto/macro headlines.
Headlines:
{text}

Respond with JSON only:
{{ "sentiment": "bullish" | "bearish" | "neutral", "impact_score": 0.0-1.0, "summary": "one sentence", "regime_change_detected": true|false }}
""",
                        }
                    ],
                    temperature=0.2,
                    max_tokens=200,
                )
                if not resp.choices or not resp.choices[0].message.content:
                    raise ValueError("Empty Perplexity response")
                raw = resp.choices[0].message.content.strip()
                json_str = re.sub(r"^```\w*\n?", "", raw).strip()
                json_str = re.sub(r"\n?```\s*$", "", json_str).strip()
                data = json.loads(json_str)
                return NewsSentiment(
                    sentiment=SentimentLabel(data.get("sentiment", "neutral")),
                    impact_score=float(data.get("impact_score", 0.5)),
                    summary=data.get("summary", "No summary"),
                    regime_change_detected=bool(data.get("regime_change_detected", False)),
                    raw_response=data,
                )
            except (json.JSONDecodeError, KeyError, TypeError):
                pass
        return NewsSentiment(
            sentiment=SentimentLabel.NEUTRAL,
            impact_score=0.5,
            summary="News available; classification unavailable (no API).",
            regime_change_detected=False,
        )
