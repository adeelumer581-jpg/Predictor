import os
import json
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TheManagingDirector")

class BossAgent:
    def __init__(self):
        self.name = "The Managing Director"
        self.db_file = "master_predictions.json"
        
    def execute(self, payload: dict) -> dict:
        ticker = payload["ticker"]
        logger.info(f"Synthesizing Institutional Scalping Report for {ticker}...")
        
        # 1. ORB Strategy Check
        orb_signal = self.check_orb_strategy(ticker)
        
        # 2. Confluence Calculation (Technical + Sentiment)
        tech = payload.get("technical_metrics", {})
        sentiment = payload.get("finbert_sentiment", 0.0)
        
        base_direction = "BULLISH" if tech.get("rsi", 50) < 60 else "BEARISH"
        
        # Confluence Bonus: If sentiment matches direction
        confluence_bonus = 0
        if (base_direction == "BULLISH" and sentiment > 0.2) or (base_direction == "BEARISH" and sentiment < -0.2):
            confluence_bonus = 15
            logger.info(f"CONFIRMED CONFLUENCE: Sentiment and Technicals aligned for {ticker}.")
            
        reduction = payload.get("bear_report", {}).get("confidence_reduction", 0)
        final_conf = min(99, 75 - reduction + confluence_bonus)
        
        # 3. Gold Signal Detection (Phase 4 Elite Rule)
        is_gold_signal = final_conf >= 90
        
        final_report = {
            "asset": ticker,
            "direction": base_direction,
            "strategy": "ORB_SCALP" if orb_signal else "QUANT_TREND",
            "confidence": f"{final_conf}%",
            "is_gold_signal": is_gold_signal,
            "bracket_order": payload.get("risk_management", {}).get("bracket_order"),
            "risk_status": payload.get("bear_report", {}).get("status"),
            "timestamp": datetime.now().isoformat()
        }
        
        if is_gold_signal:
            logger.critical(f" [GOLD_STRIKE] 90%+ Consensus reached for {ticker}!")
            self.log_to_db(final_report, is_gold=True)
        else:
            self.log_to_db(final_report)
            
        return final_report

    def check_orb_strategy(self, ticker):
        """Opening Range Breakout (ORB) Detection Logic"""
        now = datetime.now()
        # Active in the first 30 mins after ORB settles (9:35 - 10:00)
        if now.hour == 9 and 35 <= now.minute <= 59:
            return True
        return False

    def log_to_db(self, report, is_gold=False):
        # Log to master database
        db_file = "gold_signals.json" if is_gold else self.db_file
        history = []
        if os.path.exists(db_file):
            try:
                with open(db_file, 'r') as f:
                    history = json.load(f)
            except: pass
        history.append(report)
        with open(db_file, 'w') as f:
            json.dump(history[-100:], f, indent=2)

if __name__ == "__main__":
    agent = BossAgent()
    print(json.dumps(agent.execute({"ticker": "AAPL", "technical_metrics": {"rsi": 45}}), indent=2))
