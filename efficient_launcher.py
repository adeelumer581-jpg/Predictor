"""
Efficiency Launcher - Unified Entry Point
=========================================
Optimized, efficient launch of all components
"""
import os
import sys
import time
import json
import psutil
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("EfficiencyLauncher")

import yfinance as yf
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
import joblib


class EfficiencyMonitor:
    """Monitor and optimize system resources"""
    def __init__(self):
        self.start_time = time.time()
        self.metrics = []

    def log_metric(self, label, value):
        self.metrics.append({"label": label, "value": value, "time": time.time() - self.start_time})

    def get_stats(self):
        cpu = psutil.cpu_percent()
        mem = psutil.virtual_memory()
        elapsed = time.time() - self.start_time
        return {"cpu": cpu, "memory": mem.percent, "elapsed": f"{elapsed:.1f}s", "metrics": self.metrics}


class FastTrainer:
    """Optimized single-ticker trainer"""
    @staticmethod
    def train(ticker, period="180d"):
        start = time.time()
        try:
            stock = yf.Ticker(ticker)
            df = stock.history(period=period)
            if len(df) < 30:
                return {"ticker": ticker, "status": "insufficient_data", "time": time.time() - start}

            df['Returns'] = df['Close'].pct_change()
            df['SMA_10'] = df['Close'].rolling(10).mean()
            delta = df['Close'].diff()
            gain = delta.where(delta > 0, 0).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            df['RSI'] = 100 - (100 / (1 + (gain / loss.replace(0, 1)).replace([np.inf, -np.inf], 50)))
            df = df.dropna()

            if len(df) < 20:
                return {"ticker": ticker, "status": "insufficient_data", "time": time.time() - start}

            X = df[['Returns', 'SMA_10', 'RSI']].values[:-1]
            y = (df['Close'].shift(-1).values[:-1] > df['Close'].values[:-1]).astype(int)

            if len(X) < 20:
                return {"ticker": ticker, "status": "insufficient_data", "time": time.time() - start}

            scaler = StandardScaler()
            X_scaled = scaler.fit_transform(X)
            model = RandomForestClassifier(n_estimators=30, max_depth=5, random_state=42, n_jobs=1)
            model.fit(X_scaled, y)

            joblib.dump(model, f"{ticker}_model.pkl")
            joblib.dump(scaler, f"{ticker}_scaler.pkl")

            return {"ticker": ticker, "status": "success", "time": time.time() - start, "accuracy": model.score(X_scaled, y)}
        except Exception as e:
            return {"ticker": ticker, "status": "error", "error": str(e), "time": time.time() - start}


class FastBacktester:
    """Optimized backtester"""
    @staticmethod
    def backtest(ticker, days=60):
        start = time.time()
        try:
            stock = yf.Ticker(ticker)
            df = stock.history(period=f"{days+30}d")
            if len(df) < 30:
                return {"ticker": ticker, "status": "insufficient_data"}

            df['SMA_20'] = df['Close'].rolling(20).mean()
            df['Signal'] = (df['Close'] > df['SMA_20']).astype(int)
            df['Returns'] = df['Close'].pct_change()
            df['Strategy'] = df['Signal'].shift(1) * df['Returns']

            strategy_returns = df['Strategy'].dropna()
            total_return = (1 + strategy_returns).prod() - 1
            sharpe = strategy_returns.mean() / strategy_returns.std() * np.sqrt(252) if strategy_returns.std() > 0 else 0

            return {"ticker": ticker, "status": "success", "time": time.time() - start, "return": total_return * 100, "sharpe": sharpe}
        except Exception as e:
            return {"ticker": ticker, "status": "error", "error": str(e)}


def main():
    print("\n" + "="*70)
    print("  STOCK PREDICTOR - EFFICIENT MODE")
    print("="*70)

    monitor = EfficiencyMonitor()
    TICKERS = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA", "META", "NFLX", "AMD", "INTC", "CRM", "ADBE"]

    print(f"\nProcessing {len(TICKERS)} tickers...\n")
    print("PHASE 1: Training Models")
    print("="*70)

    train_results = []
    for i, ticker in enumerate(TICKERS):
        result = FastTrainer.train(ticker)
        train_results.append(result)
        status = "OK" if result["status"] == "success" else "FAIL"
        print(f"[{i+1}/{len(TICKERS)}] {ticker:6} {status:4} {result.get('time', 0):.1f}s")

    success_train = sum(1 for r in train_results if r['status'] == 'success')
    print(f"\nTraining: {success_train}/{len(TICKERS)} successful")

    print("\nPHASE 2: Backtesting")
    print("="*70)

    trained = [r['ticker'] for r in train_results if r['status'] == 'success']
    for i, ticker in enumerate(trained[:8]):
        result = FastBacktester.backtest(ticker)
        print(f"{ticker:6} Return: {result.get('return', 0):7.2f}% Sharpe: {result.get('sharpe', 0):5.2f}")

    stats = monitor.get_stats()
    print("\n" + "="*70)
    print(f"Elapsed: {stats['elapsed']} | CPU: {stats['cpu']:.1f}% | Memory: {stats['memory']:.1f}%")
    print("="*70)

    with open("efficiency_results.json", "w") as f:
        json.dump({"training": train_results, "stats": stats}, f, indent=2)

    print("Results saved.")


if __name__ == "__main__":
    main()