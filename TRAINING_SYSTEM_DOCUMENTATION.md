# 🎓 UNIVERSAL TRAINING SYSTEM DOCUMENTATION

## Overview

The **Universal Training System** is an autonomous, continuous machine learning training pipeline that trains ALL agents and employees on ALL available market data. It operates 24/7 in the background, constantly improving prediction models.

---

## 🎯 What It Does

### **Trains On EVERYTHING**
- ✅ **200+ Global Stocks** (Tech, Finance, Healthcare, Consumer, Energy, Industrials, etc.)
- ✅ **20+ Pakistani Stocks** (KSE-100 companies)
- ✅ **30+ Cryptocurrencies** (BTC, ETH, SOL, AVAX, etc.)
- ✅ **20+ Commodities** (Gold, Silver, Oil, Natural Gas, Wheat, Corn, etc.)
- ✅ **7+ Market Indices** (S&P 500, NASDAQ, Dow Jones, etc.)

**Total: 300+ Assets**

---

## 🔄 How It Works

### **Continuous Loop Architecture**

```
┌─────────────────────────────────────────────────────────┐
│  UNIVERSAL TRAINING LOOP (Infinite)                     │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  1. Get Next Batch (10 assets)                          │
│     ↓                                                    │
│  2. Download 2 Years Historical Data                    │
│     ↓                                                    │
│  3. Calculate ALL Technical Indicators (40+)            │
│     ↓                                                    │
│  4. Prepare Training Data (X, y)                        │
│     ↓                                                    │
│  5. Train TWO Models (RandomForest + GradientBoosting)  │
│     ↓                                                    │
│  6. Evaluate & Select Best Model                        │
│     ↓                                                    │
│  7. Save Model + Scaler to Disk                         │
│     ↓                                                    │
│  8. Update Statistics                                   │
│     ↓                                                    │
│  9. Move to Next Batch                                  │
│     ↓                                                    │
│  10. When All Assets Trained → Restart from Beginning   │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

### **Batch Processing**
- **Batch Size**: 10 assets per cycle
- **Cycle Time**: ~2-5 minutes per batch
- **Full Loop**: ~150 minutes (2.5 hours) to train all 300+ assets
- **Then**: Automatically restarts from beginning (continuous improvement)

---

## 📊 Technical Indicators (40+ Features)

### **Returns & Momentum**
- Returns, Log Returns
- Momentum (10-day, 20-day)
- Rate of Change (ROC 10, ROC 20)
- Price Oscillator

### **Moving Averages (16 indicators)**
- Simple Moving Averages: SMA 5, 10, 20, 50, 100, 200
- Exponential Moving Averages: EMA 5, 10, 20, 50, 100, 200

### **Volatility (4 indicators)**
- Volatility 5, 10, 20, 50 (annualized)

### **RSI (3 indicators)**
- RSI 7, 14, 21 (Relative Strength Index)

### **MACD (3 indicators)**
- MACD Line
- MACD Signal Line
- MACD Histogram

### **Bollinger Bands (4 indicators)**
- BB Upper, Middle, Lower
- BB Width

### **Stochastic (2 indicators)**
- Stochastic K
- Stochastic D

### **ATR (2 indicators)**
- Average True Range 14, 20

### **Volume (2 indicators)**
- Volume Ratio
- On-Balance Volume (OBV)

---

## 🤖 Machine Learning Models

### **Ensemble Approach**
For each asset, TWO models are trained:

1. **Random Forest Classifier**
   - 100 trees
   - Max depth: 10
   - Min samples split: 5
   - Parallel processing enabled

2. **Gradient Boosting Classifier**
   - 100 estimators
   - Max depth: 5
   - Learning rate: 0.1

### **Model Selection**
- Both models are evaluated on test data
- The model with **higher accuracy** is selected
- Selected model is saved to disk as `{TICKER}_model.pkl`

### **Feature Scaling**
- StandardScaler is used to normalize all features
- Scaler is saved as `{TICKER}_model_scaler.pkl`

---

## 💾 Model Storage

### **File Structure**
```
stock-market-predictor/
├── AAPL_model.pkl           # Apple model
├── AAPL_model_scaler.pkl    # Apple scaler
├── MSFT_model.pkl           # Microsoft model
├── MSFT_model_scaler.pkl    # Microsoft scaler
├── BTC-USD_model.pkl        # Bitcoin model
├── BTC-USD_model_scaler.pkl # Bitcoin scaler
└── ... (300+ model files)
```

### **Model Metadata**
Each model file contains:
```python
{
    "model": <trained_model>,
    "scaler": <fitted_scaler>,
    "features": [list of 40 feature names],
    "model_type": "RandomForest" or "GradientBoosting",
    "accuracy": 0.65,  # Test accuracy
    "trained_at": "2026-05-17T12:34:56"
}
```

---

## 📈 Training Statistics

### **Real-Time Tracking**
The system tracks:
- **Total Trained**: Number of training attempts
- **Successful**: Number of successful trainings
- **Failed**: Number of failed trainings
- **Success Rate**: Percentage of successful trainings
- **Models Trained**: Number of unique models saved

### **Statistics API**
Access training stats at:
```
GET /api/training/stats
```

Response:
```json
{
  "status": "active",
  "total_assets": 300,
  "total_trained": 150,
  "successful": 142,
  "failed": 8,
  "models_trained": 142,
  "success_rate": 94.67
}
```

---

## 🚀 Integration with Main System

### **4 Agent Systems Running**

1. **Live Prediction Stream**
   - Uses trained models for real-time predictions
   - Falls back to technical signals if model not available

2. **PerpetualOrchestrator**
   - Scout → Math → Historian → Bear → Warden → Boss → Equity
   - Continuous analysis pipeline

3. **MultiAgentSystem**
   - Training, Development, Security, Debug, Upscaling agents
   - Coordinated monitoring and improvement

4. **MainAgency**
   - Boss Agent: Daily market intelligence
   - Worker Agent: Executes predictions every 5 minutes

5. **UniversalTraining** ⭐ NEW
   - Trains ALL models on ALL data
   - Continuous improvement loop

---

## 🔍 Monitoring

### **Check Agent Status**
```
GET /api/agents
```

Response:
```json
{
  "agents": [
    {"name": "live-prediction-stream", "status": "running"},
    {"name": "PerpetualOrchestrator", "status": "running"},
    {"name": "MultiAgentSystem", "status": "running"},
    {"name": "MainAgency", "status": "running"},
    {"name": "UniversalTraining", "status": "running"}
  ],
  "total": 5,
  "running": 5
}
```

### **Check System Status**
```
GET /api/status
```

### **Check Training Progress**
```
GET /api/training/stats
```

---

## 🎯 Training Strategy

### **Data Requirements**
- **Minimum**: 100 days of historical data
- **Optimal**: 2 years (730 days)
- **Training Split**: 80% train, 20% test

### **Quality Control**
- Assets with insufficient data are skipped
- Failed trainings are logged but don't stop the loop
- Models are only saved if accuracy > 50%

### **Continuous Improvement**
- Models are retrained every ~2.5 hours
- Each retraining uses the latest market data
- Old models are overwritten with improved versions

---

## 📝 Logs

### **Training Logs**
```
[2026-05-17 12:34:56] Training AAPL...
[2026-05-17 12:35:12] ✓ AAPL: RandomForest - 67.5% accuracy in 16.2s
[2026-05-17 12:35:13] Training MSFT...
[2026-05-17 12:35:28] ✓ MSFT: GradientBoosting - 64.8% accuracy in 15.1s
[2026-05-17 12:35:29] Training BTC-USD...
[2026-05-17 12:35:45] ✓ BTC-USD: RandomForest - 71.2% accuracy in 16.8s
```

### **Batch Summary**
```
Batch complete: 9/10 successful
Overall: 142/150 trained (94.7% success)
```

---

## 🔧 Configuration

### **Adjustable Parameters**

In `universal_training_system.py`:

```python
# Batch size (assets per cycle)
self.batch_size = 10

# Model parameters
RandomForestClassifier(
    n_estimators=100,      # Number of trees
    max_depth=10,          # Tree depth
    min_samples_split=5    # Min samples to split
)

GradientBoostingClassifier(
    n_estimators=100,      # Number of boosting stages
    max_depth=5,           # Tree depth
    learning_rate=0.1      # Learning rate
)
```

---

## 🎓 How Agents Use Trained Models

### **Prediction Flow**

1. **User requests prediction** for ticker (e.g., AAPL)
2. **PredictionEngine** checks if `AAPL_model.pkl` exists
3. If exists:
   - Load model + scaler
   - Calculate 40 technical indicators
   - Scale features
   - Run model.predict()
   - Return prediction with confidence
4. If not exists:
   - Use technical signal heuristics
   - Return prediction with lower confidence

### **Model Priority**
```
Trained ML Model > Technical Signals > Fallback Heuristics
```

---

## 🌟 Benefits

### **For Predictions**
- ✅ Higher accuracy (ML models learn patterns)
- ✅ Confidence scores (probability estimates)
- ✅ Adaptive (models retrain on new data)

### **For System**
- ✅ Autonomous (no manual intervention)
- ✅ Scalable (handles 300+ assets)
- ✅ Resilient (continues despite failures)

### **For Users**
- ✅ Better predictions over time
- ✅ Transparent (can see training stats)
- ✅ Always improving (continuous retraining)

---

## 🚦 Status Indicators

### **Training Active**
- UniversalTraining thread is running
- Models are being trained in batches
- Stats are being updated

### **Training Complete (Cycle)**
- All 300+ assets have been trained once
- Loop automatically restarts
- Models are now available for predictions

### **Training Failed (Asset)**
- Specific asset couldn't be trained
- Logged and skipped
- Will retry in next cycle

---

## 📞 Support

### **Check if Training is Running**
```bash
curl https://web-production-5bda7.up.railway.app/api/agents
```

### **View Training Progress**
```bash
curl https://web-production-5bda7.up.railway.app/api/training/stats
```

### **View System Status**
```bash
curl https://web-production-5bda7.up.railway.app/api/status
```

---

## 🎉 Summary

The **Universal Training System** is a fully autonomous, continuous machine learning pipeline that:

1. ✅ Trains on **ALL 300+ assets** (stocks, crypto, commodities, forex)
2. ✅ Uses **40+ technical indicators** as features
3. ✅ Trains **TWO models** per asset (ensemble approach)
4. ✅ Runs **24/7** in continuous loops
5. ✅ Saves models to disk for real-time predictions
6. ✅ Tracks statistics and progress
7. ✅ Integrates seamlessly with all other agents

**Result**: Your prediction system gets smarter every 2.5 hours! 🚀
