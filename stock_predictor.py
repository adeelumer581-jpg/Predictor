"""
Stock Market Predictor
=====================
A machine learning-based stock price direction predictor.

Uses technical indicators as features and Random Forest classifier for predictions.
WARNING: This is for educational purposes only. Not financial advice.
"""

import yfinance as yf
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.model_selection import train_test_split, TimeSeriesSplit
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, classification_report
import warnings
import joblib
import os
from datetime import datetime, timedelta
from database_manager import db_manager

warnings.filterwarnings('ignore')


class StockPredictor:
    def __init__(self, ticker: str, lookback_days: int = 365):
        self.ticker = ticker.upper()
        self.lookback_days = lookback_days
        self.model = None
        self.scaler = None
        self.feature_columns = None
        self.data = None
        self.sentiment_score = 0.0

    def fetch_data(self, period: str = None) -> pd.DataFrame:
        """Fetch historical stock data from Yahoo Finance or local cache."""
        if period is None:
            period = f"{self.lookback_days}d"

        # Try to load from cache first
        cached_df = db_manager.get_data(self.ticker)
        if cached_df is not None and not cached_df.empty:
            return cached_df

        if self.ticker.endswith('.PSX'):
            print(f"Fetching {self.ticker} data from PSX Data Portal...")
            import psxdata
            pure_ticker = self.ticker.replace('.PSX', '')
            
            end_date = datetime.now().strftime("%Y-%m-%d")
            start_date = (datetime.now() - timedelta(days=self.lookback_days)).strftime("%Y-%m-%d")
            
            df = psxdata.stocks(pure_ticker, start=start_date, end=end_date)
            
            if df is None or df.empty:
                 raise ValueError(f"No data found for PSX ticker: {self.ticker}")
            
            # Standardize columns to match yfinance
            df = df.rename(columns={
                'date': 'Date',
                'open': 'Open',
                'high': 'High',
                'low': 'Low',
                'close': 'Close',
                'volume': 'Volume'
            })
            df['Date'] = pd.to_datetime(df['Date'])
            df = df.set_index('Date').sort_index()
        else:
            print(f"Fetching {self.ticker} data from yfinance for {period}...")
            stock = yf.Ticker(self.ticker)
            df = stock.history(period=period)

        if df.empty:
            raise ValueError(f"No data found for ticker: {self.ticker}")

        print(f"Downloaded {len(df)} days of data")
        
        # Save to cache for future use
        db_manager.save_data(self.ticker, df)
        
        return df

    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate technical indicators for feature engineering."""
        df = df.copy()

        # Price-based features
        df['Returns'] = df['Close'].pct_change()
        df['Log_Returns'] = np.log(df['Close'] / df['Close'].shift(1))

        # Moving averages
        for window in [5, 10, 20, 50, 100, 200]:
            df[f'SMA_{window}'] = df['Close'].rolling(window=window).mean()
            df[f'EMA_{window}'] = df['Close'].ewm(span=window, adjust=False).mean()

        # Moving average crossovers
        df['SMA_5_20_Cross'] = (df['SMA_5'] - df['SMA_20']) / df['SMA_20']
        df['SMA_20_50_Cross'] = (df['SMA_20'] - df['SMA_50']) / df['SMA_50']
        df['SMA_50_200_Cross'] = (df['SMA_50'] - df['SMA_200']) / df['SMA_200']

        # Price relative to moving averages
        df['Price_SMA_20_Ratio'] = df['Close'] / df['SMA_20']
        df['Price_SMA_50_Ratio'] = df['Close'] / df['SMA_50']
        df['Price_SMA_200_Ratio'] = df['Close'] / df['SMA_200']

        # Volatility
        for window in [5, 10, 20, 50]:
            df[f'Volatility_{window}'] = df['Returns'].rolling(window=window).std()

        # RSI (Relative Strength Index)
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['RSI_14'] = 100 - (100 / (1 + rs))
        df['RSI_7'] = 100 - (100 / (1 + (
            df['Close'].diff().where(df['Close'].diff() > 0, 0).rolling(window=7).mean() /
            -df['Close'].diff().where(df['Close'].diff() < 0, 0).rolling(window=7).mean()
        ).replace([np.inf, -np.inf], 1)))

        # MACD
        exp12 = df['Close'].ewm(span=12, adjust=False).mean()
        exp26 = df['Close'].ewm(span=26, adjust=False).mean()
        df['MACD'] = exp12 - exp26
        df['MACD_Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
        df['MACD_Hist'] = df['MACD'] - df['MACD_Signal']

        # Bollinger Bands
        df['BB_Middle'] = df['Close'].rolling(window=20).mean()
        bb_std = df['Close'].rolling(window=20).std()
        df['BB_Upper'] = df['BB_Middle'] + (bb_std * 2)
        df['BB_Lower'] = df['BB_Middle'] - (bb_std * 2)
        df['BB_Width'] = (df['BB_Upper'] - df['BB_Lower']) / df['BB_Middle']
        df['BB_Position'] = (df['Close'] - df['BB_Lower']) / (df['BB_Upper'] - df['BB_Lower'])

        # Average True Range (ATR)
        high_low = df['High'] - df['Low']
        high_close = np.abs(df['High'] - df['Close'].shift())
        low_close = np.abs(df['Low'] - df['Close'].shift())
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df['ATR_14'] = true_range.rolling(window=14).mean()
        df['ATR_Ratio'] = df['ATR_14'] / df['Close']

        # Volume indicators
        df['Volume_SMA_20'] = df['Volume'].rolling(window=20).mean()
        df['Volume_Ratio'] = df['Volume'] / df['Volume_SMA_20']

        # On-Balance Volume (simplified)
        df['OBV'] = (np.sign(df['Close'].diff()) * df['Volume']).fillna(0).cumsum()
        df['OBV_SMA_10'] = df['OBV'].rolling(window=10).mean()

        # Price momentum
        for period in [1, 3, 5, 10, 20]:
            df[f'Momentum_{period}'] = df['Close'] / df['Close'].shift(period) - 1

        # Rate of Change
        for period in [5, 10, 20]:
            df[f'ROC_{period}'] = ((df['Close'] - df['Close'].shift(period)) / df['Close'].shift(period)) * 100

        # High/Low range
        df['Daily_Range'] = (df['High'] - df['Low']) / df['Close']
        df['Daily_Change'] = (df['Close'] - df['Open']) / df['Open']

        # Lag features
        for lag in [1, 2, 3, 5]:
            df[f'Returns_Lag_{lag}'] = df['Returns'].shift(lag)
            df[f'Volume_Ratio_Lag_{lag}'] = df['Volume_Ratio'].shift(lag)

        # Add news sentiment (calculated during indicator phase)
        # We'll set this later in the pipeline
        df['Sentiment'] = 0.0

        return df

    def create_target(self, df: pd.DataFrame, horizon: int = 1) -> pd.DataFrame:
        """
        Create target variable: 1 if price goes up, 0 if down.
        horizon: number of days ahead to predict
        """
        df = df.copy()
        df['Future_Close'] = df['Close'].shift(-horizon)
        df['Target'] = (df['Future_Close'] > df['Close']).astype(int)
        return df

    def fetch_news_sentiment(self) -> float:
        """Fetch news and calculate average sentiment score using VADER"""
        try:
            from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
            from duckduckgo_search import DDGS
            
            analyzer = SentimentIntensityAnalyzer()
            scores = []
            
            with DDGS() as ddgs:
                results = list(ddgs.text(f"{self.ticker} stock news", max_results=5))
                for r in results:
                    vs = analyzer.polarity_scores(f"{r['title']} {r['body']}")
                    scores.append(vs['compound'])
            
            score = sum(scores) / len(scores) if scores else 0.0
            print(f"Sentiment score for {self.ticker}: {score:.2f}")
            return score
        except Exception as e:
            print(f"Sentiment analysis error: {e}")
            return 0.0

    def prepare_features(self, df: pd.DataFrame) -> tuple:
        """Prepare feature matrix and target variable."""
        # Drop rows with NaN (from indicator calculations)
        df_clean = df.dropna()

        # Define feature columns (exclude target and helper columns)
        exclude_cols = ['Target', 'Future_Close', 'Open', 'High', 'Low', 'Close', 'Volume', 'Dividends', 'Stock Splits']
        self.feature_columns = [col for col in df_clean.columns if col not in exclude_cols]

        X = df_clean[self.feature_columns]
        y = df_clean['Target']

        return X, y

    def train(self, test_size: float = 0.2, use_gb: bool = False):
        """Train the prediction model."""
        print("\n" + "="*50)
        print("TRAINING STOCK PREDICTOR")
        print("="*50)

        # Fetch and prepare data
        raw_data = self.fetch_data()
        data = self.calculate_indicators(raw_data)
        
        # Inject real-time sentiment
        self.sentiment_score = self.fetch_news_sentiment()
        data['Sentiment'] = self.sentiment_score
        
        data = self.create_target(data, horizon=1)

        X, y = self.prepare_features(data)

        # Remove any remaining NaN
        valid_idx = ~(X.isna().any(axis=1) | y.isna())
        X = X[valid_idx]
        y = y[valid_idx]

        print(f"Training samples: {len(X)}")
        print(f"Features: {len(self.feature_columns)}")
        print(f"Class distribution: {y.value_counts().to_dict()}")

        # Time-series split for train/test (preserve temporal order)
        split_idx = int(len(X) * (1 - test_size))
        X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
        y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]

        # Scale features
        self.scaler = StandardScaler()
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)

        # Train model
        if use_gb:
            print("\nUsing Gradient Boosting Classifier...")
            self.model = GradientBoostingClassifier(
                n_estimators=200,
                max_depth=5,
                learning_rate=0.05,
                min_samples_split=10,
                min_samples_leaf=5,
                random_state=42
            )
        else:
            print("\nUsing Random Forest Classifier...")
            self.model = RandomForestClassifier(
                n_estimators=200,
                max_depth=10,
                min_samples_split=10,
                min_samples_leaf=5,
                random_state=42,
                n_jobs=-1
            )

        self.model.fit(X_train_scaled, y_train)

        # Evaluate
        train_pred = self.model.predict(X_train_scaled)
        test_pred = self.model.predict(X_test_scaled)

        train_acc = accuracy_score(y_train, train_pred)
        test_acc = accuracy_score(y_test, test_pred)

        print(f"\n--- Results ---")
        print(f"Training Accuracy: {train_acc:.2%}")
        print(f"Test Accuracy: {test_acc:.2%}")
        print(f"\nClassification Report (Test):")
        print(classification_report(y_test, test_pred, target_names=['Down', 'Up']))

        # Feature importance
        if hasattr(self.model, 'feature_importances_'):
            importance = pd.DataFrame({
                'feature': self.feature_columns,
                'importance': self.model.feature_importances_
            }).sort_values('importance', ascending=False)
            print("\nTop 10 Most Important Features:")
            print(importance.head(10).to_string(index=False))

        self.data = data
        return test_acc

    def predict_next(self) -> dict:
        """Predict next day's price direction."""
        if self.model is None:
            raise ValueError("Model not trained. Call train() first.")

        # Get latest data
        raw_data = self.fetch_data(period="30d")
        data = self.calculate_indicators(raw_data)
        
        # Inject real-time sentiment
        self.sentiment_score = self.fetch_news_sentiment()
        data['Sentiment'] = self.sentiment_score
        
        data = self.create_target(data, horizon=1)

        # Get latest features
        latest = data.iloc[-1:][self.feature_columns].copy()

        # Handle any NaN
        latest = latest.fillna(latest.mean())

        # Scale
        latest_scaled = self.scaler.transform(latest)

        # Predict
        prediction = self.model.predict(latest_scaled)[0]
        probability = self.model.predict_proba(latest_scaled)[0]

        current_price = raw_data['Close'].iloc[-1]

        return {
            'ticker': self.ticker,
            'current_price': current_price,
            'prediction': 'UP' if prediction == 1 else 'DOWN',
            'confidence': max(probability) * 100,
            'up_probability': probability[1] * 100,
            'down_probability': probability[0] * 100,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M')
        }

    def backtest(self, initial_capital: float = 10000) -> dict:
        """Backtest the strategy on historical data."""
        if self.data is None:
            raise ValueError("No data. Train model first.")

        df = self.data.dropna(subset=['Target'])
        X = df[self.feature_columns].fillna(0)
        y = df['Target']

        # Split
        split_idx = int(len(X) * 0.7)
        X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
        y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]
        prices = df['Close'].iloc[split_idx:]

        # Scale and predict
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)

        self.model.fit(X_train_scaled, y_train)
        predictions = self.model.predict(X_test_scaled)

        # Simulate trading
        capital = initial_capital
        shares = 0
        position = False

        for i in range(len(predictions)):
            if predictions[i] == 1 and not position:  # Buy signal
                shares = capital / prices.iloc[i]
                capital = 0
                position = True
            elif predictions[i] == 0 and position:  # Sell signal
                capital = shares * prices.iloc[i]
                shares = 0
                position = False

        # Final value
        if position:
            final_value = shares * prices.iloc[-1]
        else:
            final_value = capital

        buy_hold_value = initial_capital * (prices.iloc[-1] / prices.iloc[0])

        return {
            'initial_capital': initial_capital,
            'final_value': final_value,
            'strategy_return': ((final_value - initial_capital) / initial_capital) * 100,
            'buy_hold_return': ((buy_hold_value - initial_capital) / initial_capital) * 100
        }

    def save_model(self, path: str = None):
        """Save the trained model."""
        if path is None:
            path = f"{self.ticker}_model.pkl"
        joblib.dump({'model': self.model, 'scaler': self.scaler, 'features': self.feature_columns}, path)
        print(f"Model saved to {path}")

    def load_model(self, path: str):
        """Load a saved model with support for multiple formats."""
        import joblib
        data = joblib.load(path)
        
        if isinstance(data, dict):
            self.model = data.get('model')
            self.scaler = data.get('scaler')
            self.feature_columns = data.get('features')
        else:
            # Fallback for models saved as raw objects
            self.model = data
            # Try to find a separate scaler file
            scaler_path = path.replace('.pkl', '_scaler.pkl')
            if os.path.exists(scaler_path):
                self.scaler = joblib.load(scaler_path)
            
            # CRITICAL: Populate feature_columns if missing to prevent "None" error
            if self.feature_columns is None:
                # Generate default feature columns using a dummy calculation
                dummy_df = pd.DataFrame(np.random.randn(250, 4), columns=['Open', 'High', 'Low', 'Close'])
                # StockPredictor logic requires these to be present
                dummy_df['Volume'] = 1000
                dummy_df['Dividends'] = 0
                dummy_df['Stock Splits'] = 0
                
                temp_df = self.calculate_indicators(dummy_df)
                temp_df = self.create_target(temp_df)
                self.prepare_features(temp_df) # This sets self.feature_columns
                
            print(f"Loaded raw model object from {path}")
            
        print(f"Model loaded from {path}")


def main():
    """Main function to run the stock predictor."""
    import argparse

    parser = argparse.ArgumentParser(description='Stock Market Predictor')
    parser.add_argument('ticker', help='Stock ticker symbol (e.g., AAPL, MSFT, GOOGL)')
    parser.add_argument('--train', action='store_true', help='Train a new model')
    parser.add_argument('--predict', action='store_true', help='Make prediction for next day')
    parser.add_argument('--backtest', action='store_true', help='Run backtesting')
    parser.add_argument('--period', default='365', help='Lookback period in days')
    parser.add_argument('--use-gb', action='store_true', help='Use Gradient Boosting instead of Random Forest')

    args = parser.parse_args()

    predictor = StockPredictor(args.ticker, lookback_days=int(args.period))

    if args.train:
        predictor.train(use_gb=args.use_gb)
        predictor.save_model()

    if args.predict:
        if predictor.model is None:
            # Try to load model
            try:
                predictor.load_model(f"{args.ticker}_model.pkl")
            except:
                print("No model found. Training first...")
                predictor.train()
        result = predictor.predict_next()
        print("\n" + "="*50)
        print("PREDICTION RESULT")
        print("="*50)
        print(f"Ticker: {result['ticker']}")
        print(f"Current Price: ${result['current_price']:.2f}")
        print(f"Prediction: {result['prediction']}")
        print(f"Confidence: {result['confidence']:.1f}%")
        print(f"  - Up probability: {result['up_probability']:.1f}%")
        print(f"  - Down probability: {result['down_probability']:.1f}%")
        print(f"Timestamp: {result['timestamp']}")

    if args.backtest:
        if predictor.model is None:
            predictor.train()
        result = predictor.backtest()
        print("\n" + "="*50)
        print("BACKTEST RESULTS")
        print("="*50)
        print(f"Initial Capital: ${result['initial_capital']:,.2f}")
        print(f"Final Value: ${result['final_value']:,.2f}")
        print(f"Strategy Return: {result['strategy_return']:.2f}%")
        print(f"Buy & Hold Return: {result['buy_hold_return']:.2f}%")

    if not args.train and not args.predict and not args.backtest:
        # Default: train and predict
        predictor.train()
        result = predictor.predict_next()
        print("\n" + "="*50)
        print("PREDICTION RESULT")
        print("="*50)
        print(f"Ticker: {result['ticker']}")
        print(f"Current Price: ${result['current_price']:.2f}")
        print(f"Prediction: {result['prediction']}")
        print(f"Confidence: {result['confidence']:.1f}%")
        print(f"  - Up probability: {result['up_probability']:.1f}%")
        print(f"  - Down probability: {result['down_probability']:.1f}%")


if __name__ == "__main__":
    main()