import os
import json
import logging
import pandas as pd
import numpy as np
from stock_predictor import StockPredictor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TheMathematician")

class MathAgent:
    def __init__(self):
        self.name = "The Mathematician"
        
    def execute(self, payload: dict) -> dict:
        ticker = payload["ticker"]
        logger.info(f"Computing quantitative structures for {ticker} using ALL historical data...")
        
        # Initialize with max possible lookback (approx 50 years)
        predictor = StockPredictor(ticker, lookback_days=18250)
        df = predictor.fetch_data(period="max")
        df_indicators = predictor.calculate_indicators(df)
        
        latest = df_indicators.iloc[-1]
        
        payload["technical_metrics"] = {
            "close": float(latest["Close"]),
            "rsi": float(latest["RSI_14"]),
            "macd": float(latest["MACD"]),
            "sma_20": float(latest["SMA_20"]),
            "sma_200": float(latest["SMA_200"]),
            "volatility": float(latest["Volatility_20"])
        }
        
        return payload

if __name__ == "__main__":
    import sys
    ticker = sys.argv[1] if len(sys.argv) > 1 else "AAPL"
    agent = MathAgent()
    print(json.dumps(agent.execute({"ticker": ticker}), indent=2))
