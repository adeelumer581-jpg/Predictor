"""
Training Agent - Trains the predictor in live time every minute
"""
import asyncio
import logging
import os
import sys
from datetime import datetime
from typing import Dict, Any
import subprocess

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agent_system.agent_coordinator import get_coordinator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TrainingAgent")

class TrainingAgent:
    def __init__(self, tickers: list = None):
        self.name = "TrainingAgent"
        self.tickers = tickers or ["AAPL", "MSFT", "NVDA", "GOOGL"]
        self.is_active = False
        self.last_trained = {}
        self.training_interval = 60  # 1 minute
        self.model_performance = {}
        self.coordinator = get_coordinator()

    async def start(self):
        """Start the training agent"""
        self.is_active = True
        logger.info(f"TrainingAgent started with tickers: {self.tickers}")
        self.coordinator.register_agent(self.name, self)

    async def stop(self):
        """Stop the training agent"""
        self.is_active = False
        logger.info("TrainingAgent stopped")

    async def receive_message(self, sender: str, message: Dict[str, Any]):
        """Receive messages from other agents"""
        msg_type = message.get("type")
        if msg_type == "train_now":
            await self.train_single_ticker(message.get("ticker"))
        elif msg_type == "update_interval":
            self.training_interval = message.get("interval", 60)
        elif msg_type == "add_ticker":
            ticker = message.get("ticker")
            if ticker and ticker not in self.tickers:
                self.tickers.append(ticker)
                logger.info(f"Added ticker: {ticker}")

    async def train_single_ticker(self, ticker: str) -> Dict[str, Any]:
        """Train model for a single ticker"""
        logger.info(f"Training model for {ticker}...")
        start_time = datetime.now()

        try:
            cmd = [sys.executable, "stock_predictor.py", ticker, "--train", "--predict"]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120,
                cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            )

            duration = (datetime.now() - start_time).total_seconds()

            training_result = {
                "ticker": ticker,
                "status": "success" if result.returncode == 0 else "failed",
                "duration": duration,
                "timestamp": datetime.now().isoformat(),
                "output": result.stdout[-500:] if result.stdout else ""
            }

            self.last_trained[ticker] = training_result

            # Broadcast to other agents
            await self.coordinator.broadcast_message(self.name, {
                "type": "training_complete",
                "ticker": ticker,
                "result": training_result
            })

            return training_result

        except Exception as e:
            error_result = {
                "ticker": ticker,
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            logger.error(f"Training failed for {ticker}: {e}")
            return error_result

    async def train_all_tickers(self) -> Dict[str, Any]:
        """Train all tickers"""
        results = {}
        for ticker in self.tickers:
            results[ticker] = await self.train_single_ticker(ticker)
        return results

    async def execute_cycle(self) -> Dict[str, Any]:
        """Execute one training cycle"""
        if not self.is_active:
            return {"status": "inactive"}

        logger.info("TrainingAgent: Running training cycle...")
        results = await self.train_all_tickers()

        successful = sum(1 for r in results.values() if r.get("status") == "success")

        return {
            "status": "completed",
            "tickers_trained": len(self.tickers),
            "successful": successful,
            "failed": len(self.tickers) - successful,
            "results": results
        }

    async def run_continuous_training(self):
        """Run continuous training every minute"""
        logger.info("Starting continuous training loop...")
        while self.is_active:
            await self.execute_cycle()
            await asyncio.sleep(self.training_interval)

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for all trained models"""
        return {
            "last_trained": self.last_trained,
            "tickers": self.tickers,
            "interval_seconds": self.training_interval
        }