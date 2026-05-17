"""
Agent Coordinator - Main hub that connects all agents
"""
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List
import json

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("AgentCoordinator")

class AgentCoordinator:
    def __init__(self):
        self.agents = {}
        self.message_queue = asyncio.Queue()
        self.agent_states = {}
        self.is_running = False

    def register_agent(self, name: str, agent):
        """Register an agent with the coordinator"""
        self.agents[name] = agent
        self.agent_states[name] = {
            "status": "idle",
            "last_run": None,
            "last_message": None,
            "errors": []
        }
        logger.info(f"Registered agent: {name}")

    async def broadcast_message(self, sender: str, message: Dict[str, Any]):
        """Broadcast message to all agents"""
        for agent_name, agent in self.agents.items():
            if agent_name != sender:
                await agent.receive_message(sender, message)
                logger.info(f"[{sender}] -> [{agent_name}]: {message.get('type', 'unknown')}")

    async def update_agent_state(self, agent_name: str, status: str, message: str = None):
        """Update agent state"""
        if agent_name in self.agent_states:
            self.agent_states[agent_name]["status"] = status
            self.agent_states[agent_name]["last_run"] = datetime.now().isoformat()
            if message:
                self.agent_states[agent_name]["last_message"] = message

    async def get_system_status(self) -> Dict[str, Any]:
        """Get status of all agents"""
        return {
            "is_running": self.is_running,
            "agents": self.agent_states,
            "active_agents": sum(1 for s in self.agent_states.values() if s["status"] == "running")
        }

    async def start_all_agents(self):
        """Start all registered agents"""
        self.is_running = True
        logger.info("Starting all agents...")
        for agent_name, agent in self.agents.items():
            try:
                await agent.start()
                await self.update_agent_state(agent_name, "running", "Agent started successfully")
            except Exception as e:
                logger.error(f"Failed to start {agent_name}: {e}")
                self.agent_states[agent_name]["errors"].append(str(e))

    async def stop_all_agents(self):
        """Stop all agents"""
        self.is_running = False
        logger.info("Stopping all agents...")
        for agent_name, agent in self.agents.items():
            try:
                await agent.stop()
                await self.update_agent_state(agent_name, "stopped", "Agent stopped")
            except Exception as e:
                logger.error(f"Error stopping {agent_name}: {e}")

    async def run_cycle(self):
        """Run one cycle of all agents"""
        results = {}
        for agent_name, agent in self.agents.items():
            try:
                result = await agent.execute_cycle()
                results[agent_name] = {"status": "success", "result": result}
            except Exception as e:
                logger.error(f"Error in {agent_name}: {e}")
                results[agent_name] = {"status": "error", "error": str(e)}
        return results


# Global coordinator instance
_coordinator = None

def get_coordinator() -> AgentCoordinator:
    global _coordinator
    if _coordinator is None:
        _coordinator = AgentCoordinator()
    return _coordinator