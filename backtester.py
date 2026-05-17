"""
Backtesting Engine - Validate Predictions on Past Trends
=========================================================
Features:
- Historical data testing
- Performance metrics (Sharpe, Drawdown, Win Rate)
- Strategy comparison
- Portfolio simulation
"""
import os
import sys
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from collections import defaultdict

import pandas as pd
import numpy as np
import yfinance as yf

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Backtester")

try:
    import joblib
except ImportError:
    joblib = None


class BacktestConfig:
    """Backtest configuration"""
    def __init__(self):
        self.initial_capital = 10000
        self.commission = 0.001  # 0.1%
        self.slippage = 0.001   # 0.1%
        self.position_size = 0.1  # 10% per trade
        self.stop_loss = 0.05    # 5% stop loss
        self.take_profit = 0.10  # 10% take profit
        self.max_positions = 5
        self.data_dir = os.path.dirname(os.path.abspath(__file__))


class BacktestResult:
    """Individual backtest result"""
    def __init__(self, ticker: str):
        self.ticker = ticker
        self.trades = []
        self.equity_curve = []
        self.daily_returns = []
        self.predictions = []

    def add_trade(self, trade: Dict):
        self.trades.append(trade)

    def add_prediction(self, prediction: Dict):
        self.predictions.append(prediction)

    def calculate_metrics(self) -> Dict:
        if not self.equity_curve:
            return {}

        equity = pd.Series(self.equity_curve)
        returns = equity.pct_change().dropna()

        # Basic metrics
        total_return = (equity.iloc[-1] / equity.iloc[0] - 1) * 100 if len(equity) > 1 else 0
        win_rate = sum(1 for t in self.trades if t.get('profit', 0) > 0) / len(self.trades) * 100 if self.trades else 0

        # Advanced metrics
        if len(returns) > 1:
            sharpe = returns.mean() / returns.std() * np.sqrt(252) if returns.std() > 0 else 0
            max_dd = ((equity.cummax() - equity) / equity.cummax()).max() * 100
        else:
            sharpe = 0
            max_dd = 0

        return {
            "ticker": self.ticker,
            "total_return": total_return,
            "sharpe_ratio": sharpe,
            "max_drawdown": max_dd,
            "win_rate": win_rate,
            "total_trades": len(self.trades),
            "profitable_trades": sum(1 for t in self.trades if t.get('profit', 0) > 0),
            "avg_profit": np.mean([t.get('profit', 0) for t in self.trades]) if self.trades else 0,
            "avg_loss": np.mean([t.get('profit', 0) for t in self.trades if t.get('profit', 0) < 0]) if self.trades else 0
        }


class PredictionEngine:
    """Prediction engine using trained models"""

    def __init__(self, model_dir: str):
        self.model_dir = model_dir
        self.models = {}

    def load_model(self, ticker: str):
        """Load model for ticker"""
        model_path = os.path.join(self.model_dir, f"{ticker}_model.pkl")
        scaler_path = os.path.join(self.model_dir, f"{ticker}_scaler.pkl")

        if not os.path.exists(model_path):
            return None

        try:
            if joblib:
                model = joblib.load(model_path)
                scaler = joblib.load(scaler_path) if os.path.exists(scaler_path) else None
                return {"model": model, "scaler": scaler}
        except Exception as e:
            logger.warning(f"Could not load model for {ticker}: {e}")

        return None

    def predict(self, ticker: str, df: pd.DataFrame) -> Optional[Dict]:
        """Make prediction on recent data"""
        model_data = self.load_model(ticker)
        if not model_data:
            return None

        model = model_data["model"]
        scaler = model_data.get("scaler")

        # Calculate features
        df = self._calculate_features(df)

        # Get last row for prediction
        if len(df) < 20:
            return None

        feature_cols = [c for c in df.columns if c not in ['Close', 'Open', 'High', 'Low', 'Volume', 'Target']]
        X = df[feature_cols].iloc[-1:].values

        if scaler:
            X = scaler.transform(X)

        try:
            prediction = model.predict(X)[0]
            proba = model.predict_proba(X)[0] if hasattr(model, 'predict_proba') else [0.5, 0.5]

            return {
                "ticker": ticker,
                "prediction": "UP" if prediction == 1 else "DOWN",
                "confidence": float(max(proba)),
                "up_probability": float(proba[1]) if len(proba) > 1 else 0.5,
                "down_probability": float(proba[0]) if len(proba) > 0 else 0.5
            }
        except Exception as e:
            logger.warning(f"Prediction error for {ticker}: {e}")
            return None

    def _calculate_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate features"""
        df = df.copy()

        # Returns
        df['Returns'] = df['Close'].pct_change()

        # Moving averages
        for window in [5, 10, 20, 50]:
            df[f'SMA_{window}'] = df['Close'].rolling(window).mean()
            df[f'Volatility_{window}'] = df['Returns'].rolling(window).std()

        # RSI
        delta = df['Close'].diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))

        # MACD
        ema12 = df['Close'].ewm(span=12).mean()
        ema26 = df['Close'].ewm(span=26).mean()
        df['MACD'] = ema12 - ema26

        # Target
        df['Target'] = (df['Close'].shift(-1) > df['Close']).astype(int)

        return df


class Backtester:
    """Main backtesting engine"""

    def __init__(self, config: Optional[BacktestConfig] = None, model_dir: str = None):
        self.config = config or BacktestConfig()
        self.model_dir = model_dir or self.config.data_dir
        self.results = {}
        self.prediction_engine = PredictionEngine(self.model_dir)

    def run_backtest(self, ticker: str, start_date: str = None, end_date: str = None,
                     lookback_days: int = 365) -> BacktestResult:
        """Run backtest for a single ticker"""
        logger.info(f"Running backtest for {ticker}...")

        result = BacktestResult(ticker)

        # Default dates
        if not end_date:
            end_date = datetime.now()
        if not start_date:
            start_date = end_date - timedelta(days=lookback_days)

        # Fetch data
        try:
            stock = yf.Ticker(ticker)
            df = stock.history(start=start_date, end=end_date)
        except Exception as e:
            logger.error(f"Error fetching data for {ticker}: {e}")
            return result

        if df.empty or len(df) < 50:
            logger.warning(f"Insufficient data for {ticker}")
            return result

        # Initialize capital
        capital = self.config.initial_capital
        position = None
        equity = [capital]

        # Simulate trading day by day
        for i in range(50, len(df) - 1):
            # Get historical data up to this point
            historical = df.iloc[:i].copy()

            # Make prediction
            pred = self.prediction_engine.predict(ticker, historical)

            if pred:
                result.add_prediction({
                    "date": df.index[i],
                    "prediction": pred["prediction"],
                    "confidence": pred["confidence"],
                    "actual": "UP" if df['Close'].iloc[i+1] > df['Close'].iloc[i] else "DOWN"
                })

            # Trading logic
            if pred and pred["prediction"] == "UP" and not position and len(result.predictions) < self.config.max_positions:
                # Buy signal
                entry_price = df['Close'].iloc[i] * (1 + self.config.slippage)
                shares = int(capital * self.config.position_size / entry_price)

                if shares > 0:
                    position = {
                        "entry_date": df.index[i],
                        "entry_price": entry_price,
                        "shares": shares,
                        "stop_loss": entry_price * (1 - self.config.stop_loss),
                        "take_profit": entry_price * (1 + self.config.take_profit)
                    }
                    capital -= shares * entry_price * (1 + self.config.commission)

            elif position:
                # Check exit conditions
                current_price = df['Close'].iloc[i]

                # Stop loss
                if current_price <= position["stop_loss"]:
                    exit_price = current_price * (1 - self.config.slippage)
                    profit = (exit_price - position["entry_price"]) * position["shares"]
                    capital += position["shares"] * exit_price * (1 - self.config.commission)

                    result.add_trade({
                        "entry_date": position["entry_date"],
                        "exit_date": df.index[i],
                        "profit": profit,
                        "return": profit / (position["entry_price"] * position["shares"]) * 100
                    })
                    position = None

                # Take profit
                elif current_price >= position["take_profit"]:
                    exit_price = current_price * (1 - self.config.slippage)
                    profit = (exit_price - position["entry_price"]) * position["shares"]
                    capital += position["shares"] * exit_price * (1 - self.config.commission)

                    result.add_trade({
                        "entry_date": position["entry_date"],
                        "exit_date": df.index[i],
                        "profit": profit,
                        "return": profit / (position["entry_price"] * position["shares"]) * 100
                    })
                    position = None

            # Update equity
            if position:
                current_value = position["shares"] * df['Close'].iloc[i]
            else:
                current_value = capital
            equity.append(current_value)

        # Close any open position
        if position:
            final_price = df['Close'].iloc[-1]
            profit = (final_price - position["entry_price"]) * position["shares"]
            capital += position["shares"] * final_price * (1 - self.config.commission)

        result.equity_curve = equity
        self.results[ticker] = result

        return result

    def run_multi_backtest(self, tickers: List[str], start_date: str = None,
                          end_date: str = None, lookback_days: int = 365) -> Dict:
        """Run backtest for multiple tickers"""
        logger.info(f"Running backtest for {len(tickers)} tickers...")

        for i, ticker in enumerate(tickers):
            logger.info(f"Progress: {i+1}/{len(tickers)}")
            self.run_backtest(ticker, start_date, end_date, lookback_days)

        return self.get_summary()

    def get_summary(self) -> Dict:
        """Get overall summary"""
        if not self.results:
            return {"status": "no_results"}

        all_metrics = []
        for ticker, result in self.results.items():
            metrics = result.calculate_metrics()
            if metrics:
                all_metrics.append(metrics)

        if not all_metrics:
            return {"status": "no_metrics"}

        # Aggregate
        total_return = np.mean([m.get("total_return", 0) for m in all_metrics])
        avg_sharpe = np.mean([m.get("sharpe_ratio", 0) for m in all_metrics])
        avg_win_rate = np.mean([m.get("win_rate", 0) for m in all_metrics])
        avg_drawdown = np.mean([m.get("max_drawdown", 0) for m in all_metrics])

        return {
            "status": "complete",
            "total_tickers": len(self.results),
            "metrics": all_metrics,
            "aggregate": {
                "avg_return": total_return,
                "avg_sharpe": avg_sharpe,
                "avg_win_rate": avg_win_rate,
                "avg_max_drawdown": avg_drawdown
            }
        }

    def get_detailed_results(self) -> pd.DataFrame:
        """Get results as DataFrame"""
        rows = []
        for ticker, result in self.results.items():
            metrics = result.calculate_metrics()
            if metrics:
                rows.append(metrics)

        return pd.DataFrame(rows)


def run_backtest(tickers: List[str] = None):
    """Run backtest"""
    config = BacktestConfig()
    model_dir = os.path.dirname(os.path.abspath(__file__))

    print("\n" + "="*60)
    print("  BACKTESTING ENGINE")
    print("="*60)
    print(f"Initial Capital: ${config.initial_capital:,.2f}")
    print(f"Position Size: {config.position_size*100}%")
    print(f"Stop Loss: {config.stop_loss*100}%")
    print(f"Take Profit: {config.take_profit*100}%")
    print("="*60)

    tickers = tickers or ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]

    backtester = Backtester(config, model_dir)
    summary = backtester.run_multi_backtest(tickers)

    print("\n" + "="*60)
    print("  BACKTEST RESULTS")
    print("="*60)

    if "aggregate" in summary:
        agg = summary["aggregate"]
        print(f"\nAggregate Performance:")
        print(f"  Average Return: {agg['avg_return']:.2f}%")
        print(f"  Average Sharpe Ratio: {agg['avg_sharpe']:.2f}")
        print(f"  Average Win Rate: {agg['avg_win_rate']:.1f}%")
        print(f"  Average Max Drawdown: {agg['avg_max_drawdown']:.2f}%")

    print("\nPer-Ticker Results:")
    df = backtester.get_detailed_results()
    print(df.to_string(index=False))

    print("\n" + "="*60)

    return summary


if __name__ == "__main__":
    run_backtest()