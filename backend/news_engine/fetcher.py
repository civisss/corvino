"""
Fetch crypto and macro news from public sources (RSS, APIs).
"""
from datetime import datetime
from typing import List
import feedparser
import httpx

from .schemas import NewsItem


# Crypto news RSS / public endpoints
CRYPTO_FEEDS = [
    "https://cointelegraph.com/rss",
    "https://www.coindesk.com/arc/outboundfeeds/news/",
]
# Fallback: if no API key, we use static/sample or RSS only


class NewsFetcher:
    """
    Fetch news from RSS and optional API.
    """

    def __init__(self, api_key: str = ""):
        self.api_key = api_key

    def fetch_latest(self, limit: int = 20) -> List[NewsItem]:
        """Fetch latest crypto/macro headlines."""
        items: List[NewsItem] = []
        for url in CRYPTO_FEEDS[:2]:
            try:
                parsed = feedparser.parse(
                    url,
                    request_headers={"User-Agent": "Corvino/1.0"},
                )
                for e in parsed.entries[:limit]:
                    pub = None
                    if hasattr(e, "published_parsed") and e.published_parsed:
                        try:
                            pub = datetime(*e.published_parsed[:6])
                        except Exception:
                            pass
                    items.append(
                        NewsItem(
                            title=e.get("title", ""),
                            url=e.get("link"),
                            source=parsed.feed.get("title", url),
                            published_at=pub,
                            summary=e.get("summary", "")[:500] if e.get("summary") else None,
                        )
                    )
            except Exception:
                continue
        # Sort by date desc, take limit
        items.sort(key=lambda x: x.published_at or datetime.min, reverse=True)
        return items[:limit]
