import time
import schedule
import os
from datetime import datetime
from boss_agent import BossAgent
from worker_agent import WorkerAgent

# Configuration
WORKER_SCAN_INTERVAL_MINUTES = 5
BOSS_MEETING_TIME = "08:00"  # 24h format for daily morning update

boss = BossAgent()
worker = WorkerAgent()

def daily_boss_meeting():
    """Runs the boss agent to get new orders."""
    print("\n" + "#"*60)
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] INITIATING DAILY BOSS MEETING")
    print("#"*60)
    
    orders = boss.issue_daily_orders(num_assets=5)
    worker.receive_orders(orders)
    
    # Run an immediate scan after receiving new orders
    worker_scan()

def worker_scan():
    """Runs the worker agent scan."""
    worker.execute_scan()

def main():
    # 1. Clear terminal
    os.system('cls' if os.name == 'nt' else 'clear')
    print("Starting Multi-Agent Stock Predictor Agency...")
    
    # 2. Schedule the Boss to run daily
    schedule.every().day.at(BOSS_MEETING_TIME).do(daily_boss_meeting)
    
    # 3. Schedule the Worker to scan the assigned assets every N minutes
    schedule.every(WORKER_SCAN_INTERVAL_MINUTES).minutes.do(worker_scan)
    
    # 4. Immediate execution on startup so we don't wait until 08:00 tomorrow
    daily_boss_meeting()
    
    # 5. Main Loop
    print("\nAgency is now running in autonomous mode.")
    print(f"- Boss will update orders daily at {BOSS_MEETING_TIME}.")
    print(f"- Workers will scan market every {WORKER_SCAN_INTERVAL_MINUTES} minutes.")
    print("Press Ctrl+C to stop.")
    
    try:
        while True:
            schedule.run_pending()
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nAgency operations terminated by user. Goodbye!")

if __name__ == "__main__":
    main()
