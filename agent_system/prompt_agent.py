"""
Prompt Engineer Agent - Listens to research and outputs commands for Claude.
"""
import asyncio
import logging
import os
import sys
from datetime import datetime
from typing import Dict, Any, List

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agent_system.agent_coordinator import get_coordinator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("PromptAgent")

class PromptAgent:
    def __init__(self):
        self.name = "PromptAgent"
        self.is_active = False
        self.pending_prompts = []
        self.coordinator = get_coordinator()

    async def start(self):
        """Start the prompt engineer agent"""
        self.is_active = True
        logger.info("PromptAgent started")
        self.coordinator.register_agent(self.name, self)

    async def stop(self):
        """Stop the prompt engineer agent"""
        self.is_active = False
        logger.info("PromptAgent stopped")

    async def receive_message(self, sender: str, message: Dict[str, Any]):
        """Receive messages from other agents"""
        msg_type = message.get("type")
        if msg_type == "new_research":
            finding = message.get("finding", {})
            self.generate_prompt_from_research(finding)

    def generate_prompt_from_research(self, finding: Dict[str, Any]):
        """Translates a research finding into an actionable Claude prompt"""
        topic = finding.get("topic", "")
        title = finding.get("top_result_title", "")
        url = finding.get("top_result_url", "")
        snippet = finding.get("snippet", "")
        
        prompt_text = (
            f"--- NEW RESEARCH DISCOVERED ---\n"
            f"Topic: {topic}\n"
            f"Source Title: {title}\n"
            f"Context snippet: {snippet}\n\n"
            f"[NEXT_STEP_FOR_ANTIGRAVITY]\n"
            f"Antigravity, analyze this concept and write a concrete plan to integrate it into our Stock Predictor.\n\n"
            f"[Claude DIRECTIVE]\n"
            f"Claude, please review this research topic: '{topic}'. "
            f"Execute any background terminal commands, migrations, or file scaffolding needed to support Antigravity's plan."
        )
        
        self.pending_prompts.append(prompt_text)

    async def execute_cycle(self) -> Dict[str, Any]:
        """Execute prompt cycle and feed to auto_bridge"""
        if not self.is_active:
            return {"status": "inactive"}

        if self.pending_prompts:
            # We pop the oldest prompt
            next_prompt = self.pending_prompts.pop(0)
            
            logger.info("PromptAgent: Outputting commands to Claude and Antigravity...")
            print("\n" + "="*80)
            print(next_prompt)
            print("="*80 + "\n")
            
            return {"status": "prompt_generated", "remaining": len(self.pending_prompts)}
            
        return {"status": "idle"}
