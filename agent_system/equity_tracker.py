import json
import os
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("EquityTracker")

class EquityTracker:
    def __init__(self):
        self.log_file = "equity_curve.json"
        self.initial_balance = 10000.0
        self.balance = self.load_latest_balance()
        
    def load_latest_balance(self):
        if os.path.exists(self.log_file):
            try:
                with open(self.log_file, 'r') as f:
                    data = json.load(f)
                    if data:
                        return data[-1]["balance"]
            except: pass
        return self.initial_balance
        
    def process_simulation(self, report):
        """Simulate a trade outcome based on the report's confidence"""
        ticker = report["asset"]
        confidence_str = report["confidence"].replace("%", "")
        confidence = float(confidence_str) / 100.0
        
        # Determine PnL (Simplified Simulation)
        # Higher confidence = higher probability of success
        import random
        win = random.random() < confidence
        
        bracket = report.get("bracket_order", {"take_profit_pct": 1.0, "stop_loss_pct": 0.5})
        tp = bracket["take_profit_pct"] / 100.0
        sl = bracket["stop_loss_pct"] / 100.0
        
        # Risk 1% of balance per the Warden's rule
        risk_amount = self.balance * 0.01
        
        if win:
            pnl = risk_amount * (tp / sl) # Reward based on RR ratio
            logger.info(f" [SIM_WIN] {ticker} Profit: +${pnl:.2f}")
        else:
            pnl = -risk_amount
            logger.warning(f" [SIM_LOSS] {ticker} Loss: -${abs(pnl):.2f}")
            
        self.balance += pnl
        self.update_log(ticker, pnl)
        
    def update_log(self, ticker, pnl):
        entry = {
            "timestamp": datetime.now().isoformat(),
            "ticker": ticker,
            "pnl": round(pnl, 2),
            "balance": round(self.balance, 2)
        }
        
        history = []
        if os.path.exists(self.log_file):
            try:
                with open(self.log_file, 'r') as f:
                    history = json.load(f)
            except: pass
            
        history.append(entry)
        with open(self.log_file, 'w') as f:
            json.dump(history[-500:], f, indent=2)
        
        logger.info(f"Current Firmware Equity: ${self.balance:.2f}")
