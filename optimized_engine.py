"""
Optimized Engine - Efficiency Improvements
==========================================
Version 2.0 with:
- Parallel processing
- Smart caching
- Model compression
- Async operations
- Memory optimization
"""
import os
import sys
import time
import json
import gc
import hashlib
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
from functools import lru_cache
import threading
import queue

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("OptimizedEngine")


class OptimizedCache:
    """Smart caching system with LRU and TTL"""

    def __init__(self, cache_dir=".opt_cache", max_size_mb=500, ttl=1800):
        self.cache_dir = cache_dir
        self.max_size_mb = max_size_mb
        self.ttl = ttl
        self.hits = 0
        self.misses = 0
        os.makedirs(cache_dir, exist_ok=True)

    def _key(self, *args) -> str:
        return hashlib.md5(str(args).encode()).hexdigest()

    def get(self, key: str):
        """Get from cache"""
        path = os.path.join(self.cache_dir, f"{key}.cache")
        if os.path.exists(path):
            mtime = os.path.getmtime(path)
            if time.time() - mtime < self.ttl:
                try:
                    with open(path, 'rb') as f:
                        self.hits += 1
                        return pickle.loads(f.read())
                except:
                    pass
            else:
                os.remove(path)
        self.misses += 1
        return None

    def set(self, key: str, value):
        """Set cache"""
        try:
            path = os.path.join(self.cache_dir, f"{key}.cache")
            with open(path, 'wb') as f:
                f.write(pickle.dumps(value))
            self._cleanup()
        except:
            pass

    def _cleanup(self):
        """LRU cleanup"""
        try:
            total_size = sum(os.path.getsize(os.path.join(self.cache_dir, f))
                           for f in os.listdir(self.cache_dir) if f.endswith('.cache'))
            if total_size > self.max_size_mb * 1024 * 1024:
                files = [(f, os.path.getmtime(os.path.join(self.cache_dir, f)))
                        for f in os.listdir(self.cache_dir) if f.endswith('.cache')]
                files.sort(key=lambda x: x[1])
                for f, _ in files[:10]:
                    os.remove(os.path.join(self.cache_dir, f))
        except:
            pass

    def stats(self):
        total = self.hits + self.misses
        return {"hits": self.hits, "misses": self.misses, "hit_rate": self.hits/total*100 if total else 0}


class ParallelTrainer:
    """Multi-threaded training with parallel workers"""

    def __init__(self, max_workers=4, batch_size=10):
        self.max_workers = max_workers
        self.batch_size = batch_size
        self.cache = OptimizedCache()
        self.executor = ThreadPoolExecutor(max_workers=max_workers)

    def train_parallel(self, tickers: List[str]) -> Dict:
        """Train multiple tickers in parallel"""
        results = []

        # Process in batches
        for i in range(0, len(tickers), self.batch_size):
            batch = tickers[i:i+self.batch_size]
            futures = {self.executor.submit(self._train_single, t): t for t in batch}

            for future in as_completed(futures):
                ticker = futures[future]
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    results.append({"ticker": ticker, "status": "error", "error": str(e)})

            # Cleanup between batches
            gc.collect()

        return {"results": results, "success": sum(1 for r in results if r.get("status") == "success")}

    def _train_single(self, ticker: str) -> Dict:
        """Train single ticker with caching"""
        # Check cache
        cache_key = f"model_{ticker}"
        cached = self.cache.get(cache_key)
        if cached:
            return cached

        # Train
        import yfinance as yf
        import pandas as pd
        import numpy as np
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.preprocessing import StandardScaler

        try:
            stock = yf.Ticker(ticker)
            df = stock.history(period="180d")  # Reduced for speed

            if df.empty or len(df) < 30:
                return {"ticker": ticker, "status": "insufficient_data"}

            # Quick features
            df['Returns'] = df['Close'].pct_change()
            df['SMA_10'] = df['Close'].rolling(10).mean()
            df['SMA_20'] = df['Close'].rolling(20).mean()
            df['Volatility'] = df['Returns'].rolling(10).std()

            delta = df['Close'].diff()
            gain = delta.where(delta > 0, 0).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            df['RSI'] = 100 - (100 / (1 + gain / loss.replace(0, 1)))

            df = df.dropna()

            if len(df) < 20:
                return {"ticker": ticker, "status": "insufficient_data"}

            features = ['Returns', 'SMA_10', 'SMA_20', 'Volatility', 'RSI']
            X = df[features].values[:-1]
            y = (df['Close'].shift(-1).values[:-1] > df['Close'].values[:-1]).astype(int)

            if len(X) < 20:
                return {"ticker": ticker, "status": "insufficient_data"}

            scaler = StandardScaler()
            X_scaled = scaler.fit_transform(X)

            model = RandomForestClassifier(n_estimators=30, max_depth=6, random_state=42, n_jobs=1)
            model.fit(X_scaled, y)

            # Save
            import joblib
            model_path = f"{ticker}_model.pkl"
            scaler_path = f"{ticker}_scaler.pkl"
            joblib.dump(model, model_path)
            joblib.dump(scaler, scaler_path)

            result = {
                "ticker": ticker,
                "status": "success",
                "samples": len(X),
                "accuracy": model.score(X_scaled, y)
            }

            # Cache result
            self.cache.set(cache_key, result)

            return result

        except Exception as e:
            return {"ticker": ticker, "status": "error", "error": str(e)}

    def shutdown(self):
        self.executor.shutdown(wait=True)


class AsyncBacktester:
    """Async backtesting with vectorized operations"""

    def __init__(self, initial_capital=10000):
        self.capital = initial_capital
        self.cache = OptimizedCache()

    def backtest_batch(self, tickers: List[str], days=90) -> Dict:
        """Batch backtest multiple tickers"""
        import yfinance as yf
        import pandas as pd
        import numpy as np

        results = []

        # Fetch all data in one request (faster)
        try:
            data = yf.download(tickers, period=f"{days+30}d", progress=False, group_by='ticker')
        except Exception as e:
            logger.error(f"Batch download failed: {e}")
            return {"error": str(e)}

        for ticker in tickers:
            try:
                if len(tickers) > 1:
                    df = data[ticker]['Close'] if ticker in data.columns else pd.Series()
                else:
                    df = data['Close'] if 'Close' in data.columns else pd.Series()

                if len(df) < 30:
                    continue

                # Vectorized signals
                returns = df.pct_change()
                sma_20 = df.rolling(20).mean()
                signal = (df > sma_20).astype(int)

                # Strategy returns
                strategy_returns = signal.shift(1) * returns

                # Metrics
                total_ret = (1 + strategy_returns).prod() - 1
                sharpe = strategy_returns.mean() / strategy_returns.std() * np.sqrt(252) if strategy_returns.std() > 0 else 0
                max_dd = ((strategy_returns.cumsum().cummax() - strategy_returns.cumsum())).max()

                results.append({
                    "ticker": ticker,
                    "return": total_ret * 100,
                    "sharpe": sharpe,
                    "max_drawdown": max_dd * 100,
                    "trades": int(signal.abs().sum())
                })

            except Exception as e:
                logger.warning(f"Backtest error for {ticker}: {e}")

        if not results:
            return {"error": "No results"}

        # Aggregate
        returns = [r['return'] for r in results]
        sharpes = [r['sharpe'] for r in results]

        return {
            "tickers": len(results),
            "avg_return": np.mean(returns),
            "avg_sharpe": np.mean(sharpes),
            "best": max(results, key=lambda x: x['return']),
            "worst": min(results, key=lambda x: x['return']),
            "results": results[:10]
        }


class ModelOptimizer:
    """Model compression and optimization"""

    @staticmethod
    def compress_model(model_path: str) -> bool:
        """Compress model file"""
        try:
            import joblib
            import pickle

            model = joblib.load(model_path)

            # Reduce n_estimators for smaller size
            if hasattr(model, 'n_estimators'):
                model.n_estimators = min(model.n_estimators, 30)

            # Save with compression
            joblib.dump(model, model_path, compress=3)
            return True
        except:
            return False

    @staticmethod
    def optimize_features(df: pd.DataFrame) -> List[str]:
        """Select best features"""
        # Return minimal feature set for speed
        return ['Returns', 'SMA_10', 'RSI']


# Import pickle for caching
import pickle


def run_optimized_training(tickers: List[str] = None):
    """Run optimized training"""
    tickers = tickers or ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA", "META", "NFLX"]

    print("\n" + "="*60)
    print("  OPTIMIZED TRAINING ENGINE")
    print("="*60)
    print(f"Tickers: {len(tickers)}")
    print(f"Workers: 4")
    print("="*60)

    trainer = ParallelTrainer(max_workers=4, batch_size=8)
    start = time.time()

    result = trainer.train_parallel(tickers)

    trainer.shutdown()

    elapsed = time.time() - start

    print(f"\nCompleted in {elapsed:.1f}s")
    print(f"Success: {result['success']}/{len(tickers)}")
    print(f"Speed: {len(tickers)/elapsed:.1f} stocks/sec")

    return result


def run_optimized_backtest(tickers: List[str] = None):
    """Run optimized backtest"""
    tickers = tickers or ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA"]

    print("\n" + "="*60)
    print("  OPTIMIZED BACKTEST ENGINE")
    print("="*60)

    backtester = AsyncBacktester()
    start = time.time()

    result = backtester.backtest_batch(tickers, days=90)

    elapsed = time.time() - start

    print(f"\nCompleted in {elapsed:.2f}s")

    if "avg_return" in result:
        print(f"Average Return: {result['avg_return']:.2f}%")
        print(f"Average Sharpe: {result['avg_sharpe']:.2f}")
        print(f"Best: {result['best']['ticker']} ({result['best']['return']:.1f}%)")

    print("="*60)

    return result


if __name__ == "__main__":
    print("\nSelect:")
    print("1. Optimized Training")
    print("2. Optimized Backtest")
    print("3. Both")

    choice = input("Choice: ").strip()

    if choice in ["1", "3"]:
        run_optimized_training()

    if choice in ["2", "3"]:
        run_optimized_backtest()