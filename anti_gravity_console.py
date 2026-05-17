"""
Anti-Gravity Real-Time Console
===============================
Interactive console to communicate with the Anti-Gravity Agent
in real-time. Prompts are automated and the system continuously
optimizes itself toward perfection.
"""
import asyncio
import sys
import os
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agent_system.agent_coordinator import get_coordinator
from agent_system.training_agent import TrainingAgent
from agent_system.development_agent import DevelopmentAgent
from agent_system.security_agent import SecurityAgent
from agent_system.debug_agent import DebugAgent
from agent_system.upscaling_agent import UpscalingAgent
from agent_system.antigravity_agent import AntiGravityAgent


class RealTimeConsole:
    """Real-time interaction with Anti-Gravity Agent"""

    def __init__(self):
        self.coordinator = get_coordinator()
        self.agents = {}
        self.antigravity = None
        self.running = False

        # Pre-defined automated prompts
        self.auto_prompts = [
            "optimize training speed",
            "check performance",
            "fix memory issues",
            "improve accuracy",
            "full system check",
            "add more tickers",
            "create backup",
            "verify integrity"
        ]

    async def initialize(self):
        """Initialize all agents"""
        print("\n" + "="*60)
        print("  ANTI-GRAVITY CONSOLE - GOOGLE LEVEL AUTOMATION")
        print("="*60)
        print("\n[1/6] Initializing Training Agent...")
        training_agent = TrainingAgent(tickers=["AAPL", "MSFT", "NVDA", "GOOGL"])
        self.agents["TrainingAgent"] = training_agent
        self.coordinator.register_agent("TrainingAgent", training_agent)
        await training_agent.start()

        print("[2/6] Initializing Development Agent...")
        dev_agent = DevelopmentAgent()
        self.agents["DevelopmentAgent"] = dev_agent
        self.coordinator.register_agent("DevelopmentAgent", dev_agent)
        await dev_agent.start()

        print("[3/6] Initializing Security Agent...")
        sec_agent = SecurityAgent()
        self.agents["SecurityAgent"] = sec_agent
        self.coordinator.register_agent("SecurityAgent", sec_agent)
        await sec_agent.start()

        print("[4/6] Initializing Debug Agent...")
        debug_agent = DebugAgent()
        self.agents["DebugAgent"] = debug_agent
        self.coordinator.register_agent("DebugAgent", debug_agent)
        await debug_agent.start()

        print("[5/6] Initializing Upscaling Agent...")
        scale_agent = UpscalingAgent()
        self.agents["UpscalingAgent"] = scale_agent
        self.coordinator.register_agent("UpscalingAgent", scale_agent)
        await scale_agent.start()

        print("[6/6] Initializing Anti-Gravity Agent...")
        self.antigravity = AntiGravityAgent()
        self.agents["AntiGravityAgent"] = self.antigravity
        self.coordinator.register_agent("AntiGravityAgent", self.antigravity)
        await self.antigravity.start()

        print("\n" + "="*60)
        print("  ALL SYSTEMS INITIALIZED & OPTIMIZED")
        print("="*60 + "\n")

    async def run_automated_cycle(self):
        """Run one automated optimization cycle"""
        print("\n" + "-"*50)
        print("AUTOMATED CYCLE STARTING...")
        print("-"*50)

        # 1. Train all models
        print("\n[STEP 1] Training Models...")
        training_result = await self.agents["TrainingAgent"].execute_cycle()
        print(f"  -> Trained: {training_result['successful']} models")

        # 2. Development check
        print("\n[STEP 2] Code Analysis...")
        dev_result = await self.agents["DevelopmentAgent"].execute_cycle()
        print(f"  -> Files analyzed: {dev_result.get('codebase_files', 0)}")

        # 3. Security scan
        print("\n[STEP 3] Security Scan...")
        sec_result = await self.agents["SecurityAgent"].execute_cycle()
        print(f"  -> Issues: {sec_result['scan_result']['issues_found']}")

        # 4. Debug check
        print("\n[STEP 4] Diagnostics...")
        debug_result = await self.agents["DebugAgent"].execute_cycle()
        print(f"  -> Bugs: {debug_result['total_bugs']}")

        # 5. Upscaling check
        print("\n[STEP 5] Resource Check...")
        scale_result = await self.agents["UpscalingAgent"].execute_cycle()
        print(f"  -> CPU: {scale_result['resources']['cpu_percent']:.1f}%")
        print(f"  -> Memory: {scale_result['resources']['memory_percent']:.1f}%")

        # 6. Anti-Gravity optimization (THE MAGIC)
        print("\n[STEP 6] Anti-Gravity Optimization...")
        opt_result = await self.antigravity.execute_cycle()
        print(f"  -> Status: {opt_result['status']}")
        print(f"  -> Optimizations: {opt_result['optimizations']}")
        if opt_result.get('target_status'):
            for k, v in opt_result['target_status'].items():
                print(f"    * {k}: {'OK' if v else 'FAIL'}")

        print("\n" + "-"*50)
        print(f"CYCLE COMPLETE - {datetime.now().strftime('%H:%M:%S')}")
        print("-"*50)

    async def run_continuous(self, cycles: int = 3, delay: int = 30):
        """Run continuous automated cycles"""
        self.running = True

        for i in range(cycles):
            if not self.running:
                break

            print(f"\n{'='*60}")
            print(f"CYCLE {i+1}/{cycles} - {datetime.now().strftime('%H:%M:%S')}")
            print(f"{'='*60}")

            await self.run_automated_cycle()

            if i < cycles - 1:
                print(f"\n[WAITING] {delay}s before next cycle...")
                await asyncio.sleep(delay)

    async def interactive_mode(self):
        """Interactive mode - user prompts the agent"""
        print("\n" + "="*60)
        print("  INTERACTIVE MODE - TYPE 'help' FOR COMMANDS")
        print("="*60)

        commands = {
            "help": "Show available commands",
            "status": "Show system status",
            "optimize": "Run full optimization",
            "train": "Train all models",
            "check": "Run diagnostics",
            "add TICKER": "Add new ticker to train",
            "targets": "Show optimization targets",
            "metrics": "Show performance metrics",
            "quit": "Exit",
            "auto": "Run automated cycles"
        }

        while True:
            try:
                user_input = input("\n>>> ").strip().lower()

                if user_input == "help":
                    print("\nAvailable Commands:")
                    for cmd, desc in commands.items():
                        print(f"  {cmd:15} - {desc}")

                elif user_input == "status":
                    await self._show_status()

                elif user_input == "optimize":
                    result = await self.antigravity.execute_cycle()
                    print(f"Optimization complete: {result['optimizations']} applied")

                elif user_input == "train":
                    result = await self.agents["TrainingAgent"].execute_cycle()
                    print(f"Trained {result['successful']} models")

                elif user_input == "check":
                    result = await self.agents["DebugAgent"].execute_cycle()
                    print(f"Diagnostics: {result['total_bugs']} issues found")

                elif user_input.startswith("add "):
                    ticker = user_input.split()[1].upper()
                    training = self.agents["TrainingAgent"]
                    if ticker not in training.tickers:
                        training.tickers.append(ticker)
                        print(f"Added {ticker} to training list")

                elif user_input == "targets":
                    print("\nOptimization Targets:")
                    for k, v in self.antigravity.targets.items():
                        print(f"  {k}: {v}")

                elif user_input == "metrics":
                    metrics = await self.antigravity._get_current_metrics()
                    print("\nCurrent Metrics:")
                    for k, v in metrics.items():
                        print(f"  {k}: {v}")

                elif user_input == "auto":
                    await self.run_continuous(cycles=2, delay=10)

                elif user_input == "quit":
                    print("Shutting down...")
                    break

                else:
                    print(f"Unknown command: {user_input}")
                    print("Type 'help' for available commands")

            except KeyboardInterrupt:
                print("\nExiting...")
                break
            except Exception as e:
                print(f"Error: {e}")

        await self.shutdown()

    async def _show_status(self):
        """Show system status"""
        print("\n" + "="*50)
        print("SYSTEM STATUS")
        print("="*50)

        # Anti-Gravity status
        report = self.antigravity.get_optimization_report()
        print(f"\nAnti-Gravity Agent:")
        print(f"  Active: {report['is_active']}")
        print(f"  Optimizations: {report['current_metrics']['optimizations_applied']}")
        print(f"  Learned patterns: {report['current_metrics']['learned_patterns']}")

        # Training agent
        training = self.agents["TrainingAgent"]
        print(f"\nTraining Agent:")
        print(f"  Tickers: {training.tickers}")
        print(f"  Models trained: {len(training.last_trained)}")

    async def shutdown(self):
        """Shutdown all agents"""
        print("\nShutting down agents...")
        for name, agent in self.agents.items():
            await agent.stop()
        print("Done!")


async def main():
    console = RealTimeConsole()
    await console.initialize()

    # Auto-run 3 cycles then enter interactive
    await console.run_continuous(cycles=3, delay=15)

    # Then enter interactive mode
    await console.interactive_mode()


if __name__ == "__main__":
    asyncio.run(main())