import os
import json
import logging
import pandas as pd
import numpy as np
import torch
from stock_predictor import StockPredictor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("DeepMathAgent")

class DeepMathAgent:
    def __init__(self):
        self.name = "Deep Mathematician"
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        logger.info(f"Initializing Deep Neural Brain on device: {self.device}")
        
    def execute(self, payload: dict) -> dict:
        ticker = payload["ticker"]
        logger.info(f"Computing Microscopic Deep Tensors for {ticker}...")
        
        # Initialize with max historical lookback
        predictor = StockPredictor(ticker, lookback_days=18250)
        df = predictor.fetch_data(period="max")
        df_indicators = predictor.calculate_indicators(df)
        
        # 1. Price Action & Candlestick Architecture (Phase 1)
        patterns = self.detect_candlestick_patterns(df)
        
        # 2. VWAP & Volume Metrics (Phase 3)
        df['VWAP'] = (df['Close'] * df['Volume']).cumsum() / df['Volume'].cumsum()
        
        # 3. Breakout Confirmation (Phase 2)
        vol_sma = df['Volume'].rolling(20).mean()
        is_confirmed = df['Volume'].iloc[-1] > 2.0 * vol_sma.iloc[-1]
        
        # Prepare Tensor for Deep Learning Model
        numeric_df = df_indicators.select_dtypes(include=[np.number]).fillna(0)
        features = numeric_df.tail(60) 
        
        features_tensor = torch.tensor(features.values, dtype=torch.float32).to(self.device)
        
        latest = df_indicators.iloc[-1]
        
        payload["technical_metrics"] = {
            "close": float(latest["Close"]),
            "vwap": float(df['VWAP'].iloc[-1]),
            "rsi": float(latest["RSI_14"]),
            "is_breakout_confirmed": is_confirmed,
            "detected_patterns": patterns,
            "tensor_ready": True
        }
        
        logger.info(f"Generated Microscopic Tensor with {len(patterns)} patterns detected.")
        return payload

    def detect_candlestick_patterns(self, df):
        """Institutional Candlestick Detection (Phase 1)"""
        latest = df.iloc[-1]
        prev = df.iloc[-2]
        body = abs(latest['Close'] - latest['Open'])
        total_range = max(0.001, latest['High'] - latest['Low'])
        
        patterns = []
        if body > 0.9 * total_range: patterns.append("MARUBOZU")
        if body < 0.05 * total_range: patterns.append("DOJI")
        if latest['Close'] > prev['Open'] and latest['Open'] < prev['Close']: patterns.append("ENGULFING")
        return patterns

if __name__ == "__main__":
    import sys
    ticker = sys.argv[1] if len(sys.argv) > 1 else "AAPL"
    agent = DeepMathAgent()
    print(json.dumps(agent.execute({"ticker": ticker}), indent=2))
