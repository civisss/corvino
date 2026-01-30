"""
News and macro: fetch crypto/regulatory/macro news, classify impact via AI.
"""
from .fetcher import NewsFetcher
from .classifier import NewsClassifier
from .schemas import NewsItem, NewsSentiment

__all__ = ["NewsFetcher", "NewsClassifier", "NewsItem", "NewsSentiment"]
