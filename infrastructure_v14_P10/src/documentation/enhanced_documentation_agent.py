"""
Enhanced Documentation Agent with Real-Time Monitoring Integration
Combines context-aware documentation with live development activity capture
"""

import json
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

from .context_aware_documentation_agent import ContextAwareDocumentationAgent, DocumentationTask
from .real_time_monitor import RealTimeMonitor, DevelopmentEvent, create_real_time_monitor
from ...core.logger import get_logger

logger = get_logger("EnhancedDocumentationAgent")


class EnhancedDocumentationAgent:
    """Documentation agent with real-time monitoring capabilities"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.project_root = Path(config.get("project_root", "."))
        
        # Initialize base documentation agent
        self.doc_agent = ContextAwareDocumentationAgent(config)
        
        # Initialize real-time monitor
        self.monitor = create_real_time_monitor(str(self.project_root))
        
        # Add event handler for real-time documentation updates
        self.monitor.add_event_handler(self._handle_development_event)
        
        # State tracking
        self.is_monitoring = False
        self.live_context = {
            "session_start": datetime.now().isoformat(),
            "decisions_made": [],
            "problems_solved": [],
            "features_implemented": [],
            "files_modified": {},
            "git_activities": []
        }
        
        logger.info("Enhanced Documentation Agent initialized with real-time monitoring")
    
    def start_monitoring(self):
        """Start real-time development monitoring"""
        if self.is_monitoring:
            logger.warning("Monitoring already active")
            return
        
        logger.info("Starting enhanced documentation monitoring")
        self.monitor.start_monitoring()
        self.is_monitoring = True
        
        # Log the start of monitoring session
        self.monitor.log_activity(
            "monitoring_session",
            "Enhanced Documentation Agent monitoring started",
            {
                "agent_capabilities": [
                    "real_time_file_monitoring",
                    "git_activity_tracking", 
                    "session_context_capture",
                    "autonomous_documentation_updates"
                ],
                "project_root": str(self.project_root)
            }
        )
    
    def stop_monitoring(self):
        """Stop real-time monitoring and generate session summary"""
        if not self.is_monitoring:
            return
        
        logger.info("Stopping enhanced documentation monitoring")
        
        # Generate final session summary
        session_summary = self._generate_session_summary()
        
        # Save session context
        self._save_session_context(session_summary)
        
        # Stop monitoring
        self.monitor.stop_monitoring()
        self.is_monitoring = False
        
        logger.info("Enhanced documentation monitoring stopped")
        return session_summary
    
    def _handle_development_event(self, event: DevelopmentEvent):
        """Handle real-time development events"""
        try:
            # Update live context based on event type
            if event.event_type == "file_change":
                self._handle_file_change_event(event)
            elif event.event_type == "git_operation":
                self._handle_git_event(event)
            elif event.event_type == "session_activity":
                self._handle_session_activity_event(event)
            
            # Check if documentation updates are needed
            self._check_documentation_triggers(event)
            
        except Exception as e:
            logger.warning(f"Error handling development event: {e}")
    
    def _handle_file_change_event(self, event: DevelopmentEvent):
        """Handle file modification events"""
        file_path = event.file_path
        module = event.details.get("module", "unknown")
        
        # Track file modifications per module
        if module not in self.live_context["files_modified"]:
            self.live_context["files_modified"][module] = []
        
        self.live_context["files_modified"][module].append({
            "file": file_path,
            "action": event.details.get("action"),
            "timestamp": event.timestamp
        })
        
        # Check for significant file changes that need documentation
        if self._is_significant_file_change(event):
            logger.info(f"Significant change detected in {module}: {Path(file_path).name}")
    
    def _handle_git_event(self, event: DevelopmentEvent):
        """Handle git operation events"""
        self.live_context["git_activities"].append({
            "description": event.description,
            "details": event.details,
            "timestamp": event.timestamp
        })
        
        # If it's a commit, trigger documentation update
        if "commit" in event.description.lower():
            self._trigger_post_commit_documentation(event)
    
    def _handle_session_activity_event(self, event: DevelopmentEvent):
        """Handle session activity events"""
        context_type = event.context
        
        if context_type == "decision":
            self.live_context["decisions_made"].append({
                "decision": event.details.get("decision"),
                "reasoning": event.details.get("reasoning"),
                "impact": event.details.get("impact"),
                "timestamp": event.timestamp
            })
        elif context_type == "problem_solved":
            self.live_context["problems_solved"].append({
                "problem": event.details.get("problem"),
                "solution": event.details.get("solution"),
                "approach": event.details.get("approach"),
                "timestamp": event.timestamp
            })
        elif context_type == "feature_implemented":
            self.live_context["features_implemented"].append({
                "feature": event.details.get("feature"),
                "details": event.details.get("implementation_details"),
                "timestamp": event.timestamp
            })
    
    def _is_significant_file_change(self, event: DevelopmentEvent) -> bool:
        """Determine if a file change is significant enough to trigger documentation"""
        file_path = Path(event.file_path)
        
        # Python files in key directories
        if file_path.suffix == '.py' and any(part in str(file_path) for part in ['agents', 'core', 'scripts']):
            return True
        
        # README files
        if file_path.name == 'README.md':
            return True
        
        # Configuration files
        if file_path.name in ['requirements.txt', 'setup.py', 'pyproject.toml']:
            return True
        
        return False
    
    def _check_documentation_triggers(self, event: DevelopmentEvent):
        """Check if event should trigger documentation updates"""
        # Trigger documentation update every 10 significant events
        significant_events = len(self.live_context["decisions_made"]) + \
                           len(self.live_context["problems_solved"]) + \
                           len(self.live_context["features_implemented"])
        
        if significant_events > 0 and significant_events % 5 == 0:
            self._trigger_incremental_documentation_update()
    
    def _trigger_post_commit_documentation(self, event: DevelopmentEvent):
        """Trigger documentation update after a git commit"""
        logger.info("Triggering post-commit documentation update")
        
        try:
            # Get current context from base agent
            result = self.doc_agent.process({})
            
            if result.success:
                tasks = result.data.get("documentation_tasks", [])
                logger.info(f"Generated {len(tasks)} documentation tasks after commit")
                
                # Auto-execute high-priority tasks
                for task in tasks:
                    if task.get("priority", 0) >= 8:
                        logger.info(f"Auto-executing: {task.get('description')}")
        
        except Exception as e:
            logger.warning(f"Error in post-commit documentation: {e}")
    
    def _trigger_incremental_documentation_update(self):
        """Trigger incremental documentation update based on live context"""
        logger.info("Triggering incremental documentation update")
        
        try:
            # Create enhanced context with live information
            enhanced_context = {
                "live_session_data": self.live_context,
                "real_time_events": [event.to_dict() for event in self.monitor.get_recent_events(20)]
            }
            
            # Process with enhanced context
            result = self.doc_agent.process(enhanced_context)
            
            if result.success:
                logger.info("Incremental documentation update completed")
            
        except Exception as e:
            logger.warning(f"Error in incremental documentation update: {e}")
    
    def _generate_session_summary(self) -> Dict[str, Any]:
        """Generate comprehensive session summary"""
        events_summary = self.monitor.get_events_summary()
        
        summary = {
            "session_metadata": {
                "start_time": self.live_context["session_start"],
                "end_time": datetime.now().isoformat(),
                "duration": events_summary.get("monitoring_duration"),
                "total_events_captured": events_summary.get("total_events", 0)
            },
            "development_activity": {
                "decisions_made": len(self.live_context["decisions_made"]),
                "problems_solved": len(self.live_context["problems_solved"]),
                "features_implemented": len(self.live_context["features_implemented"]),
                "modules_modified": list(self.live_context["files_modified"].keys()),
                "git_operations": len(self.live_context["git_activities"])
            },
            "detailed_context": self.live_context,
            "events_breakdown": events_summary.get("event_types", {}),
            "active_modules": events_summary.get("active_modules", [])
        }
        
        return summary
    
    def _save_session_context(self, summary: Dict[str, Any]):
        """Save session context for future reference"""
        try:
            # Save detailed session log
            session_file = self.project_root / f"session_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            with open(session_file, 'w', encoding='utf-8') as f:
                json.dump(summary, f, indent=2)
            
            logger.info(f"Session context saved to: {session_file}")
            
            # Update main session state file
            self._update_main_session_state(summary)
            
        except Exception as e:
            logger.warning(f"Error saving session context: {e}")
    
    def _update_main_session_state(self, summary: Dict[str, Any]):
        """Update main session state file with latest information"""
        try:
            session_state_file = self.project_root / "V8_CURRENT_SESSION_STATE.md"
            
            # Generate markdown update
            update_content = self._generate_markdown_update(summary)
            
            # Append to existing session state
            if session_state_file.exists():
                with open(session_state_file, 'a', encoding='utf-8') as f:
                    f.write(f"\n\n## Real-Time Session Update - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(update_content)
            
            logger.info("Main session state updated with real-time context")
            
        except Exception as e:
            logger.warning(f"Error updating main session state: {e}")
    
    def _generate_markdown_update(self, summary: Dict[str, Any]) -> str:
        """Generate markdown content from session summary"""
        content = []
        
        # Session overview
        activity = summary["development_activity"]
        content.append(f"### Session Activity Summary")
        content.append(f"- **Decisions Made**: {activity['decisions_made']}")
        content.append(f"- **Problems Solved**: {activity['problems_solved']}")
        content.append(f"- **Features Implemented**: {activity['features_implemented']}")
        content.append(f"- **Modules Modified**: {', '.join(activity['modules_modified'])}")
        content.append(f"- **Git Operations**: {activity['git_operations']}")
        content.append("")
        
        # Detailed decisions
        if self.live_context["decisions_made"]:
            content.append("### Development Decisions Made")
            for decision in self.live_context["decisions_made"][-3:]:  # Last 3
                content.append(f"- **{decision['decision']}**")
                content.append(f"  - Reasoning: {decision['reasoning']}")
                if decision.get('impact'):
                    content.append(f"  - Impact: {decision['impact']}")
            content.append("")
        
        # Problems solved
        if self.live_context["problems_solved"]:
            content.append("### Problems Solved")
            for problem in self.live_context["problems_solved"][-3:]:  # Last 3
                content.append(f"- **Problem**: {problem['problem']}")
                content.append(f"  - Solution: {problem['solution']}")
                if problem.get('approach'):
                    content.append(f"  - Approach: {problem['approach']}")
            content.append("")
        
        return "\n".join(content)
    
    # Public API for manual logging
    def log_decision(self, decision: str, reasoning: str, impact: str = None):
        """Log a development decision with real-time capture"""
        if self.is_monitoring:
            self.monitor.log_decision(decision, reasoning, impact)
    
    def log_problem_solved(self, problem: str, solution: str, approach: str = None):
        """Log a solved problem with real-time capture"""
        if self.is_monitoring:
            self.monitor.log_problem_solved(problem, solution, approach)
    
    def log_feature_implemented(self, feature: str, details: str = None):
        """Log a new feature implementation with real-time capture"""
        if self.is_monitoring:
            self.monitor.log_feature_implemented(feature, details)
    
    def get_live_summary(self) -> Dict[str, Any]:
        """Get current live session summary"""
        return {
            "monitoring_active": self.is_monitoring,
            "session_duration": str(datetime.now() - datetime.fromisoformat(self.live_context["session_start"])),
            "events_captured": self.monitor.get_events_summary(),
            "context_summary": {
                "decisions": len(self.live_context["decisions_made"]),
                "problems_solved": len(self.live_context["problems_solved"]),
                "features": len(self.live_context["features_implemented"]),
                "modules_active": len(self.live_context["files_modified"])
            }
        }


def create_enhanced_documentation_agent(project_root: str = ".") -> EnhancedDocumentationAgent:
    """Factory function to create enhanced documentation agent"""
    config = {
        "project_root": project_root,
        "session_context": "V8_CURRENT_SESSION_STATE.md",
        "auto_commit": False,
        "auto_update_scripts": True,
        "real_time_monitoring": True
    }
    
    return EnhancedDocumentationAgent(config)


def main():
    """Test the enhanced documentation agent"""
    agent = create_enhanced_documentation_agent()
    
    print("Starting Enhanced Documentation Agent with Real-Time Monitoring...")
    agent.start_monitoring()
    
    # Test manual logging
    agent.log_decision(
        "Implement real-time monitoring",
        "Need to capture development context as it happens",
        "Complete information preservation during development"
    )
    
    agent.log_feature_implemented(
        "Real-time development monitoring system",
        "File watching, git monitoring, and session activity capture"
    )
    
    try:
        print("Enhanced monitoring active. Try modifying files to see real-time capture.")
        print("Press Ctrl+C to stop and generate session summary...")
        
        while True:
            time.sleep(10)
            summary = agent.get_live_summary()
            print(f"Live Summary: {summary['context_summary']} | Duration: {summary['session_duration']}")
            
    except KeyboardInterrupt:
        print("\nStopping enhanced documentation agent...")
        session_summary = agent.stop_monitoring()
        
        print("\nSession Summary:")
        print(f"Total Events: {session_summary['session_metadata']['total_events_captured']}")
        print(f"Development Activity: {session_summary['development_activity']}")
        print(f"Active Modules: {session_summary['active_modules']}")


if __name__ == "__main__":
    main()
