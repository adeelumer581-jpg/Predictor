"""
UNIVERSAL TRAINING SYSTEM
=========================
Trains ALL agents, ALL employees, on ALL data in continuous loops
Covers EVERYTHING in the app: Stocks, Crypto, Commodities, Forex, Pakistani Stocks
"""
import os
import sys
import time
import json
import logging
import asyncio
import threading
from datetime import datetime
from typing import Dict, List, Any
import yfinance as yf
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.preprocessing import StandardScaler
import joblib

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("UniversalTraining")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


class UniversalDataSource:
    """ALL possible assets for training"""
    
    # Pakistani Stocks
    PAKISTANI_STOCKS = [
        "OGDC", "PSO", "PPL", "HUBC", "EFERT", "LUCK", "ENGRO", "FFBL", 
        "FCCL", "DGKC", "HBL", "UBL", "BAFL", "MCB", "BAHN", "NML", 
        "NCC", "SNGP", "MUGHAL", "JKLC"
    ]
    
    # Global Stocks (200+ tickers)
    GLOBAL_STOCKS = [
        # Tech Giants
        "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "NFLX", "ADBE", "CRM",
        "ORCL", "IBM", "INTC", "AMD", "QCOM", "TXN", "AVGO", "MU", "AMAT", "LRCX",
        "PANW", "FTNT", "CRWD", "NET", "DDOG", "SNOW", "ZM", "OKTA", "WDAY", "NOW",
        "SHOP", "SQ", "PYPL", "UBER", "LYFT", "ABNB", "DASH", "COIN",
        # Finance
        "JPM", "BAC", "WFC", "C", "GS", "MS", "AXP", "V", "MA", "PYPL",
        "BLK", "SCHW", "PNC", "USB", "BK", "STT", "COF", "DFS", "ALLY",
        # Healthcare
        "JNJ", "UNH", "PFE", "ABBV", "MRK", "LLY", "TMO", "ABT", "DHR", "MDT",
        "BMY", "AMGN", "GILD", "REGN", "VRTX", "BIIB", "MRNA", "ISRG", "SYK", "ZTS",
        "CVS", "CI", "HUM", "ANTM", "ELV",
        # Consumer
        "WMT", "HD", "COST", "TGT", "LOW", "NKE", "SBUX", "MCD", "KO", "PEP",
        "PG", "CL", "KMB", "MDLZ", "KHC", "HSY", "DG", "DLTR", "ROST", "TJX",
        "LULU", "ULTA", "BBY", "GPS", "M", "JWN",
        # Energy
        "XOM", "CVX", "COP", "EOG", "SLB", "MPC", "PSX", "VLO", "OXY", "DVN",
        "HAL", "BKR", "NOV", "FTI", "HP",
        # Industrials
        "BA", "CAT", "GE", "HON", "UPS", "RTX", "LMT", "MMM", "DE", "EMR",
        "ITW", "ETN", "CMI", "ROK", "PH", "GRMN", "FDX", "UNP", "CSX", "NSC",
        "DAL", "UAL", "AAL", "LUV", "JBLU",
        # Materials
        "LIN", "APD", "ECL", "SHW", "DD", "DOW", "NEM", "FCX", "NUE", "STLD",
        # Real Estate
        "AMT", "PLD", "CCI", "EQIX", "PSA", "SPG", "O", "WELL", "DLR", "AVB",
        # Utilities
        "NEE", "DUK", "SO", "D", "AEP", "EXC", "SRE", "XEL", "WEC", "ES",
        # Communication
        "DIS", "CMCSA", "VZ", "T", "TMUS", "CHTR", "NFLX", "PARA", "WBD", "FOXA",
        # Other
        "SPGI", "MCO", "ICE", "CME", "MSCI", "TRV", "PGR", "ALL", "CB", "AIG"
    ]
    
    # Commodities
    COMMODITIES = [
        "GC=F", "SI=F", "PL=F", "PA=F",  # Precious Metals
        "CL=F", "NG=F", "RB=F", "HO=F",  # Energy
        "ZW=F", "ZC=F", "ZS=F", "KE=F", "CT=F", "OJ=F", "LTC=F", "HE=F",  # Agriculture
        "HG=F", "ALU=F", "NI=F", "PB=F"  # Base Metals
    ]
    
    # Cryptocurrency
    CRYPTO = [
        "BTC-USD", "ETH-USD", "BNB-USD", "XRP-USD", "ADA-USD", "DOGE-USD",
        "SOL-USD", "DOT-USD", "POL-USD", "LTC-USD", "AVAX-USD", "LINK-USD",
        "ATOM-USD", "XLM-USD", "VET-USD", "FIL-USD", "THETA-USD",
        "ALGO-USD", "MANA-USD", "SAND-USD", "AAVE-USD", "MKR-USD", "NEAR-USD",
        "UNI-USD", "SUSHI-USD", "COMP-USD", "YFI-USD", "SNX-USD", "CRV-USD"
    ]
    
    # Indices
    INDICES = [
        "^GSPC", "^DJI", "^IXIC", "^RUT", "^VIX", "^TNX", "^NSE"
    ]
    
    @classmethod
    def get_all_assets(cls) -> List[str]:
        """Get ALL assets for training"""
        all_assets = []
        all_assets.extend(cls.PAKISTANI_STOCKS)
        all_assets.extend(cls.GLOBAL_STOCKS)
        all_assets.extend(cls.COMMODITIES)
        all_assets.extend(cls.CRYPTO)
        all_assets.extend(cls.INDICES)
        return list(set(all_assets))


class UniversalTrainingEngine:
    """Trains models on ALL data"""
    
    def __init__(self):
        self.models_trained = {}
        self.training_stats = {
            "total_trained": 0,
            "successful": 0,
            "failed": 0,
            "start_time": datetime.now().isoformat()
        }
        self.lock = threading.RLock()
    
    def calculate_all_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate ALL technical indicators"""
        df = df.copy()
        if df.empty or len(df) < 50:
            return df
        
        # Ensure all OHLCV columns exist
        for col in ["Open", "High", "Low", "Close"]:
            if col not in df:
                df[col] = df["Close"] if "Close" in df else 0
        if "Volume" not in df:
            df["Volume"] = 0
        
        # Returns
        df['Returns'] = df['Close'].pct_change()
        df['Log_Returns'] = np.log(df['Close'] / df['Close'].shift(1))
        
        # Moving Averages (ALL periods)
        for w in [5, 10, 12, 20, 26, 50, 100, 200]:
            df[f'SMA_{w}'] = df['Close'].rolling(w, min_periods=1).mean()
            df[f'EMA_{w}'] = df['Close'].ewm(span=w, adjust=False).mean()
        
        # Volatility (ALL periods)
        for w in [5, 10, 20, 50]:
            df[f'Volatility_{w}'] = df['Returns'].rolling(w, min_periods=1).std() * np.sqrt(252)
        
        # RSI (ALL periods)
        delta = df['Close'].diff()
        for period in [7, 14, 21]:
            gain = delta.where(delta > 0, 0).rolling(period, min_periods=1).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(period, min_periods=1).mean()
            rs = gain / loss.replace(0, 1)
            df[f'RSI_{period}'] = 100 - (100 / (1 + rs))
        
        # MACD
        ema12 = df['Close'].ewm(span=12, adjust=False).mean()
        ema26 = df['Close'].ewm(span=26, adjust=False).mean()
        df['MACD'] = ema12 - ema26
        df['MACD_Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
        df['MACD_Hist'] = df['MACD'] - df['MACD_Signal']
        
        # Bollinger Bands
        df['BB_Middle'] = df['Close'].rolling(20, min_periods=1).mean()
        bb_std = df['Close'].rolling(20, min_periods=1).std()
        df['BB_Upper'] = df['BB_Middle'] + (bb_std * 2)
        df['BB_Lower'] = df['BB_Middle'] - (bb_std * 2)
        df['BB_Width'] = (df['BB_Upper'] - df['BB_Lower']) / df['BB_Middle']
        
        # Stochastic
        low14 = df['Low'].rolling(14, min_periods=1).min()
        high14 = df['High'].rolling(14, min_periods=1).max()
        df['Stoch_K'] = 100 * (df['Close'] - low14) / (high14 - low14).replace(0, 1)
        df['Stoch_D'] = df['Stoch_K'].rolling(3, min_periods=1).mean()
        
        # ATR
        high_low = df['High'] - df['Low']
        high_close = abs(df['High'] - df['Close'].shift())
        low_close = abs(df['Low'] - df['Close'].shift())
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df['ATR_14'] = true_range.rolling(14, min_periods=1).mean()
        df['ATR_20'] = true_range.rolling(20, min_periods=1).mean()
        
        # Volume indicators
        df['Volume_SMA_20'] = df['Volume'].rolling(20, min_periods=1).mean()
        df['Volume_Ratio'] = df['Volume'] / df['Volume_SMA_20'].replace(0, np.nan)
        df['OBV'] = (np.sign(df['Close'].diff()) * df['Volume']).fillna(0).cumsum()
        
        # Momentum
        df['Momentum_10'] = df['Close'] - df['Close'].shift(10)
        df['Momentum_20'] = df['Close'] - df['Close'].shift(20)
        df['ROC_10'] = (df['Close'] - df['Close'].shift(10)) / df['Close'].shift(10).replace(0, 1) * 100
        df['ROC_20'] = (df['Close'] - df['Close'].shift(20)) / df['Close'].shift(20).replace(0, 1) * 100
        
        # Price Oscillator
        df['Price_Oscillator'] = (df['SMA_10'] - df['SMA_20']) / df['SMA_20'].replace(0, 1) * 100
        
        return df.replace([np.inf, -np.inf], np.nan).ffill().bfill()
    
    def prepare_training_data(self, df: pd.DataFrame) -> tuple:
        """Prepare X, y for training"""
        if df.empty or len(df) < 50:
            return None, None
        
        # Calculate indicators
        df = self.calculate_all_indicators(df)
        
        # Feature columns (ALL indicators)
        feature_cols = [
            'Returns', 'Log_Returns',
            'SMA_5', 'SMA_10', 'SMA_20', 'SMA_50', 'SMA_100', 'SMA_200',
            'EMA_5', 'EMA_10', 'EMA_20', 'EMA_50', 'EMA_100', 'EMA_200',
            'BB_Upper', 'BB_Middle', 'BB_Lower', 'BB_Width',
            'RSI_7', 'RSI_14', 'RSI_21',
            'MACD', 'MACD_Signal', 'MACD_Hist',
            'Stoch_K', 'Stoch_D',
            'ATR_14', 'ATR_20',
            'Volatility_5', 'Volatility_10', 'Volatility_20', 'Volatility_50',
            'Momentum_10', 'Momentum_20', 'ROC_10', 'ROC_20',
            'Volume_Ratio', 'OBV', 'Price_Oscillator'
        ]
        
        # Target: 1 if next day price goes up, 0 if down
        df['Target'] = (df['Close'].shift(-1) > df['Close']).astype(int)
        
        # Drop rows with NaN
        df = df.dropna()
        
        if len(df) < 30:
            return None, None
        
        X = df[feature_cols].values
        y = df['Target'].values
        
        return X[:-1], y[:-1]  # Remove last row (no future target)
    
    def train_single_asset(self, ticker: str) -> Dict[str, Any]:
        """Train model for a single asset"""
        logger.info(f"Training {ticker}...")
        start_time = time.time()
        
        try:
            # Download data
            stock = yf.Ticker(ticker)
            df = stock.history(period="2y", auto_adjust=False)
            
            if df is None or len(df) < 100:
                logger.warning(f"{ticker}: Insufficient data")
                return {"ticker": ticker, "status": "insufficient_data"}
            
            # Prepare training data
            X, y = self.prepare_training_data(df)
            
            if X is None or len(X) < 30:
                logger.warning(f"{ticker}: Could not prepare training data")
                return {"ticker": ticker, "status": "preparation_failed"}
            
            # Split train/test
            split_idx = int(len(X) * 0.8)
            X_train, X_test = X[:split_idx], X[split_idx:]
            y_train, y_test = y[:split_idx], y[split_idx:]
            
            # Scale features
            scaler = StandardScaler()
            X_train_scaled = scaler.fit_transform(X_train)
            X_test_scaled = scaler.transform(X_test)
            
            # Train TWO models (ensemble)
            rf_model = RandomForestClassifier(
                n_estimators=100,
                max_depth=10,
                min_samples_split=5,
                random_state=42,
                n_jobs=-1
            )
            
            gb_model = GradientBoostingClassifier(
                n_estimators=100,
                max_depth=5,
                learning_rate=0.1,
                random_state=42
            )
            
            # Train both
            rf_model.fit(X_train_scaled, y_train)
            gb_model.fit(X_train_scaled, y_train)
            
            # Evaluate
            rf_score = rf_model.score(X_test_scaled, y_test)
            gb_score = gb_model.score(X_test_scaled, y_test)
            
            # Use best model
            best_model = rf_model if rf_score >= gb_score else gb_model
            best_score = max(rf_score, gb_score)
            model_type = "RandomForest" if rf_score >= gb_score else "GradientBoosting"
            
            # Save model
            model_path = os.path.join(BASE_DIR, f"{ticker}_model.pkl")
            scaler_path = os.path.join(BASE_DIR, f"{ticker}_model_scaler.pkl")
            
            joblib.dump({
                "model": best_model,
                "scaler": scaler,
                "features": [
                    'Returns', 'Log_Returns',
                    'SMA_5', 'SMA_10', 'SMA_20', 'SMA_50', 'SMA_100', 'SMA_200',
                    'EMA_5', 'EMA_10', 'EMA_20', 'EMA_50', 'EMA_100', 'EMA_200',
                    'BB_Upper', 'BB_Middle', 'BB_Lower', 'BB_Width',
                    'RSI_7', 'RSI_14', 'RSI_21',
                    'MACD', 'MACD_Signal', 'MACD_Hist',
                    'Stoch_K', 'Stoch_D',
                    'ATR_14', 'ATR_20',
                    'Volatility_5', 'Volatility_10', 'Volatility_20', 'Volatility_50',
                    'Momentum_10', 'Momentum_20', 'ROC_10', 'ROC_20',
                    'Volume_Ratio', 'OBV', 'Price_Oscillator'
                ],
                "model_type": model_type,
                "accuracy": best_score,
                "trained_at": datetime.now().isoformat()
            }, model_path)
            
            joblib.dump(scaler, scaler_path)
            
            duration = time.time() - start_time
            
            result = {
                "ticker": ticker,
                "status": "success",
                "model_type": model_type,
                "accuracy": round(best_score * 100, 2),
                "samples": len(X),
                "duration_sec": round(duration, 2),
                "timestamp": datetime.now().isoformat()
            }
            
            with self.lock:
                self.models_trained[ticker] = result
                self.training_stats["total_trained"] += 1
                self.training_stats["successful"] += 1
                # Save stats to file
                self._save_stats()
            
            logger.info(f"✓ {ticker}: {model_type} - {result['accuracy']}% accuracy in {duration:.1f}s")
            return result
            
        except Exception as e:
            logger.error(f"✗ {ticker}: {str(e)[:100]}")
            with self.lock:
                self.training_stats["total_trained"] += 1
                self.training_stats["failed"] += 1
                self._save_stats()
            return {
                "ticker": ticker,
                "status": "error",
                "error": str(e)[:200],
                "timestamp": datetime.now().isoformat()
            }
    
    def _save_stats(self):
        """Save training stats to file"""
        try:
            cache_dir = os.path.join(BASE_DIR, '.smart_cache')
            os.makedirs(cache_dir, exist_ok=True)
            stats_file = os.path.join(cache_dir, 'training_stats.json')
            with open(stats_file, 'w') as f:
                json.dump(self.get_stats(), f, indent=2)
        except Exception as e:
            logger.warning(f"Could not save stats: {e}")
    
    def train_batch(self, tickers: List[str]) -> Dict[str, Any]:
        """Train a batch of assets"""
        results = {}
        for ticker in tickers:
            results[ticker] = self.train_single_asset(ticker)
            time.sleep(0.5)  # Rate limiting
        return results
    
    def get_stats(self) -> Dict[str, Any]:
        """Get training statistics"""
        with self.lock:
            return {
                **self.training_stats,
                "models_trained": len(self.models_trained),
                "success_rate": round(
                    (self.training_stats["successful"] / max(1, self.training_stats["total_trained"])) * 100, 2
                )
            }


class UniversalTrainingLoop:
    """Continuous training loop for ALL assets"""
    
    def __init__(self):
        self.engine = UniversalTrainingEngine()
        self.all_assets = UniversalDataSource.get_all_assets()
        self.is_running = False
        self.current_batch = 0
        self.batch_size = 10  # Train 10 assets at a time
        
    def start_continuous_training(self):
        """Start continuous training loop"""
        self.is_running = True
        logger.info(f"Starting Universal Training Loop for {len(self.all_assets)} assets")
        logger.info(f"Batch size: {self.batch_size} assets per cycle")
        
        cycle = 0
        while self.is_running:
            cycle += 1
            logger.info(f"\n{'='*60}")
            logger.info(f"TRAINING CYCLE #{cycle}")
            logger.info(f"{'='*60}")
            
            # Get next batch
            start_idx = self.current_batch * self.batch_size
            end_idx = start_idx + self.batch_size
            
            if start_idx >= len(self.all_assets):
                # Restart from beginning
                self.current_batch = 0
                start_idx = 0
                end_idx = self.batch_size
                logger.info("Completed full training cycle. Restarting from beginning...")
            
            batch = self.all_assets[start_idx:end_idx]
            logger.info(f"Training batch {self.current_batch + 1}: {batch}")
            
            # Train batch
            results = self.engine.train_batch(batch)
            
            # Show results
            successful = sum(1 for r in results.values() if r.get("status") == "success")
            logger.info(f"Batch complete: {successful}/{len(batch)} successful")
            
            # Show overall stats
            stats = self.engine.get_stats()
            logger.info(f"Overall: {stats['successful']}/{stats['total_trained']} trained ({stats['success_rate']}% success)")
            
            self.current_batch += 1
            
            # Wait before next batch
            time.sleep(5)
    
    def stop(self):
        """Stop training loop"""
        self.is_running = False
        logger.info("Training loop stopped")


def run_universal_training():
    """Run the universal training system"""
    training_loop = UniversalTrainingLoop()
    
    try:
        training_loop.start_continuous_training()
    except KeyboardInterrupt:
        logger.info("\nShutdown signal received...")
        training_loop.stop()
    except Exception as e:
        logger.error(f"Training loop error: {e}")
        training_loop.stop()


if __name__ == "__main__":
    logger.info("="*60)
    logger.info("UNIVERSAL TRAINING SYSTEM")
    logger.info("Training ALL agents on ALL data")
    logger.info("="*60)
    run_universal_training()
