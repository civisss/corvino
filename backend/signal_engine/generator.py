"""
Orchestrate: fetch OHLCV -> indicators -> patterns -> support/resistance -> AI + ML -> risk -> signal.
ML (local trained model) + Perplexity AI work together for sharper signals.
"""
from typing import Optional

from config import get_settings
from market_data import MarketDataFetcher
from indicators import IndicatorCalculator, compute_support_resistance
from patterns import PatternDetector
from ai_engine import AIAnalyzer
from news_engine import NewsFetcher, NewsClassifier
from risk_management import RiskCalculator
from ml_models import MLPredictor

from .schemas import RawSignal


# Blend AI confidence with ML: weight AI 0.6, ML 0.4 when both agree; else use AI with slight penalty
AI_WEIGHT = 0.6
ML_WEIGHT = 0.4


class SignalGenerator:
    """
    End-to-end signal generation: ML (local) + Perplexity AI combined for precision.
    """

    def __init__(self):
        self.settings = get_settings()
        self.fetcher = MarketDataFetcher()
        self.indicator_calc = IndicatorCalculator()
        self.pattern_detector = PatternDetector(lookback=100)
        self.ai = AIAnalyzer()
        self.ml = MLPredictor()
        self.ml.load()
        self.news_fetcher = NewsFetcher(api_key=self.settings.news_api_key)
        self.news_classifier = NewsClassifier()
        self.risk = RiskCalculator()

    def generate(
        self,
        asset: str,
        timeframe: str,
        use_news: bool = True,
    ) -> Optional[RawSignal]:
        """
        Generate one signal for the given asset and timeframe.
        Returns None if confidence too low or data insufficient.
        """
        # 1. OHLCV
        df = self.fetcher.fetch_ohlcv_dataframe(asset, timeframe, limit=200)
        if df.empty or len(df) < 50:
            return None

        # 2. Indicators
        df = self.indicator_calc.compute_all(df)
        metrics = self.indicator_calc.get_latest_metrics(df)
        atr = metrics.get("atr") or (metrics.get("close", 0) * 0.02)

        # 3. Support / Resistance
        supports, resistances = compute_support_resistance(df, lookback=100, num_levels=5)

        # 4. Patterns
        pattern_results = self.pattern_detector.detect_all(df)
        patterns_for_ai = [
            {
                "pattern_type": p.pattern_type,
                "confidence": p.confidence,
                "description": p.description,
                "level_or_price": p.level_or_price,
            }
            for p in pattern_results
        ]

        # 5. News sentiment (optional)
        news_sentiment_str = None
        if use_news:
            news_items = self.news_fetcher.fetch_latest(limit=10)
            sentiment = self.news_classifier.classify_batch(news_items)
            news_sentiment_str = f"{sentiment.sentiment.value} (impact: {sentiment.impact_score:.2f}). {sentiment.summary}"

        # 6. AI analysis (Perplexity) - with Risk Scenarios
        # Extract Order Blocks and FVGs from patterns for risk calculation
        order_blocks = []
        fvg_zones = []
        for p in pattern_results:
            if p.pattern_type == "order_block_bullish" and p.metadata:
                order_blocks.append({"type": "bullish", "low": p.metadata.get("ob_low"), "high": p.metadata.get("ob_high")})
            elif p.pattern_type == "order_block_bearish" and p.metadata:
                order_blocks.append({"type": "bearish", "low": p.metadata.get("ob_low"), "high": p.metadata.get("ob_high")})
            elif p.pattern_type == "fvg_bullish" and p.metadata:
                fvg_zones.append({"type": "bullish", "low": p.metadata.get("fvg_low"), "high": p.metadata.get("fvg_high")})
            elif p.pattern_type == "fvg_bearish" and p.metadata:
                fvg_zones.append({"type": "bearish", "low": p.metadata.get("fvg_low"), "high": p.metadata.get("fvg_high")})

        # Compute hypothetical risk setups for both directions
        sl_long, tp1_l, tp2_l, tp3_l, rr_long = self.risk.compute_dynamic_levels(
            entry=metrics.get("close", 0), atr=atr, direction="LONG", 
            supports=supports, resistances=resistances,
            order_blocks=order_blocks, fvg_zones=fvg_zones
        )
        sl_short, tp1_s, tp2_s, tp3_s, rr_short = self.risk.compute_dynamic_levels(
            entry=metrics.get("close", 0), atr=atr, direction="SHORT", 
            supports=supports, resistances=resistances,
            order_blocks=order_blocks, fvg_zones=fvg_zones
        )
        
        scenarios = {
            "LONG": {"sl": sl_long, "tps": [tp1_l, tp2_l, tp3_l], "rr": rr_long},
            "SHORT": {"sl": sl_short, "tps": [tp1_s, tp2_s, tp3_s], "rr": rr_short},
        }

        ai_result = self.ai.analyze(
            asset=asset,
            timeframe=timeframe,
            indicators=metrics,
            patterns=patterns_for_ai,
            supports=supports,
            resistances=resistances,
            news_sentiment=news_sentiment_str,
            risk_scenarios=scenarios
        )
        
        # 6b. ML local model (if trained): combine with AI for sharper signal
        direction = ai_result.direction
        confidence = ai_result.confidence_score
        if direction == "NEUTRAL":
            direction = "LONG"  # default for signal
        ml_direction, ml_confidence = self.ml.predict(df, pattern_types=[p.pattern_type for p in pattern_results])
        if self.ml.is_loaded and ml_direction is not None:
            if ml_direction == direction:
                confidence = AI_WEIGHT * confidence + ML_WEIGHT * ml_confidence
            else:
                confidence = max(25, confidence - 15)  # slight penalty when ML disagrees
            confidence = min(100, round(confidence, 1))

        # Skip if too low confidence
        if confidence < 25:
            return None

        entry = metrics.get("close", 0)
        if not entry or entry <= 0:
            return None

        # 7. Finalize Risk levels based on chosen direction
        # We use the pre-calculated scenarios or fallback to default method if needed
        chosen_scenario = scenarios.get(direction)
        if chosen_scenario:
            stop_loss = chosen_scenario["sl"]
            tps = chosen_scenario["tps"]
            take_profit_1 = tps[0]
            take_profit_2 = tps[1]
            take_profit_3 = tps[2]
            risk_reward = chosen_scenario["rr"]
        else:
             # Fallback (should not happen if direction is valid)
             stop_loss, take_profit_1, take_profit_2, take_profit_3, risk_reward = self.risk.compute_levels(
                entry=entry, atr=atr, direction=direction
            )
        position_size_pct = self.risk.position_size_pct(entry, stop_loss, risk_pct=1.0)

        invalidation = "; ".join(ai_result.explanation.invalidation_conditions or [])

        explanation = ai_result.explanation.model_dump()
        if self.ml.is_loaded and ml_direction is not None:
            explanation["ml_agreement"] = ml_direction == direction
            explanation["ml_confidence"] = ml_confidence

        return RawSignal(
            asset=asset,
            timeframe=timeframe,
            direction=direction,
            entry_price=entry,
            stop_loss=stop_loss,
            take_profit_1=take_profit_1,
            take_profit_2=take_profit_2,
            take_profit_3=take_profit_3,
            position_size_pct=position_size_pct,
            risk_reward=round(risk_reward, 2),
            invalidation_conditions=invalidation or None,
            confidence_score=confidence,
            explanation=explanation,
        )

    def generate_all(
        self,
        use_news: bool = True,
        exclude_assets: list[str] = None
    ) -> list[RawSignal]:
        """
        Generate signals for all configured asset/timeframe combinations.
        Applies aggregation logic: only returns a signal for an asset if at least
        3 timeframes confirm the same direction.
        
        Args:
            use_news: Whether to include news sentiment.
            exclude_assets: List of asset names (e.g. 'BTC/USDT') to skip.
        """
        final_signals: list[RawSignal] = []
        exclude_assets = set(exclude_assets or [])
        # Normalize exclusion list: strip :USDT suffix if present
        clean_exclusions = {a.split(":")[0] for a in exclude_assets}

        for asset in self.settings.supported_assets:
            # Normalize current asset for check
            clean_asset = asset.split(":")[0]
            
            if clean_asset in clean_exclusions:
                print(f"Skipping {asset} (already active)")
                continue

            asset_signals: list[RawSignal] = []
            
            # 1. Generate for all timeframes
            for tf in self.settings.supported_timeframes:
                try:
                    s = self.generate(asset, tf, use_news=use_news)
                    if s:
                        asset_signals.append(s)
                except Exception as e:
                    print(f"Error generating {asset} {tf}: {e}")
                    continue

            if not asset_signals:
                continue

            # 2. Group by direction
            longs = [s for s in asset_signals if s.direction == "LONG"]
            shorts = [s for s in asset_signals if s.direction == "SHORT"]

            # 3. Check for confirmation (>= 3 timeframes)
            # We pick the direction with the most signals
            consensus_signals = []
            if len(longs) >= 3:
                consensus_signals = longs
            elif len(shorts) >= 3:
                consensus_signals = shorts
            
            if not consensus_signals:
                continue

            # 4. Select the "best" signal (highest confidence)
            best_signal = max(consensus_signals, key=lambda s: s.confidence_score)
            
            # Enrich explanation with confirmation details
            confirming_tfs = [s.timeframe for s in consensus_signals]
            confirmation_note = f"Signal confirmed by {len(consensus_signals)} timeframes: {', '.join(confirming_tfs)}."
            
            # explanation is a dict (from model_dump above)
            if best_signal.explanation.get("summary"):
                best_signal.explanation["summary"] += f" [{confirmation_note}]"
            else:
                best_signal.explanation["summary"] = confirmation_note

            final_signals.append(best_signal)

        return final_signals
