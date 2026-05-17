import os
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TheWarden")

class WardenAgent:
    def __init__(self):
        self.name = "The Warden"
        
    def execute(self, payload: dict) -> dict:
        logger.info("Applying Elite Sentiment-Weighted Risk Rules...")
        
        # Win probability (estimate from technicals/bear report)
        p = 0.55 if payload.get("bear_report", {}).get("status") == "PASS" else 0.45
        
        # 1. Microscopic Sentiment Weighting (Phase 3 Rule)
        sentiment = payload.get("finbert_sentiment", 0.0)
        max_risk_pct = 1.0 # Standard 1% risk
        
        # DIVERGENCE PROTECTION: If technicals are bullish but sentiment is bearish
        if sentiment < -0.2:
            logger.warning("Sentiment Divergence Detected (Bearish Sentiment). Slashing risk exposure.")
            max_risk_pct = 0.2 # Reduce risk by 80%
        elif sentiment > 0.5:
            logger.info("High Sentiment Conviction. Maintaining full risk exposure.")
            max_risk_pct = 1.0
            
        stop_loss = 0.5 # Strict 0.5% stop for scalping
        take_profit = stop_loss * 2.0
        
        # Recommended Allocation based on sentiment-weighted risk
        recommended_allocation = max_risk_pct / stop_loss 
        
        payload["risk_management"] = {
            "p_win_est": p,
            "sentiment_score": round(sentiment, 2),
            "weighted_risk_pct": max_risk_pct,
            "recommended_allocation_pct": round(recommended_allocation, 2),
            "bracket_order": {
                "stop_loss_pct": stop_loss,
                "take_profit_pct": take_profit,
                "ratio": "2:1"
            },
            "liquidity_check": "PASSED" if payload["ticker"] in ["AAPL", "MSFT", "NVDA", "TSLA", "SPY", "QQQ", "BTC-USD"] else "CAUTION"
        }
        
        return payload

if __name__ == "__main__":
    agent = WardenAgent()
    print(json.dumps(agent.execute({"technical_metrics": {"rsi": 45}}), indent=2))
