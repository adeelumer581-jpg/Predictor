"""
Debug Agent - Debugs and diagnoses the predictor
"""
import asyncio
import logging
import os
import sys
import traceback
from datetime import datetime
from typing import Dict, Any, List

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agent_system.agent_coordinator import get_coordinator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("DebugAgent")

class DebugAgent:
    def __init__(self):
        self.name = "DebugAgent"
        self.is_active = False
        self.bugs_found = []
        self.diagnostics = []
        self.error_history = []
        self.last_diagnosis = None
        self.coordinator = get_coordinator()

    async def start(self):
        """Start the debug agent"""
        self.is_active = True
        logger.info("DebugAgent started")
        self.coordinator.register_agent(self.name, self)
        
        # Hook into system exceptions to catch actual crashes
        self._original_excepthook = sys.excepthook
        sys.excepthook = self._custom_excepthook
        
        await self.run_diagnostics()

    def _custom_excepthook(self, exc_type, exc_value, exc_traceback):
        """Catches unhandled exceptions globally and logs them as bugs"""
        tb_str = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        logger.error(f"[SYSTEM CRASH DETECTED]\n{tb_str}")
        
        self.bugs_found.append({
            "source": "sys.excepthook",
            "error": str(exc_value),
            "traceback": tb_str,
            "timestamp": datetime.now().isoformat(),
            "severity": "critical"
        })
        
        # Call the original excepthook to maintain standard behavior
        self._original_excepthook(exc_type, exc_value, exc_traceback)

    async def stop(self):
        """Stop the debug agent"""
        self.is_active = False
        logger.info("DebugAgent stopped")

    async def receive_message(self, sender: str, message: Dict[str, Any]):
        """Receive messages from other agents"""
        msg_type = message.get("type")
        if msg_type == "error":
            error_info = message.get("error")
            await self.analyze_error(error_info, sender)
        elif msg_type == "training_complete":
            # Check training results for issues
            result = message.get("result", {})
            await self.check_model_health(result)
        elif msg_type == "debug_request":
            target = message.get("target")
            await self.debug_component(target)

    async def analyze_error(self, error: Dict[str, Any], source: str):
        """Analyze an error and find root cause"""
        logger.info(f"Analyzing error from {source}: {error.get('message', 'Unknown')}")

        bug_report = {
            "source": source,
            "error": error.get("message", "Unknown"),
            "timestamp": datetime.now().isoformat(),
            "severity": error.get("severity", "medium")
        }

        # Try to diagnose the issue
        diagnosis = await self.diagnose_issue(error)
        bug_report["diagnosis"] = diagnosis

        self.bugs_found.append(bug_report)

        # Suggest fix to development agent
        await self.coordinator.broadcast_message(self.name, {
            "type": "bug_fix_request",
            "description": diagnosis.get("suggestion", "Unknown issue"),
            "bug": bug_report
        })

    async def diagnose_issue(self, error: Dict[str, Any]) -> Dict[str, Any]:
        """Diagnose the root cause of an issue"""
        error_msg = error.get("message", "").lower()

        # Common issue patterns
        if "connection" in error_msg or "network" in error_msg:
            return {
                "type": "network",
                "cause": "Network connectivity issue",
                "suggestion": "Check internet connection and API endpoints"
            }
        elif "memory" in error_msg or "out of memory" in error_msg:
            return {
                "type": "resource",
                "cause": "Memory exhaustion",
                "suggestion": "Reduce data batch size or add memory management"
            }
        elif "model" in error_msg or "predict" in error_msg:
            return {
                "type": "model",
                "cause": "Model loading or prediction error",
                "suggestion": "Retrain model or check model file integrity"
            }
        elif "data" in error_msg or "empty" in error_msg:
            return {
                "type": "data",
                "cause": "Data issue",
                "suggestion": "Check data source and data preprocessing"
            }
        else:
            return {
                "type": "unknown",
                "cause": "Unknown error",
                "suggestion": "Review error logs for details"
            }

    async def check_model_health(self, result: Dict[str, Any]):
        """Check if trained model is healthy"""
        ticker = result.get("ticker", "unknown")

        # Check for low accuracy
        # In real implementation, would parse actual metrics
        health_status = {
            "ticker": ticker,
            "checked_at": datetime.now().isoformat(),
            "status": "healthy"
        }

        # If training failed
        if result.get("status") == "failed":
            health_status["status"] = "unhealthy"
            health_status["issue"] = "Training failed"

            await self.coordinator.broadcast_message(self.name, {
                "type": "error",
                "error": {
                    "message": f"Training failed for {ticker}",
                    "severity": "high"
                }
            })

        self.diagnostics.append(health_status)
        logger.info(f"Model health check for {ticker}: {health_status['status']}")

    async def run_diagnostics(self) -> Dict[str, Any]:
        """Run full system diagnostics"""
        logger.info("Running system diagnostics...")

        diagnostics = {
            "timestamp": datetime.now().isoformat(),
            "checks": []
        }

        # Check model files
        project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        model_files = ["AAPL_model.pkl", "MSFT_model.pkl", "NVDA_model.pkl", "GOOGL_model.pkl"]

        for model in model_files:
            model_path = os.path.join(project_dir, model)
            exists = os.path.exists(model_path)
            diagnostics["checks"].append({
                "check": f"model_{model}",
                "status": "ok" if exists else "missing",
                "path": model_path
            })

        # Check data files
        data_files = ["requirements.txt"]
        for data in data_files:
            data_path = os.path.join(project_dir, data)
            exists = os.path.exists(data_path)
            diagnostics["checks"].append({
                "check": f"file_{data}",
                "status": "ok" if exists else "missing",
                "path": data_path
            })

        self.last_diagnosis = diagnostics
        logger.info(f"Diagnostics complete: {len(diagnostics['checks'])} checks performed")

        return diagnostics

    async def debug_component(self, target: str):
        """Debug a specific component"""
        logger.info(f"Debugging component: {target}")

        debug_result = {
            "target": target,
            "timestamp": datetime.now().isoformat(),
            "findings": []
        }

        # Add findings based on target
        if "training" in target.lower():
            debug_result["findings"].append({
                "issue": "Check training data quality",
                "recommendation": "Ensure sufficient historical data"
            })
        elif "model" in target.lower():
            debug_result["findings"].append({
                "issue": "Verify model parameters",
                "recommendation": "Review model hyperparameters"
            })

        await self.coordinator.broadcast_message(self.name, {
            "type": "diagnostic_result",
            "result": debug_result
        })

    async def execute_cycle(self) -> Dict[str, Any]:
        """Execute debug cycle"""
        if not self.is_active:
            return {"status": "inactive"}

        logger.info("DebugAgent: Running debug cycle...")

        # Run diagnostics
        diag = await self.run_diagnostics()

        # Check recent bugs
        recent_bugs = len([b for b in self.bugs_found
            if (datetime.now() - datetime.fromisoformat(b["timestamp"])).total_seconds() < 3600])

        return {
            "status": "completed",
            "diagnostics": diag,
            "recent_bugs": recent_bugs,
            "total_bugs": len(self.bugs_found),
            "timestamp": datetime.now().isoformat()
        }

    def get_debug_status(self) -> Dict[str, Any]:
        """Get debug status"""
        return {
            "agent": self.name,
            "is_active": self.is_active,
            "last_diagnosis": self.last_diagnosis,
            "total_bugs": len(self.bugs_found),
            "recent_errors": len(self.error_history)
        }