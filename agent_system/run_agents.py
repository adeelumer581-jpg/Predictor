"""
Main Agent System Runner - Connects all 5 agents together
"""
import asyncio
import logging
import signal
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent_system.agent_coordinator import get_coordinator
from agent_system.training_agent import TrainingAgent
from agent_system.development_agent import DevelopmentAgent
from agent_system.security_agent import SecurityAgent
from agent_system.debug_agent import DebugAgent
from agent_system.upscaling_agent import UpscalingAgent

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("AgentSystem")


class MultiAgentSystem:
    def __init__(self):
        self.coordinator = get_coordinator()
        self.agents = {}
        self.is_running = False

    def setup_agents(self):
        """Initialize all agents"""
        logger.info("Initializing all agents...")

        # 1. Training Agent - trains every minute
        training_agent = TrainingAgent(tickers=["AAPL", "MSFT", "NVDA", "GOOGL"])
        self.agents["TrainingAgent"] = training_agent
        logger.info("  - Training Agent: Ready (trains every minute)")

        # 2. Development Agent - develops code daily
        development_agent = DevelopmentAgent()
        self.agents["DevelopmentAgent"] = development_agent
        logger.info("  - Development Agent: Ready (daily code development)")

        # 3. Security Agent - provides security
        security_agent = SecurityAgent()
        self.agents["SecurityAgent"] = security_agent
        logger.info("  - Security Agent: Ready (security monitoring)")

        # 4. Debug Agent - debugs the predictor
        debug_agent = DebugAgent()
        self.agents["DebugAgent"] = debug_agent
        logger.info("  - Debug Agent: Ready (diagnostics & debugging)")

        # 5. Upscaling Agent - scales the predictor
        upscaling_agent = UpscalingAgent()
        self.agents["UpscalingAgent"] = upscaling_agent
        logger.info("  - Upscaling Agent: Ready (resource management)")

        return self.agents

    async def start_all(self):
        """Start all agents"""
        logger.info("\n" + "="*50)
        logger.info("STARTING MULTI-AGENT SYSTEM")
        logger.info("="*50 + "\n")

        self.is_running = True

        # Start each agent
        for name, agent in self.agents.items():
            try:
                await agent.start()
                logger.info(f"Started: {name}")
            except Exception as e:
                logger.error(f"Failed to start {name}: {e}")

        # Connect agents via coordinator
        for name, agent in self.agents.items():
            self.coordinator.register_agent(name, agent)

        logger.info("\n" + "="*50)
        logger.info("ALL AGENTS CONNECTED AND RUNNING")
        logger.info("="*50)

    async def run_training_loop(self):
        """Run training agent in continuous loop"""
        training_agent = self.agents.get("TrainingAgent")
        if training_agent:
            logger.info("Starting continuous training loop (every 60 seconds)...")
            await training_agent.run_continuous_training()

    async def run_monitoring_cycle(self, interval: int = 30):
        """Run monitoring cycles for other agents"""
        logger.info(f"Running monitoring cycles every {interval} seconds...")

        development_agent = self.agents.get("DevelopmentAgent")
        security_agent = self.agents.get("SecurityAgent")
        debug_agent = self.agents.get("DebugAgent")
        upscaling_agent = self.agents.get("UpscalingAgent")

        while self.is_running:
            try:
                # Development cycle (every 5 minutes)
                if development_agent:
                    await development_agent.execute_cycle()

                # Security cycle (every minute)
                if security_agent:
                    await security_agent.execute_cycle()

                # Debug cycle (every 2 minutes)
                if debug_agent:
                    await debug_agent.execute_cycle()

                # Upscaling cycle (every minute)
                if upscaling_agent:
                    await upscaling_agent.execute_cycle()

                await asyncio.sleep(interval)

            except Exception as e:
                logger.error(f"Error in monitoring cycle: {e}")
                await asyncio.sleep(interval)

    async def stop_all(self):
        """Stop all agents"""
        logger.info("\nStopping all agents...")
        self.is_running = False

        for name, agent in self.agents.items():
            try:
                await agent.stop()
                logger.info(f"Stopped: {name}")
            except Exception as e:
                logger.error(f"Error stopping {name}: {e}")

    def get_system_status(self) -> dict:
        """Get status of all agents"""
        status = {
            "is_running": self.is_running,
            "agents": {}
        }

        for name, agent in self.agents.items():
            if hasattr(agent, 'get_performance_metrics'):
                status["agents"][name] = agent.get_performance_metrics()
            elif hasattr(agent, 'get_security_status'):
                status["agents"][name] = agent.get_security_status()
            elif hasattr(agent, 'get_debug_status'):
                status["agents"][name] = agent.get_debug_status()
            elif hasattr(agent, 'get_upscaling_status'):
                status["agents"][name] = agent.get_upscaling_status()
            elif hasattr(agent, 'generate_report'):
                status["agents"][name] = asyncio.run(agent.generate_report())
            else:
                status["agents"][name] = {"status": "active" if agent.is_active else "inactive"}

        return status


async def main():
    """Main entry point"""
    system = MultiAgentSystem()

    # Setup signal handlers
    def signal_handler(sig, frame):
        print("\nShutdown signal received...")
        asyncio.create_task(system.stop_all())

    signal.signal(signal.SIGINT, signal_handler)

    # Initialize and start agents
    system.setup_agents()
    await system.start_all()

    # Print agent connections
    print("\n" + "="*60)
    print("AGENT CONNECTIONS:")
    print("="*60)
    print("""
    [TrainingAgent] ----> [DevelopmentAgent]
          |                     |
          v                     v
    [DebugAgent] <------> [SecurityAgent]
          |                     |
          v                     v
    [UpscalingAgent] <---- (All Agents)
    """)
    print("="*60 + "\n")

    # Run training in background and monitoring in foreground
    try:
        # Create tasks for training and monitoring
        training_task = asyncio.create_task(system.run_training_loop())
        monitoring_task = asyncio.create_task(system.run_monitoring_cycle())

        # Wait for both
        await asyncio.gather(training_task, monitoring_task)

    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
    finally:
        await system.stop_all()

    # Print final status
    print("\n" + "="*60)
    print("FINAL SYSTEM STATUS:")
    print("="*60)
    status = system.get_system_status()
    for agent, info in status["agents"].items():
        print(f"\n{agent}:")
        for key, value in info.items():
            print(f"  {key}: {value}")


def run_agents():
    """Run the agent system"""
    asyncio.run(main())


if __name__ == "__main__":
    run_agents()