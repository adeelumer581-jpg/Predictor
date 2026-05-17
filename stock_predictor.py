import yfinance as yf
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, classification_report
import joblib
import os
import warnings
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
        if period is None:
            period = f"{self.lookback_days}d"
        cached_df = db_manager.get_data(self.ticker)
        if cached_df is not None and not cached_df.empty:
            return cached_df
        if self.ticker.endswith('.PSX'):
            print(f"Fetching {self.ticker} from PSX...")
            try:
                import psxdata
                pure_ticker = self.ticker.replace('.PSX', '')
                end_date = datetime.now().strftime("%Y-%m-%d")
                start_date = (datetime.now() - timedelta(days=self.lookback_days)).strftime("%Y-%m-%d")
                df = psxdata.stocks(pure_ticker, start=start_date, end=end_date)
                if df is None or df.empty:
                    raise ValueError(f"No PSX data for {self.ticker}")
                df = df.rename(columns={'date': 'Date', 'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close', 'volume': 'Volume'})
                df['Date'] = pd.to_datetime(df['Date'])
                df = df.set_index('Date').sort_index()
            except ImportError:
                print("psxdata not installed, falling back to yfinance")
                stock = yf.Ticker(self.ticker.replace('.PSX', '.PSX'))
                df = stock.history(period=period)
        else:
            print(f"Fetching {self.ticker} from yfinance...")
            stock = yf.Ticker(self.ticker)
            df = stock.history(period=period)
        if df.empty:
            raise ValueError(f"No data found for {self.ticker}")
        db_manager.save_data(self.ticker, df)
        return df

    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df['Returns'] = df['Close'].pct_change()
        df['Log_Returns'] = np.log(df['Close'] / df['Close'].shift(1))
        for window in [5, 10, 20, 50, 100, 200]:
            df[f'SMA_{window}'] = df['Close'].rolling(window=window).mean()
            df[f'EMA_{window}'] = df['Close'].ewm(span=window, adjust=False).mean()
        df['SMA_5_20_Cross'] = (df['SMA_5'] - df['SMA_20']) / df['SMA_20']
        df['SMA_20_50_Cross'] = (df['SMA_20'] - df['SMA_50']) / df['SMA_50']
        df['Price_SMA_20_Ratio'] = df['Close'] / df['SMA_20']
        df['Price_SMA_50_Ratio'] = df['Close'] / df['SMA_50']
        for window in [5, 10, 20, 50]:
            df[f'Volatility_{window}'] = df['Returns'].rolling(window=window).std()
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['RSI_14'] = 100 - (100 / (1 + rs))
        exp12 = df['Close'].ewm(span=12, adjust=False).mean()
        exp26 = df['Close'].ewm(span=26, adjust=False).mean()
        df['MACD'] = exp12 - exp26
        df['MACD_Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
        df['MACD_Hist'] = df['MACD'] - df['MACD_Signal']
        df['BB_Middle'] = df['Close'].rolling(window=20).mean()
        bb_std = df['Close'].rolling(window=20).std()
        df['BB_Upper'] = df['BB_Middle'] + (bb_std * 2)
        df['BB_Lower'] = df['BB_Middle'] - (bb_std * 2)
        df['BB_Width'] = (df['BB_Upper'] - df['BB_Lower']) / df['BB_Middle']
        df['BB_Position'] = (df['Close'] - df['BB_Lower']) / (df['BB_Upper'] - df['BB_Lower'])
        high_low = df['High'] - df['Low']
        high_close = np.abs(df['High'] - df['Close'].shift())
        low_close = np.abs(df['Low'] - df['Close'].shift())
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df['ATR_14'] = true_range.rolling(window=14).mean()
        df['ATR_Ratio'] = df['ATR_14'] / df['Close']
        df['Volume_SMA_20'] = df['Volume'].rolling(window=20).mean()
        df['Volume_Ratio'] = df['Volume'] / df['Volume_SMA_20']
        for period in [1, 3, 5, 10, 20]:
            df[f'Momentum_{period}'] = df['Close'] / df['Close'].shift(period) - 1
        df['Daily_Range'] = (df['High'] - df['Low']) / df['Close']
        df['Daily_Change'] = (df['Close'] - df['Open']) / df['Open']
        for lag in [1, 2, 3, 5]:
            df[f'Returns_Lag_{lag}'] = df['Returns'].shift(lag)
        df['Sentiment'] = 0.0
        return df

    def create_target(self, df: pd.DataFrame, horizon: int = 1) -> pd.DataFrame:
        df = df.copy()
        df['Future_Close'] = df['Close'].shift(-horizon)
        df['Target'] = (df['Future_Close'] > df['Close']).astype(int)
        return df

    def prepare_features(self, df: pd.DataFrame) -> tuple:
        df_clean = df.dropna()
        exclude_cols = ['Target', 'Future_Close', 'Open', 'High', 'Low', 'Close', 'Volume', 'Dividends', 'Stock Splits']
        self.feature_columns = [col for col in df_clean.columns if col not in exclude_cols]
        X = df_clean[self.feature_columns]
        y = df_clean['Target']
        return X, y

    def train(self, test_size: float = 0.2, use_gb: bool = False):
        raw_data = self.fetch_data()
        data = self.calculate_indicators(raw_data)
        data = self.create_target(data, horizon=1)
        X, y = self.prepare_features(data)
        valid_idx = ~(X.isna().any(axis=1) | y.isna())
        X = X[valid_idx]
        y = y[valid_idx]
        split_idx = int(len(X) * (1 - test_size))
        X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
        y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]
        self.scaler = StandardScaler()
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        if use_gb:
            self.model = GradientBoostingClassifier(n_estimators=200, max_depth=5, learning_rate=0.05, random_state=42)
        else:
            self.model = RandomForestClassifier(n_estimators=200, max_depth=10, min_samples_split=10, min_samples_leaf=5, random_state=42, n_jobs=-1)
        self.model.fit(X_train_scaled, y_train)
        test_pred = self.model.predict(X_test_scaled)
        test_acc = accuracy_score(y_test, test_pred)
        print(f"Test Accuracy: {test_acc:.2%}")
        self.data = data
        return test_acc

    def predict_next(self) -> dict:
        if self.model is None:
            raise ValueError("Model not trained. Call train() first.")
        raw_data = self.fetch_data(period="30d")
        data = self.calculate_indicators(raw_data)
        data = self.create_target(data, horizon=1)
        latest = data.iloc[-1:][self.feature_columns].copy()
        latest = latest.fillna(latest.mean())
        latest_scaled = self.scaler.transform(latest)
        prediction = self.model.predict(latest_scaled)[0]
        probability = self.model.predict_proba(latest_scaled)[0]
        current_price = float(raw_data['Close'].iloc[-1])
        return {
            'ticker': self.ticker, 'current_price': current_price,
            'prediction': 'UP' if prediction == 1 else 'DOWN',
            'confidence': max(probability) * 100,
            'up_probability': probability[1] * 100,
            'down_probability': probability[0] * 100,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M')
        }

    def save_model(self, path: str = None):
        if path is None:
            path = f"{self.ticker}_model.pkl"
        joblib.dump({'model': self.model, 'scaler': self.scaler, 'features': self.feature_columns}, path)
        print(f"Model saved to {path}")

    def load_model(self, path: str):
        data = joblib.load(path)
        if isinstance(data, dict):
            self.model = data.get('model')
            self.scaler = data.get('scaler')
            self.feature_columns = data.get('features')
        else:
            self.model = data
            scaler_path = path.replace('.pkl', '_scaler.pkl')
            if os.path.exists(scaler_path):
                self.scaler = joblib.load(scaler_path)
            if self.feature_columns is None:
                dummy_df = pd.DataFrame(np.random.randn(250, 4), columns=['Open', 'High', 'Low', 'Close'])
                for c in ['Volume', 'Dividends', 'Stock Splits']:
                    dummy_df[c] = 1000
                temp_df = self.calculate_indicators(dummy_df)
                temp_df = self.create_target(temp_df)
                self.prepare_features(temp_df)
            print(f"Loaded raw model from {path}")
