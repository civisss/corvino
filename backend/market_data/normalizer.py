"""
Normalize OHLCV data from exchange format to internal OHLCVRow.
"""
from datetime import datetime
from typing import List

from models.ohlcv import OHLCVRow


def normalize_ohlcv(raw: list) -> List[OHLCVRow]:
    """
    CCXT returns [timestamp_ms, open, high, low, close, volume].
    Normalize to OHLCVRow list.
    """
    out: List[OHLCVRow] = []
    for row in raw:
        if len(row) < 6:
            continue
        ts_ms, o, h, l, c, v = row[0], row[1], row[2], row[3], row[4], row[5]
        out.append(
            OHLCVRow(
                timestamp=datetime.utcfromtimestamp(ts_ms / 1000.0),
                open=float(o),
                high=float(h),
                low=float(l),
                close=float(c),
                volume=float(v),
            )
        )
    return out
