"""
Launch all three components:
1. Mass Trainer - S&P 500
2. Backtesting Engine
3. Web UI Dashboard
"""
import subprocess
import sys
import os
import time

# Install dependencies if needed
def install_deps():
    deps = ['flask', 'flask-socketio', 'yfinance', 'pandas', 'numpy', 'scikit-learn', 'joblib']
    for dep in deps:
        try:
            __import__(dep)
        except ImportError:
            print(f"Installing {dep}...")
            subprocess.run([sys.executable, '-m', 'pip', 'install', dep, '-q'])


def main():
    print("\n" + "="*60)
    print("  STOCK PREDICTOR - FULL SUITE")
    print("="*60)
    print("\nSelect component to run:")
    print("  1. Mass Trainer (S&P 500)")
    print("  2. Backtesting Engine")
    print("  3. Web UI Dashboard")
    print("  4. All (Mass Trainer + Backtest)")
    print("  5. Quit")
    print("="*60)

    choice = input("\nEnter choice (1-5): ").strip()

    if choice == "1":
        print("\nStarting Mass Trainer...")
        from mass_trainer import run_mass_trainer
        run_mass_trainer()

    elif choice == "2":
        print("\nStarting Backtesting Engine...")
        from backtester import run_backtest
        run_backtest()

    elif choice == "3":
        print("\nStarting Web UI...")
        install_deps()
        from web_ui import run_server
        run_server()

    elif choice == "4":
        print("\nRunning Mass Trainer + Backtest...")
        print("\n--- Phase 1: Mass Trainer ---")
        from mass_trainer import run_mass_trainer
        run_mass_trainer()

        print("\n--- Phase 2: Backtest ---")
        from backtester import run_backtest
        run_backtest()

    else:
        print("Exiting...")


if __name__ == "__main__":
    main()