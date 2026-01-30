# Corvino – Crypto Trading Signal System

**Corvino** is an advanced **trading signal generator** (no automatic execution) that combines technical analysis, chart patterns, AI (Perplexity), and local Machine Learning models to produce high-confluence LONG/SHORT signals for the crypto market (Binance USD-M Futures).

---

## 🚀 Key Features

- **Multi-Factor Analysis**: Combines indicators (RSI, MACD, EMA), pattern recognition, and AI reasoning.
- **Signal Aggregation**: Signals are only generated if **at least 3 timeframes** (e.g., 1h, 4h, 1d) confirm the same direction for an asset.
- **AI-Powered Explanations**: Uses **Perplexity API** to analyze market context and explain the "Why" behind every signal.
- **Machine Learning**: Supports local training (LightGBM/XGBoost) to validate signals and improve confidence scores.
- **Risk Management**: Automatically calculates Entry, Stop Loss, and 3 Take Profit levels based on volatility (ATR).
- **Auto-Scan Dashboard**: The frontend automatically scans for new signals every 5 minutes.

---

## 🛠 Tech Stack

- **Backend**: Python (FastAPI), SQLAlchemy, Pandas, Scikit-learn/LightGBM.
- **Frontend**: React (Vite), TypeScript.
- **Database**: PostgreSQL.
- **Infrastructure**: Docker / Podman (Compose).

---

## ⚡ Quick Start

### Prerequisites
- Docker (or Podman with `podman-compose`).
- Perplexity API Key (for AI analysis).

### Setup

1. **Clone & Configure**
   ```bash
   cp .env.example .env
   # Edit .env and set your PERPLEXITY_API_KEY
   ```

2. **Run with Docker/Podman**
   ```bash
   # Docker
   docker-compose up -d --build

   # Podman
   podman-compose up -d --build
   ```

3. **Access**
   - **Dashboard**: [http://localhost:3000](http://localhost:3000)
   - **API Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 🧠 Machine Learning Training

The system works with just AI/Patterns, but you can train a local model to improve accuracy.

### Train on All Assets
To train a LightGBM model on all configured assets and timeframes:

```bash
curl -X POST "http://localhost:8000/api/ml/train?mode=all&limit=800&model_type=lightgbm"
```

### Train on Single Asset
```bash
curl -X POST "http://localhost:8000/api/ml/train?mode=single&symbol=BTC/USDT:USDT&timeframe=4h&limit=800&model_type=lightgbm"
```

The model artifacts are saved in `backend/ml_models/artifacts/` and automatically loaded by the signal generator.

---

## ⚙️ Configuration (.env)

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL connection string. |
| `PERPLEXITY_API_KEY` | Required for AI analysis/explanations. |
| `NEWS_API_KEY` | (Optional) For fetching external news sentiment. |

### Supported Assets Configuration
To modify the list of assets scanned by the system, edit the file `backend/supported_assets.txt`.
- Add one asset per line (e.g., `BTC/USDT:USDT`).
- Lines starting with `#` are ignored.
- The system will load this list on startup.
- **Note**: If running with Docker, you must rebuild the backend image after changing this file: `podman-compose up -d --build backend`.

---

## 📊 Dashboard Features

- **Auto-Scan**: A countdown timer triggers a new market scan every 5 minutes.
- **Manual Scan**: "Scan Manuale" button to force an immediate update.
- **Signal Cards**: Displays active signals with Entry, SL, TP levels, and AI reasoning.
- **Aggregated View**: You will only see one card per asset, representing the best signal confirmed by multiple timeframes.

---

## ⚠️ Disclaimer
This software is for educational purposes only. Do not use funds you cannot afford to lose.
