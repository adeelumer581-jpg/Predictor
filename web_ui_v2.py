"""
Stock Predictor AI - Complete Web Dashboard V2
==============================================
Full-featured, production-ready web interface
"""
import os
import sys
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("WebUI")

from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO

app = Flask(__name__, template_folder='templates', static_folder='static')
app.config['SECRET_KEY'] = 'stock-predictor-2024'
socketio = SocketIO(app, cors_allowed_origins="*")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = BASE_DIR
CHECKPOINT_FILE = os.path.join(BASE_DIR, "training_checkpoint.json")


class WebUIManager:
    def __init__(self):
        self.predictions = {}
        self.backtest_results = {}

    def get_models(self):
        models = []
        try:
            for f in os.listdir(MODELS_DIR):
                if f.endswith('_model.pkl'):
                    models.append(f.replace('_model.pkl', ''))
        except:
            pass
        return sorted(models)

    def get_status(self):
        if os.path.exists(CHECKPOINT_FILE):
            try:
                with open(CHECKPOINT_FILE, 'r') as f:
                    cp = json.load(f)
                    return {"models": len(self.get_models()), "trained": len(cp.get("completed", [])), "failed": len(cp.get("failed", []))}
            except:
                pass
        return {"models": len(self.get_models()), "trained": 0, "failed": 0}


ui_manager = WebUIManager()


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/status')
def api_status():
    return jsonify(ui_manager.get_status())


@app.route('/api/models')
def api_models():
    return jsonify({"models": ui_manager.get_models()})


@app.route('/api/predict/<ticker>')
def api_predict(ticker):
    ticker = ticker.upper()
    try:
        import yfinance as yf
        import pandas as pd
        import numpy as np
        import joblib

        model_file = f"{ticker}_model.pkl"
        scaler_file = f"{ticker}_scaler.pkl"

        if not os.path.exists(model_file):
            return jsonify({"error": f"No model for {ticker}. Train first."})

        model = joblib.load(model_file)
        scaler = joblib.load(scaler_file) if os.path.exists(scaler_file) else None

        stock = yf.Ticker(ticker)
        df = stock.history(period='30d')

        if len(df) < 10:
            return jsonify({"error": "Insufficient data"})

        df['Returns'] = df['Close'].pct_change()
        df['SMA_10'] = df['Close'].rolling(10).mean()
        delta = df['Close'].diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        df['RSI'] = 100 - (100 / (1 + (gain / loss.replace(0, 1)).replace([np.inf, -np.inf], 50)))
        df = df.dropna()

        X = df[['Returns', 'SMA_10', 'RSI']].iloc[-1:].values
        if scaler:
            X = scaler.transform(X)

        pred = model.predict(X)[0]
        proba = model.predict_proba(X)[0]

        return jsonify({
            "ticker": ticker, "prediction": "UP" if pred == 1 else "DOWN",
            "confidence": round(float(max(proba)) * 100, 1),
            "up_prob": round(float(proba[1]) * 100, 1) if len(proba) > 1 else 50,
            "price": round(float(df['Close'].iloc[-1]), 2),
            "volume": int(df['Volume'].iloc[-1]),
            "change": round(float(df['Close'].iloc[-1] - df['Close'].iloc[-2]), 2),
            "change_pct": round(float((df['Close'].iloc[-1] / df['Close'].iloc[-2] - 1) * 100), 2)
        })
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route('/api/predict/all')
def api_predict_all():
    models = ui_manager.get_models()[:30]
    results = []
    for ticker in models:
        try:
            import yfinance as yf
            import pandas as pd
            import numpy as np
            import joblib

            model_file = f"{ticker}_model.pkl"
            scaler_file = f"{ticker}_scaler.pkl"
            if not os.path.exists(model_file):
                continue

            model = joblib.load(model_file)
            scaler = joblib.load(scaler_file) if os.path.exists(scaler_file) else None
            stock = yf.Ticker(ticker)
            df = stock.history(period='30d')
            if len(df) < 10:
                continue

            df['Returns'] = df['Close'].pct_change()
            df['SMA_10'] = df['Close'].rolling(10).mean()
            delta = df['Close'].diff()
            gain = delta.where(delta > 0, 0).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            df['RSI'] = 100 - (100 / (1 + (gain / loss.replace(0, 1)).replace([np.inf, -np.inf], 50)))
            df = df.dropna()

            X = df[['Returns', 'SMA_10', 'RSI']].iloc[-1:].values
            if scaler:
                X = scaler.transform(X)

            pred = model.predict(X)[0]
            proba = model.predict_proba(X)[0]

            results.append({"ticker": ticker, "prediction": "UP" if pred == 1 else "DOWN",
                "confidence": round(float(max(proba)) * 100, 1), "price": round(float(df['Close'].iloc[-1]), 2)})
        except:
            pass

    results.sort(key=lambda x: x['confidence'], reverse=True)
    return jsonify({"predictions": results})


@app.route('/api/top-picks')
def api_top_picks():
    import yfinance as yf
    import pandas as pd
    import numpy as np
    import joblib

    tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "AMD", "INTC", "AMGN"]
    results = []

    for ticker in tickers:
        try:
            model_file = f"{ticker}_model.pkl"
            scaler_file = f"{ticker}_scaler.pkl"
            if not os.path.exists(model_file):
                continue

            model = joblib.load(model_file)
            scaler = joblib.load(scaler_file) if os.path.exists(scaler_file) else None
            stock = yf.Ticker(ticker)
            df = stock.history(period='30d')
            if len(df) < 10:
                continue

            df['Returns'] = df['Close'].pct_change()
            df['SMA_10'] = df['Close'].rolling(10).mean()
            delta = df['Close'].diff()
            gain = delta.where(delta > 0, 0).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            df['RSI'] = 100 - (100 / (1 + (gain / loss.replace(0, 1)).replace([np.inf, -np.inf], 50)))
            df = df.dropna()

            X = df[['Returns', 'SMA_10', 'RSI']].iloc[-1:].values
            if scaler:
                X = scaler.transform(X)

            pred = model.predict(X)[0]
            proba = model.predict_proba(X)[0]
            up_prob = float(proba[1]) if len(proba) > 1 else 0.5

            results.append({"ticker": ticker, "prediction": "UP" if pred == 1 else "DOWN",
                "confidence": round(float(max(proba)) * 100, 1),
                "score": round(up_prob * float(max(proba)), 2),
                "price": round(float(df['Close'].iloc[-1]), 2),
                "change": round(float((df['Close'].iloc[-1] / df['Close'].iloc[-2] - 1) * 100), 2)})
        except:
            pass

    results.sort(key=lambda x: x['score'], reverse=True)
    return jsonify({"picks": results[:5]})


@app.route('/api/backtest', methods=['POST'])
def api_backtest():
    data = request.json or {}
    tickers = data.get('tickers', [])
    import yfinance as yf
    import pandas as pd
    import numpy as np
    results = []

    for ticker in tickers:
        try:
            stock = yf.Ticker(ticker)
            df = stock.history(period='90d')
            if len(df) < 30:
                continue

            df['SMA_20'] = df['Close'].rolling(20).mean()
            df['Signal'] = (df['Close'] > df['SMA_20']).astype(int)
            df['Returns'] = df['Close'].pct_change()
            df['Strategy'] = df['Signal'].shift(1) * df['Returns']

            strategy_returns = df['Strategy'].dropna()
            total_return = (1 + strategy_returns).prod() - 1
            sharpe = strategy_returns.mean() / strategy_returns.std() * np.sqrt(252) if strategy_returns.std() > 0 else 0

            results.append({"ticker": ticker, "return": round(total_return * 100, 2),
                "sharpe": round(sharpe, 2), "trades": int(df['Signal'].diff().abs().sum())})
        except:
            pass

    results.sort(key=lambda x: x['return'], reverse=True)
    return jsonify({"results": results})


@app.route('/api/train', methods=['POST'])
def api_train():
    data = request.json or {}
    ticker = data.get('ticker', '').upper()
    if not ticker:
        return jsonify({"error": "No ticker provided"})

    try:
        import yfinance as yf
        import pandas as pd
        import numpy as np
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.preprocessing import StandardScaler
        import joblib

        stock = yf.Ticker(ticker)
        df = stock.history(period='180d')
        if len(df) < 30:
            return jsonify({"error": "Insufficient data"})

        df['Returns'] = df['Close'].pct_change()
        df['SMA_10'] = df['Close'].rolling(10).mean()
        delta = df['Close'].diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        df['RSI'] = 100 - (100 / (1 + (gain / loss.replace(0, 1)).replace([np.inf, -np.inf], 50)))
        df = df.dropna()

        X = df[['Returns', 'SMA_10', 'RSI']].values[:-1]
        y = (df['Close'].shift(-1).values[:-1] > df['Close'].values[:-1]).astype(int)

        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        model = RandomForestClassifier(n_estimators=30, max_depth=5, random_state=42)
        model.fit(X_scaled, y)

        joblib.dump(model, f"{ticker}_model.pkl")
        joblib.dump(scaler, f"{ticker}_scaler.pkl")

        return jsonify({"status": "success", "ticker": ticker, "accuracy": round(model.score(X_scaled, y) * 100, 1)})
    except Exception as e:
        return jsonify({"error": str(e)})


def create_template():
    template = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Stock Predictor AI - Dashboard</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/3.9.1/chart.min.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        body { font-family: 'Inter', sans-serif; }
        .gradient-bg { background: linear-gradient(135deg, #0f172a 0%, #1e3a5f 50%, #0f172a 100%); }
        .glass { background: rgba(255,255,255,0.05); backdrop-filter: blur(20px); border: 1px solid rgba(255,255,255,0.1); }
        .glow-blue { box-shadow: 0 0 30px rgba(59,130,246,0.3); }
        .glow-green { box-shadow: 0 0 20px rgba(34,197,94,0.4); }
        .glow-red { box-shadow: 0 0 20px rgba(239,68,68,0.4); }
    </style>
</head>
<body class="gradient-bg min-h-screen text-white">
    <nav class="glass sticky top-0 z-50 border-b border-gray-800/50">
        <div class="max-w-7xl mx-auto px-4 py-3 flex justify-between items-center">
            <div class="flex items-center gap-3">
                <div class="w-10 h-10 bg-gradient-to-r from-blue-500 to-purple-600 rounded-xl flex items-center justify-center font-bold text-lg">S</div>
                <div><h1 class="font-bold text-xl">Stock Predictor AI</h1><p class="text-xs text-gray-400">S&P 500 Intelligence</p></div>
            </div>
            <div class="flex gap-2">
                <button onclick="showTab('dashboard')" class="px-4 py-2 rounded-lg hover:bg-white/10 transition text-sm font-medium">Dashboard</button>
                <button onclick="showTab('predict')" class="px-4 py-2 rounded-lg hover:bg-white/10 transition text-sm font-medium">Predict</button>
                <button onclick="showTab('top-picks')" class="px-4 py-2 rounded-lg hover:bg-white/10 transition text-sm font-medium">Top Picks</button>
                <button onclick="showTab('backtest')" class="px-4 py-2 rounded-lg hover:bg-white/10 transition text-sm font-medium">Backtest</button>
                <button onclick="showTab('all-predictions')" class="px-4 py-2 rounded-lg hover:bg-white/10 transition text-sm font-medium">All</button>
            </div>
        </div>
    </nav>
    <main class="max-w-7xl mx-auto px-4 py-6">
        <div id="dashboard-tab">
            <div class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
                <div class="glass rounded-xl p-5"><div class="text-gray-400 text-sm mb-1">Active Models</div><div class="text-3xl font-bold text-blue-400" id="model-count">-</div></div>
                <div class="glass rounded-xl p-5"><div class="text-gray-400 text-sm mb-1">Trained Stocks</div><div class="text-3xl font-bold text-green-400" id="trained-count">-</div></div>
                <div class="glass rounded-xl p-5"><div class="text-gray-400 text-sm mb-1">Top Pick</div><div class="text-2xl font-bold" id="top-pick">-</div></div>
                <div class="glass rounded-xl p-5"><div class="text-gray-400 text-sm mb-1">System</div><div class="text-2xl font-bold text-green-400">Online</div></div>
            </div>
            <div class="glass rounded-xl p-6 mb-6">
                <h2 class="text-xl font-bold mb-4 flex items-center gap-2"><span class="w-2 h-8 bg-green-500 rounded-full"></span>Today's Top Recommendations</h2>
                <div id="top-picks-grid" class="grid grid-cols-1 md:grid-cols-5 gap-4"><div class="text-gray-400">Loading...</div></div>
            </div>
            <div class="glass rounded-xl p-6"><h2 class="text-xl font-bold mb-4">Prediction Confidence</h2><canvas id="confidenceChart" height="100"></canvas></div>
        </div>
        <div id="predict-tab" class="hidden">
            <div class="max-w-2xl mx-auto">
                <div class="glass rounded-xl p-8">
                    <h2 class="text-2xl font-bold mb-6 text-center">Stock Predictor</h2>
                    <div class="flex gap-3 mb-6">
                        <input type="text" id="ticker-input" placeholder="Enter ticker (e.g., AAPL)" class="flex-1 bg-gray-800/50 border border-gray-700 rounded-xl px-5 py-4 text-lg focus:border-blue-500 focus:outline-none uppercase">
                        <button onclick="predict()" class="bg-gradient-to-r from-blue-600 to-purple-600 px-8 py-4 rounded-xl font-bold hover:opacity-90 transition glow-blue">Predict</button>
                    </div>
                    <div id="prediction-result" class="hidden">
                        <div class="grid grid-cols-2 gap-4 mb-4">
                            <div class="bg-gray-800/50 rounded-xl p-4 text-center"><div class="text-gray-400 text-sm mb-1">Prediction</div><div id="pred-direction" class="text-4xl font-bold">-</div></div>
                            <div class="bg-gray-800/50 rounded-xl p-4 text-center"><div class="text-gray-400 text-sm mb-1">Confidence</div><div id="pred-confidence" class="text-4xl font-bold">-</div></div>
                        </div>
                        <div class="grid grid-cols-3 gap-4">
                            <div class="bg-gray-800/50 rounded-xl p-4 text-center"><div class="text-gray-400 text-sm">Price</div><div id="pred-price" class="text-xl font-bold">-</div></div>
                            <div class="bg-gray-800/50 rounded-xl p-4 text-center"><div class="text-gray-400 text-sm">Change</div><div id="pred-change" class="text-xl font-bold">-</div></div>
                            <div class="bg-gray-800/50 rounded-xl p-4 text-center"><div class="text-gray-400 text-sm">Up Probability</div><div id="pred-up" class="text-xl font-bold">-</div></div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        <div id="top-picks-tab" class="hidden">
            <div class="glass rounded-xl p-6"><h2 class="text-2xl font-bold mb-6">Today's Best Opportunities</h2><div id="all-picks" class="space-y-3"><div class="text-gray-400">Loading recommendations...</div></div></div>
        </div>
        <div id="backtest-tab" class="hidden">
            <div class="max-w-2xl mx-auto">
                <div class="glass rounded-xl p-8">
                    <h2 class="text-2xl font-bold mb-6">Strategy Backtest</h2>
                    <div class="mb-4"><label class="block text-gray-400 mb-2">Tickers (comma-separated)</label><input type="text" id="backtest-tickers" value="AAPL,MSFT,GOOGL,AMZN,NVDA,TSLA" class="w-full bg-gray-800/50 border border-gray-700 rounded-xl px-4 py-3"></div>
                    <button onclick="runBacktest()" class="w-full bg-gradient-to-r from-green-600 to-blue-600 py-4 rounded-xl font-bold">Run Backtest</button>
                    <div id="backtest-results" class="mt-6 space-y-3"></div>
                </div>
            </div>
        </div>
        <div id="all-predictions-tab" class="hidden">
            <div class="glass rounded-xl p-6"><h2 class="text-2xl font-bold mb-4">All Stock Predictions</h2><div class="overflow-x-auto"><table class="w-full"><thead><tr class="text-gray-400 border-b border-gray-700"><th class="text-left py-3">Ticker</th><th class="text-left py-3">Prediction</th><th class="text-right py-3">Confidence</th><th class="text-right py-3">Price</th></tr></thead><tbody id="all-predictions-body"></tbody></table></div></div>
        </div>
    </main>
    <script>
        let chart;
        async function loadDashboard() {
            const status = await fetch('/api/status').then(r => r.json());
            document.getElementById('model-count').textContent = status.models || 0;
            document.getElementById('trained-count').textContent = status.trained || 0;
            const picks = await fetch('/api/top-picks').then(r => r.json());
            if (picks.picks && picks.picks.length > 0) {
                document.getElementById('top-pick').textContent = picks.picks[0].ticker;
                renderTopPicks(picks.picks);
                renderChart(picks.picks);
            }
        }
        function renderTopPicks(picks) {
            const grid = document.getElementById('top-picks-grid');
            grid.innerHTML = picks.map(p => `<div class="bg-gray-800/50 rounded-xl p-4 ${p.prediction === 'UP' ? 'glow-green' : 'glow-red'}"><div class="flex justify-between items-center mb-2"><span class="font-bold text-lg">${p.ticker}</span><span class="${p.prediction === 'UP' ? 'text-green-400' : 'text-red-400'} font-bold">${p.prediction}</span></div><div class="text-2xl font-bold mb-1">${p.confidence}%</div><div class="text-gray-400 text-sm">\$${p.price.toFixed(2)}</div><div class="${p.change >= 0 ? 'text-green-400' : 'text-red-400'} text-sm">${p.change >= 0 ? '+' : ''}${p.change.toFixed(2)}%</div></div>`).join('');
        }
        function renderChart(picks) {
            const ctx = document.getElementById('confidenceChart');
            if (chart) chart.destroy();
            chart = new Chart(ctx, {type: 'bar', data: {labels: picks.map(p => p.ticker), datasets: [{label: 'Confidence %', data: picks.map(p => p.confidence), backgroundColor: picks.map(p => p.prediction === 'UP' ? 'rgba(34,197,94,0.7)' : 'rgba(239,68,68,0.7)'), borderColor: picks.map(p => p.prediction === 'UP' ? '#22c55e' : '#ef4444'), borderWidth: 2}]}, options: {responsive: true, scales: {y: {beginAtZero: true, max: 100, grid: {color: 'rgba(255,255,255,0.1)'}}, x: {grid: {display: false}}}}});
        }
        async function predict() {
            const ticker = document.getElementById('ticker-input').value.toUpperCase();
            if (!ticker) return;
            const result = await fetch('/api/predict/' + ticker).then(r => r.json());
            if (result.error) { alert(result.error); return; }
            document.getElementById('prediction-result').classList.remove('hidden');
            document.getElementById('pred-direction').textContent = result.prediction;
            document.getElementById('pred-direction').className = 'text-4xl font-bold ' + (result.prediction === 'UP' ? 'text-green-400' : 'text-red-400');
            document.getElementById('pred-confidence').textContent = result.confidence + '%';
            document.getElementById('pred-price').textContent = '$' + result.price;
            document.getElementById('pred-change').textContent = (result.change >= 0 ? '+' : '') + result.change + '%';
            document.getElementById('pred-change').className = 'text-xl font-bold ' + (result.change >= 0 ? 'text-green-400' : 'text-red-400');
            document.getElementById('pred-up').textContent = result.up_prob + '%';
        }
        async function runBacktest() {
            const tickers = document.getElementById('backtest-tickers').value.split(',').map(t => t.trim());
            const results = await fetch('/api/backtest', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({tickers})}).then(r => r.json());
            document.getElementById('backtest-results').innerHTML = results.results.map(r => `<div class="flex justify-between items-center bg-gray-800/50 rounded-xl p-4"><span class="font-bold">${r.ticker}</span><div class="text-right"><div class="${r.return >= 0 ? 'text-green-400' : 'text-red-400'} font-bold">${r.return}%</div><div class="text-gray-400 text-sm">Sharpe: ${r.sharpe}</div></div></div>`).join('');
        }
        async function loadAllPredictions() {
            const results = await fetch('/api/predict/all').then(r => r.json());
            const tbody = document.getElementById('all-predictions-body');
            tbody.innerHTML = results.predictions.map(p => `<tr class="border-b border-gray-800 hover:bg-white/5"><td class="py-3 font-bold">${p.ticker}</td><td class="py-3"><span class="${p.prediction === 'UP' ? 'text-green-400' : 'text-red-400'} font-bold">${p.prediction}</span></td><td class="py-3 text-right">${p.confidence}%</td><td class="py-3 text-right">\$${p.price.toFixed(2)}</td></tr>`).join('');
        }
        function showTab(tab) { document.querySelectorAll('[id$="-tab"]').forEach(t => t.classList.add('hidden')); document.getElementById(tab + '-tab').classList.remove('hidden'); if (tab === 'all-predictions') loadAllPredictions(); }
        loadDashboard();
    </script>
</body>
</html>"""
    os.makedirs(os.path.join(BASE_DIR, 'templates'), exist_ok=True)
    with open(os.path.join(BASE_DIR, 'templates', 'index.html'), 'w') as f:
        f.write(template)
    print("Template created successfully")


def run_server(port=5000):
    create_template()
    print(f"\n{'='*60}")
    print(f"  STOCK PREDICTOR AI - WEB DASHBOARD")
    print(f"{'='*60}")
    print(f"  Open: http://localhost:{port}")
    print(f"{'='*60}\n")
    socketio.run(app, host='0.0.0.0', port=port, debug=False)


if __name__ == "__main__":
    import argparse
    run_server(argparse.ArgumentParser().parse_args().port if hasattr(argparse, 'parse_args') else 5000)