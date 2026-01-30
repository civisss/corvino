"""
Train local ML model on historical OHLCV + indicators + pattern flags.
Labels: next-bar return > 0 -> LONG (1), else SHORT (0).
Supports: LightGBM (default, ottimo per serie temporali/tabular), XGBoost, GradientBoosting (sklearn).
"""
from pathlib import Path
from typing import Any, Tuple

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, classification_report

from config import get_settings
from market_data import MarketDataFetcher
from indicators import IndicatorCalculator
from patterns import PatternDetector

from .features import FeatureBuilder

# Modelli alternativi (spesso migliori per crypto/finanza)
try:
    import lightgbm as lgb
    HAS_LIGHTGBM = True
except ImportError:
    HAS_LIGHTGBM = False
try:
    import xgboost as xgb
    HAS_XGBOOST = True
except ImportError:
    HAS_XGBOOST = False


def _serialize_report(report: dict) -> dict:
    """Rende il classification_report JSON-serializable (numpy -> float)."""
    out = {}
    for k, v in report.items():
        if isinstance(v, dict):
            out[k] = {kk: float(vv) if isinstance(vv, (np.floating, np.integer)) else vv for kk, vv in v.items()}
        else:
            out[k] = float(v) if isinstance(v, (np.floating, np.integer)) else v
    return out


# Default path for saved model and scaler
MODELS_DIR = Path(__file__).resolve().parent / "artifacts"
MODEL_FILE = "signal_model.joblib"
SCALER_FILE = "feature_scaler.joblib"
META_FILE = "meta.joblib"


def _make_model(model_type: str, random_state: int) -> Any:
    """Crea il classificatore: lightgbm (default), xgboost, gbm (sklearn)."""
    model_type = (model_type or "lightgbm").lower()
    if model_type == "lightgbm" and HAS_LIGHTGBM:
        return lgb.LGBMClassifier(
            n_estimators=150,
            max_depth=6,
            learning_rate=0.08,
            num_leaves=31,
            min_child_samples=20,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=random_state,
            verbosity=-1,
            n_jobs=-1,
        )
    if model_type == "xgboost" and HAS_XGBOOST:
        return xgb.XGBClassifier(
            n_estimators=150,
            max_depth=6,
            learning_rate=0.08,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=random_state,
            n_jobs=-1,
            use_label_encoder=False,
            eval_metric="logloss",
        )
    # Fallback: sklearn GradientBoosting
    return GradientBoostingClassifier(
        n_estimators=100,
        max_depth=4,
        learning_rate=0.1,
        random_state=random_state,
    )


class MLTrainer:
    """
    Train a classifier on (features from OHLCV+indicators+patterns) -> (next bar direction).
    Saves model + scaler to ml_models/artifacts/.
    """

    def __init__(
        self,
        forward_bars: int = 1,
        test_size: float = 0.2,
        random_state: int = 42,
        model_type: str = "lightgbm",
    ):
        self.forward_bars = forward_bars
        self.test_size = test_size
        self.random_state = random_state
        self.model_type = (model_type or "lightgbm").lower()
        self.settings = get_settings()
        self.fetcher = MarketDataFetcher()
        self.indicator_calc = IndicatorCalculator()
        self.pattern_detector = PatternDetector(lookback=100)
        self.feature_builder = FeatureBuilder(normalize=False)

    def _fetch_and_prepare(self, symbol: str, timeframe: str, limit: int = 1000) -> pd.DataFrame:
        df = self.fetcher.fetch_ohlcv_dataframe(symbol, timeframe, limit=limit)
        if df.empty or len(df) < 100:
            return pd.DataFrame()
        df = self.indicator_calc.compute_all(df)
        return df.dropna(how="all", subset=["rsi", "macd", "atr"])

    def _build_labels(self, df: pd.DataFrame) -> np.ndarray:
        """Label = 1 (LONG) if close[t+forward_bars] > close[t], else 0 (SHORT)."""
        close = df["close"].values
        n = len(close)
        labels = np.zeros(n - self.forward_bars, dtype=np.int64)
        for i in range(n - self.forward_bars):
            labels[i] = 1 if close[i + self.forward_bars] > close[i] else 0
        return labels

    def _pattern_types_per_row(self, df: pd.DataFrame) -> list[list[str]]:
        """For each row index i, run pattern detection on df up to i and return list of pattern_type."""
        out = []
        for i in range(1, len(df)):
            sub = df.iloc[: i + 1]
            results = self.pattern_detector.detect_all(sub)
            out.append([p.pattern_type for p in results])
        return out

    def train_single(
        self,
        symbol: str,
        timeframe: str,
        limit: int = 1000,
    ) -> Tuple[float, dict]:
        """
        Train on one asset/timeframe. Returns (accuracy, report_dict).
        """
        df = self._fetch_and_prepare(symbol, timeframe, limit=limit)
        if len(df) < 80:
            return 0.0, {"error": "Insufficient data"}

        # Labels from future return
        labels = self._build_labels(df)
        # Features: one per row (align with label at same index)
        pattern_per_row = self._pattern_types_per_row(df)
        # build_matrix uses row 1..n-1; labels are 0..n-1-forward_bars. We need same length.
        # build_matrix returns shape (n-1, n_feat) from indices 1..n-1
        # labels have length n - forward_bars. So we need to align: for row i we have label for i (future at i+forward_bars).
        # So label[i] = close[i+forward_bars] > close[i]. Features at row i = features from df[:i+1]. So features row index i (0-based) = bar i. So we want label[i] for the same i. So we need labels of length n-1 (for rows 1..n-1). So we need labels for indices 1..n-1, i.e. label = 1 if close[i+forward_bars] > close[i] else 0, for i in 1..n-1. So we need i+forward_bars < n => i < n - forward_bars. So labels only for i in 1..n-1-forward_bars. So we have fewer labels than feature rows. So we should make labels for indices 0..n-1-forward_bars and features for indices 0..n-2 (so that last feature row has a label). So features: build_matrix gives rows for df indices 1,2,...,n-1 (length n-1). Label for feature row j (0-based) which corresponds to df index j+1: we need close[j+1+forward_bars] > close[j+1]. So label[j] = 1 if close[j+1+forward_bars] > close[j+1] else 0. So we need j+1+forward_bars < n => j < n-1-forward_bars. So we have feature rows 0..n-2 (length n-1) and we want labels for 0..n-2-forward_bars. So we truncate features to length n-1-forward_bars to match labels. Actually _build_labels returns length n - forward_bars, and the label at index i is for bar i (future = bar i+forward_bars). So we have n - forward_bars labels. Our build_matrix returns n-1 rows (for bar indices 1..n-1). So we need to take the first (n - forward_bars) feature rows and align with labels. So we take feature_rows = X[:(n - forward_bars)] and labels = labels[:(n - forward_bars)]. But labels are already length n - forward_bars. So we need feature rows from bar index 0? No - build_matrix row 0 is from df indices 0..1 (last row is index 1). So feature row 0 corresponds to bar 1. So we need label for bar 1 = close[1+forward_bars] > close[1]. So label index 1 in our _build_labels. So _build_labels[i] is for bar i. We have feature rows for bars 1,2,...,n-1. So we need labels[1], labels[2], ..., and we need 1+forward_bars < n so bar 1 has label. So labels for indices 1..n-1-forward_bars. So we take X = matrix (rows for bars 1..n-1) and y = labels[1 : n-forward_bars]. So len(y) = n - forward_bars - 1 = n - 1 - forward_bars. And we take X rows 0 : (n - 1 - forward_bars) so that we have same length. So X_tr = X[:(n-1-forward_bars)], y_tr = labels[1:(n-forward_bars)].
        X = self.feature_builder.build_matrix(df, pattern_results_per_row=pattern_per_row)
        # X has n-1 rows (bars 1..n-1). labels has n - forward_bars (bars 0..n-1-forward_bars).
        n_labels = len(labels)
        n_feat_rows = len(X)
        # Align: use feature rows that have a label. Bar i (1-based from X) = row i-1 in X. Label for bar i is labels[i] for i in 0..n-1-forward_bars. So we need bar index from 0 to n-1-forward_bars. So X rows 0 to n-1-forward_bars-1 (0-indexed) and labels 0 to n-1-forward_bars. So y = labels[:n-1-forward_bars+1] but labels has indices 0..n-forward_bars-1. So label at 0 is for bar 0, at 1 for bar 1, ... So we want labels[1 : n-forward_bars] (bars 1..n-1-forward_bars) and X[0 : n-1-forward_bars] (bars 1..n-1-forward_bars). So len = n - 1 - forward_bars.
        max_len = min(n_feat_rows, n_labels - 1)
        if max_len < 50:
            return 0.0, {"error": "Not enough samples after alignment"}
        X = X[:max_len]
        y = labels[1 : 1 + max_len]

        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        try:
            X_train, X_test, y_train, y_test = train_test_split(
                X_scaled, y, test_size=self.test_size, random_state=self.random_state, stratify=y
            )
        except ValueError:
            X_train, X_test, y_train, y_test = train_test_split(
                X_scaled, y, test_size=self.test_size, random_state=self.random_state
            )

        model = _make_model(self.model_type, self.random_state)
        model.fit(X_train, y_train)
        y_pred = model.predict(X_test)
        acc = accuracy_score(y_test, y_pred)
        report = classification_report(y_test, y_pred, output_dict=True)
        report_ser = _serialize_report(report)

        MODELS_DIR.mkdir(parents=True, exist_ok=True)
        joblib.dump(model, MODELS_DIR / MODEL_FILE)
        joblib.dump(scaler, MODELS_DIR / SCALER_FILE)
        joblib.dump(
            {"symbol": symbol, "timeframe": timeframe, "forward_bars": self.forward_bars, "model_type": self.model_type},
            MODELS_DIR / META_FILE,
        )
        self.feature_builder.set_normalization_params(scaler.mean_, np.sqrt(scaler.var_))
        return float(acc), report_ser

    def train_all(self, limit: int = 800) -> dict:
        """Train on all configured asset/timeframe combos; merge data. Returns summary."""
        all_X = []
        all_y = []
        for symbol in self.settings.supported_assets:
            for tf in self.settings.supported_timeframes:
                df = self._fetch_and_prepare(symbol, tf, limit=limit)
                if len(df) < 80:
                    continue
                labels = self._build_labels(df)
                pattern_per_row = self._pattern_types_per_row(df)
                X = self.feature_builder.build_matrix(df, pattern_results_per_row=pattern_per_row)
                max_len = min(len(X), len(labels) - 1)
                if max_len < 50:
                    continue
                X = X[:max_len]
                y = labels[1 : 1 + max_len]
                all_X.append(X)
                all_y.append(y)
        if not all_X:
            return {"error": "No data", "accuracy": 0.0}
        X = np.vstack(all_X)
        y = np.concatenate(all_y)
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        try:
            X_train, X_test, y_train, y_test = train_test_split(
                X_scaled, y, test_size=self.test_size, random_state=self.random_state, stratify=y
            )
        except ValueError:
            X_train, X_test, y_train, y_test = train_test_split(
                X_scaled, y, test_size=self.test_size, random_state=self.random_state
            )
        model = _make_model(self.model_type, self.random_state)
        model.fit(X_train, y_train)
        y_pred = model.predict(X_test)
        acc = accuracy_score(y_test, y_pred)
        report = classification_report(y_test, y_pred, output_dict=True)
        report_ser = _serialize_report(report)
        MODELS_DIR.mkdir(parents=True, exist_ok=True)
        joblib.dump(model, MODELS_DIR / MODEL_FILE)
        joblib.dump(scaler, MODELS_DIR / SCALER_FILE)
        joblib.dump(
            {"symbols": self.settings.supported_assets, "timeframes": self.settings.supported_timeframes, "forward_bars": self.forward_bars, "model_type": self.model_type},
            MODELS_DIR / META_FILE,
        )
        return {"accuracy": float(acc), "samples": int(len(y)), "report": report_ser, "model_type": self.model_type}
