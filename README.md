# Stock Predictor Pro - All Markets Live Trading

A comprehensive stock prediction system covering stocks, crypto, commodities, forex, and Pakistani markets with real-time predictions and AI-powered analysis.

## Live Demo

**[Click to Deploy to Render](https://render.com/deploy?repo=https://github.com/adeelumer581-jpg/Predictor)**

## Features

- **197+ Assets Tracked** - Stocks, Crypto, Commodities, Forex, Pakistani Stocks
- **Real-time Predictions** - UP/DOWN with confidence scores
- **Technical Analysis** - RSI, MACD, Bollinger Bands, Stochastic
- **Candlestick Patterns** - Hammer, Doji, Engulfing, Morning/Evening Star
- **Screenshot Analysis** - Upload charts for AI predictions
- **Live News** - Market news with sentiment analysis
- **Auto-refresh** - Updates every 30 seconds

## Quick Deploy to Render

1. Click: https://render.com/deploy?repo=https://github.com/adeelumer581-jpg/Predictor
2. Connect GitHub account
3. Use settings:
   - Name: `stock-predictor`
   - Build: `pip install -r requirements.txt`
   - Start: `python comprehensive_system.py`
4. Click "Create" and wait 2-3 minutes

## What's Tracked

| Category | Count | Examples |
|----------|-------|----------|
| Stocks | 127 | AAPL, MSFT, NVDA, TSLA |
| Crypto | 23 | BTC, ETH, SOL, XRP |
| Commodities | 21 | Gold, Oil, Wheat, Corn |
| Forex | 20 | USD/PKR, EUR/USD, GBP/USD |
| Pakistani | 10 | OGDC, PSO, HBL, UBL |

## API Endpoints

- `/api/stocks` - Global stocks
- `/api/crypto` - Cryptocurrencies
- `/api/commodities` - Commodities
- `/api/forex` - Forex pairs
- `/api/pakistani` - KSE-100 stocks
- `/api/news` - Market news
- `/api/predict/<ticker>` - Single prediction
- `/api/analyze/screenshot` - Screenshot analysis

## Local Development

```bash
pip install -r requirements.txt
python comprehensive_system.py
# Open http://localhost:5003
```

## Tech Stack

- Python 3.11
- Flask + Flask-SocketIO
- scikit-learn (Random Forest)
- yfinance (market data)
- TailwindCSS (UI)

## License

MIT