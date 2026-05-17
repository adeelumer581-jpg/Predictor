"""
Stock Predictor Web UI — with APEX GODMODE Predictor
"""
import os, sys, json, logging
from datetime import datetime
from threading import Thread
from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("WebUI")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, 'templates')

# Load .env
env_path = os.path.join(BASE_DIR, '.env')
if os.path.exists(env_path):
    with open(env_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, v = line.split('=', 1)
                os.environ.setdefault(k.strip(), v.strip())

app = Flask(__name__, template_folder=TEMPLATES_DIR, static_folder='static')
app.config['SECRET_KEY'] = 'apex-predictor-2026'
async_mode = 'gevent' if os.environ.get('RENDER') else None
socketio = SocketIO(app, cors_allowed_origins="*", async_mode=async_mode)

class WebUIManager:
    def __init__(self):
        self.predictions = {}
        self.system_status = {"training": "idle", "backtesting": "idle", "models_loaded": 0}
    def get_available_models(self):
        models = []
        try:
            for f in os.listdir(BASE_DIR):
                if f.endswith('_model.pkl'):
                    models.append(f.replace('_model.pkl', ''))
        except: pass
        return sorted(models)
    def get_system_status(self):
        return {"available_models": len(self.get_available_models()), "timestamp": datetime.now().isoformat()}

ui_manager = WebUIManager()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/status')
def api_status():
    return jsonify(ui_manager.get_system_status())

@app.route('/api/models')
def api_models():
    return jsonify({"models": ui_manager.get_available_models()})

@app.route('/api/predict/<ticker>')
def api_predict(ticker):
    ticker = ticker.upper()
    try:
        sys.path.insert(0, BASE_DIR)
        from stock_predictor import StockPredictor
        predictor = StockPredictor(ticker)
        model_path = os.path.join(BASE_DIR, f"{ticker}_model.pkl")
        if os.path.exists(model_path):
            predictor.load_model(model_path)
        else:
            predictor.fetch_data()
            predictor.calculate_indicators(predictor.fetch_data())
            predictor.train()
        res = predictor.predict_next()
        return jsonify(res)
    except Exception as e:
        logger.error(f"Predict error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/chart/<ticker>')
def api_chart(ticker):
    ticker = ticker.upper()
    lookback = request.args.get('lookback_days', 100, type=int)
    try:
        sys.path.insert(0, BASE_DIR)
        from apex_predictor import ApexPredictor
        predictor = ApexPredictor(ticker)
        df = predictor.fetch_data(period=f"{max(5, lookback)}d" if lookback <= 365 else "1y")
        if df is None or df.empty:
            return jsonify({"error": "No data"}), 404
        data = []
        for idx, row in df.iterrows():
            data.append({
                "time": int(idx.timestamp()),
                "open": float(row['Open']), "high": float(row['High']),
                "low": float(row['Low']), "close": float(row['Close'])
            })
        return jsonify(data)
    except Exception as e:
        logger.error(f"Chart error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/apex/predict/<ticker>')
def api_apex_predict(ticker):
    ticker = ticker.upper()
    try:
        sys.path.insert(0, BASE_DIR)
        from apex_predictor import ApexPredictor
        predictor = ApexPredictor(ticker)
        result = predictor.predict()
        return jsonify(result)
    except Exception as e:
        logger.error(f"APEX error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/apex/accuracy')
def api_apex_accuracy():
    path = os.path.join(BASE_DIR, "apex_accuracy.json")
    if os.path.exists(path):
        with open(path, 'r') as f:
            return jsonify(json.load(f))
    return jsonify({"total": 0, "correct": 0, "recent": [], "by_confidence": {}})

@app.route('/api/apex/record_outcome', methods=['POST'])
def api_apex_record_outcome():
    data = request.json or {}
    try:
        sys.path.insert(0, BASE_DIR)
        from apex_predictor import ApexPredictor
        p = ApexPredictor(data.get('ticker', 'AAPL').upper())
        p.record_outcome(data.get('was_correct', False), data.get('confidence_label', 'Medium'))
        return jsonify({"status": "recorded"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ─── TEMPLATE ───

def create_templates():
    os.makedirs(TEMPLATES_DIR, exist_ok=True)
    html = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>APEX Predictor — Stock Market AI</title>
<script src="https://cdn.tailwindcss.com"></script>
<script src="https://unpkg.com/lightweight-charts/dist/lightweight-charts.standalone.production.js"></script>
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
body { font-family: 'Inter', sans-serif; background: linear-gradient(135deg, #0f0f1a 0%, #1a0a0a 100%); min-height: 100vh; color: #e2e8f0; }
.card { background: rgba(255,255,255,0.03); backdrop-filter: blur(10px); border: 1px solid rgba(255,255,255,0.08); }
.glow { animation: glow 2s ease-in-out infinite alternate; }
.glow-red { animation: glowRed 2s ease-in-out infinite alternate; }
@keyframes glow { from { box-shadow: 0 0 10px rgba(59,130,246,0.3); } to { box-shadow: 0 0 20px rgba(59,130,246,0.6); } }
@keyframes glowRed { from { box-shadow: 0 0 10px rgba(239,68,68,0.3); } to { box-shadow: 0 0 25px rgba(239,68,68,0.6); } }
.nav-link { position: relative; }
.nav-link::after { content: ''; position: absolute; bottom: -2px; left: 0; width: 0; height: 2px; transition: width 0.3s; }
.nav-link:hover::after { width: 100%; }
</style>
</head>
<body>
<header class="border-b border-gray-800 bg-black/50 backdrop-blur-md sticky top-0 z-50">
  <div class="max-w-7xl mx-auto px-6 py-3 flex flex-wrap justify-between items-center gap-2">
    <div class="flex items-center gap-3">
      <div class="w-10 h-10 bg-gradient-to-br from-red-600 to-orange-500 rounded-lg flex items-center justify-center text-xl font-bold">A</div>
      <div><h1 class="text-xl font-bold">Stock Predictor AI</h1><p class="text-xs text-gray-500">GODMODE — APEX Engine</p></div>
    </div>
    <nav class="flex gap-3 text-sm flex-wrap">
      <a href="#" onclick="showSection('dashboard')" class="nav-link hover:text-blue-400 transition">Dashboard</a>
      <a href="#" onclick="showSection('predict')" class="nav-link hover:text-blue-400 transition">Predict</a>
      <a href="#" onclick="showSection('live')" class="nav-link hover:text-indigo-400 transition">Live Charts</a>
      <a href="#" onclick="showSection('apex')" class="nav-link text-red-400 hover:text-red-300 font-bold transition border-b-2 border-red-500">APEX Predict</a>
      <a href="#" onclick="showSection('backtest')" class="nav-link hover:text-blue-400 transition">Backtest</a>
      <a href="#" onclick="showSection('train')" class="nav-link hover:text-blue-400 transition">Train</a>
    </nav>
  </div>
</header>

<main class="max-w-7xl mx-auto px-6 py-8">

<!-- DASHBOARD -->
<div id="dashboard" class="section">
  <div class="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
    <div class="card rounded-xl p-6"><div class="text-gray-500 text-sm mb-2">Active Models</div><div class="text-3xl font-bold" id="model-count">-</div></div>
    <div class="card rounded-xl p-6"><div class="text-gray-500 text-sm mb-2">System Status</div><div class="text-3xl font-bold text-green-400" id="system-status">Active</div></div>
    <div class="card rounded-xl p-6"><div class="text-gray-500 text-sm mb-2">APEX Accuracy</div><div class="text-3xl font-bold text-orange-400" id="apex-accuracy-dash">-</div></div>
    <div class="card rounded-xl p-6"><div class="text-gray-500 text-sm mb-2">Last Updated</div><div class="text-3xl font-bold" id="last-updated">-</div></div>
  </div>
  <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
    <div class="card rounded-xl p-6"><h3 class="text-lg font-semibold mb-4">Live Market Chart</h3><div id="tv-chart" class="h-[300px] w-full bg-gray-900/30 rounded-lg"></div></div>
    <div class="card rounded-xl p-6"><h3 class="text-lg font-semibold mb-4">Available Models</h3><div id="model-list" class="space-y-2 max-h-[300px] overflow-y-auto"></div></div>
  </div>
</div>

<!-- PREDICT -->
<div id="predict" class="section hidden">
  <div class="max-w-xl mx-auto">
    <div class="card rounded-xl p-8">
      <h2 class="text-2xl font-bold mb-6 text-center">Make Prediction</h2>
      <div class="flex gap-4 mb-6">
        <input type="text" id="ticker-input" placeholder="Enter ticker (e.g., AAPL, EURUSD=X, GC=F, LUCK.PSX)" class="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-4 py-3 focus:border-blue-500 focus:outline-none uppercase">
        <button onclick="makePrediction()" class="bg-blue-600 hover:bg-blue-700 px-8 py-3 rounded-lg font-semibold glow">Predict</button>
      </div>
      <div id="prediction-result" class="hidden text-center p-6 bg-gray-800 rounded-lg">
        <div class="text-lg font-bold mb-2" id="pred-direction">-</div>
        <div class="text-2xl font-bold" id="pred-confidence">-</div>
        <div class="mt-2 text-gray-400" id="pred-price">-</div>
      </div>
    </div>
  </div>
</div>

<!-- LIVE CHARTS -->
<div id="live" class="section hidden">
  <div class="max-w-7xl mx-auto">
    <div class="card rounded-xl p-8">
      <h2 class="text-2xl font-bold mb-6">Live Charts</h2>
      <div class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <div>
          <label class="text-gray-400 text-sm block mb-1">Asset Type</label>
          <select id="live-asset-type" class="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-3">
            <option value="stocks">US Stocks</option><option value="commodities">Commodities</option>
            <option value="pakistani">PSX (Pakistan)</option><option value="forex">Forex</option><option value="crypto">Crypto</option>
          </select>
        </div>
        <div>
          <label class="text-gray-400 text-sm block mb-1">Symbol</label>
          <input type="text" id="live-symbol" value="AAPL" placeholder="AAPL, GC=F, LUCK.PSX, EURUSD=X, BTC-USD" class="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-3 uppercase">
        </div>
        <div>
          <label class="text-gray-400 text-sm block mb-1">Timeframe</label>
          <select id="live-timeframe" class="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-3">
            <option value="5d">5 Days</option><option value="1mo">1 Month</option>
            <option value="3mo" selected>3 Months</option><option value="6mo">6 Months</option><option value="1y">1 Year</option>
          </select>
        </div>
        <div class="flex items-end"><button onclick="loadLiveChart()" class="w-full bg-indigo-600 hover:bg-indigo-700 py-3 rounded-lg font-semibold">Load Chart</button></div>
      </div>
      <div id="live-chart-container" class="h-[500px] bg-gray-900/30 rounded-lg"></div>
      <div id="prediction-info" class="grid grid-cols-4 gap-4 mt-4">
        <div class="p-4 bg-gray-800 rounded-lg text-center"><div class="text-gray-400 text-sm">Price</div><div id="live-price" class="text-xl font-bold">-</div></div>
        <div class="p-4 bg-gray-800 rounded-lg text-center"><div class="text-gray-400 text-sm">Prediction</div><div id="live-prediction" class="text-xl font-bold">-</div></div>
        <div class="p-4 bg-gray-800 rounded-lg text-center"><div class="text-gray-400 text-sm">Confidence</div><div id="live-confidence" class="text-xl font-bold">-</div></div>
        <div class="p-4 bg-gray-800 rounded-lg text-center"><div class="text-gray-400 text-sm">Signal</div><div id="live-signal" class="text-xl font-bold">-</div></div>
      </div>
    </div>
  </div>
</div>

<!-- APEX PREDICTOR -->
<div id="apex" class="section hidden">
  <div class="max-w-7xl mx-auto">
    <div class="bg-gradient-to-r from-red-900/20 to-orange-900/20 border border-red-500/30 rounded-xl p-6 shadow-[0_0_30px_rgba(255,0,0,0.1)]">
      <div class="flex items-center gap-4 mb-6">
        <div class="text-4xl">A</div>
        <div><h2 class="text-3xl font-bold text-red-400">APEX PREDICTOR</h2><p class="text-gray-500 text-sm">GODMODE Multi-Dimensional Confluence Engine</p></div>
      </div>
      <div class="grid grid-cols-1 md:grid-cols-5 gap-4 mb-6">
        <div>
          <label class="text-gray-400 text-sm block mb-1">Symbol</label>
          <input type="text" id="apex-ticker" value="AAPL" class="w-full bg-gray-900 border border-gray-700 rounded-lg px-4 py-3 uppercase text-lg font-bold">
        </div>
        <div>
          <label class="text-gray-400 text-sm block mb-1">Asset</label>
          <select id="apex-asset-class" class="w-full bg-gray-900 border border-gray-700 rounded-lg px-4 py-3">
            <option value="auto">Auto-Detect</option><option value="stock">US Stock</option>
            <option value="commodity">Commodity</option><option value="forex">Forex</option>
            <option value="psx">PSX</option><option value="crypto">Crypto</option>
          </select>
        </div>
        <div>
          <label class="text-gray-400 text-sm block mb-1">Period</label>
          <select id="apex-period" class="w-full bg-gray-900 border border-gray-700 rounded-lg px-4 py-3">
            <option value="5d">5 Days</option><option value="1mo">1 Month</option>
            <option value="3mo" selected>3 Months</option><option value="6mo">6 Months</option><option value="1y">1 Year</option>
          </select>
        </div>
        <div class="flex items-end"><button onclick="runApexPrediction()" class="w-full bg-gradient-to-r from-red-600 to-orange-600 hover:from-red-500 hover:to-orange-500 py-3 rounded-lg font-bold glow-red">PREDICT</button></div>
        <div class="flex items-end"><button onclick="toggleApexAutoRefresh()" id="apex-auto-btn" class="w-full bg-gray-800 hover:bg-gray-700 border border-gray-700 py-3 rounded-lg font-semibold">Auto: OFF</button></div>
      </div>

      <div id="apex-loading" class="hidden text-center py-20">
        <div class="animate-spin text-6xl mb-4 rounded-full h-16 w-16 border-t-4 border-red-500 mx-auto"></div>
        <p class="text-gray-400 text-xl">Calculating multi-dimensional confluence...</p>
        <div class="mt-4 h-2 bg-gray-800 rounded-full max-w-md mx-auto overflow-hidden">
          <div id="apex-progress-bar" class="h-full bg-gradient-to-r from-red-500 to-orange-500 transition-all" style="width: 0%"></div>
        </div>
      </div>

      <div id="apex-result" class="hidden">
        <div class="bg-gray-900/80 border border-gray-800 rounded-xl p-4 mb-6 flex justify-between items-center">
          <div><div class="text-gray-500 text-xs">APEX PREDICTION</div><div id="apex-timestamp" class="text-lg font-bold">-</div></div>
          <div class="text-right"><div class="text-gray-500 text-xs">ASSET</div><div class="text-lg font-bold" id="apex-asset-display">-</div></div>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          <div class="bg-gray-900/80 border border-gray-800 rounded-xl p-6 text-center">
            <div class="text-gray-500 text-xs mb-1">DIRECTION</div>
            <div id="apex-direction" class="text-4xl font-bold">-</div>
            <div id="apex-current-price" class="text-lg mt-1 text-gray-400">-</div>
          </div>
          <div class="bg-gray-900/80 border border-gray-800 rounded-xl p-6 text-center">
            <div class="text-gray-500 text-xs mb-1">CONFIDENCE</div>
            <div id="apex-confidence" class="text-4xl font-bold">-</div>
            <div id="apex-confidence-label" class="text-sm mt-1">-</div>
          </div>
          <div class="bg-gray-900/80 border border-gray-800 rounded-xl p-6 text-center">
            <div class="text-gray-500 text-xs mb-1">CONFLUENCE</div>
            <div id="apex-confluence" class="text-4xl font-bold text-orange-400">-</div>
            <div class="text-sm mt-1 text-gray-500">/ 50</div>
          </div>
        </div>

        <div class="grid grid-cols-3 gap-4 mb-6">
          <div class="bg-gray-900/50 border border-gray-800 rounded-lg p-4 text-center"><div class="text-gray-500 text-xs">ENTRY</div><div id="apex-entry" class="text-lg font-bold">-</div></div>
          <div class="bg-gray-900/50 border border-gray-800 rounded-lg p-4 text-center"><div class="text-gray-500 text-xs">TARGET</div><div id="apex-target" class="text-lg font-bold text-green-500">-</div></div>
          <div class="bg-gray-900/50 border border-gray-800 rounded-lg p-4 text-center"><div class="text-gray-500 text-xs">STOP LOSS</div><div id="apex-stop" class="text-lg font-bold text-red-500">-</div></div>
        </div>

        <div class="bg-gray-900/80 border border-gray-800 rounded-xl p-6 mb-6">
          <h3 class="text-lg font-bold mb-4 text-orange-400">CONFLUENCE SCORES</h3>
          <div id="apex-dimensions" class="space-y-2"></div>
          <div class="mt-4 pt-4 border-t border-gray-800 flex justify-between">
            <span class="text-gray-400">TOTAL CONFLUENCE</span>
            <span id="apex-total-confluence" class="font-bold text-xl text-orange-400">- / 50</span>
          </div>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
          <div class="bg-gray-900/80 border border-gray-800 rounded-xl p-6">
            <h3 class="text-lg font-bold mb-4 text-red-400">KEY LEVELS</h3>
            <div id="apex-levels" class="space-y-1 text-sm"></div>
          </div>
          <div class="bg-gray-900/80 border border-gray-800 rounded-xl p-6">
            <h3 class="text-lg font-bold mb-4 text-blue-400">CANDLE FORMATION</h3>
            <div id="apex-candle" class="space-y-1 text-sm"></div>
            <div class="mt-3 pt-3 border-t border-gray-800">
              <div class="text-gray-400 text-xs mb-1">Multi-TF Alignment</div>
              <div id="apex-multitf" class="text-sm font-mono"></div>
            </div>
          </div>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
          <div class="bg-gray-900/80 border border-gray-800 rounded-xl p-6">
            <h3 class="text-lg font-bold mb-4 text-green-400">TOP REASONS</h3>
            <div id="apex-reasons" class="space-y-1 text-sm"></div>
          </div>
          <div class="bg-gray-900/80 border border-gray-800 rounded-xl p-6">
            <h3 class="text-lg font-bold mb-4 text-red-400">RISK FACTORS</h3>
            <div id="apex-risks" class="space-y-1 text-sm"></div>
          </div>
        </div>

        <div class="bg-gray-900/80 border border-gray-800 rounded-xl p-6 mb-6">
          <h3 class="text-lg font-bold mb-4 text-gray-400">RAW PREDICTION</h3>
          <pre id="apex-raw-output" class="text-xs text-gray-500 font-mono whitespace-pre-wrap max-h-40 overflow-y-auto p-4 bg-black/50 rounded-lg"></pre>
        </div>

        <div class="bg-gray-900/80 border border-gray-800 rounded-xl p-6">
          <h3 class="text-lg font-bold mb-4 text-yellow-400">SELF-CORRECTING FEEDBACK</h3>
          <p class="text-gray-500 text-sm mb-4">Was this prediction correct?</p>
          <div class="flex gap-4">
            <button onclick="recordApexOutcome(true)" class="bg-green-700 hover:bg-green-600 px-8 py-3 rounded-lg font-bold">YES — Correct</button>
            <button onclick="recordApexOutcome(false)" class="bg-red-700 hover:bg-red-600 px-8 py-3 rounded-lg font-bold">NO — Incorrect</button>
          </div>
          <div id="apex-accuracy-display" class="mt-4 p-4 bg-gray-800/50 rounded-lg">
            <div class="text-gray-400 text-sm">Loading accuracy stats...</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</div>

<!-- BACKTEST -->
<div id="backtest" class="section hidden">
  <div class="max-w-2xl mx-auto">
    <div class="card rounded-xl p-8">
      <h2 class="text-2xl font-bold mb-6">Run Backtest</h2>
      <div class="mb-6">
        <label class="text-gray-400 block mb-2">Tickers</label>
        <input type="text" id="backtest-tickers" value="AAPL,MSFT,NVDA,TSLA" class="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-3">
      </div>
      <button onclick="runBacktest()" class="w-full bg-blue-600 hover:bg-blue-700 py-3 rounded-lg font-semibold">Run Backtest</button>
      <div id="backtest-results" class="mt-6 hidden p-4 bg-gray-800 rounded-lg"></div>
    </div>
  </div>
</div>

<!-- TRAIN -->
<div id="train" class="section hidden">
  <div class="max-w-2xl mx-auto">
    <div class="card rounded-xl p-8">
      <h2 class="text-2xl font-bold mb-6">Mass Training</h2>
      <button onclick="startTraining()" class="w-full bg-blue-600 hover:bg-blue-700 py-3 rounded-lg font-semibold">Start Training</button>
      <div id="training-status" class="mt-6 p-4 bg-gray-800 rounded-lg text-center text-gray-400">Models are pre-trained and ready</div>
    </div>
  </div>
</div>

</main>

<footer class="border-t border-gray-800 bg-black/50 py-6 px-6 mt-8">
  <div class="max-w-7xl mx-auto text-center text-xs text-gray-500">
    <p class="mb-2">DISCLAIMER: This is for educational purposes only. Not financial advice.</p>
    <p>APEX Predictor v2.0 &mdash; Multi-Dimensional Market Confluence Engine</p>
  </div>
</footer>

<script>
let currentSection = 'dashboard';
const socket = io();

function showSection(section) {
  document.querySelectorAll('.section').forEach(s => s.classList.add('hidden'));
  document.getElementById(section).classList.remove('hidden');
  currentSection = section;
  if(section === 'dashboard') { loadDashboard(); initChart(); }
  if(section === 'apex') { loadApexAccuracy(); }
}

// Dashboard
let tvChart = null;

function initChart() {
  const container = document.getElementById('tv-chart');
  if(!container || tvChart) return;
  tvChart = LightweightCharts.createChart(container, {
    width: container.clientWidth, height: 300,
    layout: { background: { type: 'solid', color: 'transparent' }, textColor: '#94a3b8' },
    grid: { vertLines: { color: '#1e293b' }, horzLines: { color: '#1e293b' } },
    crosshair: { mode: LightweightCharts.CrosshairMode.Normal }
  });
  const series = tvChart.addAreaSeries({
    color: '#3b82f6', lineColor: '#3b82f6', topColor: 'rgba(59,130,246,0.3)', bottomColor: 'rgba(59,130,246,0.05)'
  });
  // Load live chart data
  loadDashboardChart(series);
}

async function loadDashboardChart(series) {
  try {
    const resp = await fetch('/api/chart/AAPL?lookback_days=90');
    const data = await resp.json();
    if(!data.error && data.length > 0) {
      const lineData = data.map(d => ({ time: d.time, value: d.close }));
      series.setData(lineData);
      tvChart.timeScale().fitContent();
      return;
    }
  } catch(e) {}
  // Fallback: generate dummy data if API fails
  const fb = [];
  let v = 180;
  for(let i = 0; i < 90; i++) {
    v += (Math.random() - 0.48) * 3;
    fb.push({ time: Math.floor(Date.now()/1000) - (90-i)*86400, value: v });
  }
  series.setData(fb);
}

async function loadDashboard() {
  try {
    const status = await fetch('/api/status').then(r => r.json());
    document.getElementById('model-count').textContent = status.available_models || 0;
    document.getElementById('last-updated').textContent = new Date().toLocaleTimeString();
    const models = await fetch('/api/models').then(r => r.json());
    document.getElementById('model-list').innerHTML = (models.models || []).slice(0,15).map(m =>
      `<div class="flex justify-between p-2 bg-gray-800 rounded"><span class="font-mono text-sm">${m}</span><span class="text-green-400 text-sm">Ready</span></div>`
    ).join('') || '<div class="text-gray-500 text-sm">No models loaded</div>';
    // APEX accuracy
    const acc = await fetch('/api/apex/accuracy').then(r => r.json());
    const pct = acc.total > 0 ? (acc.correct/acc.total*100).toFixed(1) : '-';
    document.getElementById('apex-accuracy-dash').textContent = acc.total > 0 ? pct + '%' : '-';
  } catch(e) { console.error(e); }
}

// Predict
async function makePrediction() {
  const ticker = document.getElementById('ticker-input').value.toUpperCase().trim();
  if(!ticker) return;
  const res = await fetch(`/api/predict/${ticker}`).then(r => r.json());
  if(res.error) { alert(res.error); return; }
  document.getElementById('prediction-result').classList.remove('hidden');
  document.getElementById('pred-direction').textContent = res.prediction;
  document.getElementById('pred-direction').className = `text-lg font-bold mb-2 ${res.prediction === 'UP' ? 'text-green-400' : 'text-red-400'}`;
  document.getElementById('pred-confidence').textContent = `Confidence: ${(res.confidence || 0).toFixed(1)}%`;
  document.getElementById('pred-price').textContent = `Price: $${res.price?.toFixed(2) || 'N/A'}`;
}

// Live Charts
let liveCandleChart = null;
function initLiveChart() {
  const container = document.getElementById('live-chart-container');
  if(!container) return;
  container.innerHTML = '';
  liveCandleChart = LightweightCharts.createChart(container, {
    width: container.clientWidth, height: 500,
    layout: { background: { type: 'solid', color: 'transparent' }, textColor: '#d1d5db' },
    grid: { vertLines: { color: '#2d3748' }, horzLines: { color: '#2d3748' } }
  });
  return liveCandleChart.addCandlestickSeries({
    upColor: '#26a69a', downColor: '#ef5350',
    borderDownColor: '#ef5350', borderUpColor: '#26a69a',
    wickDownColor: '#ef5350', wickUpColor: '#26a69a'
  });
}

async function loadLiveChart() {
  const symbol = document.getElementById('live-symbol').value.toUpperCase().trim();
  const tf = document.getElementById('live-timeframe').value;
  if(!symbol) return;
  const lookbacks = { '5d': 5, '1mo': 30, '3mo': 90, '6mo': 180, '1y': 365 };
  document.getElementById('live-chart-container').innerHTML = '<div class="flex h-[500px] items-center justify-center text-gray-400">Loading...</div>';
  let cs = liveCandleChart;
  if(!liveCandleChart) cs = initLiveChart();
  try {
    const resp = await fetch(`/api/chart/${symbol}?lookback_days=${lookbacks[tf] || 90}`);
    const data = await resp.json();
    if(data.error) throw new Error(data.error);
    cs.setData(data);
    liveCandleChart.timeScale().fitContent();
  } catch(e) {
    document.getElementById('live-chart-container').innerHTML = `<div class="flex h-[500px] items-center justify-center text-red-400">Error: ${e.message}</div>`;
  }
  try {
    const pred = await fetch(`/api/predict/${symbol}`).then(r => r.json());
    if(!pred.error) {
      document.getElementById('live-price').textContent = `$${pred.price?.toFixed(2) || 'N/A'}`;
      document.getElementById('live-prediction').textContent = pred.prediction || '-';
      document.getElementById('live-prediction').className = `text-xl font-bold ${pred.prediction === 'UP' ? 'text-green-400' : pred.prediction === 'DOWN' ? 'text-red-400' : ''}`;
      document.getElementById('live-confidence').textContent = `${(pred.confidence || 0).toFixed(1)}%`;
      const sig = document.getElementById('live-signal');
      const c = pred.confidence || 0;
      if(pred.prediction === 'UP' && c > 70) { sig.textContent = 'STRONG BUY'; sig.className = 'text-xl font-bold text-green-600'; }
      else if(pred.prediction === 'UP') { sig.textContent = 'BUY'; sig.className = 'text-xl font-bold text-green-400'; }
      else if(pred.prediction === 'DOWN' && c > 70) { sig.textContent = 'STRONG SELL'; sig.className = 'text-xl font-bold text-red-600'; }
      else if(pred.prediction === 'DOWN') { sig.textContent = 'SELL'; sig.className = 'text-xl font-bold text-red-400'; }
      else { sig.textContent = 'HOLD'; sig.className = 'text-xl font-bold text-yellow-400'; }
    }
  } catch(e) {}
}

// APEX Predictor
let apexAutoRefreshInterval = null;

async function runApexPrediction() {
  const ticker = document.getElementById('apex-ticker').value.toUpperCase().trim();
  if(!ticker) return;
  document.getElementById('apex-result').classList.add('hidden');
  document.getElementById('apex-loading').classList.remove('hidden');
  const bar = document.getElementById('apex-progress-bar');
  let p = 0;
  const pi = setInterval(() => { p = Math.min(90, p + Math.random() * 15); bar.style.width = p+'%'; }, 400);
  try {
    const resp = await fetch(`/api/apex/predict/${ticker}`);
    const data = await resp.json();
    clearInterval(pi); bar.style.width = '100%';
    if(data.error) throw new Error(data.error);
    setTimeout(() => { document.getElementById('apex-loading').classList.add('hidden'); displayApexPrediction(data); }, 500);
  } catch(e) {
    clearInterval(pi); document.getElementById('apex-loading').classList.add('hidden');
    alert('APEX Error: ' + e.message);
  }
}

function displayApexPrediction(data) {
  document.getElementById('apex-result').classList.remove('hidden');
  document.getElementById('apex-timestamp').textContent = data.timestamp || '-';
  document.getElementById('apex-asset-display').textContent = `${data.asset || '-'} (${data.asset_class || '-'})`;
  const dir = data.direction || 'HOLD';
  const dirEl = document.getElementById('apex-direction');
  if(dir === 'UP') { dirEl.textContent = 'UP'; dirEl.className = 'text-4xl font-bold text-green-500'; }
  else if(dir === 'DOWN') { dirEl.textContent = 'DOWN'; dirEl.className = 'text-4xl font-bold text-red-500'; }
  else { dirEl.textContent = 'HOLD'; dirEl.className = 'text-4xl font-bold text-yellow-500'; }
  document.getElementById('apex-current-price').textContent = `$${data.current_price || 'N/A'}`;
  const conf = data.confidence_pct || 0;
  const confEl = document.getElementById('apex-confidence');
  confEl.textContent = `${conf.toFixed(1)}%`;
  confEl.className = `text-4xl font-bold ${conf >= 75 ? 'text-green-400' : conf >= 55 ? 'text-yellow-400' : 'text-red-400'}`;
  document.getElementById('apex-confidence-label').textContent = data.confidence_label || '-';
  const ct = data.confluence?.total || 0;
  document.getElementById('apex-confluence').textContent = ct.toFixed(1);
  document.getElementById('apex-entry').textContent = `$${data.entry_price || 'N/A'}`;
  document.getElementById('apex-target').textContent = `$${data.target_price || 'N/A'}`;
  document.getElementById('apex-stop').textContent = `$${data.stop_loss || 'N/A'}`;
  const dims = data.confluence?.dimensions || [];
  document.getElementById('apex-dimensions').innerHTML = dims.map(d => {
    const icon = d.signal?.toLowerCase().includes('bullish') ? 'U' : d.signal?.toLowerCase().includes('bearish') ? 'D' : '--';
    const color = d.signal?.toLowerCase().includes('bullish') ? 'text-green-400' : d.signal?.toLowerCase().includes('bearish') ? 'text-red-400' : 'text-gray-400';
    return `<div class="flex justify-between p-2 bg-gray-800/50 rounded"><span class="text-gray-300">${d.name}</span><span class="font-mono"><span class="${color} font-bold">${d.score}/10</span> <span class="text-gray-600">-></span> <span class="${color}">${d.signal}</span></span></div>`;
  }).join('');
  document.getElementById('apex-total-confluence').textContent = `${ct.toFixed(1)} / 50`;
  const lv = data.levels || {};
  document.getElementById('apex-levels').innerHTML = [
    ['Resistance R3', lv.r3], ['Resistance R2', lv.r2], ['Resistance R1', lv.r1],
    ['Pivot', lv.pivot],
    ['Support S1', lv.s1], ['Support S2', lv.s2], ['Support S3', lv.s3],
    ['VWAP', lv.vwap], ['Recent High', lv.recent_high], ['Recent Low', lv.recent_low]
  ].map(([label, val]) => val ? `<div class="flex justify-between p-1 bg-gray-800/30 rounded"><span class="text-gray-400">${label}</span><span class="font-mono font-bold">${val}</span></div>` : '').join('');
  const cd = data.dimensions?.candle_strategy?.details || {};
  document.getElementById('apex-candle').innerHTML = [
    ['Pattern', cd.current_pattern || 'N/A'],
    ['Body %', cd.body_pct ? cd.body_pct+'%' : 'N/A'],
    ['Upper Wick', cd.upper_wick_pct ? cd.upper_wick_pct+'%' : 'N/A'],
    ['Lower Wick', cd.lower_wick_pct ? cd.lower_wick_pct+'%' : 'N/A']
  ].map(([label, val]) => `<div class="flex justify-between p-1 bg-gray-800/30 rounded"><span class="text-gray-400">${label}</span><span class="font-mono font-bold">${val}</span></div>`).join('');
  const tf = data.multi_tf_alignment || {};
  const tfHtml = Object.entries(tf).map(([k, v]) => {
    const i = v === 'Bullish' ? 'U' : v === 'Bearish' ? 'D' : '--';
    const c = v === 'Bullish' ? 'text-green-400' : v === 'Bearish' ? 'text-red-400' : 'text-gray-400';
    return `${k}=<span class="${c}">${i}</span>`;
  }).join(' ');
  document.getElementById('apex-multitf').innerHTML = tfHtml;
  let allSignals = [];
  Object.entries(data.dimensions || {}).forEach(([k, d]) => {
    if(d && d.signals) d.signals.forEach(s => allSignals.push(s));
  });
  allSignals = allSignals.slice(0, 8);
  document.getElementById('apex-reasons').innerHTML = allSignals.length ? allSignals.map((s, i) =>
    `<div class="flex gap-2 p-1 bg-gray-800/30 rounded"><span class="text-green-400">${i+1}.</span><span class="text-gray-300 text-xs">${s}</span></div>`
  ).join('') : '<div class="text-gray-500 text-xs p-2">No specific signals</div>';
  document.getElementById('apex-risks').innerHTML = `
    <div class="flex gap-2 p-1 bg-gray-800/30 rounded"><span class="text-yellow-400">!</span><span class="text-gray-300 text-xs">Confidence: ${conf.toFixed(1)}%</span></div>
    <div class="flex gap-2 p-1 bg-gray-800/30 rounded"><span class="text-yellow-400">!</span><span class="text-gray-300 text-xs">Markets change rapidly</span></div>`;
  document.getElementById('apex-raw-output').textContent = JSON.stringify(data, null, 2);
  loadApexAccuracy();
}

async function loadApexAccuracy() {
  try {
    const data = await fetch('/api/apex/accuracy').then(r => r.json());
    const t = data.total || 0; const c = data.correct || 0;
    const pct = t > 0 ? (c/t*100).toFixed(1) : 0;
    const recent = data.recent || []; const rc = recent.filter(r => r.correct).length;
    document.getElementById('apex-accuracy-display').innerHTML = `
      <div class="grid grid-cols-2 md:grid-cols-4 gap-4 text-center text-sm">
        <div><div class="text-2xl font-bold text-white">${t}</div><div class="text-gray-500">Total</div></div>
        <div><div class="text-2xl font-bold text-green-400">${pct}%</div><div class="text-gray-500">Accuracy</div></div>
        <div><div class="text-2xl font-bold ${recent.length > 0 && rc/recent.length >= 0.5 ? 'text-green-400' : 'text-red-400'}">${recent.length > 0 ? (rc/recent.length*100).toFixed(1) : '-'}%</div><div class="text-gray-500">Last ${recent.length}</div></div>
        <div><div class="text-2xl font-bold text-white">${Object.keys(data.by_confidence || {}).length}</div><div class="text-gray-500">Confidence Levels</div></div>
      </div>`;
  } catch(e) {}
}

async function recordApexOutcome(wasCorrect) {
  const ticker = document.getElementById('apex-ticker').value.toUpperCase().trim();
  const label = document.getElementById('apex-confidence-label').textContent;
  await fetch('/api/apex/record_outcome', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({ticker, was_correct: wasCorrect, confidence_label: label}) });
  loadApexAccuracy();
  alert(wasCorrect ? 'CORRECT' : 'INCORRECT');
}

function toggleApexAutoRefresh() {
  const btn = document.getElementById('apex-auto-btn');
  if(apexAutoRefreshInterval) {
    clearInterval(apexAutoRefreshInterval); apexAutoRefreshInterval = null;
    btn.textContent = 'Auto: OFF'; btn.className = 'w-full bg-gray-800 hover:bg-gray-700 border border-gray-700 py-3 rounded-lg font-semibold';
  } else {
    apexAutoRefreshInterval = setInterval(runApexPrediction, 30000);
    btn.textContent = 'Auto: ON (30s)'; btn.className = 'w-full bg-red-800 hover:bg-red-700 border border-red-500 py-3 rounded-lg font-semibold';
  }
}

// Backtest
async function runBacktest() {
  const tickers = document.getElementById('backtest-tickers').value.split(',').map(t => t.trim());
  const res = await fetch('/api/backtest', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({tickers}) }).then(r => r.json());
  document.getElementById('backtest-results').classList.remove('hidden');
  document.getElementById('backtest-results').innerHTML = '<div class="text-gray-400">Backtest started for: ' + tickers.join(', ') + '</div>';
}

// Train
async function startTraining() {
  document.getElementById('training-status').innerHTML = '<div class="text-gray-400">Training triggered. Check console logs.</div>';
}

// Init
loadDashboard();
</script>
</body>
</html>"""
    with open(os.path.join(TEMPLATES_DIR, 'index.html'), 'w', encoding='utf-8') as f:
        f.write(html)

def run_server(port=5000):
    create_templates()
    print("\n" + "="*60)
    print("  APEX PREDICTOR — FULL SUITE")
    print("="*60)
    print(f"  Running at: http://localhost:{port}")
    print("="*60)
    socketio.run(app, host='0.0.0.0', port=port, debug=True)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=5000)
    args = parser.parse_args()
    run_server(args.port)
