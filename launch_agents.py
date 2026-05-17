"""
Quick launcher for Agent System
Usage: python launch_agents.py [mode]

Modes:
  all     - Run all 5 connected agents (default)
  train   - Run only Training Agent
  dev     - Run only Development Agent
  sec     - Run only Security Agent
  debug   - Run only Debug Agent
  scale   - Run only Upscaling Agent
"""
import sys
import asyncio
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agent_system.agent_coordinator import get_coordinator
from agent_system.training_agent import TrainingAgent
from agent_system.development_agent import DevelopmentAgent
from agent_system.security_agent import SecurityAgent
from agent_system.debug_agent import DebugAgent
from agent_system.upscaling_agent import UpscalingAgent
from agent_system.research_agent import ResearchAgent
from agent_system.prompt_agent import PromptAgent
from agent_system.ipo_agent import IPOAgent


async def run_all_agents():
    """Run all 5 agents connected together"""
    print("\n" + "="*60)
    print("  STOCK PREDICTOR MULTI-AGENT SYSTEM")
    print("="*60)

    coordinator = get_coordinator()

    # Create all 5 agents
    training_agent = TrainingAgent(tickers=["AAPL", "MSFT", "NVDA", "GOOGL"])
    development_agent = DevelopmentAgent()
    security_agent = SecurityAgent()
    debug_agent = DebugAgent()
    upscaling_agent = UpscalingAgent()
    research_agent = ResearchAgent()
    prompt_agent = PromptAgent()
    ipo_agent = IPOAgent()

    agents = {
        "TrainingAgent": training_agent,
        "DevelopmentAgent": development_agent,
        "SecurityAgent": security_agent,
        "DebugAgent": debug_agent,
        "UpscalingAgent": upscaling_agent,
        "ResearchAgent": research_agent,
        "PromptAgent": prompt_agent,
        "IPOAgent": ipo_agent
    }

    print("\n[1] TrainingAgent     - Trains predictor every 60 seconds")
    print("[2] DevelopmentAgent - Daily code development & improvements")
    print("[3] SecurityAgent    - Security scanning & monitoring")
    print("[4] DebugAgent       - Diagnostics & bug detection")
    print("[5] UpscalingAgent   - Resource management & scaling")
    print("[6] ResearchAgent    - Web & GitHub R&D scanning")
    print("[7] PromptAgent      - Translates R&D into Claude Prompts")
    print("[8] IPOAgent        - Global & PSX IPO scouting")
    print("\nConnecting agents...\n")

    # Register and start all agents
    for name, agent in agents.items():
        coordinator.register_agent(name, agent)
        await agent.start()

    # Show connections
    print("Agent Connections:")
    print("  TrainingAgent <---> DevelopmentAgent")
    print("  TrainingAgent <---> DebugAgent")
    print("  SecurityAgent <---> DevelopmentAgent")
    print("  DebugAgent    <---> UpscalingAgent")
    print("  ResearchAgent <---> PromptAgent")
    print("  All Agents   <---> UpscalingAgent\n")

    # Run initial cycle
    print("Running initial cycle...")
    for name, agent in agents.items():
        result = await agent.execute_cycle()
        print(f"  {name}: {result.get('status', 'done')}")

    print("\n" + "="*60)
    print("  ALL AGENTS RUNNING")
    print("  Press Ctrl+C to stop")
    print("="*60 + "\n")

    # Keep running
    try:
        while True:
            await asyncio.sleep(60)
            print("\n--- Cycle Report ---")
            for name, agent in agents.items():
                if hasattr(agent, 'last_trained'):
                    print(f"  {name}: {len(agent.last_trained)} models trained")
    except KeyboardInterrupt:
        print("\nStopping agents...")
        for name, agent in agents.items():
            await agent.stop()
        print("Done!")


async def run_single_agent(agent_type: str):
    """Run a single agent"""
    print(f"Starting {agent_type}...")

    coordinator = get_coordinator()

    if agent_type == "train":
        agent = TrainingAgent(tickers=["AAPL"])
    elif agent_type == "dev":
        agent = DevelopmentAgent()
    elif agent_type == "sec":
        agent = SecurityAgent()
    elif agent_type == "debug":
        agent = DebugAgent()
    elif agent_type == "scale":
        agent = UpscalingAgent()
    else:
        print(f"Unknown agent: {agent_type}")
        return

    coordinator.register_agent(agent_type, agent)
    await agent.start()

    # Run one cycle
    await agent.execute_cycle()

    print(f"\n{agent_type} completed one cycle")
    await agent.stop()


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"

    if mode == "all":
        asyncio.run(run_all_agents())
    else:
        asyncio.run(run_single_agent(mode))


if __name__ == "__main__":
    main()