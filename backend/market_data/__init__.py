"""
Market data: real-time and historical OHLCV via CCXT and WebSocket.
"""
from .fetcher import MarketDataFetcher
from .normalizer import normalize_ohlcv
from .websocket_client import BinanceWebSocketClient

__all__ = ["MarketDataFetcher", "normalize_ohlcv", "BinanceWebSocketClient"]
