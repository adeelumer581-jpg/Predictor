import time
import os
from datetime import datetime
from stock_predictor import StockPredictor

class WorkerAgent:
    def __init__(self):
        self.current_orders = []
        
    def receive_orders(self, tickers):
        """Receives new list of tickers from the Boss Agent."""
        self.current_orders = tickers
        print(f"[*] WORKER AGENT: Received orders to monitor: {', '.join(tickers)}")
        
    def execute_scan(self):
        """Runs a single live scan on the current orders."""
        if not self.current_orders:
            print("[*] WORKER AGENT: No orders to execute. Waiting...")
            return

        print(f"\n[*] WORKER AGENT: Starting live market scan at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("-" * 60)
        
        results = []
        for ticker in self.current_orders:
            try:
                # Some commodities might need less lookback due to data availability, but 365 is generally fine
                predictor = StockPredictor(ticker, lookback_days=365)
                predictor.train()
                result = predictor.predict_next()
                results.append(result)
                
                direction = "^" if result['prediction'] == 'UP' else "v"
                print(f"{ticker:6} | Price: ${result['current_price']:>8.2f} | {direction} {result['prediction']:3} | Conf: {result['confidence']:5.1f}%")
                
            except Exception as e:
                print(f"{ticker:6} | ERROR: {str(e)[:50]}")
                
        print("-" * 60)
        if results:
            up_count = sum(1 for r in results if r['prediction'] == 'UP')
            down_count = len(results) - up_count
            avg_conf = sum(r['confidence'] for r in results) / len(results)
            print(f"WORKER SUMMARY: {up_count} UP | {down_count} DOWN | Avg Conf: {avg_conf:.1f}%")
        print("=" * 60)

if __name__ == "__main__":
    worker = WorkerAgent()
    worker.receive_orders(['AAPL', 'GC=F'])
    worker.execute_scan()
