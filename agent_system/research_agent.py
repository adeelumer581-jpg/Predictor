"""
Research Agent - Autonomously searches the web and GitHub for trading strategies and ML improvements.
"""
import asyncio
import logging
import os
import sys
from datetime import datetime
from typing import Dict, Any, List
from duckduckgo_search import DDGS

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agent_system.agent_coordinator import get_coordinator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ResearchAgent")

class ResearchAgent:
    def __init__(self):
        self.name = "ResearchAgent"
        self.is_active = False
        self.research_findings = []
        self.coordinator = get_coordinator()
        self.search_topics = [
            "latest machine learning algorithmic trading strategies github",
            "pytorch lstm stock prediction optimizations",
            "advanced technical indicators for algorithmic trading python"
        ]
        self.current_topic_index = 0

    async def start(self):
        """Start the research agent"""
        self.is_active = True
        logger.info("ResearchAgent started")
        self.coordinator.register_agent(self.name, self)

    async def stop(self):
        """Stop the research agent"""
        self.is_active = False
        logger.info("ResearchAgent stopped")

    async def receive_message(self, sender: str, message: Dict[str, Any]):
        """Receive messages from other agents"""
        pass # Currently focuses only on outgoing research

    async def execute_cycle(self) -> Dict[str, Any]:
        """Execute research cycle"""
        if not self.is_active:
            return {"status": "inactive"}

        logger.info("ResearchAgent: Running web research cycle...")
        
        topic = self.search_topics[self.current_topic_index]
        self.current_topic_index = (self.current_topic_index + 1) % len(self.search_topics)
        
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(topic, max_results=3))
            
            if results:
                summary = f"Found {len(results)} articles on '{topic}'. Top result: {results[0]['title']} - {results[0]['href']}"
                logger.info(f"Research Success: {summary}")
                
                finding = {
                    "topic": topic,
                    "top_result_title": results[0]['title'],
                    "top_result_url": results[0]['href'],
                    "snippet": results[0]['body'],
                    "timestamp": datetime.now().isoformat()
                }
                self.research_findings.append(finding)
                
                # Broadcast the finding to the Prompt Agent
                await self.coordinator.broadcast_message(self.name, {
                    "type": "new_research",
                    "finding": finding
                })
                
                return {"status": "completed", "finding": finding}
        except Exception as e:
            logger.error(f"ResearchAgent error during search: {e}")
            return {"status": "error", "message": str(e)}
            
        return {"status": "completed", "finding": None}
