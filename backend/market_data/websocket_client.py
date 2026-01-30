"""
WebSocket client for live kline updates: Binance USD-M Futures.
"""
import asyncio
import json
from typing import Callable, Optional

import websockets

from models.ohlcv import OHLCVRow
from datetime import datetime


TIMEFRAME_STREAM = {"1h": "1h", "2h": "2h", "4h": "4h", "1d": "1d"}


class BinanceWebSocketClient:
    """
    Subscribe to Binance USD-M Futures kline streams (wss://fstream.binance.com).
    """

    BASE_WS = "wss://fstream.binance.com/ws"

    def __init__(
        self,
        symbol: str = "btcusdt",
        timeframe: str = "1h",
        on_kline: Optional[Callable[[OHLCVRow], None]] = None,
    ):
        # Futures symbol: BTC/USDT:USDT -> btcusdt
        self.symbol = symbol.lower().replace("/", "").replace(":usdt", "")
        self.timeframe = timeframe
        self.on_kline = on_kline or (lambda _: None)
        self._ws = None
        self._running = False

    def _stream_id(self) -> str:
        return f"{self.symbol}@kline_{TIMEFRAME_STREAM.get(self.timeframe, '1h')}"

    async def connect(self):
        """Connect and start consuming kline events."""
        url = f"{self.BASE_WS}/{self._stream_id()}"
        self._running = True
        try:
            async with websockets.connect(url) as ws:
                self._ws = ws
                async for message in ws:
                    if not self._running:
                        break
                    try:
                        data = json.loads(message)
                        row = self._parse_kline(data)
                        if row:
                            self.on_kline(row)
                    except (json.JSONDecodeError, KeyError, TypeError):
                        continue
        except asyncio.CancelledError:
            pass
        finally:
            self._ws = None

    def _parse_kline(self, data: dict) -> Optional[OHLCVRow]:
        k = data.get("k")
        if not k or not k.get("x"):  # x = candle closed
            return None
        return OHLCVRow(
            timestamp=datetime.utcfromtimestamp(int(k["t"]) / 1000.0),
            open=float(k["o"]),
            high=float(k["h"]),
            low=float(k["l"]),
            close=float(k["c"]),
            volume=float(k["v"]),
        )

    def stop(self):
        self._running = False
