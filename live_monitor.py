"""
Stock Market Live Monitor
==========================
Runs continuous predictions on multiple stocks with auto-refresh.
Usage: python live_monitor.py
Press Ctrl+C to stop.
"""

import time
import os
from stock_predictor import StockPredictor
from datetime import datetime

# Stocks to monitor
WATCHLIST = [
    'AAPL',   # Apple
    'MSFT',   # Microsoft
    'NVDA',   # NVIDIA
    'GOOGL',  # Google
    'AMZN',   # Amazon
    'TSLA',   # Tesla
    'META',   # Meta
    'AMD',    # AMD
    'JPM',    # JPMorgan
    'V',      # Visa
    'LUCK.PSX', # Lucky Cement
    'ENGRO.PSX', # Engro
    'SYS.PSX',   # Systems Limited
]

REFRESH_INTERVAL = 300  # seconds (5 minutes)

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def run_monitor():
    print("="*60)
    print("STOCK MARKET LIVE MONITOR")
    print("="*60)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Watchlist: {', '.join(WATCHLIST)}")
    print(f"Refresh: every {REFRESH_INTERVAL} seconds")
    print("Press Ctrl+C to stop")
    print("="*60)

    while True:
        clear_screen()
        print(f"\n[*] Last Update: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*60)

        results = []

        for ticker in WATCHLIST:
            try:
                predictor = StockPredictor(ticker, lookback_days=365)
                predictor.train()
                result = predictor.predict_next()
                results.append(result)

                direction = "^" if result['prediction'] == 'UP' else "v"
                print(f"{ticker:6} ${result['current_price']:>8.2f}  {direction} {result['prediction']:3}  "
                      f"Conf: {result['confidence']:5.1f}%")

            except Exception as e:
                print(f"{ticker:6} ERROR: {str(e)[:40]}")

        # Summary
        print("\n" + "="*60)
        up_count = sum(1 for r in results if r['prediction'] == 'UP')
        down_count = len(results) - up_count
        avg_confidence = sum(r['confidence'] for r in results) / len(results)

        print(f"MARKET SENTIMENT: {up_count} UP | {down_count} DOWN")
        print(f"AVERAGE CONFIDENCE: {avg_confidence:.1f}%")
        print("="*60)
        print(f"Next update in {REFRESH_INTERVAL} seconds... (Ctrl+C to stop)")

        time.sleep(REFRESH_INTERVAL)

if __name__ == "__main__":
    try:
        run_monitor()
    except KeyboardInterrupt:
        print("\n\n[*] Monitor stopped by user")
        print(f"Stopped at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")