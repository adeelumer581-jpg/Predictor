"""
Keep-alive pinger for Render free tier.
Render free services sleep after 15 minutes of inactivity.
This script pings the app every 10 minutes to keep it awake.
Run this separately or use UptimeRobot (free) to ping /api/status every 5 minutes.
"""
import os
import time
import threading
import urllib.request
import logging

logger = logging.getLogger("KeepAlive")

def ping_self():
    """Ping own health endpoint to prevent sleep on free hosting."""
    app_url = os.environ.get("RENDER_EXTERNAL_URL", "")
    if not app_url:
        return  # Not on Render, skip

    url = f"{app_url}/api/status"
    while True:
        try:
            with urllib.request.urlopen(url, timeout=10) as resp:
                logger.info(f"Keep-alive ping OK: {resp.status}")
        except Exception as e:
            logger.warning(f"Keep-alive ping failed: {e}")
        time.sleep(600)  # ping every 10 minutes


def start_keep_alive():
    """Start keep-alive thread (non-blocking)."""
    t = threading.Thread(target=ping_self, daemon=True)
    t.start()
    logger.info("Keep-alive thread started")
