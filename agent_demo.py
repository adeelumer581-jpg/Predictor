"""
Quick demo launcher - runs agent system for 2 minutes then exits
"""
import sys
import asyncio
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agent_system.agent_coordinator import get_coordinator
from agent_system.training_agent import TrainingAgent
from agent_system.development_agent import DevelopmentAgent
from agent_system.security_agent import SecurityAgent
from agent_system.debug_agent import DebugAgent
from agent_system.upscaling_agent import UpscalingAgent
from agent_system.antigravity_agent import AntiGravityAgent


async def demo():
    print("\n" + "="*60)
    print("  STOCK PREDICTOR - MULTI-AGENT SYSTEM")
    print("="*60)

    coordinator = get_coordinator()

    # Create all 6 agents including AntiGravityAgent
    training_agent = TrainingAgent(tickers=["AAPL"])
    development_agent = DevelopmentAgent()
    security_agent = SecurityAgent()
    debug_agent = DebugAgent()
    upscaling_agent = UpscalingAgent()
    antigravity_agent = AntiGravityAgent()

    agents = {
        "TrainingAgent": training_agent,
        "DevelopmentAgent": development_agent,
        "SecurityAgent": security_agent,
        "DebugAgent": debug_agent,
        "UpscalingAgent": upscaling_agent,
        "AntiGravityAgent": antigravity_agent
    }

    print("\nAgents Initialized:")
    print("  [1] TrainingAgent      - Trains predictor every 60s")
    print("  [2] DevelopmentAgent  - Daily code development")
    print("  [3] SecurityAgent     - Security scanning")
    print("  [4] DebugAgent        - Diagnostics & debugging")
    print("  [5] UpscalingAgent    - Resource management")
    print("  [6] AntiGravityAgent   - Optimization & efficiency")
    print()

    # Register and start
    for name, agent in agents.items():
        coordinator.register_agent(name, agent)
        await agent.start()

    print("All agents connected and running!\n")

    # Run 2 cycles (about 2 minutes)
    for cycle in range(2):
        print(f"--- Cycle {cycle + 1} ---")

        # Training
        result = await training_agent.execute_cycle()
        print(f"  Training: {result['successful']} models trained")

        # Development
        result = await development_agent.execute_cycle()
        print(f"  Development: {result.get('codebase_files', 0)} files analyzed")

        # Security
        result = await security_agent.execute_cycle()
        print(f"  Security: {result['scan_result']['issues_found']} issues found")

        # Debug
        result = await debug_agent.execute_cycle()
        print(f"  Debug: {result['total_bugs']} bugs tracked")

        # Upscaling
        result = await upscaling_agent.execute_cycle()
        print(f"  Upscaling: CPU {result['resources']['cpu_percent']:.1f}%")

        # Anti-Gravity (Optimization)
        result = await antigravity_agent.execute_cycle()
        print(f"  Anti-Gravity: {result['optimizations_applied']} optimizations applied")

        print()
        await asyncio.sleep(60)

    # Stop all
    print("Stopping agents...")
    for name, agent in agents.items():
        await agent.stop()

    print("\n" + "="*60)
    print("  AGENT SYSTEM DEMO COMPLETE")
    print("="*60)

    # Show results
    print("\nFinal Status:")
    print(f"  - Models trained: {len(training_agent.last_trained)}")
    print(f"  - Security issues: {len(security_agent.security_issues)}")
    print(f"  - Bugs found: {len(debug_agent.bugs_found)}")
    print(f"  - Scaling decisions: {len(upscaling_agent.scaling_decisions)}")
    print(f"  - Optimizations: {len(antigravity_agent.improvements_history)}")


if __name__ == "__main__":
    asyncio.run(demo())