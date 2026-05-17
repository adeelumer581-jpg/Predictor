"""
Upscaling Agent - Scales up the predictor system
"""
import asyncio
import logging
import os
import sys
import psutil
from datetime import datetime
from typing import Dict, Any, List

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agent_system.agent_coordinator import get_coordinator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("UpscalingAgent")

class UpscalingAgent:
    def __init__(self):
        self.name = "UpscalingAgent"
        self.is_active = False
        self.scaling_decisions = []
        self.resource_usage = {}
        self.performance_metrics = {}
        self.last_scale_action = None
        self.coordinator = get_coordinator()

        # Thresholds for scaling
        self.cpu_threshold = 80  # percent
        self.memory_threshold = 85  # percent
        self.auto_scale_enabled = True

    async def start(self):
        """Start the upscaling agent"""
        self.is_active = True
        logger.info("UpscalingAgent started")
        self.coordinator.register_agent(self.name, self)
        await self.assess_current_capacity()

    async def stop(self):
        """Stop the upscaling agent"""
        self.is_active = False
        logger.info("UpscalingAgent stopped")

    async def receive_message(self, sender: str, message: Dict[str, Any]):
        """Receive messages from other agents"""
        msg_type = message.get("type")
        if msg_type == "training_complete":
            # Record training performance
            result = message.get("result", {})
            self.record_performance(sender, result)
        elif msg_type == "scaling_request":
            action = message.get("action")
            await self.perform_scaling(action)
        elif msg_type == "resource_alert":
            # Handle resource alerts from other agents
            await self.handle_resource_alert(message)

    async def assess_current_capacity(self) -> Dict[str, Any]:
        """Assess current system capacity"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')

            self.resource_usage = {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_available_gb": memory.available / (1024**3),
                "disk_percent": disk.percent,
                "timestamp": datetime.now().isoformat()
            }

            logger.info(f"Resource usage: CPU {cpu_percent}%, Memory {memory.percent}%")

            return self.resource_usage

        except Exception as e:
            logger.warning(f"Could not get system resources: {e}")
            return {"error": str(e)}

    async def check_scaling_needs(self) -> Dict[str, Any]:
        """Check if scaling is needed based on current resources"""
        await self.assess_current_capacity()

        scaling_needed = []
        recommendations = []

        cpu = self.resource_usage.get("cpu_percent", 0)
        memory = self.resource_usage.get("memory_percent", 0)

        if cpu > self.cpu_threshold:
            scaling_needed.append("cpu_high")
            recommendations.append("Consider reducing training frequency or batch size")

        if memory > self.memory_threshold:
            scaling_needed.append("memory_high")
            recommendations.append("Clear unused models or reduce data cache")

        # Check if we can scale up (more tickers)
        if cpu < 20 and memory < 50:
            scaling_needed.append("capacity_available")
            recommendations.append("System has capacity for more tickers. Dynamically upscaling.")
            
            # Send scaling request directly
            await self.perform_scaling("add_ticker")

        return {
            "scaling_needed": len(scaling_needed) > 0,
            "reasons": scaling_needed,
            "recommendations": recommendations,
            "current_resources": self.resource_usage
        }

    async def perform_scaling(self, action: str) -> Dict[str, Any]:
        """Perform a scaling action"""
        logger.info(f"Performing scaling action: {action}")

        scale_result = {
            "action": action,
            "timestamp": datetime.now().isoformat(),
            "success": True
        }

        if action == "add_ticker":
            scale_result["message"] = "Request to add new ticker forwarded to Training Agent"
            # Notify training agent
            await self.coordinator.broadcast_message(self.name, {
                "type": "add_ticker",
                "ticker": "NEW_TICKER"  # Placeholder
            })

        elif action == "increase_training_frequency":
            scale_result["message"] = "Increasing training frequency"
            await self.coordinator.broadcast_message(self.name, {
                "type": "update_interval",
                "interval": 30  # 30 seconds
            })

        elif action == "optimize_resources":
            scale_result["message"] = "Optimizing resource usage"
            # Would implement memory optimization here

        self.last_scale_action = scale_result
        self.scaling_decisions.append(scale_result)

        return scale_result

    async def handle_resource_alert(self, message: Dict[str, Any]):
        """Handle resource alerts from other agents"""
        resource = message.get("resource")
        value = message.get("value")

        logger.warning(f"Resource alert: {resource} at {value}%")

        # Auto-scaling response
        if self.auto_scale_enabled:
            if resource == "cpu" and value > self.cpu_threshold:
                await self.coordinator.broadcast_message(self.name, {
                    "type": "scaling_request",
                    "action": "optimize_resources"
                })

    def record_performance(self, agent: str, result: Dict[str, Any]):
        """Record performance metrics"""
        self.performance_metrics[agent] = {
            "last_result": result,
            "recorded_at": datetime.now().isoformat()
        }

    async def get_performance_report(self) -> Dict[str, Any]:
        """Get performance report"""
        return {
            "resource_usage": self.resource_usage,
            "scaling_decisions": len(self.scaling_decisions),
            "performance_metrics": self.performance_metrics,
            "auto_scale_enabled": self.auto_scale_enabled
        }

    async def execute_cycle(self) -> Dict[str, Any]:
        """Execute upscaling cycle"""
        if not self.is_active:
            return {"status": "inactive"}

        logger.info("UpscalingAgent: Running upscaling cycle...")

        # Check current capacity
        capacity = await self.check_scaling_needs()

        # Assess resources
        resources = await self.assess_current_capacity()

        return {
            "status": "completed",
            "scaling_needed": capacity.get("scaling_needed", False),
            "reasons": capacity.get("reasons", []),
            "recommendations": capacity.get("recommendations", []),
            "resources": resources,
            "timestamp": datetime.now().isoformat()
        }

    def enable_auto_scaling(self):
        """Enable auto-scaling"""
        self.auto_scale_enabled = True
        logger.info("Auto-scaling enabled")

    def disable_auto_scaling(self):
        """Disable auto-scaling"""
        self.auto_scale_enabled = False
        logger.info("Auto-scaling disabled")

    def get_upscaling_status(self) -> Dict[str, Any]:
        """Get upscaling status"""
        return {
            "agent": self.name,
            "is_active": self.is_active,
            "auto_scale_enabled": self.auto_scale_enabled,
            "last_scale_action": self.last_scale_action,
            "total_scaling_decisions": len(self.scaling_decisions),
            "resource_usage": self.resource_usage
        }