"""
Historical and recent OHLCV via CCXT: Binance USD-M Futures (perpetual).
Solo dati pubblici: nessuna API key richiesta per fetch OHLCV.
"""
from typing import Optional

import ccxt
import pandas as pd

from config import get_settings
from models.ohlcv import OHLCVRow
from .normalizer import normalize_ohlcv

TF_MAP = {"1h": "1h", "2h": "2h", "4h": "4h", "1d": "1d"}


class MarketDataFetcher:
    """Fetch OHLCV from Binance USD-M Futures (perpetual). Public data only, no API key needed."""

    def __init__(self):
        self.settings = get_settings()
        self._exchange: Optional[ccxt.Exchange] = None

    @property
    def exchange(self) -> ccxt.Exchange:
        if self._exchange is None:
            # Binance USD-M Futures (perpetual): dati pubblici senza apiKey/secret
            self._exchange = ccxt.binanceusdm(
                {
                    "enableRateLimit": True,
                    "options": {"defaultType": "future"},
                }
            )
        return self._exchange

    def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        limit: int = 500,
        since: Optional[int] = None,
    ) -> list[OHLCVRow]:
        """
        Fetch OHLCV candles and return normalized list of OHLCVRow.
        """
        tf = TF_MAP.get(timeframe, timeframe)
        if since is None:
            # Fetch last `limit` candles
            ohlcv = self.exchange.fetch_ohlcv(symbol, tf, limit=limit)
        else:
            ohlcv = self.exchange.fetch_ohlcv(symbol, tf, since=since, limit=limit)
        return normalize_ohlcv(ohlcv)

    def fetch_ohlcv_dataframe(
        self,
        symbol: str,
        timeframe: str,
        limit: int = 500,
        since: Optional[int] = None,
    ) -> pd.DataFrame:
        """Fetch OHLCV and return as pandas DataFrame (for indicators)."""
        rows = self.fetch_ohlcv(symbol, timeframe, limit=limit, since=since)
        if not rows:
            return pd.DataFrame()
        data = [
            {
                "timestamp": r.timestamp,
                "open": r.open,
                "high": r.high,
                "low": r.low,
                "close": r.close,
                "volume": r.volume,
            }
            for r in rows
        ]
        df = pd.DataFrame(data)
        df.set_index("timestamp", inplace=True)
        return df

    def fetch_current_prices(self, symbols: list[str]) -> dict[str, float]:
        """
        Fetch current prices for a list of symbols.
        Returns a dict mapping symbol -> price.
        """
        if not symbols:
            return {}
        
        # Ensure unique and clean symbols if needed, but ccxt usually handles it
        # binanceusdm expects symbols like 'BTC/USDT'. If we have 'BTC/USDT:USDT', we might need to normalize.
        # However, settings.supported_assets usually has 'BTC/USDT'.
        
        try:
            tickers = self.exchange.fetch_tickers(symbols)
            return {
                symbol: ticker["last"]
                for symbol, ticker in tickers.items()
                if ticker and ticker.get("last")
            }
        except Exception as e:
            print(f"Error fetching prices: {e}")
            return {}
