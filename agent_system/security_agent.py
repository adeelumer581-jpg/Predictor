"""
Security Agent - Provides security monitoring and analysis
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
logger = logging.getLogger("SecurityAgent")

class SecurityAgent:
    def __init__(self):
        self.name = "SecurityAgent"
        self.is_active = False
        self.security_issues = []
        self.access_logs = []
        self.threats_detected = []
        self.last_scan = None
        self.coordinator = get_coordinator()

        # Security patterns to check
        self.dangerous_patterns = [
            "eval(", "exec(", "os.system(", "subprocess.call(",
            "pickle.load", "yaml.load", "input(",
            "os.environ", " secrets ", "password", "api_key"
        ]

    async def start(self):
        """Start the security agent"""
        self.is_active = True
        logger.info("SecurityAgent started")
        self.coordinator.register_agent(self.name, self)
        await self.perform_security_scan()

    async def stop(self):
        """Stop the security agent"""
        self.is_active = False
        logger.info("SecurityAgent stopped")

    async def receive_message(self, sender: str, message: Dict[str, Any]):
        """Receive messages from other agents"""
        msg_type = message.get("type")
        if msg_type == "code_change":
            # Check new code for security issues
            code = message.get("code", "")
            await self.analyze_code_security(code, message.get("file", "unknown"))
        elif msg_type == "security_alert":
            threat = message.get("threat")
            self.threats_detected.append({
                "threat": threat,
                "detected_at": datetime.now().isoformat(),
                "from_agent": sender
            })

    async def analyze_code_security(self, code: str, filename: str) -> Dict[str, Any]:
        """Analyze code for security vulnerabilities"""
        issues = []

        for pattern in self.dangerous_patterns:
            if pattern in code.lower():
                issues.append({
                    "pattern": pattern,
                    "severity": "high" if pattern in ["eval(", "exec(", "pickle.load"] else "medium",
                    "file": filename
                })

        if issues:
            logger.warning(f"Security issues found in {filename}: {len(issues)} issues")
            self.security_issues.extend(issues)

            # Alert other agents
            await self.coordinator.broadcast_message(self.name, {
                "type": "security_issue",
                "issues": issues,
                "file": filename
            })

        return {"file": filename, "issues": issues, "clean": len(issues) == 0}

    async def perform_security_scan(self) -> Dict[str, Any]:
        """Perform full security scan of codebase"""
        logger.info("Performing security scan...")
        project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        scan_results = []

        for root, _, filenames in os.walk(project_dir):
            for f in filenames:
                if f.endswith('.py') and not f.startswith('__'):
                    if f == "security_agent.py":
                        continue
                        
                    filepath = os.path.join(root, f)
                    try:
                        with open(filepath, 'r', encoding='utf-8') as file:
                            content = file.read()
                            result = await self.analyze_code_security(content, f)
                            scan_results.append(result)
                    except:
                        pass

        self.last_scan = datetime.now().isoformat()

        clean_files = sum(1 for r in scan_results if r.get("clean", False))
        issues_found = sum(len(r.get("issues", [])) for r in scan_results)

        logger.info(f"Security scan complete: {clean_files} clean, {issues_found} issues found")

        return {
            "total_files": len(scan_results),
            "clean_files": clean_files,
            "issues_found": issues_found,
            "scan_time": self.last_scan
        }

    async def execute_cycle(self) -> Dict[str, Any]:
        """Execute security cycle"""
        if not self.is_active:
            return {"status": "inactive"}

        logger.info("SecurityAgent: Running security cycle...")

        # Perform periodic security scan
        scan_result = await self.perform_security_scan()

        # Check for threats
        active_threats = len(self.threats_detected)

        return {
            "status": "completed",
            "scan_result": scan_result,
            "active_threats": active_threats,
            "total_issues": len(self.security_issues),
            "timestamp": datetime.now().isoformat()
        }

    def get_security_status(self) -> Dict[str, Any]:
        """Get current security status"""
        return {
            "agent": self.name,
            "is_active": self.is_active,
            "last_scan": self.last_scan,
            "total_issues": len(self.security_issues),
            "active_threats": len(self.threats_detected),
            "recent_issues": self.security_issues[-10:] if self.security_issues else []
        }