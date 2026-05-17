import os
import json
import logging
import time
from duckduckgo_search import DDGS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TheHistorian")

class HistorianAgent:
    def __init__(self):
        self.name = "The Historian"
        
    def execute(self, payload: dict) -> dict:
        logger.info("Analyzing macroeconomic context...")
        
        queries = [
            "latest FOMC interest rate decision news",
            "current US inflation CPI data report",
            "S&P 500 sector rotation today"
        ]
        
        macro_news = []
        with DDGS() as ddgs:
            for query in queries:
                try:
                    results = list(ddgs.text(query, max_results=2))
                    macro_news.extend(results)
                except:
                    pass
        
        payload["macro_context"] = macro_news
        # Simple macro risk scoring (can be expanded)
        payload["macro_risk_score"] = 0.5 
        
        return payload

if __name__ == "__main__":
    agent = HistorianAgent()
    print(json.dumps(agent.execute({"ticker": "AAPL"}), indent=2))
