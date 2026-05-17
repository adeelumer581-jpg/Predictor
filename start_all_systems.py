"""
UNIFIED SYSTEM LAUNCHER
=======================
Starts all agents, marketplace, and live training systems together.
"""
import asyncio
import logging
import os
import sys
import time
import threading
import json
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("UnifiedLauncher")

# Add project path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import agents
from agent_system.training_agent import TrainingAgent
from agent_system.antigravity_agent import AntiGravityAgent
from agent_system.agent_coordinator import get_coordinator
import yfinance as yf
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
import joblib
import psutil


class LiveMarketTrainer:
    """Live market training with candlestick pattern recognition"""

    def __init__(self):
        self.tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA",
                       "AMD", "INTC", "NFLX", "CRM", "ADBE", "DIS", "JPM", "BAC"]
        self.models = {}
        self.scalers = {}
        self.patterns_detected = {}

    def detect_candlestick_patterns(self, df):
        """Detect candlestick patterns for prediction"""
        patterns = {
            "DOJI": False,
            "HAMMER": False,
            "SHOOTING_STAR": False,
            "BULLISH_ENGULFING": False,
            "BEARISH_ENGULFING": False,
            "MORNING_STAR": False,
            "EVENING_STAR": False
        }

        if len(df) < 3:
            return patterns

        # Latest candle
        latest = df.iloc[-1]
        prev = df.iloc[-2]

        # Calculate body and shadows
        body = latest['Close'] - latest['Open']
        body_size = abs(body)
        upper_shadow = latest['High'] - max(latest['Close'], latest['Open'])
        lower_shadow = min(latest['Close'], latest['Open']) - latest['Low']
        total_range = latest['High'] - latest['Low']

        # Doji - very small body
        if body_size < total_range * 0.1:
            patterns["DOJI"] = True

        # Hammer - small body, long lower shadow
        if lower_shadow > body_size * 2 and upper_shadow < body_size:
            patterns["HAMMER"] = True

        # Shooting Star - small body, long upper shadow
        if upper_shadow > body_size * 2 and lower_shadow < body_size:
            patterns["SHOOTING_STAR"] = True

        # Bullish Engulfing
        if (prev['Close'] < prev['Open'] and
            latest['Close'] > latest['Open'] and
            latest['Open'] < prev['Close'] and
            latest['Close'] > prev['Open']):
            patterns["BULLISH_ENGULFING"] = True

        # Bearish Engulfing
        if (prev['Close'] > prev['Open'] and
            latest['Close'] < latest['Open'] and
            latest['Open'] > prev['Close'] and
            latest['Close'] < prev['Open']):
            patterns["BEARISH_ENGULFING"] = True

        return patterns

    def calculate_indicators(self, df):
        """Calculate technical indicators"""
        df = df.copy()

        # Returns
        df['Returns'] = df['Close'].pct_change()

        # Moving averages
        for window in [5, 10, 20, 50]:
            df[f'SMA_{window}'] = df['Close'].rolling(window).mean()

        # RSI
        delta = df['Close'].diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss.replace(0, 1)
        df['RSI'] = 100 - (100 / (1 + rs))

        # EMA
        df['EMA_12'] = df['Close'].ewm(span=12).mean()
        df['EMA_26'] = df['Close'].ewm(span=26).mean()
        df['MACD'] = df['EMA_12'] - df['EMA_26']

        # Volatility
        df['Volatility_10'] = df['Returns'].rolling(10).std()

        return df

    def prepare_features(self, df):
        """Prepare features for model training"""
        df = self.calculate_indicators(df)
        df = df.dropna()

        if len(df) < 20:
            return None, None

        # Features: price action + patterns + indicators
        feature_cols = ['Returns', 'SMA_5', 'SMA_10', 'SMA_20', 'RSI', 'MACD', 'Volatility_10', 'EMA_12', 'EMA_26']

        X = df[feature_cols].values[:-1]

        # Target: 1 if next day up, 0 if down
        y = (df['Close'].shift(-1).values[:-1] > df['Close'].values[:-1]).astype(int)

        if len(X) < 20:
            return None, None

        return X, y

    def train_ticker(self, ticker):
        """Train a single ticker with live data"""
        try:
            stock = yf.Ticker(ticker)
            df = stock.history(period="180d")

            if len(df) < 30:
                return {"ticker": ticker, "status": "insufficient_data"}

            # Detect patterns
            patterns = self.detect_candlestick_patterns(df)
            self.patterns_detected[ticker] = patterns

            # Prepare features
            X, y = self.prepare_features(df)
            if X is None:
                return {"ticker": ticker, "status": "insufficient_features"}

            # Scale features
            scaler = StandardScaler()
            X_scaled = scaler.fit_transform(X)

            # Train model
            model = RandomForestClassifier(
                n_estimators=50,
                max_depth=7,
                random_state=42,
                n_jobs=1
            )
            model.fit(X_scaled, y)

            # Save
            model_path = f"{ticker}_model.pkl"
            scaler_path = f"{ticker}_scaler.pkl"
            joblib.dump(model, model_path)
            joblib.dump(scaler, scaler_path)

            self.models[ticker] = model
            self.scalers[ticker] = scaler

            accuracy = model.score(X_scaled, y)

            return {
                "ticker": ticker,
                "status": "success",
                "accuracy": accuracy,
                "patterns": patterns,
                "last_price": float(df['Close'].iloc[-1])
            }

        except Exception as e:
            return {"ticker": ticker, "status": "error", "error": str(e)}

    def predict_today(self, ticker):
        """Predict for today using trained model"""
        if ticker not in self.models:
            return None

        try:
            stock = yf.Ticker(ticker)
            df = stock.history(period="30d")

            if len(df) < 5:
                return None

            df = self.calculate_indicators(df)
            df = df.dropna()

            if len(df) < 5:
                return None

            feature_cols = ['Returns', 'SMA_5', 'SMA_10', 'SMA_20', 'RSI', 'MACD', 'Volatility_10', 'EMA_12', 'EMA_26']
            X = df[feature_cols].iloc[-1:].values

            X_scaled = self.scalers[ticker].transform(X)
            prediction = self.models[ticker].predict(X_scaled)[0]
            probability = self.models[ticker].predict_proba(X_scaled)[0]

            return {
                "ticker": ticker,
                "prediction": "UP" if prediction == 1 else "DOWN",
                "confidence": float(max(probability)),
                "pattern": self.patterns_detected.get(ticker, {})
            }

        except Exception as e:
            return None


class AntiGravityOptimizer:
    """Anti-Gravity optimization wrapper"""

    def __init__(self):
        self.agent = AntiGravityAgent()
        self.metrics = {
            "training_time_ms": [],
            "memory_mb": [],
            "accuracy": [],
            "predictions_made": 0
        }

    def optimize_training(self, trainer):
        """Apply anti-gravity optimizations to training"""
        start_time = time.time()

        # Train all tickers
        results = []
        for ticker in trainer.tickers:
            result = trainer.train_ticker(ticker)
            results.append(result)

        training_time = (time.time() - start_time) * 1000 / len(trainer.tickers)

        # Record metrics
        memory_mb = psutil.virtual_memory().used / (1024 * 1024)
        accuracy = np.mean([r.get('accuracy', 0) for r in results if r.get('status') == 'success'])

        self.metrics["training_time_ms"].append(training_time)
        self.metrics["memory_mb"].append(memory_mb)
        self.metrics["accuracy"].append(accuracy)
        self.metrics["predictions_made"] += len([r for r in results if r.get('status') == 'success'])

        # Apply optimizations
        self.apply_optimizations(results)

        return {
            "training_time_ms": training_time,
            "memory_mb": memory_mb,
            "accuracy": accuracy,
            "results": results
        }

    def apply_optimizations(self, results):
        """Apply anti-gravity optimization rules"""
        # Memory optimization
        import gc
        gc.collect()

        # Report to anti-gravity agent
        logger.info(f"Anti-Gravity Metrics: {len(self.metrics['training_time_ms'])} training cycles completed")


class UnifiedSystem:
    """Unified system controller"""

    def __init__(self):
        self.coordinator = get_coordinator()
        self.trainer = LiveMarketTrainer()
        self.optimizer = AntiGravityOptimizer()
        self.is_running = False

    async def start_all_agents(self):
        """Start all agents"""
        logger.info("\n" + "="*60)
        logger.info("ACTIVATING ALL AGENTS")
        logger.info("="*60)

        # Training Agent
        training_agent = TrainingAgent(tickers=self.trainer.tickers)
        self.coordinator.register_agent("TrainingAgent", training_agent)
        logger.info("[OK] Training Agent activated")

        # Anti-Gravity Agent
        self.coordinator.register_agent("AntiGravityAgent", self.optimizer.agent)
        logger.info("[OK] Anti-Gravity Agent activated")

        logger.info("\nAll agents connected to coordinator")

    async def run_live_training(self, cycles=10, interval=30):
        """Run live market training cycles"""
        logger.info(f"\nStarting live market training: {cycles} cycles every {interval}s")

        for cycle in range(cycles):
            logger.info(f"\n--- Cycle {cycle + 1}/{cycles} ---")

            # Anti-gravity optimized training
            results = self.optimizer.optimize_training(self.trainer)

            logger.info(f"Training time: {results['training_time_ms']:.0f}ms/ticker")
            logger.info(f"Memory: {results['memory_mb']:.0f}MB")
            logger.info(f"Accuracy: {results['accuracy']*100:.1f}%")

            # Make predictions
            predictions = []
            for ticker in self.trainer.tickers[:5]:
                pred = self.trainer.predict_today(ticker)
                if pred:
                    predictions.append(pred)
                    logger.info(f"  {ticker}: {pred['prediction']} ({pred['confidence']*100:.0f}% confidence)")

            # Save cycle results
            self.save_results(cycle, results, predictions)

            if cycle < cycles - 1:
                await asyncio.sleep(interval)

        return self.get_summary()

    def save_results(self, cycle, training_results, predictions):
        """Save cycle results"""
        data = {
            "cycle": cycle,
            "timestamp": datetime.now().isoformat(),
            "training": training_results,
            "predictions": predictions
        }
        with open(f"cycle_{cycle}_results.json", "w") as f:
            json.dump(data, f, indent=2)

    def get_summary(self):
        """Get system summary"""
        return {
            "training_cycles": len(self.optimizer.metrics["training_time_ms"]),
            "avg_training_time_ms": np.mean(self.optimizer.metrics["training_time_ms"]),
            "avg_memory_mb": np.mean(self.optimizer.metrics["memory_mb"]),
            "avg_accuracy": np.mean(self.optimizer.metrics["accuracy"]),
            "total_predictions": self.optimizer.metrics["predictions_made"]
        }


async def main():
    """Main entry point"""
    print("\n" + "="*70)
    print("  STOCK PREDICTOR - UNIFIED AGENT SYSTEM")
    print("  Live Market Training + Anti-Gravity Optimization")
    print("="*70)

    system = UnifiedSystem()

    # Start all agents
    await system.start_all_agents()

    # Run live training
    print("\nStarting live market training with candlestick patterns...")
    summary = await system.run_live_training(cycles=5, interval=20)

    # Print final summary
    print("\n" + "="*70)
    print("  SYSTEM SUMMARY")
    print("="*70)
    print(f"  Training Cycles: {summary['training_cycles']}")
    print(f"  Avg Training Time: {summary['avg_training_time_ms']:.0f}ms per ticker")
    print(f"  Avg Memory: {summary['avg_memory_mb']:.0f}MB")
    print(f"  Avg Accuracy: {summary['avg_accuracy']*100:.1f}%")
    print(f"  Total Predictions: {summary['total_predictions']}")
    print("="*70)

    print("\n[SYSTEM READY]")
    print("Marketplace: http://localhost:5002")

    return summary


if __name__ == "__main__":
    asyncio.run(main())