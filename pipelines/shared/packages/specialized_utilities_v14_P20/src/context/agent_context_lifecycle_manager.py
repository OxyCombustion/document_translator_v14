#!/usr/bin/env python3
"""
Agent Context Lifecycle Manager
Handles automated agent context management, checkpoint/restart cycle for V9 system

Critical Features:
- Token threshold monitoring (80% warning, 95% critical)
- Automated context save before restart
- Agent restart with preserved context
- Background monitoring and proactive management
"""

import sys
import os
from pathlib import Path
import json
import time
import threading
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
import psutil

# UTF-8 encoding setup for Windows console
if sys.platform == 'win32':
    import io
    if not hasattr(sys.stdout, '_wrapped_utf8'):
        try:
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
            sys.stdout._wrapped_utf8 = True
        except (AttributeError, ValueError):
            import os
            os.system('chcp 65001')

# V14 imports (updated from v13 imports)
from pipelines.shared.packages.common.src.context.context_manager import ContextManager

class AgentContextLifecycleManager:
    """
    Manages agent context lifecycle with automated checkpoint/restart
    
    Key Responsibilities:
    1. Monitor token usage against thresholds
    2. Save agent context when approaching limits
    3. Gracefully restart agents with preserved context
    4. Maintain agent registry and process tracking
    """
    
    def __init__(self, config_file: str = "V8_AGENT_LIFECYCLE_CONFIG.json"):
        """Initialize the agent context lifecycle manager"""
        self.config_file = Path(config_file)
        self.config = self._load_config()
        self.context_manager = ContextManager()
        self.agent_registry = {}  # PID tracking for active agents
        self.checkpoint_storage = Path("agent_checkpoints")
        self.checkpoint_storage.mkdir(exist_ok=True)
        
        # Monitoring control
        self.is_monitoring = False
        self.monitor_thread = None
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
    def _load_config(self) -> Dict[str, Any]:
        """Load agent lifecycle configuration"""
        default_config = {
            "context_limits": {
                "session_management": 200000,
                "development": 200000, 
                "gui_development": 150000,
                "docling_first": 180000,
                "equation_extractor": 160000,
                "figure_extractor": 140000,
                "table_extractor": 160000,
                "default": 150000
            },
            "thresholds": {
                "warning": 0.8,   # 80% - start preparing for restart
                "critical": 0.95, # 95% - immediate restart required
                "emergency": 0.98 # 98% - force restart
            },
            "monitoring_interval": 30,  # seconds between checks
            "restart_timeout": 60,      # seconds to wait for restart
            "max_restart_attempts": 3,  # max restarts per agent
            "checkpoint_retention": 10  # keep last N checkpoints per agent
        }
        
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                    # Merge with defaults
                    for key, value in default_config.items():
                        if key not in loaded_config:
                            loaded_config[key] = value
                    return loaded_config
            else:
                # Create default config file
                with open(self.config_file, 'w', encoding='utf-8') as f:
                    json.dump(default_config, f, indent=2, ensure_ascii=False)
                return default_config
        except Exception as e:
            self.logger.error(f"Error loading config, using defaults: {e}")
            return default_config
    
    def register_agent(self, agent_name: str, agent_type: str, process_id: int, 
                      initial_tokens: int = 0) -> bool:
        """Register an agent for lifecycle management"""
        try:
            agent_info = {
                "name": agent_name,
                "type": agent_type,
                "pid": process_id,
                "tokens": initial_tokens,
                "last_checkpoint": None,
                "restart_count": 0,
                "registered_at": datetime.now().isoformat(),
                "last_activity": datetime.now().isoformat(),
                "status": "active"
            }
            
            self.agent_registry[agent_name] = agent_info
            self.logger.info(f"Registered agent: {agent_name} (PID: {process_id})")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to register agent {agent_name}: {e}")
            return False
    
    def update_agent_tokens(self, agent_name: str, token_count: int) -> None:
        """Update token count for an agent"""
        if agent_name in self.agent_registry:
            self.agent_registry[agent_name]["tokens"] = token_count
            self.agent_registry[agent_name]["last_activity"] = datetime.now().isoformat()
    
    def get_context_usage(self, agent_name: str) -> Tuple[float, str]:
        """Get context usage percentage and status for an agent"""
        if agent_name not in self.agent_registry:
            return 0.0, "unknown"
            
        agent_info = self.agent_registry[agent_name]
        agent_type = agent_info["type"]
        tokens = agent_info["tokens"]
        
        # Get context limit for this agent type
        limit = self.config["context_limits"].get(agent_type, 
                                                 self.config["context_limits"]["default"])
        
        usage_percentage = (tokens / limit) * 100
        
        # Determine status based on thresholds
        thresholds = self.config["thresholds"]
        if usage_percentage >= thresholds["emergency"] * 100:
            return usage_percentage, "emergency"
        elif usage_percentage >= thresholds["critical"] * 100:
            return usage_percentage, "critical"
        elif usage_percentage >= thresholds["warning"] * 100:
            return usage_percentage, "warning"
        else:
            return usage_percentage, "normal"
    
    def save_agent_checkpoint(self, agent_name: str) -> bool:
        """Save a checkpoint of agent's current context and state"""
        try:
            if agent_name not in self.agent_registry:
                self.logger.error(f"Agent {agent_name} not registered")
                return False
                
            agent_info = self.agent_registry[agent_name]
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Create checkpoint data
            checkpoint_data = {
                "agent_name": agent_name,
                "agent_type": agent_info["type"],
                "checkpoint_timestamp": timestamp,
                "tokens_at_checkpoint": agent_info["tokens"],
                "context_state": self._extract_agent_context(agent_name),
                "process_info": {
                    "pid": agent_info["pid"],
                    "restart_count": agent_info["restart_count"]
                },
                "session_data": self._get_agent_session_data(agent_name)
            }
            
            # Save checkpoint to file
            checkpoint_file = self.checkpoint_storage / f"{agent_name}_checkpoint_{timestamp}.json"
            with open(checkpoint_file, 'w', encoding='utf-8') as f:
                json.dump(checkpoint_data, f, indent=2, ensure_ascii=False)
            
            # Update agent registry
            self.agent_registry[agent_name]["last_checkpoint"] = str(checkpoint_file)
            
            self.logger.info(f"Checkpoint saved for {agent_name}: {checkpoint_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to save checkpoint for {agent_name}: {e}")
            return False
    
    def _extract_agent_context(self, agent_name: str) -> Dict[str, Any]:
        """Extract current context state from an agent"""
        # This would interface with the actual agent to get its context
        # For now, return a placeholder structure
        return {
            "conversation_history": f"Context for {agent_name}",
            "active_tasks": [],
            "learned_patterns": {},
            "processing_state": "idle",
            "memory_cache": {}
        }
    
    def _get_agent_session_data(self, agent_name: str) -> Dict[str, Any]:
        """Get session-specific data for an agent"""
        return {
            "session_start": self.agent_registry[agent_name]["registered_at"],
            "tasks_completed": 0,
            "processing_time": 0,
            "performance_metrics": {}
        }
    
    def restart_agent_with_context(self, agent_name: str) -> bool:
        """Restart an agent with preserved context from latest checkpoint"""
        try:
            if agent_name not in self.agent_registry:
                self.logger.error(f"Agent {agent_name} not registered")
                return False
            
            agent_info = self.agent_registry[agent_name]
            
            # Check restart limit
            if agent_info["restart_count"] >= self.config["max_restart_attempts"]:
                self.logger.error(f"Agent {agent_name} exceeded max restart attempts")
                return False
            
            self.logger.info(f"Restarting agent {agent_name} (attempt {agent_info['restart_count'] + 1})")
            
            # Step 1: Save current checkpoint
            checkpoint_saved = self.save_agent_checkpoint(agent_name)
            if not checkpoint_saved:
                self.logger.warning(f"Failed to save checkpoint for {agent_name}, proceeding anyway")
            
            # Step 2: Gracefully stop the agent
            self._stop_agent_gracefully(agent_name)
            
            # Step 3: Start new agent with preserved context
            new_pid = self._start_agent_with_context(agent_name)
            
            if new_pid:
                # Update registry with new process info
                self.agent_registry[agent_name].update({
                    "pid": new_pid,
                    "tokens": 0,  # Reset token count
                    "restart_count": agent_info["restart_count"] + 1,
                    "last_activity": datetime.now().isoformat(),
                    "status": "restarted"
                })
                
                self.logger.info(f"Successfully restarted {agent_name} with new PID: {new_pid}")
                return True
            else:
                self.logger.error(f"Failed to restart {agent_name}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error restarting agent {agent_name}: {e}")
            return False
    
    def _stop_agent_gracefully(self, agent_name: str) -> bool:
        """Gracefully stop an agent process"""
        try:
            agent_info = self.agent_registry[agent_name]
            pid = agent_info["pid"]
            
            # Check if process is still running
            if psutil.pid_exists(pid):
                proc = psutil.Process(pid)
                proc.terminate()  # Send SIGTERM
                
                # Wait for graceful shutdown
                try:
                    proc.wait(timeout=30)
                    self.logger.info(f"Agent {agent_name} stopped gracefully")
                    return True
                except psutil.TimeoutExpired:
                    # Force kill if not responding
                    proc.kill()
                    self.logger.warning(f"Agent {agent_name} force-killed after timeout")
                    return True
            else:
                self.logger.info(f"Agent {agent_name} process already terminated")
                return True
                
        except Exception as e:
            self.logger.error(f"Error stopping agent {agent_name}: {e}")
            return False
    
    def _start_agent_with_context(self, agent_name: str) -> Optional[int]:
        """Start a new agent instance with preserved context"""
        try:
            agent_info = self.agent_registry[agent_name]
            checkpoint_file = agent_info.get("last_checkpoint")
            
            # This would interface with the agent startup system
            # to launch a new instance with the preserved context
            
            # For now, return a mock PID
            # In real implementation, this would:
            # 1. Load the checkpoint data
            # 2. Initialize new agent with that context
            # 3. Return the new process ID
            
            self.logger.info(f"Starting new instance of {agent_name} with context from {checkpoint_file}")
            
            # Mock new PID for demonstration
            import random
            return random.randint(10000, 99999)
            
        except Exception as e:
            self.logger.error(f"Error starting agent {agent_name} with context: {e}")
            return None
    
    def start_monitoring(self) -> None:
        """Start background monitoring of agent contexts"""
        if self.is_monitoring:
            self.logger.info("Context monitoring already running")
            return
            
        self.is_monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        self.logger.info("Started context lifecycle monitoring")
    
    def stop_monitoring(self) -> None:
        """Stop background monitoring"""
        self.is_monitoring = False
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=5)
        self.logger.info("Stopped context lifecycle monitoring")
    
    def _monitor_loop(self) -> None:
        """Main monitoring loop that checks agent contexts"""
        while self.is_monitoring:
            try:
                for agent_name in list(self.agent_registry.keys()):
                    usage_percent, status = self.get_context_usage(agent_name)
                    
                    if status == "emergency":
                        self.logger.critical(f"EMERGENCY: {agent_name} at {usage_percent:.1f}% context usage - forcing restart")
                        self.restart_agent_with_context(agent_name)
                    elif status == "critical":
                        self.logger.warning(f"CRITICAL: {agent_name} at {usage_percent:.1f}% context usage - restarting")
                        self.restart_agent_with_context(agent_name)
                    elif status == "warning":
                        self.logger.info(f"WARNING: {agent_name} at {usage_percent:.1f}% context usage - creating checkpoint")
                        self.save_agent_checkpoint(agent_name)
                
                time.sleep(self.config["monitoring_interval"])
                
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                time.sleep(10)  # Brief pause before retrying
    
    def get_status_report(self) -> Dict[str, Any]:
        """Get comprehensive status report of all managed agents"""
        report = {
            "timestamp": datetime.now().isoformat(),
            "monitoring_active": self.is_monitoring,
            "total_agents": len(self.agent_registry),
            "agents": {}
        }
        
        for agent_name, agent_info in self.agent_registry.items():
            usage_percent, status = self.get_context_usage(agent_name)
            report["agents"][agent_name] = {
                "type": agent_info["type"],
                "pid": agent_info["pid"],
                "context_usage_percent": usage_percent,
                "status": status,
                "restart_count": agent_info["restart_count"],
                "last_checkpoint": agent_info.get("last_checkpoint"),
                "tokens": agent_info["tokens"]
            }
        
        return report

def main():
    """Test the agent context lifecycle manager"""
    print("🔄 Agent Context Lifecycle Manager Test")
    print("=" * 50)
    
    manager = AgentContextLifecycleManager()
    
    # Register some test agents
    manager.register_agent("DoclingFirstAgent", "docling_first", 12345, 150000)
    manager.register_agent("V8EquationExtractorAgent", "equation_extractor", 12346, 100000)
    
    # Update token counts to test thresholds
    manager.update_agent_tokens("DoclingFirstAgent", 171000)  # 95% of 180k limit
    manager.update_agent_tokens("V8EquationExtractorAgent", 128000)  # 80% of 160k limit
    
    # Get status report
    report = manager.get_status_report()
    print(json.dumps(report, indent=2))
    
    # Test monitoring (briefly)
    print("\n🔍 Starting monitoring for 10 seconds...")
    manager.start_monitoring()
    time.sleep(10)
    manager.stop_monitoring()
    
    print("\n✅ Agent Context Lifecycle Manager test complete")

if __name__ == "__main__":
    main()