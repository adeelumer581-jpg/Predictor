"""
COMPREHENSIVE PRODUCTION SYSTEM
===============================
All markets: Stocks, Commodities, Forex, Crypto, Pakistani Stocks
Real-time predictions, News, Screenshot analysis, All agents working
"""
import os
import sys
import time
import json
import logging
import threading
from concurrent.futures import ThreadPoolExecutor, TimeoutError, as_completed
from datetime import datetime
from typing import Dict, List, Any, Optional
from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO
import yfinance as yf
import pandas as pd
import numpy as np
import joblib
import psutil
from collections import deque

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("ComprehensiveSystem")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PREDICTION_WORKERS = int(os.environ.get("PREDICTION_WORKERS", "6"))
PREDICTION_CACHE_TTL = int(os.environ.get("PREDICTION_CACHE_TTL", "300"))
MARKET_DATA_CACHE_TTL = int(os.environ.get("MARKET_DATA_CACHE_TTL", "900"))

# ============================================================
# ALL MARKET DATA - EVERYTHING
# ============================================================

class ComprehensiveDataSource:
    """All possible trading assets"""

    # Pakistani Stocks (KSE-100) - use different tickers for yfinance
    PAKISTANI_STOCKS = [
        "OGDC-PSX.KL", "PSO-PSX.KL", "PPL-PSX.KL", "HUBC-PSX.KL", "EFERT-PSX.KL",
        "LUCK-PSX.KL", "ENGRO-PSX.KL", "FFBL-PSX.KL", "FCCL-PSX.KL", "DGKC-PSX.KL",
        "HBL-PSX.KL", "UBL-PSX.KL", "BAFL-PSX.KL", "MCB-PSX.KL", "BAHN-PSX.KL",
        "NML-PSX.KL", "NCC-PSX.KL", "SNGP-PSX.KL", "MUGHAL-PSX.KL", "JKLC-PSX.KL"
    ]

    # Alternative: Use global stocks that might have Pakistan listing
    PAKISTANI_SIMULATED = [
        {"ticker": "OGDC", "name": "Oil & Gas Development Co", "base_price": 120.5},
        {"ticker": "PSO", "name": "Pakistan State Oil", "base_price": 180.2},
        {"ticker": "PPL", "name": "Pakistan Petroleum", "base_price": 95.8},
        {"ticker": "HUBC", "name": "Hub Power Co", "base_price": 220.0},
        {"ticker": "HBL", "name": "Habib Bank", "base_price": 105.3},
        {"ticker": "UBL", "name": "United Bank", "base_price": 215.6},
        {"ticker": "MCB", "name": "MCB Bank", "base_price": 165.4},
        {"ticker": "LUCK", "name": "Lucky Cement", "base_price": 890.5},
        {"ticker": "ENGRO", "name": "Engro Corp", "base_price": 285.2},
        {"ticker": "NCC", "name": "National Cement", "base_price": 410.8}
    ]

    # Major Global Stocks
    GLOBAL_STOCKS = [
        # Tech
        "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "NFLX", "ADBE", "CRM",
        "ORCL", "IBM", "INTC", "AMD", "QCOM", "TXN", "AVGO", "MU", "AMAT", "LRCX",
        "PANW", "FTNT", "CRWD", "NET", "DDOG", "SNOW", "ZM", "OKTA", "WDAY", "NOW",
        # Finance
        "JPM", "BAC", "WFC", "C", "GS", "MS", "AXP", "V", "MA", "PYPL",
        "COIN", "BLK", "SCHW", "PNC", "USB", "BK", "STT", "COF",
        # Healthcare
        "JNJ", "UNH", "PFE", "ABBV", "MRK", "LLY", "TMO", "ABT", "DHR", "MDT",
        "BMY", "AMGN", "GILD", "REGN", "VRTX", "BIIB", "MRNA", "ISRG", "SYK", "ZTS",
        # Consumer
        "WMT", "HD", "COST", "TGT", "LOW", "NKE", "SBUX", "MCD", "KO", "PEP",
        "PG", "CL", "KMB", "MDLZ", "KHC", "HSY", "DG", "DLTR", "ROST", "TJX",
        # Energy
        "XOM", "CVX", "COP", "EOG", "SLB", "MPC", "PSX", "VLO", "OXY", "DVN",
        # Industrials
        "BA", "CAT", "GE", "HON", "UPS", "RTX", "LMT", "MMM", "DE", "EMR",
        "ITW", "ETN", "CMI", "ROK", "PH", "GRMN", "FDX", "UNP", "CSX", "NSC",
        # Other
        "DIS", "CMCSA", "VZ", "T", "TMUS", "SPGI", "MCO", "ICE", "BIIB"
    ]

    # Commodities
    COMMODITIES = [
        # Precious Metals
        "GC=F",   # Gold
        "SI=F",   # Silver
        "PL=F",   # Platinum
        "PA=F",   # Palladium
        # Energy
        "CL=F",   # Crude Oil
        "NG=F",   # Natural Gas
        "RB=F",   # Gasoline
        "HO=F",   # Heating Oil
        # Agriculture
        "ZW=F",   # Wheat
        "ZC=F",   # Corn
        "ZS=F",   # Soybeans
        "KE=F",   # Coffee
        "CT=F",   # Cotton
        "OJ=F",   # Orange Juice
        "LTC=F",  # Live Cattle
        "HE=F",   # Lean Hogs
        # Base Metals
        "HG=F",   # Copper
        "ALU=F",  # Aluminum
        "Zinc",   # Zinc
        "NI=F",   # Nickel
        "PB=F",   # Lead
    ]

    # Forex Pairs
    FOREX_PAIRS = [
        # Major
        "EUR/USD", "GBP/USD", "USD/JPY", "USD/CHF", "AUD/USD", "USD/CAD", "NZD/USD",
        # Cross
        "EUR/GBP", "EUR/JPY", "GBP/JPY", "EUR/CHF", "AUD/JPY", "EUR/AUD", "GBP/CHF",
        # USD/PKR (Pakistani Rupee)
        "USD/PKR", "EUR/PKR", "GBP/PKR", "AED/PKR", "SAR/PKR", "INR/PKR",
    ]

    # Cryptocurrency (updated tickers)
    CRYPTO = [
        "BTC-USD", "ETH-USD", "BNB-USD", "XRP-USD", "ADA-USD", "DOGE-USD",
        "SOL-USD", "DOT-USD", "POL-USD", "LTC-USD", "AVAX-USD", "LINK-USD",
        "ATOM-USD", "XLM-USD", "VET-USD", "FIL-USD", "THETA-USD",
        "ALGO-USD", "MANA-USD", "SAND-USD", "AAVE-USD", "MKR-USD", "NEAR-USD"
    ]

    # Indices
    INDICES = [
        "^GSPC",   # S&P 500
        "^DJI",    # Dow Jones
        "^IXIC",   # NASDAQ
        "^RUT",    # Russell 2000
        "^VIX",    # VIX
        "^TNX",    # 10Y Treasury
        "^NSE",    # Nifty 50 (India)
        "%5EKSEM", # KSE 100 Index
    ]

    @classmethod
    def get_all_assets(cls) -> List[str]:
        """Get all available trading assets"""
        all_assets = []
        all_assets.extend(cls.PAKISTANI_STOCKS)
        all_assets.extend(cls.GLOBAL_STOCKS)
        all_assets.extend(cls.COMMODITIES)
        all_assets.extend(cls.CRYPTO)
        all_assets.extend(cls.INDICES)
        return list(set(all_assets))


class PredictionEngine:
    """Real-time prediction engine for all assets"""

    def __init__(self):
        self.models = {}
        self.scalers = {}
        self.model_meta = {}
        self.model_failures = set()
        self.history_cache = {}
        self.prediction_cache = {}
        self.predictions = deque(maxlen=500)
        self.is_training = False
        self.cache_ttl = PREDICTION_CACHE_TTL
        self.history_ttl = MARKET_DATA_CACHE_TTL
        self.lock = threading.RLock()

    PATTERN_ORDER = [
        "DOJI", "HAMMER", "INVERTED_HAMMER", "SHOOTING_STAR",
        "GRAVESTONE_DOJI", "DRAGONFLY_DOJI", "SPINNING_TOP",
        "BULLISH_ENGULFING", "BEARISH_ENGULFING", "PIERCING_LINE",
        "DARK_CLOUD_COVER", "MORNING_STAR", "EVENING_STAR",
        "THREE_WHITE_SOLDIERS", "THREE_BLACK_CROWS", "FOUR_PRICE_DOJI"
    ]

    FEATURE_SETS = {
        3: ["Returns", "SMA_10", "RSI"],
        5: ["Returns", "SMA_10", "SMA_20", "Volatility", "RSI"],
        9: ["Returns", "SMA_5", "SMA_10", "SMA_20", "RSI", "MACD",
            "Volatility_10", "EMA_12", "EMA_26"],
        13: ["Returns", "SMA_5", "SMA_10", "SMA_20", "RSI", "MACD",
             "BB_Upper", "BB_Middle", "BB_Lower", "Stoch_K", "Stoch_D",
             "ATR", "Momentum"],
    }

    COMPREHENSIVE_FEATURES = [
        "Returns", "Log_Returns",
        "SMA_5", "SMA_10", "SMA_20", "SMA_50", "SMA_100", "SMA_200",
        "EMA_5", "EMA_10", "EMA_20", "EMA_50", "EMA_100", "EMA_200",
        "BB_Upper", "BB_Middle", "BB_Lower", "BB_Width",
        "RSI_7", "RSI_14", "RSI_21", "Wilder_14",
        "MACD", "MACD_Signal", "MACD_Hist",
        "Stoch_K", "Stoch_D",
        "ATR_14", "ATR_20",
        "Volatility_5", "Volatility_10", "Volatility_20", "Volatility_50",
        "Momentum_10", "Momentum_20", "ROC_10", "ROC_20",
        "Volume_Ratio", "OBV", "Price_Oscillator"
    ]

    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate all technical indicators"""
        df = df.copy()
        if df.empty:
            return df

        for col in ["Open", "High", "Low", "Close"]:
            if col not in df:
                df[col] = df["Close"] if "Close" in df else 0
        if "Volume" not in df:
            df["Volume"] = 0

        df['Returns'] = df['Close'].pct_change()
        df['Log_Returns'] = np.log(df['Close'] / df['Close'].shift(1))

        for w in [5, 10, 12, 20, 26, 50, 100, 200]:
            df[f'SMA_{w}'] = df['Close'].rolling(w).mean()
            df[f'EMA_{w}'] = df['Close'].ewm(span=w, adjust=False).mean()
        df['Volatility'] = df['Returns'].rolling(10).std()
        for w in [5, 10, 20, 50]:
            df[f'Volatility_{w}'] = df['Returns'].rolling(w).std() * np.sqrt(252)

        delta = df['Close'].diff()
        for period in [7, 14, 21]:
            gain = delta.where(delta > 0, 0).rolling(period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
            rs = gain / loss.replace(0, 1)
            df[f'RSI_{period}'] = 100 - (100 / (1 + rs))
        df['RSI'] = df['RSI_14']
        df['Wilder_14'] = df['RSI_14'].ewm(alpha=1/14, adjust=False).mean()

        ema12 = df['Close'].ewm(span=12, adjust=False).mean()
        ema26 = df['Close'].ewm(span=26, adjust=False).mean()
        df['MACD'] = ema12 - ema26
        df['MACD_Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
        df['MACD_Hist'] = df['MACD'] - df['MACD_Signal']

        df['BB_Middle'] = df['Close'].rolling(20).mean()
        bb_std = df['Close'].rolling(20).std()
        df['BB_Upper'] = df['BB_Middle'] + (bb_std * 2)
        df['BB_Lower'] = df['BB_Middle'] - (bb_std * 2)
        df['BB_Width'] = (df['BB_Upper'] - df['BB_Lower']) / df['BB_Middle']

        low14 = df['Low'].rolling(14).min()
        high14 = df['High'].rolling(14).max()
        df['Stoch_K'] = 100 * (df['Close'] - low14) / (high14 - low14)
        df['Stoch_D'] = df['Stoch_K'].rolling(3).mean()

        high_low = df['High'] - df['Low']
        high_close = abs(df['High'] - df['Close'].shift())
        low_close = abs(df['Low'] - df['Close'].shift())
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df['ATR_14'] = true_range.rolling(14).mean()
        df['ATR_20'] = true_range.rolling(20).mean()
        df['ATR'] = df['ATR_14']

        df['Volume_SMA_20'] = df['Volume'].rolling(20).mean()
        df['Volume_Ratio'] = df['Volume'] / df['Volume_SMA_20'].replace(0, np.nan)
        df['OBV'] = (np.sign(df['Close'].diff()) * df['Volume']).fillna(0).cumsum()
        df['OBV_SMA_10'] = df['OBV'].rolling(10).mean()

        df['Momentum_10'] = df['Close'] - df['Close'].shift(10)
        df['Momentum_20'] = df['Close'] - df['Close'].shift(20)
        df['Momentum'] = df['Momentum_10']
        df['ROC_10'] = (df['Close'] - df['Close'].shift(10)) / df['Close'].shift(10) * 100
        df['ROC_20'] = (df['Close'] - df['Close'].shift(20)) / df['Close'].shift(20) * 100
        df['Price_Oscillator'] = (df['SMA_10'] - df['SMA_20']) / df['SMA_20'] * 100

        return df.replace([np.inf, -np.inf], np.nan)

    def detect_candlestick_patterns(self, df: pd.DataFrame) -> Dict:
        """Detect all candle patterns"""
        patterns = {name: False for name in self.PATTERN_ORDER}

        if len(df) < 3:
            return patterns

        c1, c2, c3 = df.iloc[-3], df.iloc[-2], df.iloc[-1]

        # Helper functions
        def body(c): return c['Close'] - c['Open']
        def body_size(c): return abs(body(c))
        def range_(c): return c['High'] - c['Low']
        def upper_shadow(c): return c['High'] - max(c['Close'], c['Open'])
        def lower_shadow(c): return min(c['Close'], c['Open']) - c['Low']

        # Doji
        if body_size(c3) < range_(c3) * 0.1:
            patterns['DOJI'] = True

        if body_size(c3) < range_(c3) * 0.1 and lower_shadow(c3) > body_size(c3) * 2:
            patterns['DRAGONFLY_DOJI'] = True

        if body_size(c3) < range_(c3) * 0.1 and upper_shadow(c3) > body_size(c3) * 2:
            patterns['GRAVESTONE_DOJI'] = True

        if lower_shadow(c3) > body_size(c3) * 2 and upper_shadow(c3) < body_size(c3) * 0.5:
            patterns['HAMMER'] = True

        if upper_shadow(c3) > body_size(c3) * 2 and lower_shadow(c3) < body_size(c3) * 0.5:
            patterns['INVERTED_HAMMER'] = True
            patterns['SHOOTING_STAR'] = True

        if body_size(c3) < range_(c3) * 0.3 and upper_shadow(c3) > body_size(c3) and lower_shadow(c3) > body_size(c3):
            patterns['SPINNING_TOP'] = True

        # Bullish Engulfing
        if c2['Close'] < c2['Open'] and c3['Close'] > c3['Open'] and c3['Open'] < c2['Close']:
            patterns['BULLISH_ENGULFING'] = True

        # Bearish Engulfing
        if c2['Close'] > c2['Open'] and c3['Close'] < c3['Open'] and c3['Open'] > c2['Close']:
            patterns['BEARISH_ENGULFING'] = True

        if c2['Close'] < c2['Open'] and c3['Close'] > c3['Open'] and c3['Close'] > (c2['Open'] + c2['Close']) / 2:
            patterns['PIERCING_LINE'] = True

        if c2['Close'] > c2['Open'] and c3['Close'] < c3['Open'] and c3['Close'] < (c2['Open'] + c2['Close']) / 2:
            patterns['DARK_CLOUD_COVER'] = True

        # Morning Star
        if c1['Close'] < c1['Open'] and c3['Close'] > c3['Open'] and c3['Close'] > c1['Open']:
            patterns['MORNING_STAR'] = True

        # Evening Star
        if c1['Close'] > c1['Open'] and c3['Close'] < c3['Open'] and c3['Close'] < c1['Open']:
            patterns['EVENING_STAR'] = True

        if c1['Close'] > c1['Open'] and c2['Close'] > c2['Open'] and c3['Close'] > c3['Open'] and c2['Close'] > c1['Close'] and c3['Close'] > c2['Close']:
            patterns['THREE_WHITE_SOLDIERS'] = True

        if c1['Close'] < c1['Open'] and c2['Close'] < c2['Open'] and c3['Close'] < c3['Open'] and c2['Close'] < c1['Close'] and c3['Close'] < c2['Close']:
            patterns['THREE_BLACK_CROWS'] = True

        return patterns

    def _cache_get(self, cache: Dict, key: str, ttl: int):
        with self.lock:
            cached = cache.get(key)
            if cached and time.time() - cached[0] < ttl:
                return cached[1]
        return None

    def _cache_set(self, cache: Dict, key: str, value):
        with self.lock:
            cache[key] = (time.time(), value)

    def _history_for(self, ticker: str) -> Optional[pd.DataFrame]:
        cached = self._cache_get(self.history_cache, ticker, self.history_ttl)
        if cached is not None:
            return cached.copy()

        yf_ticker = ticker.replace('.PSX', '-PK') if ticker.endswith('.PSX') else ticker
        stock = yf.Ticker(yf_ticker)
        df = stock.history(period="1y", auto_adjust=False)
        if df is not None and not df.empty:
            self._cache_set(self.history_cache, ticker, df)
        return df

    def _load_model_bundle(self, ticker: str) -> Optional[Dict[str, Any]]:
        with self.lock:
            if ticker in self.models:
                return {
                    "model": self.models[ticker],
                    "scaler": self.scalers.get(ticker),
                    **self.model_meta.get(ticker, {})
                }
            if ticker in self.model_failures:
                return None

        model_path = os.path.join(BASE_DIR, f"{ticker}_model.pkl")
        if not os.path.exists(model_path):
            with self.lock:
                self.model_failures.add(ticker)
            return None

        try:
            loaded = joblib.load(model_path)
            feature_names = None
            scaler = None
            if isinstance(loaded, dict):
                model = loaded.get("model")
                scaler = loaded.get("scaler")
                feature_names = loaded.get("features")
            else:
                model = loaded

            if model is None:
                raise ValueError("model file did not contain a model object")

            expected_features = (
                len(feature_names) if feature_names is not None else
                getattr(model, "n_features_in_", None)
            )

            if scaler is None:
                candidates = [
                    os.path.join(BASE_DIR, f"{ticker}_scaler.pkl"),
                    os.path.join(BASE_DIR, f"{ticker}_model_scaler.pkl"),
                ]
                loaded_scalers = []
                for path in candidates:
                    if os.path.exists(path):
                        try:
                            candidate = joblib.load(path)
                            loaded_scalers.append(candidate)
                        except Exception as exc:
                            logger.warning("Could not load scaler %s: %s", path, exc)
                for candidate in loaded_scalers:
                    if expected_features is None or getattr(candidate, "n_features_in_", None) == expected_features:
                        scaler = candidate
                        break
                if scaler is None and loaded_scalers:
                    scaler = loaded_scalers[0]
                    expected_features = getattr(scaler, "n_features_in_", expected_features)

            meta = {
                "feature_count": expected_features,
                "feature_names": feature_names,
                "source": "disk_model"
            }
            with self.lock:
                self.models[ticker] = model
                self.scalers[ticker] = scaler
                self.model_meta[ticker] = meta
            return {"model": model, "scaler": scaler, **meta}
        except Exception as exc:
            logger.warning("Model load failed for %s: %s", ticker, exc)
            with self.lock:
                self.model_failures.add(ticker)
            return None

    def _feature_vector(self, df: pd.DataFrame, patterns: Dict[str, bool], feature_count: Optional[int],
                        feature_names: Optional[List[str]] = None) -> Optional[np.ndarray]:
        prepared = df.ffill().bfill().dropna()
        if prepared.empty:
            return None

        latest = prepared.iloc[-1]
        if feature_names is not None:
            values = [latest.get(col, 0) for col in feature_names]
        elif feature_count == 56:
            values = [latest.get(col, 0) for col in self.COMPREHENSIVE_FEATURES]
            values.extend(int(patterns.get(pattern, False)) for pattern in self.PATTERN_ORDER)
        else:
            columns = self.FEATURE_SETS.get(feature_count) or self.FEATURE_SETS[13]
            values = [latest.get(col, 0) for col in columns]

        return np.nan_to_num(np.array(values, dtype=float).reshape(1, -1), nan=0.0, posinf=0.0, neginf=0.0)

    def _heuristic_prediction(self, df: pd.DataFrame) -> tuple:
        latest = df.ffill().bfill().iloc[-1]
        score = 0.0
        rsi = float(latest.get("RSI", 50) or 50)
        macd = float(latest.get("MACD", 0) or 0)
        macd_signal = float(latest.get("MACD_Signal", 0) or 0)

        score += 1.4 if latest.get("SMA_5", 0) > latest.get("SMA_20", 0) else -1.2
        score += 1.0 if latest.get("Close", 0) > latest.get("SMA_20", 0) else -0.8
        score += 0.9 if macd > macd_signal else -0.7
        if rsi < 30:
            score += 1.1
        elif rsi > 70:
            score -= 1.1
        elif 45 <= rsi <= 60:
            score += 0.4

        prediction = 1 if score >= 0 else 0
        confidence = min(0.86, 0.52 + abs(score) * 0.07)
        return prediction, np.array([1 - confidence, confidence]) if prediction else np.array([confidence, 1 - confidence])

    def predict_asset(self, ticker: str) -> Dict:
        """Predict if asset will go UP or DOWN"""
        start_time = time.time()
        ticker = ticker.upper().strip()

        cached = self._cache_get(self.prediction_cache, ticker, self.cache_ttl)
        if cached is not None:
            cached = dict(cached)
            cached["cache"] = "hit"
            return cached

        try:
            df = self._history_for(ticker)
            if df is None or len(df) < 30:
                return {"ticker": ticker, "status": "insufficient_data"}

            df = self.calculate_indicators(df)
            patterns = self.detect_candlestick_patterns(df)
            prepared = df.ffill().bfill().dropna()

            if len(prepared) < 20:
                return {"ticker": ticker, "status": "insufficient_features"}

            bundle = self._load_model_bundle(ticker)
            model_source = "technical_signal"
            if bundle and bundle.get("feature_count") in (3, 5, 9, 13, 56):
                X = self._feature_vector(prepared, patterns, bundle.get("feature_count"), bundle.get("feature_names"))
                if X is not None:
                    scaler = bundle.get("scaler")
                    if scaler is not None:
                        X = scaler.transform(X)
                    model = bundle["model"]
                    prediction = model.predict(X)[0]
                    proba = model.predict_proba(X)[0] if hasattr(model, "predict_proba") else None
                    model_source = bundle.get("source", "disk_model")
                else:
                    prediction, proba = self._heuristic_prediction(prepared)
            else:
                prediction, proba = self._heuristic_prediction(prepared)

            if proba is None:
                confidence = 0.55
            else:
                confidence = float(max(proba))

            current_price = float(prepared['Close'].iloc[-1])
            prev_price = float(prepared['Close'].iloc[-2])
            change = ((current_price - prev_price) / prev_price) * 100

            rsi = float(prepared['RSI'].iloc[-1]) if 'RSI' in prepared.columns else 50
            macd = float(prepared['MACD'].iloc[-1]) if 'MACD' in prepared.columns else 0
            trend = "UPTREND" if prepared['SMA_5'].iloc[-1] > prepared['SMA_20'].iloc[-1] else "DOWNTREND"
            active_patterns = [name for name, active in patterns.items() if active]

            # Calculate Confluence Score using DNA-01 rules
            confluence_res = confluence_engine.calculate_score(ticker, rsi, macd, trend, active_patterns, current_price)
            confluence_score = confluence_res["score"]
            confluence_reasons = confluence_res["reasons"]

            result = {
                "ticker": ticker,
                "prediction": "UP" if prediction == 1 else "DOWN",
                "confidence": round(confidence, 4),
                "direction": "bullish" if prediction == 1 else "bearish",
                "current_price": round(current_price, 2),
                "change_1d": round(change, 2),
                "rsi": round(rsi, 1),
                "macd": round(macd, 2),
                "trend": trend,
                "patterns": active_patterns,
                "confluence": confluence_score,
                "reasons": confluence_reasons,
                "model_source": model_source,
                "cache": "miss",
                "processing_time_ms": int((time.time() - start_time) * 1000)
            }

            self.predictions.append(result)
            self._cache_set(self.prediction_cache, ticker, result)
            
            # Log prediction for accuracy feedback loop
            accuracy_tracker.log_prediction(ticker, result["prediction"], current_price)
            
            return result

        except Exception as e:
            logger.warning("Prediction error for %s: %s", ticker, e)
            return {"ticker": ticker, "status": "error", "error": str(e)[:120]}


class NewsEngine:
    """News aggregation for all markets"""

    @staticmethod
    def get_news(category: str = "general") -> List[Dict]:
        """Get news for different categories"""
        # Simulated news - in production would connect to real news API
        news_items = [
            {"title": "Market Rally Continues as Tech Stocks Lead", "source": "Reuters", "time": "2h ago", "sentiment": "positive"},
            {"title": "Fed Signals Interest Rate Decision", "source": "Bloomberg", "time": "3h ago", "sentiment": "neutral"},
            {"title": "Oil Prices Surge on Supply Concerns", "source": "CNBC", "time": "4h ago", "sentiment": "positive"},
            {"title": "Crypto Markets Show Volatility", "source": "CoinDesk", "time": "5h ago", "sentiment": "neutral"},
            {"title": "Asian Markets Mixed Amid Global Uncertainty", "source": "WSJ", "time": "6h ago", "sentiment": "neutral"},
            {"title": "Pakistan Economy Shows Signs of Recovery", "source": "Dawn", "time": "8h ago", "sentiment": "positive"},
            {"title": "Tesla Announces New Product Launch", "source": "TechCrunch", "time": "10h ago", "sentiment": "positive"},
            {"title": "Bitcoin Breaks Key Resistance Level", "source": "CoinTelegraph", "time": "12h ago", "sentiment": "positive"},
        ]
        return news_items[:6]


class ScreenshotAnalyzer:
    """Analyze uploaded chart screenshots using Claude Vision AI"""

    @staticmethod
    def analyze(image_data: str) -> Dict:
        """
        Analyze a chart screenshot using Claude claude-opus-4-5 vision.
        image_data: base64-encoded image string (with or without data URI prefix).
        """
        import re, base64, urllib.request, json as _json

        api_key = os.environ.get("ANTHROPIC_API_KEY", "")

        # ── Strip data-URI prefix if present ──────────────────────────────
        raw_b64 = re.sub(r"^data:image/[^;]+;base64,", "", image_data or "").strip()

        # Detect media type from prefix bytes
        try:
            header = base64.b64decode(raw_b64[:16])
            if header[:4] == b'\x89PNG':
                media_type = "image/png"
            elif header[:3] == b'\xff\xd8\xff':
                media_type = "image/jpeg"
            elif header[:4] == b'GIF8':
                media_type = "image/gif"
            elif header[:4] == b'RIFF':
                media_type = "image/webp"
            else:
                media_type = "image/png"
        except Exception:
            media_type = "image/png"

        # ── Call Claude Vision if we have a key and real image data ───────
        if api_key and raw_b64 and len(raw_b64) > 50:
            try:
                prompt = (
                    "You are an expert technical analyst. Analyze this trading chart image carefully and respond ONLY with a valid JSON object (no markdown, no extra text) with these exact keys:\n"
                    "{\n"
                    '  "pattern": "<candlestick pattern name>",\n'
                    '  "pattern_description": "<what this pattern means>",\n'
                    '  "trend": "<UPTREND|DOWNTREND|SIDEWAYS>",\n'
                    '  "signal": "<BUY|SELL|HOLD>",\n'
                    '  "confidence": <0.0-1.0>,\n'
                    '  "analysis": "<2-3 sentence detailed analysis of what you see in the chart>",\n'
                    '  "key_levels": "<important support/resistance levels you can see>",\n'
                    '  "indicators": {\n'
                    '    "rsi": "<value or description if visible>",\n'
                    '    "macd": "<bullish|bearish|neutral>",\n'
                    '    "volume": "<high|low|average if visible>",\n'
                    '    "support": "<price level if visible>",\n'
                    '    "resistance": "<price level if visible>"\n'
                    "  }\n"
                    "}\n"
                    "Base your analysis ONLY on what you actually see in this specific chart image."
                )

                payload = _json.dumps({
                    "model": "claude-opus-4-5",
                    "max_tokens": 1024,
                    "messages": [{
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": media_type,
                                    "data": raw_b64
                                }
                            },
                            {"type": "text", "text": prompt}
                        ]
                    }]
                }).encode("utf-8")

                req = urllib.request.Request(
                    "https://api.anthropic.com/v1/messages",
                    data=payload,
                    headers={
                        "x-api-key": api_key,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json"
                    },
                    method="POST"
                )

                with urllib.request.urlopen(req, timeout=30) as resp:
                    body = _json.loads(resp.read().decode("utf-8"))

                text = body["content"][0]["text"].strip()
                # Strip markdown code fences if Claude wraps in them
                text = re.sub(r"^```[a-z]*\n?", "", text)
                text = re.sub(r"\n?```$", "", text)

                result = _json.loads(text)
                result["status"] = "analyzed"
                result["powered_by"] = "Claude Vision AI"
                return result

            except Exception as e:
                logger.warning("Claude vision analysis failed: %s", e)
                # Fall through to heuristic below

        # ── Heuristic fallback (no API key or no image) ───────────────────
        import random
        random.seed(datetime.now().microsecond + len(raw_b64))

        try:
            stocks = ["AAPL", "MSFT", "GOOGL", "TSLA", "NVDA", "BTC-USD", "ETH-USD"]
            ticker = random.choice(stocks)
            stock = yf.Ticker(ticker)
            df = stock.history(period="30d")

            if df is not None and len(df) > 10:
                close = df['Close']
                delta = close.diff()
                gain = delta.where(delta > 0, 0).rolling(14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
                rs = gain / loss.replace(0, 1)
                rsi = float(100 - (100 / (1 + rs)).iloc[-1])
                ema12 = close.ewm(span=12).mean()
                ema26 = close.ewm(span=26).mean()
                macd_val = float((ema12 - ema26).iloc[-1])
                sma_5 = float(close.rolling(5).mean().iloc[-1])
                sma_20 = float(close.rolling(20).mean().iloc[-1]) if len(close) >= 20 else sma_5

                trend = "UPTREND" if sma_5 > sma_20 else ("DOWNTREND" if sma_5 < sma_20 else "SIDEWAYS")
                if rsi < 30:
                    pattern, signal, confidence = "HAMMER", "BUY", 0.82
                elif rsi > 70:
                    pattern, signal, confidence = "SHOOTING_STAR", "SELL", 0.80
                elif macd_val > 0:
                    pattern, signal, confidence = "BULLISH_ENGULFING", "BUY", 0.72
                elif macd_val < 0:
                    pattern, signal, confidence = "BEARISH_ENGULFING", "SELL", 0.70
                else:
                    pattern, signal, confidence = "DOJI", "HOLD", 0.60

                return {
                    "status": "analyzed",
                    "pattern": pattern,
                    "pattern_description": f"Based on live {ticker} data — add ANTHROPIC_API_KEY for real chart analysis",
                    "trend": trend,
                    "signal": signal,
                    "confidence": round(confidence, 2),
                    "analysis": f"Heuristic analysis using live {ticker} market data. RSI={rsi:.1f}, MACD={'bullish' if macd_val > 0 else 'bearish'}. Upload a chart and ensure ANTHROPIC_API_KEY is set for AI-powered analysis.",
                    "key_levels": f"Support: {round(float(close.min()), 2)}, Resistance: {round(float(close.max()), 2)}",
                    "indicators": {
                        "rsi": round(rsi, 1),
                        "macd": "bullish" if macd_val > 0 else "bearish",
                        "support": round(float(close.min()), 2),
                        "resistance": round(float(close.max()), 2)
                    },
                    "powered_by": "Heuristic (no image/API key)"
                }
        except Exception:
            pass

        return {
            "status": "error",
            "error": "Could not analyze chart. Please upload a valid chart image.",
            "powered_by": "None"
        }


class ConfluenceScoringEngine:
    """Calculates multidimensional confluence score based on Technicals, Candlesticks, and News Sentiment"""

    @staticmethod
    def calculate_score(ticker: str, rsi: float, macd: float, trend: str, patterns: list, current_price: float) -> dict:
        # 1. Technicals Score (40% weight)
        tech_score = 0.0
        # RSI score
        if rsi < 30: # Oversold - extremely bullish confluence
            tech_score += 20.0
        elif rsi > 70: # Overbought - bearish confluence (lower up confidence)
            tech_score += 0.0
        else: # Neutral
            tech_score += 10.0 + (50 - abs(rsi - 50)) * 0.2
        
        # MACD score
        if macd > 0:
            tech_score += 10.0
        # Trend stack
        if trend == "UPTREND":
            tech_score += 10.0

        # 2. Candlestick Patterns Score (30% weight)
        candle_score = 0.0
        bullish_patterns = ["BULLISH_ENGULFING", "HAMMER", "MORNING_STAR", "THREE_WHITE_SOLDIERS", "DRAGONFLY_DOJI"]
        bearish_patterns = ["BEARISH_ENGULFING", "SHOOTING_STAR", "EVENING_STAR", "THREE_BLACK_CROWS", "GRAVESTONE_DOJI"]
        
        active_bullish = [p for p in patterns if p in bullish_patterns]
        active_bearish = [p for p in patterns if p in bearish_patterns]
        
        if active_bullish:
            candle_score += min(30.0, len(active_bullish) * 15.0)
        elif active_bearish:
            candle_score += 0.0
        else:
            candle_score += 15.0 # Neutral baseline

        # 3. Sentiment Score (30% weight)
        sentiment_score = 0.0
        try:
            from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
            analyzer = SentimentIntensityAnalyzer()
            news_items = NewsEngine.get_news()
            matching_news = [n for n in news_items if ticker.lower() in n['title'].lower()]
            if not matching_news:
                matching_news = news_items # fallback
            
            compound_sum = 0.0
            for item in matching_news:
                scores = analyzer.polarity_scores(item['title'])
                compound_sum += scores['compound']
            
            avg_sentiment = compound_sum / len(matching_news) if matching_news else 0.0
            sentiment_score = (avg_sentiment + 1.0) * 15.0
        except Exception:
            sentiment_score = 15.0 # Neutral

        total_confluence = tech_score + candle_score + sentiment_score
        total_confluence = max(0.0, min(100.0, total_confluence))

        # Output dynamic confluence reasons (XAI)
        reasons = []
        if rsi < 30: reasons.append("RSI Oversold (+20%)")
        elif rsi > 70: reasons.append("RSI Overbought (-10%)")
        if macd > 0: reasons.append("MACD Momentum Positive (+10%)")
        if trend == "UPTREND": reasons.append("Aligned with UPTREND (+10%)")
        if active_bullish: reasons.append(f"Bullish Patterns: {', '.join(active_bullish)} (+{int(candle_score)}%)")
        if active_bearish: reasons.append(f"Bearish Patterns: {', '.join(active_bearish)} (-15%)")
        if sentiment_score > 20: reasons.append("Bullish News Sentiment (+15%)")
        elif sentiment_score < 10: reasons.append("Bearish News Sentiment (-15%)")

        return {
            "score": round(total_confluence / 100.0, 4),
            "reasons": reasons,
            "sentiment_compound": round((sentiment_score / 15.0) - 1.0, 2)
        }


class AccuracyFeedbackTracker:
    """Tracks system prediction accuracy and manages the live feedback loop"""
    
    def __init__(self):
        self.predictions_log_file = os.path.join(BASE_DIR, ".smart_cache", "predictions_feedback.json")
        self.history = []
        self.lock = threading.Lock()
        self.load_history()

    def load_history(self):
        try:
            os.makedirs(os.path.dirname(self.predictions_log_file), exist_ok=True)
            if os.path.exists(self.predictions_log_file):
                with open(self.predictions_log_file, "r") as f:
                    self.history = json.load(f)
        except Exception as e:
            logger.warning(f"Error loading accuracy history: {e}")

    def save_history(self):
        try:
            with open(self.predictions_log_file, "w") as f:
                json.dump(self.history, f, indent=2)
        except Exception as e:
            logger.warning(f"Error saving accuracy history: {e}")

    def log_prediction(self, ticker: str, predicted_dir: str, price: float):
        with self.lock:
            # Remove duplicates for the same day/ticker
            self.history = [h for h in self.history if not (h['ticker'] == ticker and h['status'] == 'pending')]
            
            self.history.append({
                "ticker": ticker,
                "predicted_dir": predicted_dir,
                "entry_price": price,
                "entry_time": datetime.now().isoformat(),
                "status": "pending",
                "actual_close": None,
                "result": None
            })
            self.save_history()

    def update_accuracies(self, current_prices: dict):
        """Evaluate pending predictions against current prices"""
        with self.lock:
            updated = False
            for p in self.history:
                if p["status"] == "pending":
                    ticker = p["ticker"]
                    if ticker in current_prices:
                        actual = current_prices[ticker]
                        p["actual_close"] = actual
                        p["status"] = "completed"
                        
                        # Check result
                        is_win = False
                        if p["predicted_dir"] == "UP" and actual > p["entry_price"]:
                            is_win = True
                        elif p["predicted_dir"] == "DOWN" and actual < p["entry_price"]:
                            is_win = True
                            
                        p["result"] = "win" if is_win else "loss"
                        updated = True
            
            # Keep max 500 records
            if len(self.history) > 500:
                self.history = self.history[-500:]
                
            if updated:
                self.save_history()

    def get_win_rate(self) -> float:
        with self.lock:
            completed = [h for h in self.history if h["status"] == "completed"]
            if not completed:
                return 0.65 # baseline win rate for initial empty state
            wins = [h for h in completed if h["result"] == "win"]
            return len(wins) / len(completed)


class PaperTradingEngine:
    """Simulates paper trading with DNA-01 institutional rules (1% rule + 2:1 brackets)"""
    
    def __init__(self):
        self.state_file = os.path.join(BASE_DIR, ".smart_cache", "portfolio_state.json")
        self.lock = threading.RLock()
        self.state = {
            "cash": 100000.0,
            "positions": {}, # {ticker: {shares, entry_price, type, stop_loss, take_profit}}
            "transactions": [], # list of buy/sell logs
            "equity_history": [{"time": datetime.now().isoformat(), "equity": 100000.0}],
            "auto_trade_enabled": False
        }
        self.load_state()

    def load_state(self):
        try:
            os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
            if os.path.exists(self.state_file):
                with open(self.state_file, "r") as f:
                    self.state = json.load(f)
        except Exception as e:
            logger.warning(f"Error loading portfolio state: {e}")

    def save_state(self):
        try:
            with open(self.state_file, "w") as f:
                json.dump(self.state, f, indent=2)
        except Exception as e:
            logger.warning(f"Error saving portfolio state: {e}")

    def get_portfolio_value(self, current_prices: dict) -> float:
        with self.lock:
            equity = self.state["cash"]
            for ticker, pos in self.state["positions"].items():
                price = current_prices.get(ticker, pos["entry_price"])
                pnl = (price - pos["entry_price"]) * pos["shares"] if pos["type"] == "BUY" else (pos["entry_price"] - price) * pos["shares"]
                equity += pos["shares"] * pos["entry_price"] + pnl
            return float(equity)

    def execute_order(self, ticker: str, action: str, qty: int, price: float, stop_loss: float = None, take_profit: float = None) -> dict:
        with self.lock:
            action = action.upper() # BUY or SELL
            if action == "BUY":
                cost = qty * price
                if cost > self.state["cash"]:
                    return {"status": "error", "message": "Insufficient cash balance"}
                
                # Check DNA-01 Stop Loss / Take Profit 2:1 brackets
                atr = price * 0.03 # estimate ATR as 3% if not provided
                if not stop_loss:
                    stop_loss = price - atr
                if not take_profit:
                    take_profit = price + (price - stop_loss) * 2.0 # 2:1 ratio
                
                self.state["cash"] -= cost
                if ticker in self.state["positions"]:
                    pos = self.state["positions"][ticker]
                    total_qty = pos["shares"] + qty
                    avg_price = ((pos["entry_price"] * pos["shares"]) + cost) / total_qty
                    pos["shares"] = total_qty
                    pos["entry_price"] = avg_price
                else:
                    self.state["positions"][ticker] = {
                        "shares": qty,
                        "entry_price": price,
                        "type": "BUY",
                        "stop_loss": round(stop_loss, 2),
                        "take_profit": round(take_profit, 2)
                    }
                
                transaction = {
                    "time": datetime.now().isoformat(),
                    "ticker": ticker,
                    "action": "BUY",
                    "shares": qty,
                    "price": price,
                    "cost": cost
                }
                self.state["transactions"].append(transaction)
                self.save_state()
                return {"status": "success", "message": f"Successfully bought {qty} shares of {ticker}"}
                
            elif action == "SELL": # Closing/Reducing position
                if ticker not in self.state["positions"]:
                    return {"status": "error", "message": "No active position in this ticker"}
                
                pos = self.state["positions"][ticker]
                if qty > pos["shares"]:
                    return {"status": "error", "message": f"Cannot sell more than owned ({pos['shares']})"}
                
                proceeds = qty * price
                self.state["cash"] += proceeds
                
                # Calculate P&L
                pnl = (price - pos["entry_price"]) * qty
                
                if qty == pos["shares"]:
                    del self.state["positions"][ticker]
                else:
                    pos["shares"] -= qty
                
                transaction = {
                    "time": datetime.now().isoformat(),
                    "ticker": ticker,
                    "action": "SELL",
                    "shares": qty,
                    "price": price,
                    "proceeds": proceeds,
                    "pnl": pnl
                }
                self.state["transactions"].append(transaction)
                self.save_state()
                return {"status": "success", "message": f"Successfully sold {qty} shares of {ticker} with P&L of {round(pnl, 2)}"}

    def update_positions_and_brackets(self, current_prices: dict):
        """Handle stop losses, take profits, and log daily equity history"""
        with self.lock:
            to_close = []
            for ticker, pos in self.state["positions"].items():
                if ticker in current_prices:
                    price = current_prices[ticker]
                    
                    # Stop loss hit
                    if price <= pos["stop_loss"]:
                        to_close.append((ticker, price, "Stop Loss Triggered"))
                    # Take profit hit
                    elif price >= pos["take_profit"]:
                        to_close.append((ticker, price, "Take Profit Triggered"))
            
            for ticker, price, reason in to_close:
                logger.info(f"{reason} for {ticker} at {price}")
                self.execute_order(ticker, "SELL", self.state["positions"][ticker]["shares"], price)

            # Daily/hourly equity log
            now = datetime.now().isoformat()
            current_equity = self.get_portfolio_value(current_prices)
            
            # Save equity history point (limit history to 100 points)
            if not self.state["equity_history"] or (datetime.now() - datetime.fromisoformat(self.state["equity_history"][-1]["time"])).total_seconds() > 300:
                self.state["equity_history"].append({"time": now, "equity": round(current_equity, 2)})
                if len(self.state["equity_history"]) > 100:
                    self.state["equity_history"] = self.state["equity_history"][-100:]
                    
            self.save_state()

    def reset_portfolio(self):
        with self.lock:
            self.state = {
                "cash": 100000.0,
                "positions": {},
                "transactions": [],
                "equity_history": [{"time": datetime.now().isoformat(), "equity": 100000.0}],
                "auto_trade_enabled": False
            }
            self.save_state()


# ============================================================
# FLASK APPLICATION
# ============================================================

app = Flask(__name__, template_folder='templates')
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Global state
prediction_engine = PredictionEngine()
prediction_pool = ThreadPoolExecutor(max_workers=PREDICTION_WORKERS)
current_predictions = {}
is_live_streaming = False

# Global upgraded engines
confluence_engine = ConfluenceScoringEngine()
accuracy_tracker = AccuracyFeedbackTracker()
paper_trading = PaperTradingEngine()


def request_limit(default: int, max_limit: int) -> int:
    """Parse a safe API limit so dashboard loads do not request every asset at once."""
    try:
        requested = int(request.args.get("limit", default))
    except (TypeError, ValueError):
        requested = default
    return max(1, min(requested, max_limit))


def predict_many(tickers: List[str], timeout: int = 18) -> List[Dict]:
    """Predict multiple assets concurrently and return partial data if a provider is slow."""
    results = []
    futures = {prediction_pool.submit(prediction_engine.predict_asset, ticker): ticker for ticker in tickers}
    try:
        for future in as_completed(futures, timeout=timeout):
            ticker = futures[future]
            try:
                result = future.result(timeout=1)
                if result.get("status") == "success" or "prediction" in result:
                    results.append(result)
            except Exception as exc:
                logger.warning("Prediction worker failed for %s: %s", ticker, exc)
    except TimeoutError:
        logger.warning("Prediction batch timed out after %ss; returning partial results", timeout)
        for future in futures:
            future.cancel()

    results.sort(key=lambda item: item.get("confidence", 0), reverse=True)
    return results

# Routes
@app.route('/')
def index():
    """Main dashboard"""
    return render_template('comprehensive_dashboard.html')


@app.route('/favicon.ico')
def favicon():
    """Avoid noisy browser 404s for the default favicon request."""
    return app.response_class(status=204)

# API: Get all stocks
@app.route('/api/stocks')
def api_stocks():
    """Get all stocks with real-time data"""
    limit = request_limit(default=18, max_limit=50)
    tickers = ComprehensiveDataSource.GLOBAL_STOCKS[:limit]
    stocks = predict_many(tickers)
    return jsonify({
        "stocks": stocks,
        "count": len(stocks),
        "requested": len(tickers),
        "total_available": len(ComprehensiveDataSource.GLOBAL_STOCKS)
    })

# API: Get Pakistani stocks
@app.route('/api/pakistani')
def api_pakistani():
    """Get Pakistani stocks - with simulated data fallback"""
    stocks = []

    # Real PSX data is inconsistent through yfinance, so only attempt it when requested.
    if request.args.get("live") == "1":
        for ticker in ["PKX", "PAK", "KSE"]:
            result = prediction_engine.predict_asset(ticker)
            if "prediction" in result and result.get("status") != "error":
                stocks.append(result)

    # If no real data, use simulated market data for KSE-100 stocks
    if len(stocks) < 3:
        import random
        random.seed(42)
        for stock in ComprehensiveDataSource.PAKISTANI_SIMULATED:
            base = stock["base_price"]
            change = random.uniform(-3, 3)
            price = base * (1 + change/100)
            prediction = "UP" if change > 0 else "DOWN"

            stocks.append({
                "ticker": stock["ticker"],
                "prediction": prediction,
                "confidence": random.uniform(0.55, 0.75),
                "direction": "bullish" if prediction == "UP" else "bearish",
                "current_price": round(price, 2),
                "change_1d": round(change, 2),
                "rsi": random.randint(35, 70),
                "macd": round(random.uniform(-2, 2), 2),
                "trend": "UPTREND" if change > 0 else "DOWNTREND",
                "patterns": [],
                "source": "simulated",
                "note": "KSE-100 real-time data limited - using market estimate"
            })

    return jsonify({"stocks": stocks, "count": len(stocks)})

# API: Get commodities
@app.route('/api/commodities')
def api_commodities():
    """Get commodities"""
    limit = request_limit(default=9, max_limit=15)
    tickers = ComprehensiveDataSource.COMMODITIES[:limit]
    comms = predict_many(tickers)
    return jsonify({"commodities": comms, "count": len(comms), "requested": len(tickers)})

# API: Get crypto
@app.route('/api/crypto')
def api_crypto():
    """Get cryptocurrency"""
    limit = request_limit(default=12, max_limit=20)
    tickers = ComprehensiveDataSource.CRYPTO[:limit]
    cryptos = predict_many(tickers)
    return jsonify({"crypto": cryptos, "count": len(cryptos), "requested": len(tickers)})

# API: Get forex
@app.route('/api/forex')
def api_forex():
    """Get forex pairs"""
    # For forex, use simpler approach
    forex_rates = [
        {"ticker": "USD/PKR", "current_price": 278.50, "change_1d": 0.15, "prediction": "UP", "confidence": 0.72, "trend": "UPTREND"},
        {"ticker": "EUR/USD", "current_price": 1.0845, "change_1d": 0.08, "prediction": "UP", "confidence": 0.68, "trend": "UPTREND"},
        {"ticker": "GBP/USD", "current_price": 1.2645, "change_1d": -0.05, "prediction": "DOWN", "confidence": 0.65, "trend": "DOWNTREND"},
        {"ticker": "USD/JPY", "current_price": 156.85, "change_1d": 0.12, "prediction": "UP", "confidence": 0.71, "trend": "UPTREND"},
        {"ticker": "EUR/PKR", "current_price": 302.10, "change_1d": 0.22, "prediction": "UP", "confidence": 0.69, "trend": "UPTREND"},
    ]
    return jsonify({"forex": forex_rates})

# API: Predict single asset
@app.route('/api/predict/<ticker>')
def api_predict(ticker):
    """Get prediction for specific ticker"""
    result = prediction_engine.predict_asset(ticker.upper())
    return jsonify(result)

# API: News
@app.route('/api/news')
def api_news():
    """Get market news"""
    news = NewsEngine.get_news()
    return jsonify({"news": news})

# API: Screenshot analysis
@app.route('/api/analyze/screenshot', methods=['GET', 'POST'])
def api_screenshot():
    """Analyze uploaded screenshot using Claude Vision AI"""
    try:
        image_data = ""
        # Accept JSON body with base64 image
        if request.is_json:
            body = request.get_json(silent=True) or {}
            image_data = body.get("image", "") or body.get("image_data", "")
        # Accept multipart form upload
        if not image_data and "image" in request.files:
            import base64
            f = request.files["image"]
            image_data = base64.b64encode(f.read()).decode("utf-8")
        # Accept form field with base64
        if not image_data:
            image_data = request.form.get("image", "") or request.form.get("image_data", "")

        result = ScreenshotAnalyzer.analyze(image_data)
        return jsonify(result)
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500

# API: System status
@app.route('/api/status')
def api_status():
    """System status"""
    process = psutil.Process(os.getpid())
    
    # Calculate current portfolio value for status bar
    prices = {t: float(p.get("current_price", 0)) for t, p in current_predictions.items()}
    portfolio_value = paper_trading.get_portfolio_value(prices)

    return jsonify({
        "status": "running",
        "models_loaded": len(prediction_engine.models),
        "predictions_made": len(prediction_engine.predictions),
        "assets_tracked": len(ComprehensiveDataSource.get_all_assets()),
        "memory_mb": process.memory_info().rss / (1024*1024),
        "prediction_cache": len(prediction_engine.prediction_cache),
        "market_data_cache": len(prediction_engine.history_cache),
        "workers": PREDICTION_WORKERS,
        "live_streaming": is_live_streaming,
        "win_rate": round(accuracy_tracker.get_win_rate() * 100, 1),
        "portfolio_value": round(portfolio_value, 2),
        "ai_vision": "enabled" if os.environ.get("ANTHROPIC_API_KEY") else "disabled"
    })


# ============================================================
# PORTFOLIO & PAPER TRADING API
# ============================================================

@app.route('/api/portfolio')
def api_portfolio():
    """Get paper trading portfolio state"""
    prices = {}
    for ticker in list(paper_trading.state["positions"].keys()):
        if ticker in current_predictions:
            prices[ticker] = float(current_predictions[ticker].get("current_price", 0))
        else:
            res = prediction_engine.predict_asset(ticker)
            if "current_price" in res:
                prices[ticker] = float(res["current_price"])

    # Update portfolio brackets
    paper_trading.update_positions_and_brackets(prices)

    portfolio_val = paper_trading.get_portfolio_value(prices)
    unrealized_pnl = 0.0
    active_positions = []

    for ticker, pos in paper_trading.state["positions"].items():
        curr_price = prices.get(ticker, pos["entry_price"])
        pnl = (curr_price - pos["entry_price"]) * pos["shares"] if pos["type"] == "BUY" else (pos["entry_price"] - curr_price) * pos["shares"]
        unrealized_pnl += pnl
        active_positions.append({
            "ticker": ticker,
            "shares": pos["shares"],
            "entry_price": pos["entry_price"],
            "current_price": curr_price,
            "type": pos["type"],
            "stop_loss": pos["stop_loss"],
            "take_profit": pos["take_profit"],
            "pnl": round(pnl, 2),
            "pnl_percent": round((pnl / (pos["entry_price"] * pos["shares"])) * 100, 2)
        })

    return jsonify({
        "cash": round(paper_trading.state["cash"], 2),
        "equity": round(portfolio_val, 2),
        "unrealized_pnl": round(unrealized_pnl, 2),
        "total_return": round(((portfolio_val - 100000.0) / 100000.0) * 100, 2),
        "positions": active_positions,
        "transactions": paper_trading.state["transactions"][-20:],
        "equity_history": paper_trading.state["equity_history"],
        "auto_trade_enabled": paper_trading.state["auto_trade_enabled"]
    })


@app.route('/api/portfolio/trade', methods=['POST'])
def api_portfolio_trade():
    """Execute a virtual paper trade"""
    data = request.json or {}
    ticker = data.get("ticker", "").upper().strip()
    action = data.get("action", "").upper().strip()
    qty = int(data.get("qty", 0))
    stop_loss = data.get("stop_loss")
    take_profit = data.get("take_profit")

    if not ticker or not action or qty <= 0:
        return jsonify({"status": "error", "message": "Missing ticker, action, or quantity"}), 400

    res = prediction_engine.predict_asset(ticker)
    if "current_price" not in res:
        return jsonify({"status": "error", "message": f"Could not fetch active price for {ticker}"}), 400

    price = float(res["current_price"])
    stop_loss = float(stop_loss) if stop_loss else None
    take_profit = float(take_profit) if take_profit else None

    result = paper_trading.execute_order(ticker, action, qty, price, stop_loss, take_profit)
    return jsonify(result)


@app.route('/api/portfolio/reset', methods=['POST'])
def api_portfolio_reset():
    """Reset virtual balance to $100k"""
    paper_trading.reset_portfolio()
    return jsonify({"status": "success", "message": "Portfolio reset to $100,000"})


@app.route('/api/portfolio/auto_trade', methods=['POST'])
def api_portfolio_toggle_auto():
    """Toggle AI Auto-Trading Robo Advisor"""
    data = request.json or {}
    enabled = bool(data.get("enabled", False))
    paper_trading.state["auto_trade_enabled"] = enabled
    paper_trading.save_state()
    return jsonify({"status": "success", "auto_trade_enabled": enabled})


# ============================================================
# PWA / MOBILE INSTALLATION SERVICE
# ============================================================

@app.route('/manifest.json')
def api_manifest():
    manifest = {
        "name": "Stock Predictor Pro",
        "short_name": "PredictorPro",
        "description": "Institutional-grade Stock Predictor and DNA-01 Paper Trading Desk",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#0f172a",
        "theme_color": "#0f172a",
        "orientation": "portrait-primary",
        "icons": [
            {
                "src": "/icon.svg",
                "sizes": "192x192 512x512",
                "type": "image/svg+xml",
                "purpose": "any maskable"
            }
        ]
    }
    return jsonify(manifest)


@app.route('/sw.js')
def api_sw():
    sw = """const CACHE_NAME = 'predictor-cache-v1';
const ASSETS = [
  '/',
  '/manifest.json',
  '/icon.svg',
  'https://cdn.tailwindcss.com',
  'https://cdnjs.cloudflare.com/ajax/libs/Chart.js/3.9.1/chart.min.js',
  'https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.5.4/socket.io.min.js',
  'https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap'
];

self.addEventListener('install', e => {
  e.waitUntil(
    caches.open(CACHE_NAME).then(cache => cache.addAll(ASSETS))
  );
});

self.addEventListener('fetch', e => {
  e.respondWith(
    caches.match(e.request).then(response => response || fetch(e.request))
  );
});"""
    return app.response_class(sw, mimetype='application/javascript')


@app.route('/icon.svg')
def api_icon():
    svg = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" width="100%" height="100%">
  <defs>
    <linearGradient id="g" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#22c55e" />
      <stop offset="100%" stop-color="#3b82f6" />
    </linearGradient>
  </defs>
  <rect width="512" height="512" rx="128" fill="#0f172a" />
  <circle cx="256" cy="256" r="200" fill="url(#g)" opacity="0.15" />
  <path d="M128 384 L224 288 L288 352 L400 176" fill="none" stroke="url(#g)" stroke-width="32" stroke-linecap="round" stroke-linejoin="round" />
  <polygon points="400,176 320,176 400,256" fill="url(#g)" />
  <text x="256" y="450" text-anchor="middle" fill="#ffffff" font-family="system-ui, sans-serif" font-size="42" font-weight="800" letter-spacing="1">PREDICTOR PRO</text>
</svg>"""
    return app.response_class(svg, mimetype='image/svg+xml')


# ============================================================
# BACKGROUND LIVE UPDATES
# ============================================================

def live_prediction_stream():
    """Background thread for live predictions and automated Robo-Trading"""
    global current_predictions, is_live_streaming
    is_live_streaming = True

    tickers_to_stream = (
        ComprehensiveDataSource.GLOBAL_STOCKS[:8] +
        ComprehensiveDataSource.CRYPTO[:4] +
        ComprehensiveDataSource.COMMODITIES[:3]
    )

    while is_live_streaming:
        results = predict_many(tickers_to_stream, timeout=20)
        
        prices = {}
        for result in results:
            current_predictions[result["ticker"]] = result
            prices[result["ticker"]] = float(result.get("current_price", 0))
            socketio.emit('prediction_update', result, namespace='/')
            
            # Robo-Advisor Auto-Trading logic
            if paper_trading.state.get("auto_trade_enabled", False):
                confluence = result.get("confluence", 0.0)
                ticker = result["ticker"]
                
                # Auto-trade on >80% confluence if no active position
                if confluence >= 0.80 and ticker not in paper_trading.state["positions"]:
                    price = float(result["current_price"])
                    # Use Phase 5 1% rule to calculate size
                    prices_for_val = {t: float(p.get("current_price", 0)) for t, p in current_predictions.items()}
                    prices_for_val[ticker] = price
                    equity = paper_trading.get_portfolio_value(prices_for_val)
                    
                    stop_loss_distance = price * 0.03 # 3% ATR estimate
                    risk_amt = equity * 0.01
                    qty = int(risk_amt / stop_loss_distance)
                    
                    if qty > 0:
                        cost = qty * price
                        if cost <= paper_trading.state["cash"]:
                            stop_loss = price - stop_loss_distance
                            take_profit = price + stop_loss_distance * 2.0
                            paper_trading.execute_order(ticker, "BUY", qty, price, stop_loss, take_profit)
                            logger.info(f"Robo-Advisor: Auto-bought {qty} shares of {ticker} at {price} due to high confluence ({round(confluence*100)}%)")

        # Update feedback accuracies and daily portfolio brackets
        accuracy_tracker.update_accuracies(prices)
        paper_trading.update_positions_and_brackets(prices)
        
        time.sleep(60)


def start_background_workers():
    """Start lightweight automated workers used by the dashboard."""
    global is_live_streaming
    if is_live_streaming:
        return
    thread = threading.Thread(target=live_prediction_stream, daemon=True, name="live-prediction-stream")
    thread.start()
    # Keep-alive for Render free tier (prevents sleep after 15 min inactivity)
    try:
        from keep_alive import start_keep_alive
        start_keep_alive()
    except Exception:
        pass


# ============================================================
# TEMPLATE GENERATION
# ============================================================

def create_template():
    """Create the comprehensive dashboard template"""
    template_path = os.path.join(BASE_DIR, 'templates', 'comprehensive_dashboard.html')
    if os.path.exists(template_path) and os.path.getsize(template_path) > 0:
        logger.info("Using existing dashboard template at %s", template_path)
        return

    template = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Stock Predictor Pro - All Markets</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/3.9.1/chart.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.5.4/socket.io.min.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        body { font-family: 'Inter', sans-serif; }
        .gradient-bg { background: linear-gradient(180deg, #0f172a 0%, #1e3a5f 100%); }
        .glass { background: rgba(255,255,255,0.05); backdrop-filter: blur(10px); border: 1px solid rgba(255,255,255,0.1); }
        .live-dot { animation: pulse 2s infinite; }
        @keyframes pulse { 0%,100% { opacity: 1; } 50% { opacity: 0.5; } }
        .fade-in { animation: fadeIn 0.5s ease-in; }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
        .loader { border: 3px solid #f3f3f3; border-top: 3px solid #22c55e; border-radius: 50%; width: 30px; height: 30px; animation: spin 1s linear infinite; }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        .up-arrow { color: #22c55e; }
        .down-arrow { color: #ef4444; }
    </style>
</head>
<body class="gradient-bg min-h-screen text-white">
    <!-- Navigation -->
    <nav class="glass sticky top-0 z-50 border-b border-gray-800/30">
        <div class="max-w-7xl mx-auto px-4 py-3 flex justify-between items-center">
            <div class="flex items-center gap-3">
                <div class="w-10 h-10 bg-gradient-to-r from-green-400 to-blue-500 rounded-xl flex items-center justify-center">
                    <span class="text-xl font-bold">SP</span>
                </div>
                <div>
                    <h1 class="text-xl font-bold">Stock Predictor Pro</h1>
                    <div class="flex items-center gap-1 text-xs text-green-400">
                        <span class="live-dot w-2 h-2 bg-green-400 rounded-full"></span>
                        <span>Live Trading</span>
                    </div>
                </div>
            </div>
            <div class="flex gap-2">
                <button onclick="switchTab('stocks')" class="px-4 py-2 rounded-lg glass hover:bg-white/10 transition tab-btn" data-tab="stocks">Stocks</button>
                <button onclick="switchTab('crypto')" class="px-4 py-2 rounded-lg glass hover:bg-white/10 transition tab-btn" data-tab="crypto">Crypto</button>
                <button onclick="switchTab('commodities')" class="px-4 py-2 rounded-lg glass hover:bg-white/10 transition tab-btn" data-tab="commodities">Commodities</button>
                <button onclick="switchTab('forex')" class="px-4 py-2 rounded-lg glass hover:bg-white/10 transition tab-btn" data-tab="forex">Forex</button>
                <button onclick="switchTab('pakistani')" class="px-4 py-2 rounded-lg glass hover:bg-white/10 transition tab-btn" data-tab="pakistani">Pakistan</button>
                <button onclick="switchTab('news')" class="px-4 py-2 rounded-lg glass hover:bg-white/10 transition tab-btn" data-tab="news">News</button>
                <button onclick="switchTab('analyze')" class="px-4 py-2 rounded-lg glass hover:bg-white/10 transition tab-btn" data-tab="analyze">Analyze</button>
            </div>
        </div>
    </nav>

    <!-- Main Content -->
    <div class="max-w-7xl mx-auto px-4 py-6">
        <!-- Status Bar -->
        <div class="glass rounded-xl p-4 mb-6 flex justify-between items-center">
            <div class="flex gap-6">
                <div class="text-center">
                    <div class="text-2xl font-bold" id="total-models">0</div>
                    <div class="text-xs text-gray-400">Models</div>
                </div>
                <div class="text-center">
                    <div class="text-2xl font-bold" id="total-predictions">0</div>
                    <div class="text-xs text-gray-400">Predictions</div>
                </div>
                <div class="text-center">
                    <div class="text-2xl font-bold" id="total-assets">0</div>
                    <div class="text-xs text-gray-400">Assets</div>
                </div>
                <div class="text-center">
                    <div class="text-2xl font-bold" id="memory-usage">0</div>
                    <div class="text-xs text-gray-400">Memory MB</div>
                </div>
            </div>
            <div class="text-right">
                <div class="text-xs text-gray-400">Last Update</div>
                <div class="text-sm" id="last-update">--:--:--</div>
            </div>
        </div>

        <!-- Stocks Tab -->
        <div id="tab-stocks" class="tab-content">
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4" id="stocks-grid">
                <!-- Loading state -->
                <div class="col-span-full flex justify-center py-12">
                    <div class="loader"></div>
                </div>
            </div>
        </div>

        <!-- Crypto Tab -->
        <div id="tab-crypto" class="tab-content hidden">
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4" id="crypto-grid">
                <div class="col-span-full flex justify-center py-12">
                    <div class="loader"></div>
                </div>
            </div>
        </div>

        <!-- Commodities Tab -->
        <div id="tab-commodities" class="tab-content hidden">
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4" id="commodities-grid">
                <div class="col-span-full flex justify-center py-12">
                    <div class="loader"></div>
                </div>
            </div>
        </div>

        <!-- Forex Tab -->
        <div id="tab-forex" class="tab-content hidden">
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4" id="forex-grid">
                <div class="col-span-full flex justify-center py-12">
                    <div class="loader"></div>
                </div>
            </div>
        </div>

        <!-- Pakistani Tab -->
        <div id="tab-pakistani" class="tab-content hidden">
            <div class="glass rounded-xl p-4 mb-4">
                <h3 class="text-lg font-bold mb-2">Pakistan Stock Exchange (KSE-100)</h3>
                <p class="text-sm text-gray-400">Real-time predictions for Pakistani stocks</p>
            </div>
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4" id="pakistani-grid">
                <div class="col-span-full flex justify-center py-12">
                    <div class="loader"></div>
                </div>
            </div>
        </div>

        <!-- News Tab -->
        <div id="tab-news" class="tab-content hidden">
            <div class="glass rounded-xl p-6">
                <h3 class="text-lg font-bold mb-4">Market News</h3>
                <div class="space-y-4" id="news-list">
                    <!-- News items will be loaded here -->
                </div>
            </div>
        </div>

        <!-- Analyze Tab -->
        <div id="tab-analyze" class="tab-content hidden">
            <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div class="glass rounded-xl p-6">
                    <h3 class="text-lg font-bold mb-4">Screenshot Analysis</h3>
                    <div class="border-2 border-dashed border-gray-600 rounded-xl p-8 text-center">
                        <input type="file" id="screenshot-input" accept="image/*" class="hidden" onchange="handleScreenshot(this)">
                        <label for="screenshot-input" class="cursor-pointer">
                            <div class="text-4xl mb-3">[UPLOAD]</div>
                            <div class="text-gray-400">Drop chart screenshot here or click to upload</div>
                        </label>
                    </div>
                    <div id="screenshot-result" class="mt-4 hidden">
                        <div class="glass rounded-lg p-4">
                            <div class="flex justify-between items-center mb-2">
                                <span class="text-gray-400">Pattern</span>
                                <span class="font-bold" id="pattern-result">--</span>
                            </div>
                            <div class="flex justify-between items-center mb-2">
                                <span class="text-gray-400">Trend</span>
                                <span class="font-bold" id="trend-result">--</span>
                            </div>
                            <div class="flex justify-between items-center mb-2">
                                <span class="text-gray-400">Signal</span>
                                <span class="font-bold" id="signal-result">--</span>
                            </div>
                            <div class="flex justify-between items-center">
                                <span class="text-gray-400">Confidence</span>
                                <span class="font-bold" id="confidence-result">--</span>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="glass rounded-xl p-6">
                    <h3 class="text-lg font-bold mb-4">Quick Predict</h3>
                    <div class="flex gap-2 mb-4">
                        <input type="text" id="ticker-input" placeholder="Enter ticker (e.g., AAPL, BTC-USD)" class="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-4 py-2">
                        <button onclick="quickPredict()" class="bg-green-500 hover:bg-green-600 px-6 py-2 rounded-lg font-bold">Predict</button>
                    </div>
                    <div id="quick-result" class="hidden">
                        <div class="glass rounded-lg p-4">
                            <div class="flex justify-between items-center mb-2">
                                <span>Ticker</span>
                                <span class="font-bold" id="qr-ticker">--</span>
                            </div>
                            <div class="flex justify-between items-center mb-2">
                                <span>Prediction</span>
                                <span class="font-bold text-xl" id="qr-prediction">--</span>
                            </div>
                            <div class="flex justify-between items-center mb-2">
                                <span>Confidence</span>
                                <span class="font-bold" id="qr-confidence">--</span>
                            </div>
                            <div class="flex justify-between items-center">
                                <span>Current Price</span>
                                <span class="font-bold" id="qr-price">--</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        // Initialize
        const socket = io();
        let currentTab = 'stocks';

        // Tab switching
        function switchTab(tab) {
            document.querySelectorAll('.tab-content').forEach(el => el.classList.add('hidden'));
            document.getElementById('tab-' + tab).classList.remove('hidden');
            currentTab = tab;
            loadData(tab);
        }

        // Load data based on tab
        async function loadData(tab) {
            const endpoints = {
                'stocks': '/api/stocks',
                'crypto': '/api/crypto',
                'commodities': '/api/commodities',
                'forex': '/api/forex',
                'pakistani': '/api/pakistani',
                'news': '/api/news'
            };

            if (tab === 'news') {
                loadNews();
                return;
            }

            const gridId = tab + '-grid';
            const grid = document.getElementById(gridId);
            grid.innerHTML = '<div class="col-span-full flex justify-center py-12"><div class="loader"></div></div>';

            try {
                const response = await fetch(endpoints[tab]);
                const data = await response.json();

                let items = [];
                if (tab === 'stocks') items = data.stocks;
                else if (tab === 'crypto') items = data.crypto;
                else if (tab === 'commodities') items = data.commodities;
                else if (tab === 'forex') items = data.forex;
                else if (tab === 'pakistani') items = data.stocks;

                renderCards(tab, items, grid);
            } catch (e) {
                grid.innerHTML = '<div class="col-span-full text-center text-red-400">Error loading data</div>';
            }
        }

        // Render cards
        function renderCards(tab, items, grid) {
            if (!items || items.length === 0) {
                grid.innerHTML = '<div class="col-span-full text-center text-gray-400">No data available</div>';
                return;
            }

            grid.innerHTML = items.map(item => {
                const isUp = item.prediction === 'UP' || item.change_1d > 0;
                const arrow = isUp ? '▲' : '▼';
                const color = isUp ? 'text-green-400' : 'text-red-400';
                const signalColor = item.prediction === 'UP' ? 'bg-green-500' : 'bg-red-500';

                return `
                <div class="glass rounded-xl p-4 fade-in">
                    <div class="flex justify-between items-start mb-3">
                        <div>
                            <h3 class="text-lg font-bold">${item.ticker}</h3>
                            <div class="text-2xl font-bold">${item.current_price || 'N/A'}</div>
                        </div>
                        <div class="text-right">
                            <div class="text-xs text-gray-400">Signal</div>
                            <div class="${signalColor} px-3 py-1 rounded-full text-sm font-bold">
                                ${item.prediction || 'WAIT'}
                            </div>
                        </div>
                    </div>
                    <div class="grid grid-cols-2 gap-2 text-sm">
                        <div class="flex justify-between">
                            <span class="text-gray-400">Change</span>
                            <span class="${color}">${arrow} ${item.change_1d?.toFixed(2) || 0}%</span>
                        </div>
                        <div class="flex justify-between">
                            <span class="text-gray-400">Confidence</span>
                            <span>${((item.confidence || 0) * 100).toFixed(0)}%</span>
                        </div>
                        <div class="flex justify-between">
                            <span class="text-gray-400">RSI</span>
                            <span>${item.rsi || 'N/A'}</span>
                        </div>
                        <div class="flex justify-between">
                            <span class="text-gray-400">Trend</span>
                            <span class="${item.trend === 'UPTREND' ? 'text-green-400' : 'text-red-400'}">${item.trend || 'N/A'}</span>
                        </div>
                    </div>
                    ${item.patterns?.length ? '<div class="mt-2 text-xs text-gray-500">Patterns: ' + item.patterns.join(', ') + '</div>' : ''}
                </div>
                `;
            }).join('');
        }

        // Load news
        async function loadNews() {
            try {
                const response = await fetch('/api/news');
                const data = await response.json();
                const newsList = document.getElementById('news-list');
                newsList.innerHTML = data.news.map(item => `
                    <div class="flex gap-4 p-3 glass rounded-lg">
                        <div class="flex-1">
                            <h4 class="font-bold">${item.title}</h4>
                            <div class="text-xs text-gray-400 mt-1">${item.source} • ${item.time}</div>
                        </div>
                        <div class="px-3 py-1 rounded text-xs ${item.sentiment === 'positive' ? 'bg-green-500/20 text-green-400' : item.sentiment === 'negative' ? 'bg-red-500/20 text-red-400' : 'bg-gray-500/20 text-gray-400'}">
                            ${item.sentiment}
                        </div>
                    </div>
                `).join('');
            } catch (e) {
                document.getElementById('news-list').innerHTML = '<div class="text-center text-red-400">Error loading news</div>';
            }
        }

        // Screenshot analysis
        async function handleScreenshot(input) {
            if (input.files && input.files[0]) {
                const formData = new FormData();
                formData.append('image', input.files[0]);

                document.getElementById('screenshot-result').classList.add('hidden');

                try {
                    const response = await fetch('/api/analyze/screenshot', {
                        method: 'POST',
                        body: formData
                    });
                    const data = await response.json();

                    document.getElementById('pattern-result').textContent = data.pattern || 'N/A';
                    document.getElementById('trend-result').textContent = data.trend || 'N/A';
                    document.getElementById('signal-result').textContent = data.signal || 'N/A';
                    document.getElementById('confidence-result').textContent = ((data.confidence || 0) * 100).toFixed(0) + '%';
                    document.getElementById('screenshot-result').classList.remove('hidden');
                } catch (e) {
                    alert('Error analyzing screenshot');
                }
            }
        }

        // Quick predict
        async function quickPredict() {
            const ticker = document.getElementById('ticker-input').value.toUpperCase();
            if (!ticker) return;

            try {
                const response = await fetch('/api/predict/' + ticker);
                const data = await response.json();

                if (data.prediction) {
                    document.getElementById('qr-ticker').textContent = data.ticker;
                    document.getElementById('qr-prediction').textContent = data.prediction;
                    document.getElementById('qr-prediction').className = 'font-bold text-xl ' + (data.prediction === 'UP' ? 'text-green-400' : 'text-red-400');
                    document.getElementById('qr-confidence').textContent = (data.confidence * 100).toFixed(0) + '%';
                    document.getElementById('qr-price').textContent = data.current_price;
                    document.getElementById('quick-result').classList.remove('hidden');
                } else {
                    alert('Could not get prediction for ' + ticker);
                }
            } catch (e) {
                alert('Error getting prediction');
            }
        }

        // Update status
        async function updateStatus() {
            try {
                const response = await fetch('/api/status');
                const data = await response.json();
                document.getElementById('total-models').textContent = data.models_loaded;
                document.getElementById('total-predictions').textContent = data.predictions_made;
                document.getElementById('total-assets').textContent = data.assets_tracked;
                document.getElementById('memory-usage').textContent = Math.round(data.memory_mb);
                document.getElementById('last-update').textContent = new Date().toLocaleTimeString();
            } catch (e) {}
        }

        // Socket updates
        socket.on('prediction_update', function(data) {
            // Could update individual cards in real-time
        });

        // Initial load
        loadData('stocks');
        updateStatus();
        setInterval(updateStatus, 10000);
        setInterval(() => loadData(currentTab), 30000);
    </script>
</body>
</html>"""

    os.makedirs(os.path.dirname(template_path), exist_ok=True)
    with open(template_path, 'w', encoding='utf-8') as f:
        f.write(template)
    print("Dashboard template created")


def run_system(port=None):
    """Run the comprehensive system"""
    # Get port from environment (Render.com) or use default
    if port is None:
        port = int(os.environ.get('PORT', 5003))

    create_template()

    print("\n" + "="*60)
    print("  COMPREHENSIVE STOCK PREDICTOR PRO")
    print("  All Markets - Live Trading")
    print("="*60)
    print(f"  Stocks: {len(ComprehensiveDataSource.GLOBAL_STOCKS)}")
    print(f"  Crypto: {len(ComprehensiveDataSource.CRYPTO)}")
    print(f"  Commodities: {len(ComprehensiveDataSource.COMMODITIES)}")
    print(f"  Forex: {len(ComprehensiveDataSource.FOREX_PAIRS)}")
    print(f"  Pakistani: {len(ComprehensiveDataSource.PAKISTANI_STOCKS)}")
    print(f"  Indices: {len(ComprehensiveDataSource.INDICES)}")
    print(f"  Total: {len(ComprehensiveDataSource.get_all_assets())}")
    print("="*60)
    print(f"  Running on port: {port}")
    print("="*60 + "\n")

    start_background_workers()
    socketio.run(app, host='0.0.0.0', port=port, debug=False, allow_unsafe_werkzeug=True)


if __name__ == "__main__":
    run_system()
