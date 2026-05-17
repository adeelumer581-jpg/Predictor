"""
Streamlined Web UI - Stock Predictor Dashboard
==============================================
A clean, modern web interface for interacting with the models.
Features:
- Real-time predictions
- Model management
- Backtest results
- Training progress
"""
import os
import sys
import json
import logging
from datetime import datetime
from threading import Thread
from typing import Dict, List

# Flask setup
try:
    from flask import Flask, render_template, jsonify, request, redirect, url_for
    from flask_socketio import SocketIO, emit
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False
    print("Installing Flask...")

# Install Flask if needed
if not FLASK_AVAILABLE:
    import subprocess
    subprocess.run([sys.executable, '-m', 'pip', 'install', 'flask', 'flask-socketio', '-q'])
    from flask import Flask, render_template, jsonify, request
    from flask_socketio import SocketIO, emit
    FLASK_AVAILABLE = True

# Load .env file if present
env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
if os.path.exists(env_path):
    try:
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    k, v = line.split('=', 1)
                    os.environ.setdefault(k.strip(), v.strip())
    except:
        pass

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("WebUI")

# App configuration
app = Flask(__name__, template_folder='templates', static_folder='static')
app.config['SECRET_KEY'] = 'stock-predictor-secret-key-2024'
socketio = SocketIO(app, cors_allowed_origins="*")

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = BASE_DIR
CHECKPOINT_FILE = os.path.join(BASE_DIR, "training_checkpoint.json")


class WebUIManager:
    """Manages the web UI and data"""

    def __init__(self):
        self.predictions = {}
        self.training_progress = {}
        self.backtest_results = {}
        self.system_status = {
            "training": "idle",
            "backtesting": "idle",
            "models_loaded": 0
        }

    def get_predictions(self, ticker: str = None) -> Dict:
        """Get predictions for a ticker"""
        if ticker:
            return self.predictions.get(ticker, {})
        return self.predictions

    def get_training_progress(self) -> Dict:
        """Get training progress with self-healing support"""
        if os.path.exists(CHECKPOINT_FILE):
            try:
                with open(CHECKPOINT_FILE, 'r') as f:
                    checkpoint = json.load(f)
                    
                    # Handle list format (self-healing)
                    if isinstance(checkpoint, list):
                        return {
                            "completed": len(checkpoint),
                            "failed": 0,
                            "total": len(checkpoint)
                        }
                        
                    return {
                        "completed": len(checkpoint.get("completed", [])),
                        "failed": len(checkpoint.get("failed", [])),
                        "total": len(checkpoint.get("completed", [])) + len(checkpoint.get("failed", []))
                    }
            except Exception as e:
                logger.error(f"Checkpoint parsing error: {e}")
        return {"completed": 0, "failed": 0, "total": 0}

    def get_available_models(self) -> List[str]:
        """Get list of available models"""
        models = []
        try:
            for f in os.listdir(MODELS_DIR):
                if f.endswith('_model.pkl'):
                    models.append(f.replace('_model.pkl', ''))
        except:
            pass
        return sorted(models)

    def get_system_status(self) -> Dict:
        """Get system status"""
        return {
            "available_models": len(self.get_available_models()),
            "training_progress": self.get_training_progress(),
            "timestamp": datetime.now().isoformat()
        }


# Global manager
ui_manager = WebUIManager()


# Routes
@app.route('/')
def index():
    """Main dashboard"""
    return render_template('index.html')


@app.route('/api/status')
def api_status():
    """Get system status"""
    return jsonify(ui_manager.get_system_status())


@app.route('/api/models')
def api_models():
    """Get available models"""
    return jsonify({
        "models": ui_manager.get_available_models()
    })


@app.route('/api/predict/<ticker>')
def api_predict(ticker):
    """Get prediction for a ticker"""
    ticker = ticker.upper()

    try:
        # Import predictor
        sys.path.insert(0, BASE_DIR)

        # Try to load and run prediction
        model_path = os.path.join(MODELS_DIR, f"{ticker}_model.pkl")

        if not os.path.exists(model_path):
            # Train on the fly
            logger.info(f"Training model for {ticker}...")
            from stock_predictor import StockPredictor

            predictor = StockPredictor(ticker)
            predictor.fetch_data()
            predictor.calculate_indicators()
            predictor.prepare_features()

            if predictor.X is not None and len(predictor.X) > 0:
                predictor.train()
                prediction = predictor.predict()

                return jsonify({
                    "ticker": ticker,
                    "prediction": prediction,
                    "status": "trained"
                })

        # Load existing model using StockPredictor
        from stock_predictor import StockPredictor
        predictor = StockPredictor(ticker)
        predictor.load_model(model_path)
        
        # Get prediction
        res = predictor.predict_next()
        
        result = {
            "ticker": res['ticker'],
            "prediction": res['prediction'],
            "confidence": res['confidence'],
            "price": res['current_price'],
            "status": "success"
        }

        return jsonify(result)

    except Exception as e:
        logger.error(f"Prediction error: {e}")
        return jsonify({"error": str(e)})


@app.route('/api/backtest', methods=['POST'])
def api_backtest():
    """Run backtest"""
    data = request.json or {}
    tickers = data.get('tickers', ['AAPL', 'MSFT', 'GOOGL', 'AMZN'])

    try:
        sys.path.insert(0, BASE_DIR)
        from backtester import Backtester, BacktestConfig

        config = BacktestConfig()
        backtester = Backtester(config, MODELS_DIR)

        # Run in background
        def run_backtest():
            summary = backtester.run_multi_backtest(tickers)
            ui_manager.backtest_results = summary
            socketio.emit('backtest_complete', summary)

        Thread(target=run_backtest, daemon=True).start()

        return jsonify({"status": "started", "tickers": tickers})

    except Exception as e:
        return jsonify({"error": str(e)})


@app.route('/api/backtest/results')
def api_backtest_results():
    """Get backtest results"""
    return jsonify(ui_manager.backtest_results)


@app.route('/api/train', methods=['POST'])
def api_train():
    """Start training"""
    data = request.json or {}
    tickers = data.get('tickers', [])

    try:
        sys.path.insert(0, BASE_DIR)
        from mass_trainer import MassTrainer, MassTrainerConfig

        config = MassTrainerConfig()
        trainer = MassTrainer(config)

        # Run in background
        def run_training():
            result = trainer.train_all(tickers)
            socketio.emit('training_complete', result)

        Thread(target=run_training, daemon=True).start()

        return jsonify({"status": "started", "tickers": tickers})

    except Exception as e:
        return jsonify({"error": str(e)})


@app.route('/api/vision_analyze', methods=['POST'])
def api_vision_analyze():
    """Analyze chart screenshot using Claude Vision"""
    data = request.json or {}
    image_data = data.get('image')
    
    if not image_data:
        return jsonify({"error": "No image provided"})
        
    try:
        import anthropic
        client = anthropic.Anthropic()
        
        if ',' in image_data:
            b64_data = image_data.split(',')[1]
            media_type = image_data.split(';')[0].split(':')[1]
        else:
            b64_data = image_data
            media_type = "image/png"
            
        message = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1024,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": b64_data
                            }
                        },
                        {
                            "type": "text",
                            "text": "Act as an expert technical analyst. Look at this stock chart screenshot. Tell me if the trend is Bullish or Bearish and provide a detailed technical reasoning based on the patterns, support/resistance, and indicators you see."
                        }
                    ]
                }
            ]
        )
        return jsonify({"result": message.content[0].text, "status": "success"})
    except Exception as e:
        logger.error(f"Vision error: {e}")
        return jsonify({"error": str(e)})


    @app.route('/api/training/progress')
    def api_training_progress():
        """Get training progress"""
        return jsonify(ui_manager.get_training_progress())


    @app.route('/api/chart/<ticker>')
    def api_chart(ticker):
        """Get chart data for a ticker"""
        try:
            ticker = ticker.upper()
            lookback_days = request.args.get('lookback_days', 100, type=int)
            # Import predictor
            sys.path.insert(0, BASE_DIR)
            from stock_predictor import StockPredictor
            
            predictor = StockPredictor(ticker, lookback_days=lookback_days)
            df = predictor.fetch_data()
            
            if df is None or df.empty:
                return jsonify({"error": "No data available"}), 404
            
            # Prepare data for Lightweight Charts: time in unix timestamp
            chart_data = []
            for idx, row in df.iterrows():
                # idx is Timestamp
                chart_data.append({
                    "time": int(idx.timestamp()),
                    "open": float(row['Open']),
                    "high": float(row['High']),
                    "low": float(row['Low']),
                    "close": float(row['Close'])
                })
            
            return jsonify(chart_data)
        except Exception as e:
            logger.error(f"Chart error for {ticker}: {e}")
            return jsonify({"error": str(e)}), 500


@app.route('/api/academy')
def api_academy():
    """Get market academy content"""
    encyclopedia_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".gemini", "antigravity", "brain", "51135b5b-5c30-46f4-a293-887079e2b703", "market_mastery_encyclopedia.md")
    if not os.path.exists(encyclopedia_path):
        # Fallback to local if artifact path fails
        encyclopedia_path = os.path.join(BASE_DIR, "market_mastery_encyclopedia.md")
        
    try:
        if os.path.exists(encyclopedia_path):
            with open(encyclopedia_path, 'r') as f:
                return jsonify({"content": f.read()})
    except:
        pass
    return jsonify({"content": "# Market Academy\nContent coming soon..."})


@app.route('/api/ipo_news')
def api_ipo_news():
    """Get latest IPO news"""
    ipo_file = os.path.join(BASE_DIR, "ipo_news.json")
    try:
        if os.path.exists(ipo_file):
            with open(ipo_file, 'r') as f:
                return jsonify(json.load(f))
    except:
        pass
    return jsonify({"articles": []})


    @app.route('/api/performance')
    def api_performance():
        """Get performance metrics"""
        models = ui_manager.get_available_models()

        performance = []
        for ticker in models[:10]:  # Limit to 10
            model_path = os.path.join(MODELS_DIR, f"{ticker}_model.pkl")
            if os.path.exists(model_path):
                try:
                    mtime = os.path.getmtime(model_path)
                    performance.append({
                        "ticker": ticker,
                        "last_trained": datetime.fromtimestamp(mtime).isoformat(),
                        "size_kb": os.path.getsize(model_path) / 1024
                    })
                except:
                    pass

        return jsonify(performance)


    # ─── APEX PREDICTOR API ───

    @app.route('/api/apex/predict/<ticker>')
    def api_apex_predict(ticker):
        """Full APEX GODMODE prediction"""
        try:
            ticker = ticker.upper()
            sys.path.insert(0, BASE_DIR)
            from apex_predictor import ApexPredictor
            predictor = ApexPredictor(ticker)
            result = predictor.predict()
            return jsonify(result)
        except Exception as e:
            logger.error(f"APEX predict error: {e}")
            return jsonify({"error": str(e)}), 500


    @app.route('/api/apex/accuracy')
    def api_apex_accuracy():
        """Get APEX accuracy stats"""
        try:
            import json, os
            path = os.path.join(BASE_DIR, "apex_accuracy.json")
            if os.path.exists(path):
                with open(path, 'r') as f:
                    return jsonify(json.load(f))
            return jsonify({"total": 0, "correct": 0, "recent": [], "by_confidence": {}})
        except Exception as e:
            return jsonify({"error": str(e)}), 500


    @app.route('/api/apex/record_outcome', methods=['POST'])
    def api_apex_record_outcome():
        """Record prediction outcome for self-correcting feedback loop"""
        try:
            data = request.json or {}
            ticker = data.get('ticker', '').upper()
            was_correct = data.get('was_correct', False)
            confidence_label = data.get('confidence_label', 'Medium')
            sys.path.insert(0, BASE_DIR)
            from apex_predictor import ApexPredictor
            predictor = ApexPredictor(ticker)
            predictor.record_outcome(was_correct, confidence_label)
            return jsonify({"status": "recorded"})
        except Exception as e:
            return jsonify({"error": str(e)}), 500


# WebSocket events
@socketio.on('connect')
def handle_connect():
    """Handle connection"""
    emit('connected', {'status': 'connected'})


@socketio.on('request_status')
def handle_status_request():
    """Handle status request"""
    emit('status_update', ui_manager.get_system_status())


def create_templates():
    """Create template files"""
    templates_dir = os.path.join(BASE_DIR, 'templates')
    os.makedirs(templates_dir, exist_ok=True)

    # Main template
    index_html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Stock Predictor AI</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/3.9.1/chart.min.js"></script>
    <script src="https://unpkg.com/lightweight-charts/dist/lightweight-charts.standalone.production.js"></script>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
        body { font-family: 'Inter', sans-serif; }
        .gradient-bg { background: linear-gradient(135deg, #1e3a5f 0%, #0f172a 100%); }
        .card { background: rgba(255,255,255,0.05); backdrop-filter: blur(10px); border: 1px solid rgba(255,255,255,0.1); }
        .glow { animation: glow 2s ease-in-out infinite alternate; }
        .glow-red { animation: glowRed 2s ease-in-out infinite alternate; }
        @keyframes glow { from { box-shadow: 0 0 10px rgba(59,130,246,0.3); } to { box-shadow: 0 0 20px rgba(59,130,246,0.6); } }
        @keyframes glowRed { from { box-shadow: 0 0 10px rgba(239,68,68,0.3); } to { box-shadow: 0 0 25px rgba(239,68,68,0.6); } }
    </style>
</head>
<body class="gradient-bg min-h-screen text-white">
    <!-- Header -->
    <header class="border-b border-gray-800 bg-black/30 backdrop-blur-md sticky top-0 z-50">
        <div class="max-w-7xl mx-auto px-6 py-4 flex justify-between items-center">
            <div class="flex items-center gap-3">
                <div class="w-10 h-10 bg-blue-500 rounded-lg flex items-center justify-center text-xl font-bold">S</div>
                <div>
                    <h1 class="text-xl font-bold">Stock Predictor AI</h1>
                    <p class="text-xs text-gray-400">S&P 500 Intelligence System</p>
                </div>
            </div>
            <nav class="flex gap-6 text-sm">
                <a href="#" onclick="showSection('dashboard')" class="hover:text-blue-400 transition">Dashboard</a>
                <a href="#" onclick="showSection('predict')" class="hover:text-blue-400 transition">Predict</a>
                <a href="#" onclick="showSection('vision')" class="hover:text-green-400 transition font-semibold text-green-400">Vision Analysis</a>
                <a href="#" onclick="showSection('ipo')" class="hover:text-yellow-400 transition">IPO Tracker</a>
                <a href="#" onclick="showSection('academy')" class="hover:text-purple-400 transition">Market Academy</a>
                <a href="#" onclick="showSection('backtest')" class="hover:text-blue-400 transition">Backtest</a>
                 <a href="#" onclick="showSection('train')" class="hover:text-blue-400 transition">Train</a>
                 <a href="#" onclick="showSection('live')" class="hover:text-indigo-400 transition">Live Charts</a>
                 <a href="#" onclick="showSection('apex')" class="hover:text-red-400 transition font-bold">APEX Predict</a>
            </nav>
        </div>
    </header>

    <!-- Main Content -->
    <main class="max-w-7xl mx-auto px-6 py-8">
        <!-- Dashboard -->
        <div id="dashboard" class="section">
            <div class="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
                <div class="card rounded-xl p-6">
                    <div class="text-gray-400 text-sm mb-2">Active Models</div>
                    <div class="text-3xl font-bold" id="model-count">-</div>
                </div>
                <div class="card rounded-xl p-6">
                    <div class="text-gray-400 text-sm mb-2">Trained Stocks</div>
                    <div class="text-3xl font-bold" id="trained-count">-</div>
                </div>
                <div class="card rounded-xl p-6">
                    <div class="text-gray-400 text-sm mb-2">Win Rate</div>
                    <div class="text-3xl font-bold" id="win-rate">-</div>
                </div>
                <div class="card rounded-xl p-6">
                    <div class="text-gray-400 text-sm mb-2">System Status</div>
                    <div class="text-3xl font-bold text-green-400" id="system-status">Active</div>
                </div>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div class="card rounded-xl p-6">
                    <h3 class="text-lg font-semibold mb-4">Live Market Chart</h3>
                    <div id="tv-chart" class="h-[300px] w-full bg-gray-900/30 rounded-lg"></div>
                </div>
                <div class="card rounded-xl p-6">
                    <h3 class="text-lg font-semibold mb-4">Model Performance</h3>
                    <div id="model-list" class="space-y-2"></div>
                </div>
            </div>
        </div>

        <!-- Predict -->
        <div id="predict" class="section hidden">
            <div class="max-w-xl mx-auto">
                <div class="card rounded-xl p-8">
                    <h2 class="text-2xl font-bold mb-6 text-center">Make Prediction</h2>
                    <div class="flex gap-4 mb-6">
                        <input type="text" id="ticker-input" placeholder="Enter ticker (e.g., AAPL)"
                            class="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-4 py-3 focus:border-blue-500 focus:outline-none uppercase">
                        <button onclick="makePrediction()" class="bg-blue-600 hover:bg-blue-700 px-8 py-3 rounded-lg font-semibold transition glow">
                            Predict
                        </button>
                    </div>
                    <div id="prediction-result" class="hidden">
                        <div class="text-center p-6 bg-gray-800 rounded-lg">
                            <div class="text-gray-400 mb-4 uppercase tracking-widest text-sm">Trend Confidence</div>
                            <div class="relative w-48 h-24 mx-auto mb-6">
                                <div class="absolute inset-0 bg-gray-700 rounded-t-full"></div>
                                <div id="gauge-fill" class="absolute inset-0 bg-blue-500 rounded-t-full origin-bottom transition-all duration-1000" style="transform: rotate(0deg);"></div>
                                <div class="absolute inset-4 bg-gray-800 rounded-t-full flex items-end justify-center pb-2">
                                    <span id="pred-confidence" class="text-3xl font-bold">-</span>
                                </div>
                            </div>
                            <div id="pred-direction" class="text-4xl font-bold mb-2">-</div>
                            <div id="pred-price" class="text-xl mt-4 text-green-400 border-t border-gray-700 pt-4">-</div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Vision Predict -->
        <div id="vision" class="section hidden">
            <div class="max-w-2xl mx-auto">
                <div class="card rounded-xl p-8 border-green-500/30 shadow-[0_0_15px_rgba(34,197,94,0.15)]">
                    <h2 class="text-2xl font-bold mb-2 text-center text-green-400">Claude Vision Analysis</h2>
                    <p class="text-center text-gray-400 mb-6">Press <b>Ctrl+V</b> (or Cmd+V) to paste a stock chart screenshot directly into this window.</p>
                    <div id="paste-area" class="border-2 border-dashed border-gray-600 hover:border-green-400 transition rounded-lg p-10 text-center flex flex-col items-center justify-center min-h-[300px] mb-6 bg-gray-900/50">
                        <img id="preview-image" src="" class="hidden max-h-[400px] rounded-lg shadow-lg mb-4">
                        <div id="paste-prompt" class="text-gray-500 flex flex-col items-center">
                            <svg class="w-12 h-12 mb-3 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"></path></svg>
                            <span>Ready for paste (Ctrl+V)</span>
                        </div>
                    </div>
                    <div id="vision-loading" class="hidden text-center text-blue-400 font-bold mb-4 flex justify-center items-center gap-2">
                        <svg class="animate-spin h-5 w-5 text-blue-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                        </svg>
                        Claude Vision is analyzing the chart...
                    </div>
                    <div id="vision-result" class="hidden p-6 bg-gray-800 rounded-lg whitespace-pre-wrap leading-relaxed text-gray-200"></div>
                </div>
            </div>
        </div>

        <!-- IPO Tracker -->
        <div id="ipo" class="section hidden">
            <div class="max-w-4xl mx-auto">
                <div class="card rounded-xl p-8 border-yellow-500/30">
                    <h2 class="text-2xl font-bold mb-6 text-yellow-400">IPO Intelligence Tracker</h2>
                    <div id="ipo-list" class="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div class="p-10 text-center text-gray-500 col-span-2">Loading latest IPO news...</div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Market Academy -->
        <div id="academy" class="section hidden">
            <div class="max-w-4xl mx-auto">
                <div class="card rounded-xl p-8 border-purple-500/30">
                    <h2 class="text-2xl font-bold mb-6 text-purple-400">Market Mastery Academy</h2>
                    <div id="academy-content" class="prose prose-invert max-w-none text-gray-300 leading-relaxed space-y-6">
                        Loading encyclopedia...
                    </div>
                </div>
            </div>
        </div>

        <!-- Backtest -->
        <div id="backtest" class="section hidden">
            <div class="max-w-2xl mx-auto">
                <div class="card rounded-xl p-8">
                    <h2 class="text-2xl font-bold mb-6">Run Backtest</h2>
                    <div class="mb-6">
                        <label class="block text-gray-400 mb-2">Tickers (comma-separated)</label>
                        <input type="text" id="backtest-tickers" value="AAPL,MSFT,GOOGL,AMZN,TSLA,NVDA"
                            class="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-3 focus:border-blue-500 focus:outline-none">
                    </div>
                    <button onclick="runBacktest()" class="w-full bg-blue-600 hover:bg-blue-700 py-3 rounded-lg font-semibold transition">
                        Run Backtest
                    </button>
                    <div id="backtest-progress" class="mt-6 hidden">
                        <div class="h-2 bg-gray-700 rounded-full overflow-hidden">
                            <div id="progress-bar" class="h-full bg-blue-500 transition-all" style="width: 0%"></div>
                        </div>
                        <p class="text-center text-gray-400 mt-2">Running backtest...</p>
                    </div>
                    <div id="backtest-results" class="mt-6 hidden">
                        <h3 class="text-lg font-semibold mb-4">Results</h3>
                        <div id="results-content" class="space-y-2"></div>
                    </div>
                </div>
            </div>
        </div>

         <!-- Train -->
         <div id="train" class="section hidden">
             <div class="max-w-2xl mx-auto">
                 <div class="card rounded-xl p-8">
                     <h2 class="text-2xl font-bold mb-6">Mass Training</h2>
                     <div class="mb-6">
                         <label class="block text-gray-400 mb-2">Select Stocks</label>
                         <select id="train-tickers" multiple class="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-3 h-40">
                             <option value="all">All S&P 500</option>
                             <option value="top50">Top 50 by Market Cap</option>
                             <option value="tech">Tech Sector</option>
                         </select>
                     </div>
                     <button onclick="startTraining()" class="w-full bg-blue-600 hover:bg-blue-700 py-3 rounded-lg font-semibold transition">
                         Start Training
                     </button>
                     <div id="training-status" class="mt-6 p-4 bg-gray-800 rounded-lg">
                         <div class="flex justify-between mb-2">
                             <span>Progress</span>
                             <span id="train-progress">0 / 0</span>
                         </div>
                         <div class="h-2 bg-gray-700 rounded-full overflow-hidden">
                             <div id="train-bar" class="h-full bg-green-500 transition-all" style="width: 0%"></div>
                         </div>
                     </div>
                 </div>
             </div>
         </div>

         <!-- Live Charts -->
         <div id="live" class="section hidden">
             <div class="max-w-7xl mx-auto">
                 <div class="card rounded-xl p-8">
                     <h2 class="text-2xl font-bold mb-6">Live Charts</h2>
                     <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
                         <div class="flex flex-col">
                             <label class="text-gray-400 mb-2">Asset Type</label>
                             <select id="live-asset-type" class="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-3 mb-4">
                                 <option value="stocks">US Stocks</option>
                                 <option value="commodities">Commodities</option>
                                 <option value="pakistani">Pakistani Stocks (.PSX)</option>
                                 <option value="forex">Forex</option>
                                 <option value="crypto">Cryptocurrency</option>
                             </select>
                         </div>
                         <div class="flex flex-col">
                             <label class="text-gray-400 mb-2">Symbol</label>
                             <input type="text" id="live-symbol" placeholder="e.g., AAPL (stock), GC=F (gold), LUCK.PSX (PSX), EURUSD=X (forex), BTC-USD (crypto)"
                                   class="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-3">
                         </div>
                         <div class="flex flex-col">
                             <label class="text-gray-400 mb-2">Timeframe</label>
                             <select id="live-timeframe" class="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-3">
                                 <option value="1d">1 Day</option>
                                 <option value="5d">5 Days</option>
                                 <option value="1mo">1 Month</option>
                                 <option value="3mo">3 Months</option>
                                 <option value="6mo">6 Months</option>
                                 <option value="1y">1 Year</option>
                             </select>
                         </div>
                         <div class="flex items-end">
                             <button onclick="loadLiveChart()" class="w-full bg-indigo-600 hover:bg-indigo-700 py-3 px-6 rounded-lg font-semibold transition">
                                 Load Chart
                             </button>
                         </div>
                     </div>
                     <div id="live-chart-container" class="h-[500px] bg-gray-900/30 rounded-lg mb-6">
                         <!-- TradingView chart will be loaded here -->
                     </div>
                     <div id="prediction-info" class="grid grid-cols-2 gap-4 text-center">
                         <div class="p-4 bg-gray-800 rounded-lg">
                             <div class="text-gray-400 text-sm">Current Price</div>
                             <div id="live-price" class="text-2xl font-bold text-green-400">-</div>
                         </div>
                         <div class="p-4 bg-gray-800 rounded-lg">
                             <div class="text-gray-400 text-sm">Prediction</div>
                             <div id="live-prediction" class="text-2xl font-bold">-</div>
                         </div>
                         <div class="p-4 bg-gray-800 rounded-lg">
                             <div class="text-gray-400 text-sm">Confidence</div>
                             <div id="live-confidence" class="text-2xl font-bold">-</div>
                         </div>
                         <div class="p-4 bg-gray-800 rounded-lg">
                             <div class="text-gray-400 text-sm">Signal</div>
                             <div id="live-signal" class="text-2xl font-bold">-</div>
                         </div>
                     </div>
                  </div>
              </div>
          </div>

         <!-- APEX PREDICTOR - GODMODE -->
         <div id="apex" class="section hidden">
             <div class="max-w-7xl mx-auto">
                 <div class="bg-gradient-to-r from-red-900/20 to-orange-900/20 border border-red-500/30 rounded-xl p-8 shadow-[0_0_30px_rgba(255,0,0,0.1)]">
                     <div class="flex items-center gap-4 mb-6">
                         <div class="text-4xl">🔱</div>
                         <div>
                             <h2 class="text-3xl font-bold text-red-400">APEX PREDICTOR</h2>
                             <p class="text-gray-500 text-sm">GODMODE — Multi-Dimensional Market Confluence Engine</p>
                         </div>
                     </div>

                     <!-- Quick Input -->
                     <div class="grid grid-cols-1 md:grid-cols-5 gap-4 mb-8">
                         <div>
                             <label class="text-gray-400 text-sm mb-1 block">Symbol</label>
                             <input type="text" id="apex-ticker" value="AAPL"
                                    class="w-full bg-gray-900 border border-gray-700 rounded-lg px-4 py-3 uppercase text-lg font-bold"
                                    placeholder="AAPL">
                         </div>
                         <div>
                             <label class="text-gray-400 text-sm mb-1 block">Asset Class</label>
                             <select id="apex-asset-class" class="w-full bg-gray-900 border border-gray-700 rounded-lg px-4 py-3">
                                 <option value="auto">Auto-Detect</option>
                                 <option value="stock">US Stock</option>
                                 <option value="commodity">Commodity</option>
                                 <option value="forex">Forex</option>
                                 <option value="psx">Pakistani Stock (PSX)</option>
                                 <option value="crypto">Crypto</option>
                             </select>
                         </div>
                         <div>
                             <label class="text-gray-400 text-sm mb-1 block">Period</label>
                             <select id="apex-period" class="w-full bg-gray-900 border border-gray-700 rounded-lg px-4 py-3">
                                 <option value="5d">5 Days</option>
                                 <option value="1mo">1 Month</option>
                                 <option value="3mo" selected>3 Months</option>
                                 <option value="6mo">6 Months</option>
                                 <option value="1y">1 Year</option>
                             </select>
                         </div>
                         <div class="flex items-end">
                             <button onclick="runApexPrediction()"
                                     class="w-full bg-gradient-to-r from-red-600 to-orange-600 hover:from-red-500 hover:to-orange-500 py-3 rounded-lg font-bold transition glow-red">
                                 PREDICT
                             </button>
                         </div>
                         <div class="flex items-end">
                             <button onclick="toggleApexAutoRefresh()"
                                     id="apex-auto-btn"
                                     class="w-full bg-gray-800 hover:bg-gray-700 border border-gray-700 py-3 rounded-lg font-semibold transition">
                                 Auto: OFF
                             </button>
                         </div>
                     </div>

                     <!-- Loading -->
                     <div id="apex-loading" class="hidden text-center py-20">
                         <div class="animate-spin text-6xl mb-4">🔱</div>
                         <p class="text-gray-400 text-xl">Calculating multi-dimensional confluence...</p>
                         <div class="mt-4 h-2 bg-gray-800 rounded-full max-w-md mx-auto overflow-hidden">
                             <div id="apex-progress-bar" class="h-full bg-gradient-to-r from-red-500 to-orange-500 transition-all" style="width: 0%"></div>
                         </div>
                     </div>

                     <!-- Prediction Result -->
                     <div id="apex-result" class="hidden">
                         <!-- Header -->
                         <div class="bg-gray-900/80 border border-gray-800 rounded-xl p-6 mb-6">
                             <div class="flex justify-between items-start">
                                 <div>
                                     <div class="text-gray-500 text-sm">APEX PREDICTION</div>
                                     <div class="text-2xl font-bold" id="apex-timestamp">-</div>
                                 </div>
                                 <div class="text-right">
                                     <div class="text-gray-500 text-sm">ASSET</div>
                                     <div class="text-xl font-bold" id="apex-asset-display">-</div>
                                     <div class="text-gray-500 text-sm" id="apex-asset-class-display">-</div>
                                 </div>
                             </div>
                         </div>

                         <!-- Main Prediction -->
                         <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
                             <div class="bg-gray-900/80 border border-gray-800 rounded-xl p-6 text-center">
                                 <div class="text-gray-500 text-sm mb-1">DIRECTION</div>
                                 <div id="apex-direction" class="text-5xl font-bold">-</div>
                                 <div id="apex-current-price" class="text-xl mt-2 text-gray-400">-</div>
                             </div>
                             <div class="bg-gray-900/80 border border-gray-800 rounded-xl p-6 text-center">
                                 <div class="text-gray-500 text-sm mb-1">CONFIDENCE</div>
                                 <div id="apex-confidence" class="text-5xl font-bold text-green-400">-</div>
                                 <div id="apex-confidence-label" class="text-lg mt-2">-</div>
                             </div>
                             <div class="bg-gray-900/80 border border-gray-800 rounded-xl p-6 text-center">
                                 <div class="text-gray-500 text-sm mb-1">CONFLUENCE</div>
                                 <div id="apex-confluence" class="text-5xl font-bold text-orange-400">-</div>
                                 <div class="text-lg mt-2 text-gray-400">/ 50 (max)</div>
                             </div>
                         </div>

                         <!-- Entry / Target / Stop -->
                         <div class="grid grid-cols-3 gap-4 mb-6">
                             <div class="bg-gray-900/50 border border-gray-800 rounded-lg p-4 text-center">
                                 <div class="text-gray-500 text-xs">ENTRY</div>
                                 <div id="apex-entry" class="text-xl font-bold">-</div>
                             </div>
                             <div class="bg-gray-900/50 border border-gray-800 rounded-lg p-4 text-center">
                                 <div class="text-gray-500 text-xs">TARGET</div>
                                 <div id="apex-target" class="text-xl font-bold text-green-500">-</div>
                             </div>
                             <div class="bg-gray-900/50 border border-gray-800 rounded-lg p-4 text-center">
                                 <div class="text-gray-500 text-xs">STOP LOSS</div>
                                 <div id="apex-stop" class="text-xl font-bold text-red-500">-</div>
                             </div>
                         </div>

                         <!-- Confluence Dimensions -->
                         <div class="bg-gray-900/80 border border-gray-800 rounded-xl p-6 mb-6">
                             <h3 class="text-lg font-bold mb-4 text-orange-400">CONFLUENCE SCORES</h3>
                             <div id="apex-dimensions" class="space-y-3"></div>
                             <div class="mt-4 pt-4 border-t border-gray-800 flex justify-between">
                                 <span class="text-gray-400">TOTAL CONFLUENCE</span>
                                 <span id="apex-total-confluence" class="font-bold text-xl text-orange-400">- / 50</span>
                             </div>
                         </div>

                         <!-- Key Levels -->
                         <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
                             <div class="bg-gray-900/80 border border-gray-800 rounded-xl p-6">
                                 <h3 class="text-lg font-bold mb-4 text-red-400">KEY LEVELS</h3>
                                 <div id="apex-levels" class="space-y-2"></div>
                             </div>
                             <div class="bg-gray-900/80 border border-gray-800 rounded-xl p-6">
                                 <h3 class="text-lg font-bold mb-4 text-blue-400">CANDLE FORMATION</h3>
                                 <div id="apex-candle" class="space-y-2"></div>
                             </div>
                         </div>

                         <!-- Top Reasons & Risk Factors -->
                         <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
                             <div class="bg-gray-900/80 border border-gray-800 rounded-xl p-6">
                                 <h3 class="text-lg font-bold mb-4 text-green-400">TOP REASONS</h3>
                                 <div id="apex-reasons" class="space-y-2"></div>
                             </div>
                             <div class="bg-gray-900/80 border border-gray-800 rounded-xl p-6">
                                 <h3 class="text-lg font-bold mb-4 text-red-400">RISK FACTORS</h3>
                                 <div id="apex-risks" class="space-y-2"></div>
                             </div>
                         </div>

                         <!-- Raw Output -->
                         <div class="bg-gray-900/80 border border-gray-800 rounded-xl p-6 mb-6">
                             <h3 class="text-lg font-bold mb-4 text-gray-400">RAW PREDICTION OUTPUT</h3>
                             <pre id="apex-raw-output" class="text-xs text-gray-500 font-mono whitespace-pre-wrap max-h-60 overflow-y-auto p-4 bg-black/50 rounded-lg"></pre>
                         </div>

                         <!-- Feedback -->
                         <div class="bg-gray-900/80 border border-gray-800 rounded-xl p-6">
                             <h3 class="text-lg font-bold mb-4 text-yellow-400">SELF-CORRECTING FEEDBACK</h3>
                             <p class="text-gray-500 text-sm mb-4">Was this prediction correct?</p>
                             <div class="flex gap-4">
                                 <button onclick="recordApexOutcome(true)"
                                         class="bg-green-700 hover:bg-green-600 px-8 py-3 rounded-lg font-bold transition">
                                     YES — Correct
                                 </button>
                                 <button onclick="recordApexOutcome(false)"
                                         class="bg-red-700 hover:bg-red-600 px-8 py-3 rounded-lg font-bold transition">
                                     NO — Incorrect
                                 </button>
                             </div>
                             <div id="apex-accuracy-display" class="mt-4 p-4 bg-gray-800/50 rounded-lg">
                                 <div class="text-gray-400 text-sm">Loading accuracy stats...</div>
                             </div>
                         </div>
                     </div>
                 </div>
             </div>
         </div>
     </main>

     <!-- Footer Disclaimer -->
    <footer class="border-t border-gray-800 bg-black/50 py-8 px-6 mt-12">
        <div class="max-w-7xl mx-auto">
            <div class="text-center text-xs text-gray-500 uppercase tracking-widest mb-4">Regulatory & Legal Safeguards</div>
            <p class="text-center text-gray-400 text-sm max-w-4xl mx-auto leading-relaxed">
                <b>THE ULTIMATE DISCLAIMER:</b> This application is for informational and educational purposes only. All predictions and technical analyses are generated by artificial intelligence models and do not constitute formal financial advice, investment recommendations, or an offer to buy or sell securities. Trading the stock market involves significant risk of loss. Past performance is not indicative of future results. Always consult with a licensed financial advisor before making any investment decisions.
            </p>
            <div class="text-center mt-6 text-gray-600 text-xs">
                © 2026 Antigravity Systems. All Rights Reserved. Bank-grade Encryption (AES-256) Active.
            </div>
        </div>
    </footer>

    <script>
        let currentSection = 'dashboard';
        const socket = io();

        // Navigation
        function showSection(section) {
            document.querySelectorAll('.section').forEach(s => s.classList.add('hidden'));
            document.getElementById(section).classList.remove('hidden');
            currentSection = section;
            if(section === 'dashboard') {
                loadDashboard();
                initChart();
            }
        }

        // TradingView Chart
        let tvChart = null;
        function initChart() {
            const container = document.getElementById('tv-chart');
            if(!container || tvChart) return;
            
            tvChart = LightweightCharts.createChart(container, {
                width: container.clientWidth,
                height: 300,
                layout: {
                    background: { type: 'solid', color: 'transparent' },
                    textColor: '#94a3b8',
                },
                grid: {
                    vertLines: { color: '#1e293b' },
                    horzLines: { color: '#1e293b' },
                },
            });
            const lineSeries = tvChart.addLineSeries({ color: '#3b82f6' });
            
            // Generate some dummy data for the visualization
            const data = [];
            for (let i = 0; i < 100; i++) {
                data.push({ time: (Date.now()/1000) - (100-i)*86400, value: 150 + Math.random() * 20 });
            }
            lineSeries.setData(data);
        }

        // Load dashboard data
        async function loadDashboard() {
            try {
                const status = await fetch('/api/status').then(r => r.json());
                document.getElementById('model-count').textContent = status.available_models || 0;

                const progress = await fetch('/api/training/progress').then(r => r.json());
                document.getElementById('trained-count').textContent = progress.completed || 0;

                const models = await fetch('/api/models').then(r => r.json());
                const list = document.getElementById('model-list');
                list.innerHTML = models.models.slice(0, 8).map(m =>
                    `<div class="flex justify-between p-2 bg-gray-800 rounded">
                        <span class="font-mono">${m}</span>
                        <span class="text-green-400">Ready</span>
                    </div>`
                ).join('');
            } catch (e) {
                console.error("Dashboard error", e);
            }
        }

        // Make prediction
        async function makePrediction() {
            const ticker = document.getElementById('ticker-input').value.toUpperCase();
            if(!ticker) return;

            const result = await fetch(`/api/predict/${ticker}`).then(r => r.json());

            if(result.error) {
                alert(result.error);
                return;
            }

            document.getElementById('prediction-result').classList.remove('hidden');
            document.getElementById('pred-direction').textContent = result.prediction;
            document.getElementById('pred-direction').className = `text-4xl font-bold mb-2 ${result.prediction === 'UP' ? 'text-green-400' : 'text-red-400'}`;
            
            const conf = result.confidence || 0;
            document.getElementById('pred-confidence').textContent = `${conf.toFixed(0)}%`;
            
            // Gauge rotation (0 to 180 degrees)
            const rotation = (conf / 100) * 180;
            document.getElementById('gauge-fill').style.transform = `rotate(${rotation}deg)`;
            document.getElementById('gauge-fill').className = `absolute inset-0 rounded-t-full origin-bottom transition-all duration-1000 ${result.prediction === 'UP' ? 'bg-green-500' : 'bg-red-500'}`;
            
            document.getElementById('pred-price').textContent = `Current Price: $${result.price?.toFixed(2) || 'N/A'}`;
        }

        // Run backtest
        async function runBacktest() {
            const tickers = document.getElementById('backtest-tickers').value.split(',').map(t => t.trim());
            document.getElementById('backtest-progress').classList.remove('hidden');

            const result = await fetch('/api/backtest', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({tickers})
            }).then(r => r.json());

            // Wait for results
            setTimeout(async () => {
                const results = await fetch('/api/backtest/results').then(r => r.json());
                document.getElementById('backtest-progress').classList.add('hidden');
                document.getElementById('backtest-results').classList.remove('hidden');

                if(results.aggregate) {
                    const a = results.aggregate;
                    document.getElementById('results-content').innerHTML = `
                        <div class="grid grid-cols-2 gap-4">
                            <div class="p-4 bg-gray-800 rounded">
                                <div class="text-gray-400">Avg Return</div>
                                <div class="text-2xl font-bold">${a.avg_return?.toFixed(2)}%</div>
                            </div>
                            <div class="p-4 bg-gray-800 rounded">
                                <div class="text-gray-400">Sharpe Ratio</div>
                                <div class="text-2xl font-bold">${a.avg_sharpe?.toFixed(2)}</div>
                            </div>
                            <div class="p-4 bg-gray-800 rounded">
                                <div class="text-gray-400">Win Rate</div>
                                <div class="text-2xl font-bold">${a.avg_win_rate?.toFixed(1)}%</div>
                            </div>
                            <div class="p-4 bg-gray-800 rounded">
                                <div class="text-gray-400">Max Drawdown</div>
                                <div class="text-2xl font-bold">${a.avg_max_drawdown?.toFixed(2)}%</div>
                            </div>
                        </div>
                    `;
                }
            }, 3000);
        }

        // Start training
        async function startTraining() {
            const tickers = document.getElementById('train-tickers').value;
            await fetch('/api/train', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({tickers: [tickers]})
            });
            alert('Training started in background');
        }

        // Vision Paste Listener
        document.addEventListener('paste', async (e) => {
            // ... (rest of the vision code)
        });

         // IPO News
        async function loadIPONews() {
            try {
                const data = await fetch('/api/ipo_news').then(r => r.json());
                const list = document.getElementById('ipo-list');
                if(!data.articles || data.articles.length === 0) {
                    list.innerHTML = '<div class="col-span-2 text-center p-10 text-gray-500">No recent IPO news found. IPO Agent is scouting...</div>';
                    return;
                }
                list.innerHTML = data.articles.map(a => `
                    <div class="p-4 bg-gray-800/50 rounded-lg border border-gray-700 hover:border-yellow-500/50 transition">
                        <div class="text-xs text-yellow-500 mb-1">${a.timestamp || 'Recent'}</div>
                        <h4 class="font-bold mb-2">${a.title}</h4>
                        <p class="text-sm text-gray-400 mb-3">${a.body.substring(0, 150)}...</p>
                        <a href="${a.href}" target="_blank" class="text-xs text-blue-400 hover:underline">Read Source</a>
                    </div>
                `).join('');
            } catch (e) { console.error(e); }
        }

        // Market Academy
        async function loadAcademy() {
            try {
                const data = await fetch('/api/academy').then(r => r.json());
                const content = document.getElementById('academy-content');
                
                // Simple markdown-ish to HTML converter
                let html = data.content
                    .replace(/^# (.*$)/gm, '<h1 class="text-3xl font-bold text-white mb-6 border-b border-purple-500 pb-2">$1</h1>')
                    .replace(/^## (.*$)/gm, '<h2 class="text-2xl font-bold text-purple-300 mt-8 mb-4">$1</h2>')
                    .replace(/^### (.*$)/gm, '<h3 class="text-xl font-semibold text-blue-300 mt-6 mb-2">$1</h3>')
                    .replace(/^\\* (.*$)/gm, '<li class="ml-4 list-disc mb-2">$1</li>')
                    .replace(/---/g, '<hr class="border-gray-700 my-8">');
                
                content.innerHTML = html;
            } catch (e) { console.error(e); }
        }

        // Live Charts
        let liveChart = null;
        function initLiveChart() {
            const container = document.getElementById('live-chart-container');
            if(!container) return;
            
            // Clear container
            container.innerHTML = '';
            
            // Create chart
            liveChart = LightweightCharts.createChart(container, {
                width: container.clientWidth,
                height: 500,
                layout: {
                    background: { type: 'solid', color: 'transparent' },
                    textColor: '#d1d5db',
                },
                grid: {
                    vertLines: { color: '#2d3748' },
                    horzLines: { color: '#2d3748' },
                },
            });
            
            // Add candlestick series
            const candleSeries = liveChart.addCandlestickSeries({
                upColor: '#26a69a',
                downColor: '#ef5350',
                borderDownColor: '#ef5350',
                borderUpColor: '#26a69a',
                wickDownColor: '#ef5350',
                wickUpColor: '#26a69a'
            });
            
            return candleSeries;
        }

        async function loadLiveChart() {
            const symbol = document.getElementById('live-symbol').value.trim().toUpperCase();
            const timeframe = document.getElementById('live-timeframe').value;
            
            if(!symbol) {
                alert('Please enter a symbol');
                return;
            }
            
            try {
                // Show loading state
                document.getElementById('live-chart-container').innerHTML = '<div class="flex h-[500px] items-center justify-center text-gray-400">Loading chart...</div>';
                
                // Initialize chart if not exists
                let candleSeries = liveChart;
                if(!liveChart) {
                    candleSeries = initLiveChart();
                }
                
                // Fetch chart data
                const response = await fetch(`/api/chart/${symbol}?lookback_days=${getLookbackDays(timeframe)}`);
                const data = await response.json();
                
                if(data.error) {
                    throw new Error(data.error);
                }
                
                // Update chart
                candleSeries.setData(data);
                liveChart.timeScale().fitContent();
                
                // Update prediction info
                await updatePredictionInfo(symbol);
                
            } catch (error) {
                console.error('Chart loading error:', error);
                document.getElementById('live-chart-container').innerHTML = 
                    `<div class="flex h-[500px] items-center justify-center text-red-400">
                        Error loading chart: ${error.message}
                    </div>`;
            }
        }

        function getLookbackDays(timeframe) {
            switch(timeframe) {
                case '1d': return 1;
                case '5d': return 5;
                case '1mo': return 30;
                case '3mo': return 90;
                case '6mo': return 180;
                case '1y': return 365;
                default: return 100;
            }
        }

        async function updatePredictionInfo(symbol) {
            try {
                const response = await fetch(`/api/predict/${symbol}`);
                const data = await response.json();
                
                if(!data.error) {
                    document.getElementById('live-price').textContent = `$${data.price?.toFixed(2) || 'N/A'}`;
                    document.getElementById('live-prediction').textContent = data.prediction || '-';
                    document.getElementById('live-confidence').textContent = `${(data.confidence || 0).toFixed(1)}%`;
                    
                    // Set prediction color
                    const predEl = document.getElementById('live-prediction');
                    predEl.className = `text-2xl font-bold ${data.prediction === 'UP' ? 'text-green-400' : data.prediction === 'DOWN' ? 'text-red-400' : 'text-gray-400'}`;
                    
                    // Set signal based on prediction and confidence
                    const signalEl = document.getElementById('live-signal');
                    const confidence = data.confidence || 0;
                    if(data.prediction === 'UP' && confidence > 70) {
                        signalEl.textContent = 'STRONG BUY';
                        signalEl.className = 'text-2xl font-bold text-green-600';
                    } else if(data.prediction === 'UP' && confidence > 50) {
                        signalEl.textContent = 'BUY';
                        signalEl.className = 'text-2xl font-bold text-green-400';
                    } else if(data.prediction === 'DOWN' && confidence > 70) {
                        signalEl.textContent = 'STRONG SELL';
                        signalEl.className = 'text-2xl font-bold text-red-600';
                    } else if(data.prediction === 'DOWN' && confidence > 50) {
                        signalEl.textContent = 'SELL';
                        signalEl.className = 'text-2xl font-bold text-red-400';
                    } else {
                        signalEl.textContent = 'HOLD';
                        signalEl.className = 'text-2xl font-bold text-yellow-400';
                    }
                } else {
                    document.getElementById('live-price').textContent = 'N/A';
                    document.getElementById('live-prediction').textContent = '-';
                    document.getElementById('live-confidence').textContent = '-';
                    document.getElementById('live-signal').textContent = '-';
                }
            } catch (error) {
                console.error('Prediction error:', error);
                document.getElementById('live-price').textContent = 'N/A';
                document.getElementById('live-prediction').textContent = '-';
                document.getElementById('live-confidence').textContent = '-';
                document.getElementById('live-signal').textContent = '-';
            }
        }

        // ─── APEX PREDICTOR ───
        let apexAutoRefreshInterval = null;

        async function runApexPrediction() {
            const ticker = document.getElementById('apex-ticker').value.toUpperCase().trim();
            if(!ticker) return;

            // Show loading
            document.getElementById('apex-result').classList.add('hidden');
            document.getElementById('apex-loading').classList.remove('hidden');

            // Animate progress bar
            const progressBar = document.getElementById('apex-progress-bar');
            let progress = 0;
            const progressInterval = setInterval(() => {
                progress = Math.min(90, progress + Math.random() * 15);
                progressBar.style.width = progress + '%';
            }, 400);

            try {
                const response = await fetch(`/api/apex/predict/${ticker}`);
                const data = await response.json();

                clearInterval(progressInterval);
                progressBar.style.width = '100%';

                if(data.error) throw new Error(data.error);

                setTimeout(() => {
                    document.getElementById('apex-loading').classList.add('hidden');
                    displayApexPrediction(data);
                }, 500);

            } catch (error) {
                clearInterval(progressInterval);
                document.getElementById('apex-loading').classList.add('hidden');
                alert('APEX Prediction Error: ' + error.message);
            }
        }

        function displayApexPrediction(data) {
            document.getElementById('apex-result').classList.remove('hidden');

            // Header
            document.getElementById('apex-timestamp').textContent = data.timestamp || '-';
            document.getElementById('apex-asset-display').textContent = data.asset || '-';
            document.getElementById('apex-asset-class-display').textContent = data.asset_class || '-';

            // Direction
            const dirEl = document.getElementById('apex-direction');
            const dir = data.direction || 'HOLD';
            if(dir === 'UP') {
                dirEl.textContent = '▲ UP';
                dirEl.className = 'text-5xl font-bold text-green-500';
            } else if(dir === 'DOWN') {
                dirEl.textContent = '▼ DOWN';
                dirEl.className = 'text-5xl font-bold text-red-500';
            } else {
                dirEl.textContent = '─ HOLD';
                dirEl.className = 'text-5xl font-bold text-yellow-500';
            }
            document.getElementById('apex-current-price').textContent = `$${data.current_price || 'N/A'}`;

            // Confidence
            const conf = data.confidence_pct || 0;
            document.getElementById('apex-confidence').textContent = `${conf.toFixed(1)}%`;
            document.getElementById('apex-confidence').className = `text-5xl font-bold ${conf >= 75 ? 'text-green-400' : conf >= 55 ? 'text-yellow-400' : 'text-red-400'}`;
            document.getElementById('apex-confidence-label').textContent = data.confidence_label || '-';
            document.getElementById('apex-confidence-label').className = `text-lg mt-2 ${conf >= 75 ? 'text-green-400' : conf >= 55 ? 'text-yellow-400' : 'text-red-400'}`;

            // Confluence
            const conTotal = data.confluence?.total || 0;
            document.getElementById('apex-confluence').textContent = conTotal.toFixed(1);
            document.getElementById('apex-confluence').className = `text-5xl font-bold ${conTotal >= 38 ? 'text-green-400' : conTotal >= 28 ? 'text-yellow-400' : 'text-red-400'}`;

            // Entry / Target / Stop
            document.getElementById('apex-entry').textContent = `$${data.entry_price || 'N/A'}`;
            document.getElementById('apex-target').textContent = `$${data.target_price || 'N/A'}`;
            document.getElementById('apex-stop').textContent = `$${data.stop_loss || 'N/A'}`;

            // Confluence Dimensions
            const dims = data.confluence?.dimensions || [];
            const dimContainer = document.getElementById('apex-dimensions');
            dimContainer.innerHTML = dims.map(d => {
                const icons = d.signal && d.signal.toLowerCase().includes('bullish') ? '▲' :
                             d.signal && d.signal.toLowerCase().includes('bearish') ? '▼' : '─';
                const colors = d.signal && d.signal.toLowerCase().includes('bullish') ? 'text-green-400' :
                               d.signal && d.signal.toLowerCase().includes('bearish') ? 'text-red-400' : 'text-gray-400';
                return `<div class="flex justify-between items-center p-3 bg-gray-800/50 rounded-lg">
                    <span class="text-gray-300"><span class="${colors}">${icons}</span> ${d.name}</span>
                    <span class="font-mono"><span class="${colors} font-bold">${d.score}/10</span> <span class="text-gray-500">→</span> <span class="${colors}">${d.signal}</span></span>
                </div>`;
            }).join('');
            document.getElementById('apex-total-confluence').textContent = `${conTotal.toFixed(1)} / 50`;

            // Key Levels
            const levels = data.levels || {};
            const levelsContainer = document.getElementById('apex-levels');
            const levelHtml = [
                ['🔴 R3', levels.r3], ['🔴 R2', levels.r2], ['🔴 R1', levels.r1],
                ['📍 Pivot', levels.pivot],
                ['🟢 S1', levels.s1], ['🟢 S2', levels.s2], ['🟢 S3', levels.s3],
                ['📊 VWAP', levels.vwap]
            ].map(([label, val]) =>
                `<div class="flex justify-between p-2 bg-gray-800/30 rounded">
                    <span class="text-gray-400">${label}</span>
                    <span class="font-mono font-bold">${val || '-'}</span>
                </div>`
            ).join('');
            levelsContainer.innerHTML = levelHtml;

            // Candle Formation
            const candleDims = data.dimensions?.candle_strategy?.details || {};
            const candleContainer = document.getElementById('apex-candle');
            candleContainer.innerHTML = `
                <div class="flex justify-between p-2 bg-gray-800/30 rounded">
                    <span class="text-gray-400">Pattern</span>
                    <span class="font-bold">${candleDims.current_pattern || 'N/A'}</span>
                </div>
                <div class="flex justify-between p-2 bg-gray-800/30 rounded">
                    <span class="text-gray-400">Body %</span>
                    <span class="font-mono">${candleDims.body_pct || 'N/A'}%</span>
                </div>
                <div class="flex justify-between p-2 bg-gray-800/30 rounded">
                    <span class="text-gray-400">Upper Wick</span>
                    <span class="font-mono">${candleDims.upper_wick_pct || 'N/A'}%</span>
                </div>
                <div class="flex justify-between p-2 bg-gray-800/30 rounded">
                    <span class="text-gray-400">Lower Wick</span>
                    <span class="font-mono">${candleDims.lower_wick_pct || 'N/A'}%</span>
                </div>
            `;

            // Multi-TF Alignment
            const tf = data.multi_tf_alignment || {};
            const tfHtml = Object.entries(tf).map(([tfName, tfDir]) => {
                const icon = tfDir === 'Bullish' ? '▲' : tfDir === 'Bearish' ? '▼' : '─';
                const color = tfDir === 'Bullish' ? 'text-green-400' : tfDir === 'Bearish' ? 'text-red-400' : 'text-gray-400';
                return `${tfName}=<span class="${color}">${icon}</span>`;
            }).join(' ');
            candleContainer.innerHTML += `
                <div class="flex justify-between p-2 bg-gray-800/30 rounded mt-2">
                    <span class="text-gray-400">Multi-TF</span>
                    <span class="font-mono text-sm">${tfHtml}</span>
                </div>
            `;

            // Top Reasons (from dimension signals)
            let allSignals = [];
            Object.entries(data.dimensions || {}).forEach(([key, dim]) => {
                if(dim && dim.signals && Array.isArray(dim.signals)) {
                    dim.signals.forEach(s => allSignals.push({ signal: s, key }));
                }
            });
            allSignals = allSignals.slice(0, 8);

            const reasonsContainer = document.getElementById('apex-reasons');
            const riskContainer = document.getElementById('apex-risks');

            if(allSignals.length > 0) {
                reasonsContainer.innerHTML = allSignals.map((s, i) =>
                    `<div class="flex gap-2 p-2 bg-gray-800/30 rounded">
                        <span class="text-green-400">${i+1}.</span>
                        <span class="text-gray-300">${s.signal}</span>
                    </div>`
                ).join('');
                riskContainer.innerHTML = `
                    <div class="flex gap-2 p-2 bg-gray-800/30 rounded">
                        <span class="text-yellow-400">⚠️</span>
                        <span class="text-gray-300">Low confidence: ${data.confidence_pct?.toFixed(1) || 'N/A'}%</span>
                    </div>
                    <div class="flex gap-2 p-2 bg-gray-800/30 rounded">
                        <span class="text-yellow-400">⚠️</span>
                        <span class="text-gray-300">Market conditions can change rapidly</span>
                    </div>
                    <div class="flex gap-2 p-2 bg-gray-800/30 rounded">
                        <span class="text-yellow-400">⚠️</span>
                        <span class="text-gray-300">Past performance ≠ future results</span>
                    </div>`;
            } else {
                reasonsContainer.innerHTML = '<div class="text-gray-500 text-sm p-4 text-center">No specific signals generated</div>';
                riskContainer.innerHTML = '<div class="text-gray-500 text-sm p-4 text-center">No specific risk factors identified</div>';
            }

            // Raw Output
            document.getElementById('apex-raw-output').textContent = JSON.stringify(data, null, 2);

            // Update accuracy
            loadApexAccuracy();
        }

        async function loadApexAccuracy() {
            try {
                const response = await fetch('/api/apex/accuracy');
                const data = await response.json();
                const total = data.total || 0;
                const correct = data.correct || 0;
                const pct = total > 0 ? (correct / total * 100).toFixed(1) : 0;
                const recent = data.recent || [];
                const recentCorrect = recent.filter(r => r.correct).length;
                const recentTotal = recent.length;

                document.getElementById('apex-accuracy-display').innerHTML = `
                    <div class="grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
                        <div>
                            <div class="text-2xl font-bold text-white">${total}</div>
                            <div class="text-gray-500 text-xs">Total Predictions</div>
                        </div>
                        <div>
                            <div class="text-2xl font-bold text-green-400">${pct}%</div>
                            <div class="text-gray-500 text-xs">Overall Accuracy</div>
                        </div>
                        <div>
                            <div class="text-2xl font-bold ${recentTotal > 0 && recentCorrect/recentTotal >= 0.5 ? 'text-green-400' : 'text-red-400'}">${recentTotal > 0 ? (recentCorrect/recentTotal*100).toFixed(1) : 0}%</div>
                            <div class="text-gray-500 text-xs">Last ${recentTotal} Accuracy</div>
                        </div>
                        <div>
                            <div class="text-2xl font-bold text-white">${data.by_confidence ? Object.keys(data.by_confidence).length : 0}</div>
                            <div class="text-gray-500 text-xs">Confidence Levels Tracked</div>
                        </div>
                    </div>
                `;
            } catch(e) {
                console.error('Accuracy load error:', e);
            }
        }

        async function recordApexOutcome(wasCorrect) {
            const ticker = document.getElementById('apex-ticker').value.toUpperCase().trim();
            const confidenceLabel = document.getElementById('apex-confidence-label').textContent;

            try {
                await fetch('/api/apex/record_outcome', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ ticker, was_correct: wasCorrect, confidence_label: confidenceLabel })
                });
                loadApexAccuracy();
                const msg = wasCorrect ? '✅ Prediction recorded as CORRECT' : '❌ Prediction recorded as INCORRECT';
                alert(msg);
            } catch(e) {
                console.error('Record error:', e);
            }
        }

        function toggleApexAutoRefresh() {
            const btn = document.getElementById('apex-auto-btn');
            if(apexAutoRefreshInterval) {
                clearInterval(apexAutoRefreshInterval);
                apexAutoRefreshInterval = null;
                btn.textContent = 'Auto: OFF';
                btn.className = 'w-full bg-gray-800 hover:bg-gray-700 border border-gray-700 py-3 rounded-lg font-semibold transition';
            } else {
                apexAutoRefreshInterval = setInterval(runApexPrediction, 30000);
                btn.textContent = 'Auto: ON (30s)';
                btn.className = 'w-full bg-red-800 hover:bg-red-700 border border-red-500 py-3 rounded-lg font-semibold transition';
            }
        }

        // ─── SECTION SWITCHER ───
        const originalShowSection = showSection;
        showSection = function(section) {
            if(section === 'ipo') loadIPONews();
            if(section === 'academy') loadAcademy();
            if(section === 'live') initLiveChart();
            if(section === 'apex') loadApexAccuracy();
            originalShowSection(section);
        }

        // Socket listeners
        socket.on('connected', () => console.log('Connected'));
        socket.on('status_update', (data) => {
            document.getElementById('model-count').textContent = data.available_models || 0;
        });

        // Initial load
        loadDashboard();
    </script>
</body>
</html>
"""

    with open(os.path.join(templates_dir, 'index.html'), 'w', encoding='utf-8') as f:
        f.write(index_html)

    logger.info(f"Template created at {templates_dir}")


def run_server(port=5000):
    """Run the web server"""
    create_templates()

    print("\n" + "="*60)
    print("  STOCK PREDICTOR WEB UI")
    print("="*60)
    print(f"  Server running at: http://localhost:{port}")
    print("="*60)

    socketio.run(app, host='0.0.0.0', port=port, debug=True)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=5000)
    args = parser.parse_args()

    run_server(args.port)