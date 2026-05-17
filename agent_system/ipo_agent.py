import os
import json
import logging
import time
import sys
from datetime import datetime
from duckduckgo_search import DDGS

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agent_system.agent_coordinator import get_coordinator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("IPOAgent")

class IPOAgent:
    def __init__(self):
        self.name = "IPOAgent"
        self.news_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ipo_news.json")
        self.is_active = False
        self.coordinator = get_coordinator()
        
    async def start(self):
        self.is_active = True
        logger.info("IPOAgent started")
        
    async def stop(self):
        self.is_active = False
        logger.info("IPOAgent stopped")
        
    async def receive_message(self, sender: str, message: dict):
        pass # Not handling messages for now
        
    async def execute_cycle(self):
        """Standard execution cycle for the coordinator"""
        if not self.is_active:
            return {"status": "inactive"}
        return self.search_ipo_news()
    def search_ipo_news(self):
        logger.info("Searching for upcoming IPO news...")
        queries = [
            "upcoming IPOs NYSE Nasdaq 2024 2025",
            "upcoming IPOs Pakistan Stock Exchange PSX 2024",
            "latest IPO rumors and filings"
        ]
        
        all_results = []
        with DDGS() as ddgs:
            for query in queries:
                try:
                    results = list(ddgs.text(query, max_results=5))
                    for r in results:
                         r['timestamp'] = datetime.now().strftime("%Y-%m-%d")
                    all_results.extend(results)
                    time.sleep(1) # Avoid rate limits
                except Exception as e:
                    logger.error(f"Search error for '{query}': {e}")
                    
        # Process and save
        news_data = {
            "last_updated": datetime.now().isoformat(),
            "articles": all_results
        }
        
        with open(self.news_file, 'w') as f:
            json.dump(news_data, f, indent=2)
            
        logger.info(f"Saved {len(all_results)} IPO news items to {self.news_file}")
        return news_data

if __name__ == "__main__":
    agent = IPOAgent()
    agent.search_ipo_news()
