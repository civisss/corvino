"""
Load trained ML model and predict direction (LONG/SHORT) + confidence from current features.
"""
from pathlib import Path
from typing import Optional, Tuple

import joblib
import numpy as np
import pandas as pd

from .features import FeatureBuilder


MODELS_DIR = Path(__file__).resolve().parent / "artifacts"
MODEL_FILE = "signal_model.joblib"
SCALER_FILE = "feature_scaler.joblib"


class MLPredictor:
    """
    Load saved model and scaler; predict direction and probability from OHLCV + indicators + patterns.
    Returns (direction "LONG"|"SHORT", confidence 0-100) or (None, 0) if no model.
    """

    def __init__(self):
        self._model = None
        self._scaler = None
        self._feature_builder = FeatureBuilder(normalize=False)

    def load(self) -> bool:
        """Load model and scaler from artifacts. Returns True if loaded."""
        model_path = MODELS_DIR / MODEL_FILE
        scaler_path = MODELS_DIR / SCALER_FILE
        if not model_path.exists() or not scaler_path.exists():
            return False
        try:
            self._model = joblib.load(model_path)
            self._scaler = joblib.load(scaler_path)
            return True
        except Exception:
            return False

    @property
    def is_loaded(self) -> bool:
        return self._model is not None and self._scaler is not None

    def predict(
        self,
        df: pd.DataFrame,
        pattern_types: Optional[list[str]] = None,
    ) -> Tuple[Optional[str], float]:
        """
        Predict direction and confidence from current state.
        Returns (direction "LONG"|"SHORT", confidence 0-100). If model not loaded, returns (None, 0).
        """
        if not self.is_loaded:
            return None, 0.0
        if df.empty or len(df) < 2:
            return None, 0.0
        try:
            feat = self._feature_builder.build_from_df(df, pattern_types=pattern_types)
            feat = feat.reshape(1, -1)
            if feat.shape[1] != self._scaler.n_features_in_:
                return None, 0.0
            X = self._scaler.transform(feat)
            pred_class = self._model.predict(X)[0]
            proba = self._model.predict_proba(X)[0]
            confidence = float(max(proba)) * 100.0  # 0-100
            direction = "LONG" if pred_class == 1 else "SHORT"
            return direction, round(confidence, 1)
        except Exception:
            return None, 0.0
