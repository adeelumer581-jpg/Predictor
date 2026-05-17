import os
import json
import time
import logging
import asyncio
from agent_system.scout_agent import ScoutAgent
from agent_system.deep_math_agent import DeepMathAgent
from agent_system.historian_agent import HistorianAgent
from agent_system.bear_agent import BearAgent
from agent_system.warden_agent import WardenAgent
from agent_system.boss_agent import BossAgent
from agent_system.equity_tracker import EquityTracker

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("PerpetualOrchestrator")

class PerpetualOrchestrator:
    def __init__(self, tickers=None):
        if tickers is None:
            # Load Global Watchlist
            watchlist_path = os.path.join(os.path.dirname(__file__), "global_watchlist.json")
            if os.path.exists(watchlist_path):
                with open(watchlist_path, 'r') as f:
                    data = json.load(f)
                    # Flatten all categories into one massive round-robin list
                    self.tickers = [item for sublist in data.values() for item in sublist]
            else:
                self.tickers = ["AAPL", "MSFT", "NVDA", "TSLA", "LUCK.PSX"]
        else:
            self.tickers = tickers
            
        self.scout = ScoutAgent()
        self.math = DeepMathAgent()
        self.historian = HistorianAgent()
        self.bear = BearAgent()
        self.warden = WardenAgent()
        self.boss = BossAgent()
        self.equity = EquityTracker()
        
    async def run_cycle(self, ticker):
        logger.info(f"--- STARTING CYCLE FOR {ticker} ---")
        try:
            # 1. Scout
            scout_data = self.scout.execute(ticker)
            
            # 2. Math
            math_data = self.math.execute(scout_data)
            
            # 3. Historian
            hist_data = self.historian.execute(math_data)
            
            # 4. Bear
            bear_data = self.bear.execute(hist_data)
            
            # 5. Warden
            warden_data = self.warden.execute(bear_data)
            
            # 6. Boss
            final_report = self.boss.execute(warden_data)
            
            # 7. Equity Simulation
            self.equity.process_simulation(final_report)
            
            logger.info(f"--- CYCLE COMPLETE FOR {ticker} ---")
            logger.info(f"Result: {final_report['direction']} ({final_report['confidence']})")
            
        except Exception as e:
            logger.error(f"Error in cycle for {ticker}: {e}")

    async def start(self):
        logger.info(f"Initializing Perpetual Loop for {len(self.tickers)} assets...")
        while True:
            for ticker in self.tickers:
                await self.run_cycle(ticker)
                await asyncio.sleep(2) # Micro-pause between tickers
            logger.info("Universal cycle complete. Re-triggering Scout for next generation...")
            await asyncio.sleep(1)

if __name__ == "__main__":
    orchestrator = PerpetualOrchestrator()
    asyncio.run(orchestrator.start())
