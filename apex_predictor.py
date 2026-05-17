"""
APEX PREDICTOR — GODMODE Multi-Dimensional Market Prediction Engine
"""
import yfinance as yf
import pandas as pd
import numpy as np
import json
import os
import warnings
import logging
from datetime import datetime
from typing import Dict, List
from scipy import stats
from database_manager import db_manager

warnings.filterwarnings('ignore')
logger = logging.getLogger("APEX")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ACCURACY_LOG = os.path.join(BASE_DIR, "apex_accuracy.json")

class SentimentEngine:
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
            scores["overall"] = scores["news"]
        except Exception as e:
            logger.warning(f"Sentiment error: {e}")
        return scores

class TechnicalAnalyzer:
    @staticmethod
    def calculate(df: pd.DataFrame) -> Dict:
        close = df['Close'].values
        volume = df['Volume'].values if 'Volume' in df.columns else np.ones_like(close)
        high = df['High'].values; low = df['Low'].values
        score = 5; signals = []
        rsi_val = 50
        if len(close) > 14:
            delta = np.diff(close)
            gain = np.where(delta > 0, delta, 0)
            loss = np.where(delta < 0, -delta, 0)
            avg_g = np.mean(gain[-14:]) if len(gain) >= 14 else np.mean(gain)
            avg_l = np.mean(loss[-14:]) if len(loss) >= 14 else np.mean(loss)
            rsi_val = 100 - 100 / (1 + avg_g / avg_l) if avg_l > 0 else 100
            if rsi_val > 70: score -= 1; signals.append("RSI overbought")
            elif rsi_val < 30: score += 1; signals.append("RSI oversold")
        if len(close) > 26:
            exp12 = pd.Series(close).ewm(span=12).mean().values
            exp26 = pd.Series(close).ewm(span=26).mean().values
            macd = exp12 - exp26
            sig = pd.Series(macd).ewm(span=9).mean().values
            if len(macd) > 1 and macd[-1] > sig[-1] and macd[-2] <= sig[-2]:
                score += 1; signals.append("MACD bullish cross")
            elif len(macd) > 1 and macd[-1] < sig[-1] and macd[-2] >= sig[-2]:
                score -= 1; signals.append("MACD bearish cross")
        if len(close) > 20:
            sma20 = np.mean(close[-20:]); sma50 = np.mean(close[-50:]) if len(close) >= 50 else sma20
            if close[-1] > sma20: score += 0.5; signals.append("Above SMA20")
            else: score -= 0.5; signals.append("Below SMA20")
            if sma20 > sma50: score += 0.5; signals.append("SMA uptrend")
            else: score -= 0.5; signals.append("SMA downtrend")
        if len(volume) > 20:
            avg_v = np.mean(volume[-20:]); cur_v = volume[-1]
            vr = cur_v / avg_v if avg_v > 0 else 1
            if vr > 1.5 and close[-1] > close[-2]: score += 0.5; signals.append("High vol bullish")
            elif vr > 1.5 and close[-1] < close[-2]: score -= 0.5; signals.append("High vol bearish")
        score = max(1, min(10, score))
        return {"score": float(f"{score:.1f}"), "signal": "Bullish" if score >= 6 else "Bearish" if score <= 4 else "Neutral",
                "details": {"rsi": float(f"{rsi_val:.1f}")}, "signals": signals[:5]}

    @staticmethod
    def key_levels(df: pd.DataFrame) -> Dict:
        if df is None or len(df) < 5: return {}
        h, l, c = df['High'].values, df['Low'].values, df['Close'].values
        p = (h[-1] + l[-1] + c[-1]) / 3
        r1, r2 = 2*p - l[-1], p + (h[-1] - l[-1])
        s1, s2 = 2*p - h[-1], p - (h[-1] - l[-1])
        rh, rl = np.max(h[-20:]), np.min(l[-20:])
        fibs = {}
        if rh - rl > 0:
            for lvl in [23.6, 38.2, 50, 61.8, 78.6]:
                fibs[f"fib_{lvl}"] = float(f"{rh - (rh - rl) * lvl / 100:.2f}")
        vwap = float(f"{np.average(c[-20:], weights=df['Volume'].values[-20:] if 'Volume' in df.columns else None) :.2f}")
        return {"pivot": float(f"{p:.2f}"), "r1": float(f"{r1:.2f}"), "r2": float(f"{r2:.2f}"),
                "r3": float(f"{r2 + (r1 - p):.2f}"), "s1": float(f"{s1:.2f}"), "s2": float(f"{s2:.2f}"),
                "s3": float(f"{s2 - (p - s1):.2f}"), "fibonacci": fibs, "vwap": vwap}

class CandleStrategyAnalyzer:
    @staticmethod
    def analyze(df: pd.DataFrame) -> Dict:
        c, o, h, l = df['Close'].values, df['Open'].values, df['High'].values, df['Low'].values
        score = 5; signals = []
        body = abs(c[-1] - o[-1]); rng = h[-1] - l[-1]
        bp = (body / rng * 100) if rng > 0 else 0
        uw = h[-1] - max(o[-1], c[-1]); lw = min(o[-1], c[-1]) - l[-1]
        up = (uw / rng * 100) if rng > 0 else 0; lp = (lw / rng * 100) if rng > 0 else 0
        is_bull = c[-1] > o[-1]
        pattern, p_sig = "No clear pattern", "neutral"
        if rng > 0 and body / rng < 0.1: pattern, p_sig = "Doji", "neutral"
        if len(df) >= 2:
            pb = abs(c[-2] - o[-2]); cb = abs(c[-1] - o[-1])
            if cb > pb * 1.3:
                if c[-1] > o[-1] and c[-2] < o[-2]: pattern, p_sig = "Bullish Engulfing", "bullish"
                elif c[-1] < o[-1] and c[-2] > o[-2]: pattern, p_sig = "Bearish Engulfing", "bearish"
        if lw > 2 * body and uw < 0.3 * body: pattern, p_sig = "Hammer", "bullish"
        if uw > 2 * body and lw < 0.3 * body: pattern, p_sig = "Shooting Star", "bearish"
        if p_sig == "bullish": score += 1.5; signals.append(f"Bullish {pattern}")
        elif p_sig == "bearish": score -= 1.5; signals.append(f"Bearish {pattern}")
        if len(c) >= 3:
            bc = sum(1 for i in range(-3, 0) if c[i] > o[i])
            if bc >= 3: score += 1; signals.append("3 bullish candles")
            elif bc <= 0: score -= 1; signals.append("3 bearish candles")
        if lp > 60: score += 1; signals.append("Lower wick rejection")
        if up > 60: score -= 0.5; signals.append("Upper wick resistance")
        return {"score": float(f"{max(1, min(10, score)):.1f}"),
                "signal": "Bullish" if score >= 6 else "Bearish" if score <= 4 else "Neutral",
                "details": {"current_pattern": pattern, "body_pct": float(f"{bp:.1f}"),
                           "upper_wick_pct": float(f"{up:.1f}"), "lower_wick_pct": float(f"{lp:.1f}")},
                "signals": signals[:5]}

class HistoricalPatternMatcher:
    @staticmethod
    def match(df: pd.DataFrame) -> Dict:
        if df is None or len(df) < 40: return {"score": 5, "signal": "Neutral", "details": {"matches": 0}, "signals": []}
        c = df['Close'].values; lb = 20
        cur = c[-lb:]; cr = np.diff(cur) / cur[:-1]
        mc = 0; bo = 0; bc = 0
        for s in range(0, len(c) - lb * 2, 5):
            hc = c[s:s+lb]; hr = np.diff(hc) / hc[:-1]
            if len(hr) != len(cr): continue
            corr, _ = stats.pearsonr(cr[-min(len(cr), len(hr)):], hr[-min(len(cr), len(hr)):])
            if abs(corr) > 0.7 and not np.isnan(corr):
                mc += 1
                nr = (c[s+lb] - c[s+lb-1]) / c[s+lb-1] if s+lb < len(c) else 0
                if nr > 0: bo += 1
                if abs(corr) > abs(bc): bc = corr
        score = 5; signals = []
        if mc > 0:
            wr = bo / mc
            if wr > 0.6: score += 2; signals.append(f"History bullish: {wr:.0%} ({mc} matches)")
            elif wr < 0.4: score -= 2; signals.append(f"History bearish: {wr:.0%} ({mc} matches)")
            else: score += 0.5; signals.append(f"Mixed history ({mc} matches)")
        return {"score": float(f"{max(1, min(10, score)):.1f}"),
                "signal": "Bullish" if score >= 6 else "Bearish" if score <= 4 else "Neutral",
                "details": {"matches": mc}, "signals": signals[:3]}

class OrderFlowAnalyzer:
    @staticmethod
    def analyze(df: pd.DataFrame) -> Dict:
        c, v = df['Close'].values, df['Volume'].values if 'Volume' in df.columns else np.ones_like(df['Close'])
        score = 5; signals = []
        if len(v) >= 20:
            avs, avl = np.mean(v[-5:]), np.mean(v[-20:])
            vt = avs / avl if avl > 0 else 1
            if vt > 1.3: score += 0.5; signals.append("Volume rising (conviction)")
            elif vt < 0.7: score -= 0.5; signals.append("Volume falling (low conviction)")
        cvd = []
        for i in range(1, len(c)):
            if c[i] > c[i-1]: cvd.append(v[i])
            elif c[i] < c[i-1]: cvd.append(-v[i])
            else: cvd.append(0)
        if cvd:
            ct = np.sum(cvd[-5:]) if len(cvd) >= 5 else np.sum(cvd)
            if ct > 0: score += 0.5; signals.append("Positive CVD (buying)")
            else: score -= 0.5; signals.append("Negative CVD (selling)")
        if len(v) >= 20:
            vz = (v[-1] - np.mean(v[-20:])) / np.std(v[-20:]) if np.std(v[-20:]) > 0 else 0
            if abs(vz) > 2: score += 1 if c[-1] > c[-2] else -1; signals.append("Volume spike (institutional)")
        score = max(1, min(10, score))
        return {"score": float(f"{score:.1f}"),
                "signal": "Bullish" if score >= 6 else "Bearish" if score <= 4 else "Neutral",
                "details": {}, "signals": signals[:5]}

class ApexPredictor:
    def __init__(self, ticker: str):
        self.ticker = ticker.upper()
        self.dimensions = {}
        self.confluence = {}
        self.prediction = {}
        self.levels = {}
        self.sentiment_engine = SentimentEngine()
        self.accuracy_stats = self._load_accuracy()

    def fetch_data(self, period: str = "30d") -> pd.DataFrame:
        cached = db_manager.get_data(self.ticker)
        if cached is not None and not cached.empty:
            return cached
        stock = yf.Ticker(self.ticker)
        df = stock.history(period=period)
        if df.empty:
            df = stock.history(period="3mo")
        if df.empty:
            raise ValueError(f"No data for {self.ticker}")
        db_manager.save_data(self.ticker, df)
        return df

    def analyze_all_dimensions(self, df: pd.DataFrame) -> Dict:
        self.dimensions = {
            "technical": TechnicalAnalyzer.calculate(df),
            "candle_strategy": CandleStrategyAnalyzer.analyze(df),
            "historical_pattern": HistoricalPatternMatcher.match(df),
            "order_flow": OrderFlowAnalyzer.analyze(df)
        }
        sent = self.sentiment_engine.analyze(self.ticker)
        sent_score = max(1, min(10, (sent["overall"] + 1) * 5))
        self.dimensions["sentiment"] = {
            "score": float(f"{sent_score:.1f}"),
            "signal": "Bullish" if sent["overall"] > 0.1 else "Bearish" if sent["overall"] < -0.1 else "Neutral",
            "details": {"overall": sent["overall"], "sources": sent["sources"], "headlines": sent["headlines"][:3]},
            "signals": [f"Sentiment: {sent['overall']:.2f}"]
        }
        self.levels = TechnicalAnalyzer.key_levels(df)
        return self.dimensions

    def calculate_confluence(self) -> Dict:
        weights = {"technical": 0.25, "candle_strategy": 0.20, "sentiment": 0.25,
                   "historical_pattern": 0.15, "order_flow": 0.15}
        total = 0.0
        dims_list = []
        for name, w in weights.items():
            d = self.dimensions.get(name, {})
            s = d.get("score", 5)
            sig = d.get("signal", "Neutral")
            total += s * w * 2
            dims_list.append({"name": name.replace("_", " ").title(), "score": s, "signal": sig})
        conf = min(50, total * 5)
        bs = sum(d["score"] for d in dims_list if d["signal"].lower().startswith("bull"))
        bs_ = sum(d["score"] for d in dims_list if d["signal"].lower().startswith("bear"))
        if conf >= 38: direction, cl = "UP", "Ultra-High"
        elif conf >= 30: direction, cl = ("UP" if bs >= bs_ else "DOWN"), "High"
        elif conf >= 22: direction, cl = ("UP" if bs > bs_ else "DOWN"), "Medium"
        elif conf >= 15: direction, cl = ("UP" if bs > bs_ else "DOWN"), "Low"
        else: direction, cl = "HOLD", "No Trade"
        self.confluence = {"total": float(f"{conf:.1f}"), "direction": direction,
                           "confidence_pct": float(f"{min(99, conf*2):.1f}"),
                           "confidence_label": cl, "dimensions": dims_list,
                           "bullish_score": float(f"{bs:.1f}"), "bearish_score": float(f"{bs_:.1f}")}
        return self.confluence

    def predict(self, df: pd.DataFrame = None) -> Dict:
        if df is None:
            df = self.fetch_data()
        self.analyze_all_dimensions(df)
        self.calculate_confluence()
        last_close = float(df['Close'].iloc[-1])
        chg = float((df['Close'].pct_change().iloc[-1] * 100) if len(df) > 1 else 0)
        if self.confluence["direction"] == "UP":
            target, stop, em = last_close * 1.01, last_close * 0.995, 1.0
        elif self.confluence["direction"] == "DOWN":
            target, stop, em = last_close * 0.99, last_close * 1.005, -1.0
        else:
            target, stop, em = last_close, last_close * 0.99, 0.0
        tf = {"1m": "Bullish" if self.confluence["direction"] == "UP" else "Bearish" if self.confluence["direction"] == "DOWN" else "Neutral",
              "5m": "Bullish" if self.confluence["confidence_label"] in ("High","Ultra-High") and self.confluence["direction"] == "UP" else "Bearish" if self.confluence["confidence_label"] in ("High","Ultra-High") and self.confluence["direction"] == "DOWN" else "Neutral",
              "15m": "Bullish" if self.confluence["confidence_label"] == "Ultra-High" and self.confluence["direction"] == "UP" else "Bearish" if self.confluence["confidence_label"] == "Ultra-High" and self.confluence["direction"] == "DOWN" else "Neutral",
              "1H": "Neutral"}
        self.prediction = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "asset": self.ticker,
            "asset_class": self._classify_asset(),
            "current_price": float(f"{last_close:.4f}"),
            "price_change_pct": chg,
            "direction": self.confluence["direction"],
            "confidence_pct": self.confluence["confidence_pct"],
            "confidence_label": self.confluence["confidence_label"],
            "entry_price": float(f"{last_close:.4f}"),
            "target_price": float(f"{target:.4f}"),
            "stop_loss": float(f"{stop:.4f}"),
            "expected_move_pct": em,
            "confluence": self.confluence,
            "levels": self.levels,
            "multi_tf_alignment": tf,
            "dimensions": self.dimensions,
            "accuracy_tracking": self.accuracy_stats
        }
        return self.prediction

    def _classify_asset(self) -> str:
        t = self.ticker
        if t.endswith('.PSX'): return "Pakistan Stock Exchange"
        if '=X' in t: return "Forex"
        if '=F' in t: return "Commodity Futures"
        if '-USD' in t: return "Cryptocurrency"
        return "US Stock"

    def _load_accuracy(self) -> Dict:
        try:
            if os.path.exists(ACCURACY_LOG):
                with open(ACCURACY_LOG, 'r') as f:
                    return json.load(f)
        except: pass
        return {"total": 0, "correct": 0, "recent": [], "by_confidence": {}}

    def record_outcome(self, was_correct: bool, confidence_label: str):
        stats = self._load_accuracy()
        stats["total"] += 1
        if was_correct: stats["correct"] += 1
        stats["recent"].append({"correct": was_correct, "time": datetime.now().isoformat()})
        stats["recent"] = stats["recent"][-50:]
        if confidence_label not in stats["by_confidence"]:
            stats["by_confidence"][confidence_label] = {"total": 0, "correct": 0}
        stats["by_confidence"][confidence_label]["total"] += 1
        if was_correct: stats["by_confidence"][confidence_label]["correct"] += 1
        with open(ACCURACY_LOG, 'w') as f:
            json.dump(stats, f, indent=2)
        self.accuracy_stats = stats

if __name__ == "__main__":
    import sys
    t = sys.argv[1] if len(sys.argv) > 1 else "AAPL"
    p = ApexPredictor(t)
    r = p.predict()
    print(json.dumps(r, indent=2))
