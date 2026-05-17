import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
import pandas as pd
import numpy as np
import os
from database_manager import db_manager
import yfinance as yf
from sklearn.preprocessing import StandardScaler
from datetime import datetime

class LSTMPredictor(nn.Module):
    def __init__(self, input_dim, hidden_dim, num_layers, output_dim, dropout=0.2):
        super(LSTMPredictor, self).__init__()
        self.hidden_dim = hidden_dim
        self.num_layers = num_layers
        
        self.lstm = nn.LSTM(input_dim, hidden_dim, num_layers, batch_first=True, dropout=dropout)
        self.fc1 = nn.Linear(hidden_dim, hidden_dim // 2)
        self.relu = nn.ReLU()
        self.fc2 = nn.Linear(hidden_dim // 2, output_dim)
        self.sigmoid = nn.Sigmoid()

    def forward(self, x):
        h0 = torch.zeros(self.num_layers, x.size(0), self.hidden_dim).requires_grad_()
        c0 = torch.zeros(self.num_layers, x.size(0), self.hidden_dim).requires_grad_()
        out, (hn, cn) = self.lstm(x, (h0.detach(), c0.detach()))
        out = out[:, -1, :]
        out = self.fc1(out)
        out = self.relu(out)
        out = self.fc2(out)
        out = self.sigmoid(out)
        return out

class DeepStockPredictor:
    def __init__(self, ticker: str, sequence_length: int = 30):
        self.ticker = ticker
        self.sequence_length = sequence_length
        self.model = None
        self.scaler = StandardScaler()
        self.model_path = f"{ticker}_lstm_model.pth"
        
    def prepare_data(self, df, is_training=True):
        """Prepare sequences for LSTM"""
        # Drop target from features
        if 'Target' in df.columns:
            features = df.drop(columns=['Target', 'Future_Close', 'Open', 'High', 'Low', 'Close', 'Volume', 'Dividends', 'Stock Splits'], errors='ignore')
            target = df['Target'].values
        else:
            features = df.drop(columns=['Open', 'High', 'Low', 'Close', 'Volume', 'Dividends', 'Stock Splits'], errors='ignore')
            target = None

        if is_training:
            features_scaled = self.scaler.fit_transform(features.fillna(0))
        else:
            features_scaled = self.scaler.transform(features.fillna(0))

        X, y = [], []
        for i in range(len(features_scaled) - self.sequence_length):
            X.append(features_scaled[i:(i + self.sequence_length)])
            if target is not None:
                y.append(target[i + self.sequence_length])

        X = np.array(X)
        if target is not None:
            y = np.array(y)
            return torch.tensor(X, dtype=torch.float32), torch.tensor(y, dtype=torch.float32).unsqueeze(1)
        
        return torch.tensor(X, dtype=torch.float32), None

    def train(self, df: pd.DataFrame, epochs: int = 50, batch_size: int = 32):
        print(f"\nTraining Deep LSTM Model for {self.ticker}...")
        
        X_train, y_train = self.prepare_data(df, is_training=True)
        
        dataset = TensorDataset(X_train, y_train)
        dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=True)
        
        input_dim = X_train.shape[2]
        self.model = LSTMPredictor(input_dim=input_dim, hidden_dim=64, num_layers=2, output_dim=1)
        
        criterion = nn.BCELoss()
        optimizer = optim.Adam(self.model.parameters(), lr=0.001)
        
        for epoch in range(epochs):
            self.model.train()
            total_loss = 0
            for batch_x, batch_y in dataloader:
                optimizer.zero_grad()
                outputs = self.model(batch_x)
                loss = criterion(outputs, batch_y)
                loss.backward()
                optimizer.step()
                total_loss += loss.item()
                
            if (epoch + 1) % 10 == 0:
                print(f"Epoch {epoch+1}/{epochs}, Loss: {total_loss/len(dataloader):.4f}")
                
        # Save model
        torch.save({
            'model_state_dict': self.model.state_dict(),
            'scaler': self.scaler
        }, self.model_path)
        print(f"Deep learning model saved to {self.model_path}")

    def predict(self, df: pd.DataFrame) -> dict:
        if self.model is None:
            try:
                checkpoint = torch.load(self.model_path)
                # Initialize model first
                X, _ = self.prepare_data(df, is_training=False)
                self.model = LSTMPredictor(input_dim=X.shape[2], hidden_dim=64, num_layers=2, output_dim=1)
                self.model.load_state_dict(checkpoint['model_state_dict'])
                self.scaler = checkpoint['scaler']
                print(f"Loaded existing deep model for {self.ticker}")
            except:
                raise ValueError("Model not trained or not found.")
                
        self.model.eval()
        X, _ = self.prepare_data(df, is_training=False)
        
        # Get the latest sequence
        latest_sequence = X[-1].unsqueeze(0)
        
        with torch.no_grad():
            probability = self.model(latest_sequence).item()
            
        prediction = 'UP' if probability > 0.5 else 'DOWN'
        confidence = max(probability, 1 - probability) * 100
        
        current_price = df['Close'].iloc[-1]
        
        return {
            'ticker': self.ticker,
            'current_price': current_price,
            'prediction': prediction,
            'confidence': confidence,
            'up_probability': probability * 100,
            'down_probability': (1 - probability) * 100,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M')
        }
