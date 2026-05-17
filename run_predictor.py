"""
Quick launcher for Stock Predictor
Run: python run_predictor.py TICKER
Example: python run_predictor.py AAPL
"""

import subprocess
import sys

def main():
    ticker = sys.argv[1] if len(sys.argv) > 1 else "AAPL"

    print(f"\n{'='*50}")
    print(f"Stock Market Predictor")
    print(f"Ticker: {ticker}")
    print(f"{'='*50}\n")

    # Run predictor with all features
    cmd = [sys.executable, "stock_predictor.py", ticker, "--train", "--predict"]
    subprocess.run(cmd)

    print("\n" + "="*50)
    print("DONE!")
    print("="*50)

if __name__ == "__main__":
    main()