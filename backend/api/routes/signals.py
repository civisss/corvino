"""
Signals CRUD: list (with filters), get by id, create, update (close/invalidate).
"""
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from models.database import get_db
from models.signal import Signal, SignalStatus, SignalCreate, SignalUpdate, SignalResponse

router = APIRouter()


@router.get("", response_model=list[SignalResponse])
def list_signals(
    status: Optional[str] = Query(None, description="active | closed | invalidated"),
    asset: Optional[str] = Query(None),
    timeframe: Optional[str] = Query(None),
    limit: int = Query(100, le=500),
    db: Session = Depends(get_db),
):
    q = db.query(Signal)
    if status:
        try:
            st = SignalStatus(status)
            q = q.filter(Signal.status == st)
        except ValueError:
            pass
    if asset:
        q = q.filter(Signal.asset == asset)
    if timeframe:
        q = q.filter(Signal.timeframe == timeframe)
    q = q.order_by(Signal.created_at.desc()).limit(limit)
    return list(q.all())


@router.get("/active", response_model=list[SignalResponse])
def list_active(db: Session = Depends(get_db)):
    return list(db.query(Signal).filter(Signal.status == SignalStatus.ACTIVE).order_by(Signal.created_at.desc()).all())


@router.get("/closed", response_model=list[SignalResponse])
def list_closed(
    limit: int = Query(100, le=500),
    db: Session = Depends(get_db),
):
    return list(
        db.query(Signal)
        .filter(Signal.status == SignalStatus.CLOSED)
        .order_by(Signal.closed_at.desc().nullslast())
        .limit(limit)
    )


@router.get("/{signal_id}", response_model=SignalResponse)
def get_signal(signal_id: str, db: Session = Depends(get_db)):
    s = db.query(Signal).filter(Signal.id == signal_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Signal not found")
    return s


@router.post("", response_model=SignalResponse, status_code=201)
def create_signal(body: SignalCreate, db: Session = Depends(get_db)):
    s = Signal(
        id=str(uuid4()),
        asset=body.asset,
        timeframe=body.timeframe,
        direction=body.direction,
        entry_price=body.entry_price,
        stop_loss=body.stop_loss,
        take_profit_1=body.take_profit_1,
        take_profit_2=body.take_profit_2,
        take_profit_3=body.take_profit_3,
        position_size_pct=body.position_size_pct,
        risk_reward=body.risk_reward,
        invalidation_conditions=body.invalidation_conditions,
        confidence_score=body.confidence_score,
        explanation=body.explanation,
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


@router.patch("/{signal_id}", response_model=SignalResponse)
def update_signal(signal_id: str, body: SignalUpdate, db: Session = Depends(get_db)):
    s = db.query(Signal).filter(Signal.id == signal_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Signal not found")
    if body.status is not None:
        s.status = body.status
    if body.exit_price is not None:
        s.exit_price = body.exit_price
        if s.entry_price and s.entry_price != 0:
            if s.direction.upper() == "LONG":
                s.pnl_pct = (body.exit_price - s.entry_price) / s.entry_price * 100
            else:
                s.pnl_pct = (s.entry_price - body.exit_price) / s.entry_price * 100
    if body.pnl_pct is not None:
        s.pnl_pct = body.pnl_pct
    if body.closed_at is not None:
        s.closed_at = body.closed_at
    db.commit()
    db.refresh(s)
    return s


@router.get("/stats/overview")
def stats_overview(db: Session = Depends(get_db)):
    """P&L overview: total closed, win rate, avg PnL."""
    from sqlalchemy import func
    closed = db.query(Signal).filter(Signal.status == SignalStatus.CLOSED)
    total = closed.count()
    if total == 0:
        return {"total_closed": 0, "wins": 0, "losses": 0, "win_rate_pct": 0, "avg_pnl_pct": 0, "total_pnl_pct": 0}
    wins = closed.filter(Signal.pnl_pct > 0).count()
    losses = closed.filter(Signal.pnl_pct <= 0).count()
    avg_pnl = db.query(func.avg(Signal.pnl_pct)).filter(Signal.status == SignalStatus.CLOSED).scalar() or 0
    total_pnl = db.query(func.sum(Signal.pnl_pct)).filter(Signal.status == SignalStatus.CLOSED).scalar() or 0
    return {
        "total_closed": total,
        "wins": wins,
        "losses": losses,
        "win_rate_pct": round(wins / total * 100, 1),
        "avg_pnl_pct": round(float(avg_pnl), 2),
        "total_pnl_pct": round(float(total_pnl), 2),
    }
