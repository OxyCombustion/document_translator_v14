"""
Real-Time Development Monitor for Document Translator V9
Captures development activity as it happens for complete information preservation
"""

import time
import json
import threading
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from queue import Queue, Empty
import subprocess
import hashlib

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False
    Observer = None
    FileSystemEventHandler = None

# V14 imports (updated from v13 imports)
from pipelines.shared.packages.common.src.logging.logger import get_logger

logger = get_logger("RealTimeMonitor")


@dataclass
class DevelopmentEvent:
    """A single development activity event"""
    timestamp: str
    event_type: str  # 'file_change', 'git_operation', 'session_activity'
    file_path: Optional[str]
    description: str
    details: Dict[str, Any]
    context: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class FileChangeHandler(FileSystemEventHandler):
    """Handles file system events for real-time monitoring"""
    
    def __init__(self, monitor):
        self.monitor = monitor
        self.last_events = {}  # Debounce rapid events
        
    def on_modified(self, event):
        if not event.is_directory:
            self._handle_file_event(event.src_path, "modified")
    
    def on_created(self, event):
        if not event.is_directory:
            self._handle_file_event(event.src_path, "created")
    
    def on_deleted(self, event):
        if not event.is_directory:
            self._handle_file_event(event.src_path, "deleted")
    
    def _handle_file_event(self, file_path: str, action: str):
        """Handle individual file events with debouncing"""
        file_path = Path(file_path)
        
        # Skip irrelevant files
        if self._should_ignore_file(file_path):
            return
        
        # Debounce rapid events (same file within 1 second)
        now = time.time()
        key = f"{file_path}_{action}"
        if key in self.last_events and now - self.last_events[key] < 1.0:
            return
        self.last_events[key] = now
        
        # Create event
        event = DevelopmentEvent(
            timestamp=datetime.now().isoformat(),
            event_type="file_change",
            file_path=str(file_path),
            description=f"File {action}: {file_path.name}",
            details={
                "action": action,
                "file_type": file_path.suffix,
                "file_size": file_path.stat().st_size if file_path.exists() else 0,
                "module": self._determine_module(file_path)
            }
        )
        
        self.monitor.add_event(event)
    
    def _should_ignore_file(self, file_path: Path) -> bool:
        """Determine if file should be ignored"""
        ignore_patterns = [
            '__pycache__',
            '.pyc',
            '.log',
            '.tmp',
            '.git',
            'node_modules',
            '.vscode',
            '.idea'
        ]
        
        file_str = str(file_path).lower()
        return any(pattern in file_str for pattern in ignore_patterns)
    
    def _determine_module(self, file_path: Path) -> str:
        """Determine which module/component the file belongs to"""
        path_parts = file_path.parts
        
        if 'agents' in path_parts:
            agents_idx = path_parts.index('agents')
            if len(path_parts) > agents_idx + 1:
                return f"agents/{path_parts[agents_idx + 1]}"
        elif 'core' in path_parts:
            return "core"
        elif 'scripts' in path_parts:
            return "scripts"
        elif 'tests' in path_parts:
            return "tests"
        
        return "project_root"


class GitMonitor:
    """Monitors git repository for changes"""
    
    def __init__(self, project_root: Path, monitor):
        self.project_root = project_root
        self.monitor = monitor
        self.last_commit_hash = self._get_current_commit()
        self.last_status_hash = self._get_status_hash()
        
    def check_git_changes(self):
        """Check for git repository changes"""
        try:
            # Check for new commits
            current_commit = self._get_current_commit()
            if current_commit != self.last_commit_hash:
                self._handle_new_commit(current_commit)
                self.last_commit_hash = current_commit
            
            # Check for status changes (staged/unstaged files)
            current_status_hash = self._get_status_hash()
            if current_status_hash != self.last_status_hash:
                self._handle_status_change()
                self.last_status_hash = current_status_hash
                
        except Exception as e:
            logger.warning(f"Error checking git changes: {e}")
    
    def _get_current_commit(self) -> str:
        """Get current commit hash"""
        try:
            result = subprocess.run(
                ['git', 'rev-parse', 'HEAD'],
                capture_output=True, text=True, cwd=self.project_root
            )
            return result.stdout.strip() if result.returncode == 0 else ""
        except:
            return ""
    
    def _get_status_hash(self) -> str:
        """Get hash of current git status"""
        try:
            result = subprocess.run(
                ['git', 'status', '--porcelain'],
                capture_output=True, text=True, cwd=self.project_root
            )
            return hashlib.md5(result.stdout.encode()).hexdigest() if result.returncode == 0 else ""
        except:
            return ""
    
    def _handle_new_commit(self, commit_hash: str):
        """Handle new commit event"""
        try:
            # Get commit message
            result = subprocess.run(
                ['git', 'log', '-1', '--pretty=%s', commit_hash],
                capture_output=True, text=True, cwd=self.project_root
            )
            commit_message = result.stdout.strip()
            
            # Get changed files
            result = subprocess.run(
                ['git', 'diff-tree', '--no-commit-id', '--name-only', '-r', commit_hash],
                capture_output=True, text=True, cwd=self.project_root
            )
            changed_files = [f for f in result.stdout.strip().split('\n') if f]
            
            event = DevelopmentEvent(
                timestamp=datetime.now().isoformat(),
                event_type="git_operation",
                file_path=None,
                description=f"New commit: {commit_message[:50]}...",
                details={
                    "commit_hash": commit_hash,
                    "commit_message": commit_message,
                    "files_changed": changed_files,
                    "file_count": len(changed_files)
                }
            )
            
            self.monitor.add_event(event)
            
        except Exception as e:
            logger.warning(f"Error handling new commit: {e}")
    
    def _handle_status_change(self):
        """Handle git status change (files staged/unstaged)"""
        try:
            result = subprocess.run(
                ['git', 'status', '--porcelain'],
                capture_output=True, text=True, cwd=self.project_root
            )
            
            if result.stdout.strip():
                lines = result.stdout.strip().split('\n')
                staged_files = []
                unstaged_files = []
                
                for line in lines:
                    if line.startswith(' M') or line.startswith(' A') or line.startswith(' D'):
                        unstaged_files.append(line[3:])
                    elif line.startswith('M ') or line.startswith('A ') or line.startswith('D '):
                        staged_files.append(line[3:])
                
                event = DevelopmentEvent(
                    timestamp=datetime.now().isoformat(),
                    event_type="git_operation",
                    file_path=None,
                    description=f"Git status change: {len(staged_files)} staged, {len(unstaged_files)} unstaged",
                    details={
                        "staged_files": staged_files,
                        "unstaged_files": unstaged_files,
                        "total_changes": len(lines)
                    }
                )
                
                self.monitor.add_event(event)
                
        except Exception as e:
            logger.warning(f"Error handling status change: {e}")


class SessionActivityMonitor:
    """Monitors session activity and captures development decisions"""
    
    def __init__(self, monitor):
        self.monitor = monitor
        self.session_start = datetime.now()
        self.last_activity = datetime.now()
        
    def log_activity(self, activity_type: str, description: str, details: Dict[str, Any] = None):
        """Log a session activity"""
        event = DevelopmentEvent(
            timestamp=datetime.now().isoformat(),
            event_type="session_activity",
            file_path=None,
            description=description,
            details=details or {},
            context=activity_type
        )
        
        self.monitor.add_event(event)
        self.last_activity = datetime.now()
    
    def log_decision(self, decision: str, reasoning: str, impact: str = None):
        """Log a development decision with reasoning"""
        self.log_activity(
            "decision",
            f"Development decision: {decision}",
            {
                "decision": decision,
                "reasoning": reasoning,
                "impact": impact,
                "session_duration": str(datetime.now() - self.session_start)
            }
        )
    
    def log_problem_solved(self, problem: str, solution: str, approach: str = None):
        """Log a problem and its solution"""
        self.log_activity(
            "problem_solved",
            f"Solved: {problem}",
            {
                "problem": problem,
                "solution": solution,
                "approach": approach
            }
        )
    
    def log_feature_implemented(self, feature: str, details: str = None):
        """Log implementation of a new feature"""
        self.log_activity(
            "feature_implemented",
            f"Implemented: {feature}",
            {
                "feature": feature,
                "implementation_details": details
            }
        )


class RealTimeMonitor:
    """Main real-time development monitoring system"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.project_root = Path(config.get("project_root", "."))
        self.events_queue = Queue()
        self.events_history = []
        self.is_running = False
        
        # Monitoring components
        self.file_observer = None
        self.git_monitor = None
        self.session_monitor = None
        
        # Background threads
        self.monitor_thread = None
        self.processor_thread = None
        
        # Event handlers
        self.event_handlers: List[Callable[[DevelopmentEvent], None]] = []
        
        logger.info(f"RealTimeMonitor initialized for {self.project_root}")
    
    def start_monitoring(self):
        """Start real-time monitoring"""
        if self.is_running:
            logger.warning("Monitor is already running")
            return
        
        self.is_running = True
        logger.info("Starting real-time development monitoring")
        
        # Initialize monitoring components
        self._setup_file_monitoring()
        self._setup_git_monitoring()
        self._setup_session_monitoring()
        
        # Start background threads
        self.monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.processor_thread = threading.Thread(target=self._event_processor_loop, daemon=True)
        
        self.monitor_thread.start()
        self.processor_thread.start()
        
        logger.info("Real-time monitoring started successfully")
    
    def stop_monitoring(self):
        """Stop real-time monitoring"""
        if not self.is_running:
            return
        
        logger.info("Stopping real-time monitoring")
        self.is_running = False
        
        # Stop file observer
        if self.file_observer:
            self.file_observer.stop()
            self.file_observer.join()
        
        logger.info("Real-time monitoring stopped")
    
    def _setup_file_monitoring(self):
        """Setup file system monitoring"""
        if not WATCHDOG_AVAILABLE:
            logger.warning("Watchdog not available - file monitoring disabled")
            return
        
        self.file_observer = Observer()
        event_handler = FileChangeHandler(self)
        
        # Monitor key directories
        directories_to_watch = [
            self.project_root / "src",
            self.project_root / "scripts",
            self.project_root / "tests"
        ]
        
        for directory in directories_to_watch:
            if directory.exists():
                self.file_observer.schedule(event_handler, str(directory), recursive=True)
                logger.info(f"Watching directory: {directory}")
        
        # Also watch project root for documentation files
        self.file_observer.schedule(event_handler, str(self.project_root), recursive=False)
        
        self.file_observer.start()
    
    def _setup_git_monitoring(self):
        """Setup git repository monitoring"""
        if (self.project_root / ".git").exists():
            self.git_monitor = GitMonitor(self.project_root, self)
            logger.info("Git monitoring enabled")
        else:
            logger.warning("No git repository found - git monitoring disabled")
    
    def _setup_session_monitoring(self):
        """Setup session activity monitoring"""
        self.session_monitor = SessionActivityMonitor(self)
        logger.info("Session activity monitoring enabled")
    
    def _monitoring_loop(self):
        """Main monitoring loop for periodic checks"""
        while self.is_running:
            try:
                # Check git changes every 5 seconds
                if self.git_monitor:
                    self.git_monitor.check_git_changes()
                
                # Log periodic heartbeat
                if len(self.events_history) % 50 == 0 and len(self.events_history) > 0:
                    self.session_monitor.log_activity(
                        "heartbeat",
                        f"Monitoring active: {len(self.events_history)} events captured",
                        {"events_count": len(self.events_history)}
                    )
                
                time.sleep(5)
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(10)
    
    def _event_processor_loop(self):
        """Process events from the queue"""
        while self.is_running:
            try:
                # Get event from queue (with timeout)
                event = self.events_queue.get(timeout=1)
                
                # Add to history
                self.events_history.append(event)
                
                # Process event
                self._process_event(event)
                
                # Call event handlers
                for handler in self.event_handlers:
                    try:
                        handler(event)
                    except Exception as e:
                        logger.warning(f"Event handler error: {e}")
                
            except Empty:
                continue
            except Exception as e:
                logger.error(f"Error processing event: {e}")
    
    def _process_event(self, event: DevelopmentEvent):
        """Process a single development event"""
        # Log significant events
        if event.event_type in ["git_operation", "session_activity"]:
            logger.info(f"Event: {event.description}")
        
        # Save events to file periodically
        if len(self.events_history) % 10 == 0:
            self._save_events_to_file()
    
    def _save_events_to_file(self):
        """Save recent events to file for persistence"""
        try:
            events_file = self.project_root / "real_time_development_log.json"
            
            # Keep only recent events (last 1000)
            recent_events = self.events_history[-1000:] if len(self.events_history) > 1000 else self.events_history
            
            events_data = {
                "monitoring_session": {
                    "start_time": self.session_monitor.session_start.isoformat() if self.session_monitor else None,
                    "total_events": len(self.events_history),
                    "last_updated": datetime.now().isoformat()
                },
                "events": [event.to_dict() for event in recent_events]
            }
            
            with open(events_file, 'w', encoding='utf-8') as f:
                json.dump(events_data, f, indent=2)
                
        except Exception as e:
            logger.warning(f"Error saving events to file: {e}")
    
    def add_event(self, event: DevelopmentEvent):
        """Add an event to the monitoring queue"""
        self.events_queue.put(event)
    
    def add_event_handler(self, handler: Callable[[DevelopmentEvent], None]):
        """Add an event handler function"""
        self.event_handlers.append(handler)
    
    def get_recent_events(self, count: int = 50) -> List[DevelopmentEvent]:
        """Get recent development events"""
        return self.events_history[-count:] if len(self.events_history) > count else self.events_history
    
    def get_events_summary(self) -> Dict[str, Any]:
        """Get summary of captured events"""
        if not self.events_history:
            return {"total_events": 0}
        
        event_types = {}
        modules_active = set()
        
        for event in self.events_history:
            event_types[event.event_type] = event_types.get(event.event_type, 0) + 1
            
            if event.details and "module" in event.details:
                modules_active.add(event.details["module"])
        
        return {
            "total_events": len(self.events_history),
            "event_types": event_types,
            "active_modules": list(modules_active),
            "monitoring_duration": str(datetime.now() - self.session_monitor.session_start) if self.session_monitor else None,
            "last_activity": self.events_history[-1].timestamp if self.events_history else None
        }
    
    # Public API for logging development activities
    def log_decision(self, decision: str, reasoning: str, impact: str = None):
        """Log a development decision"""
        if self.session_monitor:
            self.session_monitor.log_decision(decision, reasoning, impact)
    
    def log_problem_solved(self, problem: str, solution: str, approach: str = None):
        """Log a solved problem"""
        if self.session_monitor:
            self.session_monitor.log_problem_solved(problem, solution, approach)
    
    def log_feature_implemented(self, feature: str, details: str = None):
        """Log a new feature implementation"""
        if self.session_monitor:
            self.session_monitor.log_feature_implemented(feature, details)
    
    def log_activity(self, activity_type: str, description: str, details: Dict[str, Any] = None):
        """Log general development activity"""
        if self.session_monitor:
            self.session_monitor.log_activity(activity_type, description, details)


def create_real_time_monitor(project_root: str = ".") -> RealTimeMonitor:
    """Factory function to create a real-time monitor"""
    config = {
        "project_root": project_root,
        "save_interval": 10,  # Save events every 10 events
        "max_events_memory": 1000  # Keep last 1000 events in memory
    }
    
    return RealTimeMonitor(config)


def main():
    """Test the real-time monitor"""
    monitor = create_real_time_monitor()
    
    print("Starting real-time development monitoring...")
    monitor.start_monitoring()
    
    # Test manual logging
    monitor.log_activity("testing", "Started real-time monitor test")
    monitor.log_decision(
        "Implement real-time monitoring", 
        "Need to capture development activity as it happens",
        "Complete information preservation"
    )
    
    try:
        print("Monitor running... Press Ctrl+C to stop")
        print("Try modifying files in src/ to see real-time events")
        
        while True:
            time.sleep(5)
            summary = monitor.get_events_summary()
            print(f"Events captured: {summary['total_events']} (Types: {summary['event_types']})")
            
    except KeyboardInterrupt:
        print("\nStopping monitor...")
        monitor.stop_monitoring()
        
        # Show final summary
        final_summary = monitor.get_events_summary()
        print(f"\nFinal Summary:")
        print(f"Total events captured: {final_summary['total_events']}")
        print(f"Event types: {final_summary['event_types']}")
        print(f"Active modules: {final_summary.get('active_modules', [])}")


if __name__ == "__main__":
    main()
