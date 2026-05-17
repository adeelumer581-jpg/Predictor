"""
Auto-Gravity Launcher
======================
Launches the fully automated Google-level optimization system.
Everything runs automatically - no manual intervention needed.
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from anti_gravity_console import RealTimeConsole


async def main():
    console = RealTimeConsole()
    await console.initialize()

    # Run continuous automated optimization
    print("\n" + "="*60)
    print("  STARTING CONTINUOUS AUTOMATED OPTIMIZATION")
    print("  Press Ctrl+C to stop")
    print("="*60 + "\n")

    await console.run_continuous(cycles=999, delay=60)  # Infinite


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nSystem stopped by user.")
        print("Optimization history saved.")