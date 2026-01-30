#!/usr/bin/env bash
# Addestra il modello ML locale su dati Binance Futures (BTC/ETH/SOL, 1h/2h/4h/1d).
# Richiede backend in esecuzione su localhost:8000 (o imposta API_BASE).
#
# Uso:
#   ./scripts/train_ml.sh           # train su tutti gli asset/timeframe (lightgbm)
#   ./scripts/train_ml.sh single     # train solo BTC 4h
#   API_BASE=http://localhost:8000 ./scripts/train_ml.sh

set -e
API_BASE="${API_BASE:-http://localhost:8000}"

echo "Training ML model (API: $API_BASE)..."
if [ "$1" = "single" ]; then
  curl -s -X POST "$API_BASE/api/ml/train?mode=single&symbol=BTC/USDT:USDT&timeframe=4h&limit=800&model_type=lightgbm" | python3 -m json.tool
else
  curl -s -X POST "$API_BASE/api/ml/train?mode=all&limit=800&model_type=lightgbm" | python3 -m json.tool
fi
echo "Done. Model saved in backend/ml_models/artifacts/"
