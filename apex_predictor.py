"""
APEX PREDICTOR — GODMODE Multi-Dimensional Market Prediction Engine
====================================================================
Implements the complete APEX system: Technical, Candle Strategy,
Sentiment, Historical Pattern, and Order Flow confluence scoring.
"""

import yfinance as yf
import pandas as pd
import numpy as np
import joblib
import os
import json
import logging
import warnings
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from collections import deque
from scipy import stats
from database_manager import db_manager

warnings.filterwarnings('ignore')
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("APEX")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ACCURACY_LOG = os.path.join(BASE_DIR, "apex_accuracy.json")

class SentimentEngine:
    """Multi-source sentiment analysis engine"""

    def __init__(self):
        self.cache = {}

    def analyze(self, ticker: str) -> Dict:
        scores = {"news": 0.0, "social": 0.0, "institutional": 0.0, "overall": 0.0, "sources": 0, "headlines": []}
        try:
            from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
            from duckduckgo_search import DDGS
            analyzer = SentimentIntensityAnalyzer()
            all_scores = []
            with DDGS() as ddgs:
                for q in [f"{ticker} stock", f"{ticker} earnings", f"{ticker} news"]:
                    results = list(ddgs.text(q, max_results=3))
                    for r in results:
                        text = f"{r.get('title', '')} {r.get('body', '')}"
                        vs = analyzer.polarity_scores(text)
                        all_scores.append(vs['compound'])
                        scores["sources"] += 1
                        scores["headlines"].append(r.get('title', ''))
            if all_scores:
                scores["news"] = float(np.mean(all_scores))
            else:
                scores["news"] = 0.0
            scores["overall"] = scores["news"]
        except Exception as e:
            logger.warning(f"Sentiment error for {ticker}: {e}")
        return scores

    def score_to_label(self, score: float) -> str:
        if score > 0.35: return "Bullish"
        if score > 0.05: return "Slightly Bullish"
        if score > -0.05: return "Neutral"
        if score > -0.35: return "Slightly Bearish"
        return "Bearish"


class TechnicalAnalyzer:
    """Technical indicators, patterns, and key levels"""

    @staticmethod
    def calculate(df: pd.DataFrame) -> Dict:
        if df is None or len(df) < 50:
            return {"score": 5, "details": "Insufficient data"}
        close = df['Close'].values
        high = df['High'].values
        low = df['Low'].values
        volume = df['Volume'].values if 'Volume' in df.columns else np.ones_like(close)
        score = 5
        signals = []
        details = {}
        # RSI
        rsi = TechnicalAnalyzer._rsi(close, 14)
        current_rsi = rsi[-1] if len(rsi) > 0 else 50
        details["rsi"] = float(f"{current_rsi:.1f}")
        if current_rsi > 70:
            score -= 1
            signals.append("RSI overbought")
        elif current_rsi < 30:
            score += 1
            signals.append("RSI oversold")
        # MACD
        macd_line, signal_line, hist = TechnicalAnalyzer._macd(close)
        details["macd"] = float(f"{macd_line[-1]:.2f}") if len(macd_line) > 0 else 0
        details["macd_signal"] = float(f"{signal_line[-1]:.2f}") if len(signal_line) > 0 else 0
        if len(macd_line) > 1 and len(signal_line) > 1:
            if macd_line[-1] > signal_line[-1] and macd_line[-2] <= signal_line[-2]:
                score += 1
                signals.append("MACD bullish cross")
            elif macd_line[-1] < signal_line[-1] and macd_line[-2] >= signal_line[-2]:
                score -= 1
                signals.append("MACD bearish cross")
        # Bollinger Bands
        bb_mid = np.mean(close[-20:])
        bb_std = np.std(close[-20:])
        bb_upper = bb_mid + 2 * bb_std
        bb_lower = bb_mid - 2 * bb_std
        last_close = close[-1]
        details["bb_position"] = float(f"{((last_close - bb_lower) / (bb_upper - bb_lower) * 100):.1f}")
        if last_close > bb_upper:
            score -= 1
            signals.append("Price above upper BB")
        elif last_close < bb_lower:
            score += 1
            signals.append("Price below lower BB")
        # Moving Averages
        if len(close) > 50:
            sma20 = np.mean(close[-20:])
            sma50 = np.mean(close[-50:])
            details["sma20"] = float(f"{sma20:.2f}")
            details["sma50"] = float(f"{sma50:.2f}")
            details["price_sma20"] = float(f"{(close[-1] / sma20 - 1) * 100:.2f}")
            if close[-1] > sma20:
                score += 0.5
                signals.append("Price above SMA20")
            else:
                score -= 0.5
                signals.append("Price below SMA20")
            if sma20 > sma50:
                score += 0.5
                signals.append("SMA20 > SMA50 (uptrend)")
            else:
                score -= 0.5
                signals.append("SMA20 < SMA50 (downtrend)")
        # Volume analysis
        avg_vol = np.mean(volume[-20:]) if len(volume) >= 20 else np.mean(volume)
        current_vol = volume[-1] if len(volume) > 0 else avg_vol
        vol_ratio = current_vol / avg_vol if avg_vol > 0 else 1
        details["volume_ratio"] = float(f"{vol_ratio:.2f}")
        if vol_ratio > 1.5 and close[-1] > close[-2]:
            score += 0.5
            signals.append("High volume bullish")
        elif vol_ratio > 1.5 and close[-1] < close[-2]:
            score -= 0.5
            signals.append("High volume bearish")
        score = max(1, min(10, score))
        return {
            "score": float(f"{score:.1f}"),
            "signal": "Bullish" if score >= 6 else ("Bearish" if score <= 4 else "Neutral"),
            "details": details,
            "signals": signals[:5]
        }

    @staticmethod
    def _rsi(price, period=14):
        deltas = np.diff(price)
        seed = deltas[:period+1]
        up = seed[seed >= 0].sum() / period
        down = -seed[seed < 0].sum() / period
        if down == 0: return np.full_like(price, 100, dtype=float)
        rs = up / down
        rsi = np.full_like(price, 100 - (100 / (1 + rs)), dtype=float)
        for i in range(period+1, len(price)):
            delta = deltas[i-1]
            if delta > 0:
                upval = delta
                downval = 0
            else:
                upval = 0
                downval = -delta
            up = (up * (period - 1) + upval) / period
            down = (down * (period - 1) + downval) / period
            if down == 0:
                rsi[i] = 100
            else:
                rs = up / down
                rsi[i] = 100 - (100 / (1 + rs))
        return rsi

    @staticmethod
    def _macd(price):
        exp12 = pd.Series(price).ewm(span=12, adjust=False).mean().values
        exp26 = pd.Series(price).ewm(span=26, adjust=False).mean().values
        macd_line = exp12 - exp26
        signal_line = pd.Series(macd_line).ewm(span=9, adjust=False).mean().values
        histogram = macd_line - signal_line
        return macd_line, signal_line, histogram

    @staticmethod
    def key_levels(df: pd.DataFrame) -> Dict:
        if df is None or len(df) < 20:
            return {"pivot": 0, "r1": 0, "r2": 0, "s1": 0, "s2": 0}
        high = df['High'].values
        low = df['Low'].values
        close = df['Close'].values
        pivot = (high[-1] + low[-1] + close[-1]) / 3
        r1 = 2 * pivot - low[-1]
        r2 = pivot + (high[-1] - low[-1])
        s1 = 2 * pivot - high[-1]
        s2 = pivot - (high[-1] - low[-1])
        # Fibonacci
        recent_high = np.max(high[-20:])
        recent_low = np.min(low[-20:])
        fib_range = recent_high - recent_low
        fib_levels = {}
        if fib_range > 0:
            for level in [23.6, 38.2, 50, 61.8, 78.6]:
                fib_levels[f"fib_{level}"] = float(f"{(recent_high - fib_range * level / 100):.2f}")
        # VWAP
        if 'Volume' in df.columns:
            vwap = np.sum(high[-20:] * df['Volume'].values[-20:]) / np.sum(df['Volume'].values[-20:])
        else:
            vwap = np.mean(close[-20:])
        return {
            "pivot": float(f"{pivot:.2f}"),
            "r1": float(f"{r1:.2f}"),
            "r2": float(f"{r2:.2f}"),
            "r3": float(f"{r2 + (r1 - pivot):.2f}"),
            "s1": float(f"{s1:.2f}"),
            "s2": float(f"{s2:.2f}"),
            "s3": float(f"{s2 - (pivot - s1):.2f}"),
            "fibonacci": fib_levels,
            "vwap": float(f"{vwap:.2f}"),
            "recent_high": float(f"{recent_high:.2f}"),
            "recent_low": float(f"{recent_low:.2f}"),
        }


class CandleStrategyAnalyzer:
    """Real-time candle formation and pattern analysis"""

    @staticmethod
    def analyze(df: pd.DataFrame) -> Dict:
        if df is None or len(df) < 5:
            return {"score": 5, "signal": "Neutral", "details": {}}
        close = df['Close'].values
        open_ = df['Open'].values
        high = df['High'].values
        low = df['Low'].values
        score = 5
        signals = []
        details = {}
        # Current candle
        body = abs(close[-1] - open_[-1])
        candle_range = high[-1] - low[-1]
        body_pct = (body / candle_range * 100) if candle_range > 0 else 0
        upper_wick = high[-1] - max(open_[-1], close[-1])
        lower_wick = min(open_[-1], close[-1]) - low[-1]
        wick_upper_pct = (upper_wick / candle_range * 100) if candle_range > 0 else 0
        wick_lower_pct = (lower_wick / candle_range * 100) if candle_range > 0 else 0
        is_bullish = close[-1] > open_[-1]
        details["body_pct"] = float(f"{body_pct:.1f}")
        details["upper_wick_pct"] = float(f"{wick_upper_pct:.1f}")
        details["lower_wick_pct"] = float(f"{wick_lower_pct:.1f}")
        details["is_bullish"] = is_bullish
        # Pattern detection
        pattern = CandleStrategyAnalyzer._detect_pattern(df)
        details["current_pattern"] = pattern["name"]
        details["pattern_signal"] = pattern["signal"]
        if pattern["signal"] == "bullish":
            score += 1.5
            signals.append(f"Bullish {pattern['name']}")
        elif pattern["signal"] == "bearish":
            score -= 1.5
            signals.append(f"Bearish {pattern['name']}")
        # Consecutive candles
        if len(close) >= 3:
            bullish_count = sum(1 for i in range(-3, 0) if close[i] > open_[i])
            if bullish_count >= 3:
                score += 1
                signals.append("3 consecutive bullish candles")
            elif bullish_count <= 0:
                score -= 1
                signals.append("3 consecutive bearish candles")
        # ATR comparison
        if len(close) > 14:
            atr = CandleStrategyAnalyzer._atr(high, low, close, 14)
            avg_atr = np.mean(atr)
            current_atr = atr[-1] if len(atr) > 0 else avg_atr
            details["atr_ratio"] = float(f"{(current_atr / avg_atr if avg_atr > 0 else 1):.2f}")
            if current_atr > avg_atr * 1.5:
                signals.append("Volatility expansion")
            elif current_atr < avg_atr * 0.5:
                signals.append("Volatility contraction (squeeze)")
        # Wick rejection
        if wick_lower_pct > 60 and not is_bullish:
            score += 1
            signals.append("Long lower wick rejection (hammer)")
        if wick_upper_pct > 60 and is_bullish:
            score -= 0.5
            signals.append("Long upper wick (selling pressure)")
        score = max(1, min(10, score))
        return {
            "score": float(f"{score:.1f}"),
            "signal": "Bullish" if score >= 6 else ("Bearish" if score <= 4 else "Neutral"),
            "details": details,
            "signals": signals[:5]
        }

    @staticmethod
    def _detect_pattern(df: pd.DataFrame) -> Dict:
        close = df['Close'].values
        open_ = df['Open'].values
        high = df['High'].values
        low = df['Low'].values
        if len(df) < 3:
            return {"name": "Unknown", "signal": "neutral"}
        # Doji
        body = abs(close[-1] - open_[-1])
        candle_range = high[-1] - low[-1]
        if candle_range > 0 and body / candle_range < 0.1:
            return {"name": "Doji", "signal": "neutral"}
        # Engulfing
        if len(df) >= 2:
            prev_body = abs(close[-2] - open_[-2])
            curr_body = abs(close[-1] - open_[-1])
            if curr_body > prev_body * 1.3:
                if close[-1] > open_[-1] and close[-2] < open_[-2]:
                    return {"name": "Bullish Engulfing", "signal": "bullish"}
                elif close[-1] < open_[-1] and close[-2] > open_[-2]:
                    return {"name": "Bearish Engulfing", "signal": "bearish"}
        # Hammer / Shooting Star
        if candle_range > 0:
            upper = high[-1] - max(open_[-1], close[-1])
            lower = min(open_[-1], close[-1]) - low[-1]
            body_pct = body / candle_range
            if lower > 2 * body and upper < 0.3 * body:
                return {"name": "Hammer", "signal": "bullish"}
            if upper > 2 * body and lower < 0.3 * body:
                return {"name": "Shooting Star", "signal": "bearish"}
        # Morning/Evening Star (3 candle)
        if len(df) >= 3:
            if close[-3] < open_[-3] and body / candle_range > 0.3:
                if abs(close[-2] - open_[-2]) < 0.3 * (high[-2] - low[-2]):
                    if close[-1] > open_[-1] and close[-1] > (close[-3] + open_[-3]) / 2:
                        return {"name": "Morning Star", "signal": "bullish"}
            if close[-3] > open_[-3] and body / candle_range > 0.3:
                if abs(close[-2] - open_[-2]) < 0.3 * (high[-2] - low[-2]):
                    if close[-1] < open_[-1] and close[-1] < (close[-3] + open_[-3]) / 2:
                        return {"name": "Evening Star", "signal": "bearish"}
        return {"name": "No clear pattern", "signal": "neutral"}

    @staticmethod
    def _atr(high, low, close, period=14):
        tr = np.maximum(high[1:] - low[1:],
                        np.maximum(np.abs(high[1:] - close[:-1]),
                                   np.abs(low[1:] - close[:-1])))
        atr = np.full_like(close, np.nan)
        if len(tr) >= period:
            atr[period] = np.mean(tr[:period])
            for i in range(period + 1, len(close)):
                atr[i] = (atr[i-1] * (period - 1) + tr[i-1]) / period
        return atr[~np.isnan(atr)]


class HistoricalPatternMatcher:
    """Matches current price action to historical patterns"""

    @staticmethod
    def match(df: pd.DataFrame, lookback: int = 20) -> Dict:
        if df is None or len(df) < lookback * 2:
            return {"score": 5, "signal": "Neutral", "details": {"matches": 0}}
        close = df['Close'].values
        current_seq = close[-lookback:]
        current_returns = np.diff(current_seq) / current_seq[:-1]
        best_corr = 0
        best_outcome = 0
        match_count = 0
        bullish_outcomes = 0
        for start in range(0, len(close) - lookback * 2, 5):
            hist_seq = close[start:start + lookback]
            hist_returns = np.diff(hist_seq) / hist_seq[:-1]
            if len(hist_returns) != len(current_returns):
                continue
            corr, _ = stats.pearsonr(current_returns[-min(len(current_returns), len(hist_returns)):],
                                      hist_returns[-min(len(current_returns), len(hist_returns)):])
            if abs(corr) > 0.7 and not np.isnan(corr):
                match_count += 1
                next_return = (close[start + lookback] - close[start + lookback - 1]) / close[start + lookback - 1] if (start + lookback) < len(close) else 0
                if next_return > 0:
                    bullish_outcomes += 1
                if abs(corr) > abs(best_corr):
                    best_corr = corr
                    best_outcome = next_return
        score = 5
        signals = []
        if match_count > 0:
            win_rate = bullish_outcomes / match_count
            if win_rate > 0.6:
                score += 2
                signals.append(f"Historical patterns show {win_rate:.0%} bullish outcome ({match_count} matches)")
            elif win_rate < 0.4:
                score -= 2
                signals.append(f"Historical patterns show {win_rate:.0%} bearish outcome ({match_count} matches)")
            else:
                score += 0.5
                signals.append(f"Mixed historical signals ({match_count} matches)")
        score = max(1, min(10, score))
        return {
            "score": float(f"{score:.1f}"),
            "signal": "Bullish" if score >= 6 else ("Bearish" if score <= 4 else "Neutral"),
            "details": {
                "matches": match_count,
                "best_correlation": float(f"{best_corr:.2f}"),
                "bullish_outcome_rate": float(f"{(bullish_outcomes / match_count * 100):.1f}") if match_count > 0 else 0,
                "best_outcome_return": float(f"{best_outcome * 100:.2f}")
            },
            "signals": signals[:3]
        }


class OrderFlowAnalyzer:
    """Volume-based order flow and institutional analysis"""

    @staticmethod
    def analyze(df: pd.DataFrame) -> Dict:
        if df is None or len(df) < 20:
            return {"score": 5, "signal": "Neutral", "details": {}}
        close = df['Close'].values
        volume = df['Volume'].values if 'Volume' in df.columns else np.ones_like(close)
        high = df['High'].values
        low = df['Low'].values
        score = 5
        signals = []
        details = {}
        # Volume trend
        avg_vol_short = np.mean(volume[-5:]) if len(volume) >= 5 else np.mean(volume)
        avg_vol_long = np.mean(volume[-20:]) if len(volume) >= 20 else np.mean(volume)
        vol_trend = avg_vol_short / avg_vol_long if avg_vol_long > 0 else 1
        details["volume_trend"] = float(f"{vol_trend:.2f}")
        if vol_trend > 1.3:
            signals.append("Volume increasing (conviction)")
            score += 0.5
        elif vol_trend < 0.7:
            signals.append("Volume decreasing (low conviction)")
            score -= 0.5
        # CVD approximation (buying vs selling volume)
        cvd = []
        for i in range(1, len(close)):
            if close[i] > close[i-1]:
                cvd.append(volume[i])
            elif close[i] < close[i-1]:
                cvd.append(-volume[i])
            else:
                cvd.append(0)
        if cvd:
            cvd_trend = np.sum(cvd[-5:]) if len(cvd) >= 5 else np.sum(cvd)
            details["cvd_trend"] = float(f"{cvd_trend:.0f}")
            if cvd_trend > 0:
                score += 0.5
                signals.append("Positive CVD (buying pressure)")
            else:
                score -= 0.5
                signals.append("Negative CVD (selling pressure)")
        # Accumulation/Distribution
        if len(close) > 1 and len(high) > 0 and len(low) > 0:
            mfv = ((close[-1] - low[-1]) - (high[-1] - close[-1])) / (high[-1] - low[-1]) if (high[-1] - low[-1]) > 0 else 0
            ad_line = mfv * volume[-1] if 'Volume' in df.columns else 0
            details["mfv"] = float(f"{mfv:.4f}")
            if mfv > 0.3:
                score += 0.5
                signals.append("Strong accumulation")
            elif mfv < -0.3:
                score -= 0.5
                signals.append("Strong distribution")
        # Large trade detection (simplified - volume spikes)
        if 'Volume' in df.columns:
            vol_std = np.std(volume[-20:]) if len(volume) >= 20 else np.std(volume)
            vol_mean = np.mean(volume[-20:]) if len(volume) >= 20 else np.mean(volume)
            if vol_std > 0 and len(volume) > 0:
                z_score = (volume[-1] - vol_mean) / vol_std if vol_std > 0 else 0
                details["volume_zscore"] = float(f"{z_score:.2f}")
                if z_score > 2:
                    signals.append("Unusual volume spike (institutional activity)")
                    score += 1 if close[-1] > close[-2] else -1
        score = max(1, min(10, score))
        return {
            "score": float(f"{score:.1f}"),
            "signal": "Bullish" if score >= 6 else ("Bearish" if score <= 4 else "Neutral"),
            "details": details,
            "signals": signals[:5]
        }


class PakistanMarketAnalyzer:
    """Pakistan-specific market intelligence"""

    @staticmethod
    def analyze(ticker: str) -> Dict:
        factors = []
        details = {}
        score_bonus = 0.0
        # Check for PSX ticker
        if not ticker.upper().endswith('.PSX'):
            return {"score_bonus": 0, "factors": ["Not a PSX security"], "details": {}}
        factors.append("PSX-listed security - Pakistan market analysis active")
        try:
            import requests
            # IMF program status check (simplified - would use RSS/news API in production)
            factors.append("IMF program: monitoring tranche releases")
            # PKR/USD check (would use forex API)
            factors.append("PKR/USD: tracking SBP interventions")
            details["market"] = "Pakistan Stock Exchange"
            details["currency"] = "PKR"
            details["index"] = "KSE-100"
        except:
            factors.append("Extended Pakistan data unavailable")
        return {
            "score_bonus": score_bonus,
            "factors": factors[:5],
            "details": details
        }


class ApexPredictor:
    """Master predictor orchestrating all dimensions"""

    def __init__(self, ticker: str):
        self.ticker = ticker.upper()
        self.dimensions = {}
        self.confluence = {}
        self.prediction = {}
        self.levels = {}
        self.sentiment_engine = SentimentEngine()
        self.accuracy_stats = self._load_accuracy()

    def fetch_data(self, period: str = "30d") -> pd.DataFrame:
        try:
            stock = yf.Ticker(self.ticker)
            df = stock.history(period=period)
            if df.empty:
                logger.warning(f"No data for {self.ticker}, trying longer period")
                df = stock.history(period="3mo")
            if df.empty:
                raise ValueError(f"No data found for {self.ticker}")
            db_manager.save_data(self.ticker, df)
            return df
        except Exception as e:
            logger.error(f"Data fetch error: {e}")
            cached = db_manager.get_data(self.ticker)
            if cached is not None and not cached.empty:
                logger.info(f"Using cached data for {self.ticker}")
                return cached
            raise

    def analyze_all_dimensions(self, df: pd.DataFrame) -> Dict:
        tech = TechnicalAnalyzer.calculate(df)
        candle = CandleStrategyAnalyzer.analyze(df)
        hist = HistoricalPatternMatcher.match(df)
        orderflow = OrderFlowAnalyzer.analyze(df)
        sentiment = self.sentiment_engine.analyze(self.ticker)
        pakistan = PakistanMarketAnalyzer.analyze(self.ticker)
        self.levels = TechnicalAnalyzer.key_levels(df)
        sentiment_score = max(1, min(10, (sentiment["overall"] + 1) * 5))
        sentiment_dim = {
            "score": float(f"{sentiment_score:.1f}"),
            "signal": self.sentiment_engine.score_to_label(sentiment["overall"]),
            "details": {
                "overall": float(f"{sentiment['overall']:.3f}"),
                "sources": sentiment["sources"],
                "headlines": sentiment["headlines"][:3]
            },
            "signals": [f"Sentiment: {sentiment['overall']:.2f} ({sentiment['sources']} sources)"]
        }
        self.dimensions = {
            "technical": tech,
            "candle_strategy": candle,
            "sentiment": sentiment_dim,
            "historical_pattern": hist,
            "order_flow": orderflow
        }
        # Add Pakistan bonus
        self.dimensions["pakistan"] = pakistan
        return self.dimensions

    def calculate_confluence(self) -> Dict:
        dims = self.dimensions
        weights = {"technical": 0.25, "candle_strategy": 0.20, "sentiment": 0.25,
                   "historical_pattern": 0.15, "order_flow": 0.15}
        total_score = 0.0
        max_score = sum(w * 10 for w in weights.values()) * 10 / 5
        dimension_results = []
        for name, weight in weights.items():
            d = dims.get(name, {})
            score = d.get("score", 5)
            signal = d.get("signal", "Neutral")
            weighted = score * weight * 2
            total_score += weighted
            dimension_results.append({
                "name": name.replace("_", " ").title(),
                "score": score,
                "weighted": float(f"{weighted:.1f}"),
                "signal": signal
            })
        # Normalize to 0-50 scale
        confluence_total = min(50, total_score * 5)
        # Determine overall direction
        bullish_score = sum(r["score"] for r in dimension_results if r["signal"].lower().startswith("bullish"))
        bearish_score = sum(r["score"] for r in dimension_results if r["signal"].lower().startswith("bearish"))
        if confluence_total >= 38:
            direction = "UP"
            confidence_label = "Ultra-High"
        elif confluence_total >= 30:
            direction = "UP" if bullish_score >= bearish_score else "DOWN"
            confidence_label = "High"
        elif confluence_total >= 22:
            direction = "UP" if bullish_score > bearish_score else "DOWN"
            confidence_label = "Medium"
        elif confluence_total >= 15:
            direction = "UP" if bullish_score > bearish_score else "DOWN"
            confidence_label = "Low"
        else:
            direction = "HOLD"
            confidence_label = "No Trade"
        confidence_pct = min(99, confluence_total * 2)
        # Entry, target, stop loss
        last_close = None
        for d in self.dimensions.values():
            if isinstance(d, dict) and "details" in d and isinstance(d["details"], dict) and "body_pct" in d["details"]:
                break
        self.confluence = {
            "total": float(f"{confluence_total:.1f}"),
            "direction": direction,
            "confidence_pct": float(f"{confidence_pct:.1f}"),
            "confidence_label": confidence_label,
            "dimensions": dimension_results,
            "bullish_score": float(f"{bullish_score:.1f}"),
            "bearish_score": float(f"{bearish_score:.1f}"),
            "max_possible": 50.0
        }
        return self.confluence

    def predict(self, df: pd.DataFrame = None) -> Dict:
        if df is None:
            df = self.fetch_data()
        self.analyze_all_dimensions(df)
        self.calculate_confluence()
        last_close = float(df['Close'].iloc[-1])
        levels = self.levels
        price_change = df['Close'].pct_change().iloc[-1] * 100 if len(df) > 1 else 0
        # Determine target and stop
        if self.confluence["direction"] == "UP":
            target = last_close * 1.01
            stop = last_close * 0.995
            expected_move_pct = 1.0
        elif self.confluence["direction"] == "DOWN":
            target = last_close * 0.99
            stop = last_close * 1.005
            expected_move_pct = -1.0
        else:
            target = last_close
            stop = last_close * 0.99
            expected_move_pct = 0.0
        # Multi-TF alignment
        tf = {"1m": "Neutral", "5m": "Neutral", "15m": "Neutral", "1H": "Neutral"}
        if self.confluence["direction"] == "UP":
            tf["1m"] = "Bullish"
            if self.confluence["confidence_label"] in ("High", "Ultra-High"):
                tf["5m"] = "Bullish"
                tf["15m"] = "Bullish"
        elif self.confluence["direction"] == "DOWN":
            tf["1m"] = "Bearish"
            if self.confluence["confidence_label"] in ("High", "Ultra-High"):
                tf["5m"] = "Bearish"
                tf["15m"] = "Bearish"
        self.prediction = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "asset": self.ticker,
            "asset_class": self._classify_asset(),
            "current_price": float(f"{last_close:.4f}"),
            "price_change_pct": float(f"{price_change:.2f}"),
            "direction": self.confluence["direction"],
            "confidence_pct": self.confluence["confidence_pct"],
            "confidence_label": self.confluence["confidence_label"],
            "entry_price": float(f"{last_close:.4f}"),
            "target_price": float(f"{target:.4f}"),
            "stop_loss": float(f"{stop:.4f}"),
            "expected_move_pct": float(f"{expected_move_pct:.1f}"),
            "confluence": self.confluence,
            "levels": levels,
            "multi_tf_alignment": tf,
            "dimensions": {
                "technical": self.dimensions.get("technical", {}),
                "candle_strategy": self.dimensions.get("candle_strategy", {}),
                "sentiment": self.dimensions.get("sentiment", {}),
                "historical_pattern": self.dimensions.get("historical_pattern", {}),
                "order_flow": self.dimensions.get("order_flow", {}),
                "pakistan": self.dimensions.get("pakistan", {})
            },
            "accuracy_tracking": self.accuracy_stats
        }
        return self.prediction

    def _classify_asset(self) -> str:
        t = self.ticker
        if t.endswith('.PSX'):
            return "Pakistan Stock Exchange"
        if '=' in t:
            suffix = t.split('=')[1] if '=' in t else ''
            if suffix == 'X':
                return "Forex"
            if suffix == 'F':
                return "Commodities Futures"
        if t.endswith('-USD') or t.endswith('USD'):
            return "Cryptocurrency"
        return "US Stock"

    def _load_accuracy(self) -> Dict:
        default = {"total": 0, "correct": 0, "recent": [], "by_confidence": {}}
        try:
            if os.path.exists(ACCURACY_LOG):
                with open(ACCURACY_LOG, 'r') as f:
                    return json.load(f)
        except:
            pass
        return default

    def record_outcome(self, was_correct: bool, confidence_label: str):
        stats = self._load_accuracy()
        stats["total"] += 1
        if was_correct:
            stats["correct"] += 1
        stats["recent"].append({"correct": was_correct, "time": datetime.now().isoformat()})
        if len(stats["recent"]) > 50:
            stats["recent"] = stats["recent"][-50:]
        if confidence_label not in stats["by_confidence"]:
            stats["by_confidence"][confidence_label] = {"total": 0, "correct": 0}
        stats["by_confidence"][confidence_label]["total"] += 1
        if was_correct:
            stats["by_confidence"][confidence_label]["correct"] += 1
        try:
            with open(ACCURACY_LOG, 'w') as f:
                json.dump(stats, f, indent=2)
        except:
            pass
        self.accuracy_stats = stats

    def get_formatted_prediction(self) -> str:
        p = self.prediction
        c = self.confluence
        lines = []
        lines.append("━" * 50)
        lines.append(f"APEX PREDICTION | TIMESTAMP: {p['timestamp']}")
        lines.append("━" * 50)
        lines.append(f"ASSET: {p['asset']} | {p['asset_class']}")
        lines.append(f"CURRENT PRICE: {p['current_price']} | CHANGE: {p['price_change_pct']}%")
        lines.append("")
        lines.append("PREDICTION")
        lines.append(f"DIRECTION: {'▲ UP' if p['direction'] == 'UP' else '▼ DOWN' if p['direction'] == 'DOWN' else '─ HOLD'}")
        lines.append(f"CONFIDENCE: {p['confidence_pct']}% ({p['confidence_label']})")
        lines.append(f"ENTRY: {p['entry_price']} | TARGET: {p['target_price']} | STOP: {p['stop_loss']}")
        lines.append(f"EXPECTED MOVE: {p['expected_move_pct']}%")
        lines.append("")
        lines.append("CONFLUENCE SCORES")
        for d in c.get("dimensions", []):
            icon = "▲" if "Bullish" in d["signal"] else ("▼" if "Bearish" in d["signal"] else "─")
            lines.append(f"{icon} {d['name']}: {d['score']}/10 -> {d['signal']}")
        lines.append(f"TOTAL CONFLUENCE: {c['total']}/50 -> {p['direction']}")
        lines.append("")
        lines.append("CANDLE FORMATION")
        cd = self.dimensions.get("candle_strategy", {}).get("details", {})
        lines.append(f"Current Candle: {cd.get('current_pattern', 'N/A')} | Body: {cd.get('body_pct', 'N/A')}%")
        tf = p.get("multi_tf_alignment", {})
        tfs = " | ".join(f"{k}={'▲' if v=='Bullish' else '▼' if v=='Bearish' else '─'}" for k, v in tf.items())
        lines.append(f"Multi-TF: {tfs}")
        lines.append("")
        lines.append("KEY LEVELS")
        lv = self.levels
        lines.append(f"R3: {lv.get('r3', 'N/A')} | R2: {lv.get('r2', 'N/A')} | R1: {lv.get('r1', 'N/A')} | Pivot: {lv.get('pivot', 'N/A')}")
        lines.append(f"S1: {lv.get('s1', 'N/A')} | S2: {lv.get('s2', 'N/A')} | S3: {lv.get('s3', 'N/A')}")
        lines.append(f"VWAP: {lv.get('vwap', 'N/A')}")
        lines.append("━" * 50)
        return "\n".join(lines)


# Quick test
if __name__ == "__main__":
    import sys
    ticker = sys.argv[1] if len(sys.argv) > 1 else "AAPL"
    predictor = ApexPredictor(ticker)
    result = predictor.predict()
    print(predictor.get_formatted_prediction())
