"""
Trigger signal generation and persist to DB.
"""
from uuid import uuid4

from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.orm import Session

from models.database import get_db
from models.signal import Signal
from signal_engine import SignalGenerator

router = APIRouter()


def _save_signal(raw, db: Session) -> Signal:
    s = Signal(
        id=str(uuid4()),
        asset=raw.asset,
        timeframe=raw.timeframe,
        direction=raw.direction,
        entry_price=raw.entry_price,
        stop_loss=raw.stop_loss,
        take_profit_1=raw.take_profit_1,
        take_profit_2=raw.take_profit_2,
        take_profit_3=raw.take_profit_3,
        position_size_pct=raw.position_size_pct,
        risk_reward=raw.risk_reward,
        invalidation_conditions=raw.invalidation_conditions,
        confidence_score=raw.confidence_score,
        explanation=raw.explanation,
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


@router.post("/generate")
def generate_signals(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Run signal generation for all asset/timeframe combos and persist new signals.
    Skips assets that already have an active signal.
    Returns count of newly created signals.
    """
    # 1. Get currently active assets to skip
    active_signals = db.query(Signal).filter(Signal.status == "active").all()
    # Normalize asset names if needed, but usually they match settings (e.g. BTC/USDT)
    active_assets = {s.asset for s in active_signals}

    gen = SignalGenerator()
    raw_list = gen.generate_all(use_news=True, exclude_assets=list(active_assets))
    
    created = []
    for raw in raw_list:
        s = _save_signal(raw, db)
        created.append(s.id)
    return {"created": len(created), "signal_ids": created, "skipped": list(active_assets)}


@router.post("/generate/{asset}/{timeframe}")
def generate_single(
    asset: str,
    timeframe: str,
    db: Session = Depends(get_db),
):
    """Generate one signal for the given asset and timeframe (Binance USD-M Futures)."""
    # Normalize to CCXT Futures format: BTC -> BTC/USDT:USDT
    sym = asset.upper().replace("-", "/")
    if not sym.endswith("/USDT:USDT"):
        if sym.endswith("/USDT"):
            sym = f"{sym}:USDT"
        else:
            sym = f"{sym}/USDT:USDT"
    gen = SignalGenerator()
    raw = gen.generate(sym, timeframe, use_news=True)
    if not raw:
        return {"created": 0, "message": "No signal generated (low confidence or insufficient data)"}
    s = _save_signal(raw, db)
    return {"created": 1, "signal_id": s.id}
