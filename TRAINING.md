# Addestramento modelli ML – Corvino

I modelli ML **non sono obbligatori**: puoi generare segnali anche senza addestrarli (solo Perplexity). Se addestri il modello, i segnali useranno **ML + Perplexity** (confidence combinata).

---

## Ordine consigliato

1. **Avvia il backend** (o l’intero stack).
2. **Addestra il modello** (una volta, o quando vuoi aggiornare).
3. **Genera i segnali** (il backend userà il modello se presente in `artifacts/`).

---

## Comandi da lanciare

### 1. Avvio stack (Docker)

```bash
cp .env.example .env
# Imposta PERPLEXITY_API_KEY in .env
docker-compose up -d
```

Oppure solo backend in locale:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
export DATABASE_URL=postgresql://corvino:corvino_secret@localhost:5432/corvino
export PYTHONPATH=$PWD
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

### 2. Addestramento modello ML

**Opzione A – Da terminale (curl)**

Train su **tutti** gli asset/timeframe (BTC, ETH, SOL × 1h, 2h, 4h, 1d) – **consigliato**:

```bash
curl -X POST "http://localhost:8000/api/ml/train?mode=all&limit=800&model_type=lightgbm"
```

Train su **un solo** simbolo/timeframe (es. BTC 4h):

```bash
curl -X POST "http://localhost:8000/api/ml/train?mode=single&symbol=BTC/USDT:USDT&timeframe=4h&limit=800&model_type=lightgbm"
```

**Opzione B – Script (backend in esecuzione)**

```bash
cd backend
chmod +x scripts/train_ml.sh
./scripts/train_ml.sh           # mode=all
./scripts/train_ml.sh single   # mode=single (BTC 4h)
```

**Opzione C – Da browser / Swagger**

1. Apri http://localhost:8000/docs  
2. Endpoint **POST /api/ml/train**  
3. Clicca "Try it out", imposta i parametri e "Execute".

### 3. Generazione segnali

Dopo il training (o anche senza, solo Perplexity):

```bash
curl -X POST "http://localhost:8000/api/generate"
```

Oppure dalla Dashboard: http://localhost:3000 → "Genera segnali".

---

## Modelli disponibili

| `model_type` | Descrizione |
|--------------|-------------|
| **lightgbm** (default) | Consigliato per serie temporali/tabular, veloce e spesso più accurato. |
| **xgboost** | Alternativa solida, ottimo per tabular. |
| **gbm** | sklearn GradientBoosting (sempre disponibile, nessuna dipendenza extra). |

Esempio con XGBoost:

```bash
curl -X POST "http://localhost:8000/api/ml/train?mode=all&limit=800&model_type=xgboost"
```

---

## Dove viene salvato il modello

- **Percorso**: `backend/ml_models/artifacts/`
- **File**: `signal_model.joblib`, `feature_scaler.joblib`, `meta.joblib`
- Il backend carica automaticamente questi file alla generazione segnali; non serve riavviare dopo un nuovo training.

---

## Ri-addestramento

Puoi rieseguire il training quando vuoi (più dati, altro `model_type`, altro timeframe). L’ultimo modello salvato in `artifacts/` è quello usato. Non serve riavviare il backend.
