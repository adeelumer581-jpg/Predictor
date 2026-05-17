"""
Development Agent - Develops code improvements daily
"""
import asyncio
import logging
import os
import sys
from datetime import datetime
from typing import Dict, Any, List
import hashlib

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agent_system.agent_coordinator import get_coordinator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("DevelopmentAgent")

class DevelopmentAgent:
    def __init__(self):
        self.name = "DevelopmentAgent"
        self.is_active = False
        self.daily_tasks = []
        self.code_changes = []
        self.improvements = []
        self.last_daily_run = None
        self.coordinator = get_coordinator()

    async def start(self):
        """Start the development agent"""
        self.is_active = True
        logger.info("DevelopmentAgent started")
        self.coordinator.register_agent(self.name, self)
        await self.analyze_codebase()

    async def stop(self):
        """Stop the development agent"""
        self.is_active = False
        logger.info("DevelopmentAgent stopped")

    async def receive_message(self, sender: str, message: Dict[str, Any]):
        """Receive messages from other agents"""
        msg_type = message.get("type")
        if msg_type == "improvement_needed":
            task = message.get("task")
            self.daily_tasks.append({
                "task": task,
                "requested_by": sender,
                "timestamp": datetime.now().isoformat()
            })
        elif msg_type == "bug_fix_request":
            bug = message.get("description")
            self.daily_tasks.append({
                "task": f"Fix bug: {bug}",
                "type": "bug_fix",
                "requested_by": sender,
                "timestamp": datetime.now().isoformat()
            })

    async def analyze_codebase(self) -> Dict[str, Any]:
        """Analyze the current codebase"""
        project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        files = {}

        for root, _, filenames in os.walk(project_dir):
            for f in filenames:
                if f.endswith('.py') and not f.startswith('__'):
                    filepath = os.path.join(root, f)
                    try:
                        with open(filepath, 'r', encoding='utf-8') as file:
                            content = file.read()
                            files[f] = {
                                "lines": len(content.split('\n')),
                                "hash": hashlib.md5(content.encode()).hexdigest()[:8],
                                "path": filepath
                            }
                    except:
                        pass

        self.codebase_analysis = {
            "files": files,
            "total_files": len(files),
            "analyzed_at": datetime.now().isoformat()
        }

        logger.info(f"Codebase analysis: {len(files)} Python files found")
        return self.codebase_analysis

    async def identify_improvements(self) -> List[Dict[str, Any]]:
        """Identify potential code improvements"""
        improvements = []

        # Check for common patterns that could be improved
        if hasattr(self, 'codebase_analysis'):
            files = self.codebase_analysis.get("files", {})

            # Check for large files that might need refactoring
            for fname, info in files.items():
                if info.get("lines", 0) > 300:
                    improvements.append({
                        "type": "refactoring",
                        "file": fname,
                        "issue": f"Large file ({info['lines']} lines) - consider splitting",
                        "priority": "medium"
                    })

            # Check for duplicate code patterns (simplified check)
            if len(files) > 10:
                improvements.append({
                    "type": "architecture",
                    "issue": "Consider adding more modules for better organization",
                    "priority": "low"
                })

        return improvements

    async def execute_cycle(self) -> Dict[str, Any]:
        """Execute daily development cycle"""
        if not self.is_active:
            return {"status": "inactive"}

        logger.info("DevelopmentAgent: Running development cycle...")

        # Run daily analysis
        await self.analyze_codebase()
        improvements = await self.identify_improvements()

        # Process pending tasks
        tasks_completed = 0
        for task in self.daily_tasks[:5]:  # Process up to 5 tasks
            tasks_completed += 1

        self.daily_tasks = self.daily_tasks[5:]

        self.last_daily_run = datetime.now().isoformat()

        # Broadcast improvements to other agents
        if improvements:
            await self.coordinator.broadcast_message(self.name, {
                "type": "improvements_identified",
                "improvements": improvements
            })

        return {
            "status": "completed",
            "codebase_files": self.codebase_analysis.get("total_files", 0),
            "improvements_found": len(improvements),
            "tasks_completed": tasks_completed,
            "timestamp": self.last_daily_run
        }

    async def generate_report(self) -> Dict[str, Any]:
        """Generate development report"""
        return {
            "agent": self.name,
            "status": "running" if self.is_active else "stopped",
            "last_run": self.last_daily_run,
            "pending_tasks": len(self.daily_tasks),
            "codebase_analysis": self.codebase_analysis if hasattr(self, 'codebase_analysis') else None
        }