"""
Trigger ML model training (local) on historical futures data.
"""
from fastapi import APIRouter, Query

from ml_models import MLTrainer

router = APIRouter(prefix="/ml", tags=["ml"])


@router.post("/train")
def train_ml(
    mode: str = Query("all", description="all | single"),
    symbol: str = Query("BTC/USDT:USDT", description="For mode=single"),
    timeframe: str = Query("4h", description="For mode=single"),
    limit: int = Query(800, le=1500),
    model_type: str = Query("lightgbm", description="lightgbm | xgboost | gbm (sklearn)"),
):
    """
    Train local ML model on OHLCV + indicators + patterns.
    - mode=all: merge data from all configured assets/timeframes and train one model.
    - mode=single: train on one symbol/timeframe.
    - model_type: lightgbm (default, consigliato), xgboost, gbm (sklearn GradientBoosting).
    Saves model to ml_models/artifacts/ for use in signal generation.
    """
    trainer = MLTrainer(forward_bars=1, test_size=0.2, model_type=model_type)
    if mode == "single":
        acc, report = trainer.train_single(symbol=symbol, timeframe=timeframe, limit=limit)
        return {"mode": "single", "symbol": symbol, "timeframe": timeframe, "accuracy": acc, "report": report, "model_type": model_type}
    result = trainer.train_all(limit=limit)
    return {"mode": "all", **result}
