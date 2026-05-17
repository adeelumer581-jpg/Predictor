import os
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TheBear")

class BearAgent:
    def __init__(self):
        self.name = "The Bear"
        
    def execute(self, payload: dict) -> dict:
        ticker = payload["ticker"]
        logger.info(f"Stress-testing {ticker} for Bull/Bear Traps...")
        
        tech = payload.get("technical_metrics", {})
        rsi = tech.get("rsi", 50)
        patterns = tech.get("detected_patterns", [])
        is_confirmed = tech.get("is_breakout_confirmed", False)
        
        adversarial_notes = []
        reduction = 0
        
        # 1. Volume-Based Trap Detection (Phase 2 Rule)
        if len(patterns) > 0 and not is_confirmed:
            adversarial_notes.append(f"TRAP ALERT: {patterns[0]} detected but failed 2.0x Volume Expansion Rule.")
            reduction += 40
            
        # 2. Institutional Exhaustion (Phase 3 Rule)
        if rsi > 70:
            adversarial_notes.append(f"CRITICAL: RSI is {rsi:.1f} (Institutional Exhaustion Zone).")
            reduction += 25
        
        # 3. VWAP Divergence
        if tech.get("close", 0) > tech.get("vwap", 0) * 1.05:
            adversarial_notes.append("WARNING: Extreme divergence from VWAP. Reversion to mean imminent.")
            reduction += 15
            
        payload["bear_report"] = {
            "adversarial_notes": adversarial_notes,
            "confidence_reduction": reduction,
            "status": "TRAP_DETECTED" if reduction > 30 else "PASS"
        }
        
        return payload

if __name__ == "__main__":
    agent = BearAgent()
    print(json.dumps(agent.execute({"ticker": "AAPL", "technical_metrics": {"rsi": 75}}), indent=2))
