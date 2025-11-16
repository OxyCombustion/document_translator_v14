# Session Preservation Agent
## V11 Document Translator Agent - Session State Management & Git Automation

[![Status](https://img.shields.io/badge/status-active-green.svg)]() 
[![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)]() 
[![Python](https://img.shields.io/badge/python-3.13-blue.svg)]() 
[![Git](https://img.shields.io/badge/git-automated-blue.svg)]()

> **Session Continuity:** Comprehensive session state preservation and git workflow automation for seamless V9 development handoffs.

---

## 🚀 Quick Start

### Basic Usage
```bash
# Navigate to session preservation agent
cd src/agents/session_preservation

# Launch interactive session management
python session_preservation_agent.py

# Quick session preservation
python session_preservation_agent.py preserve

# Check current system status
python session_preservation_agent.py status
```

### Interactive CLI Menu
```
V9 Session Preservation Agent
=============================

Available commands:
  preserve  - Complete session preservation workflow
  capture   - Capture current session state only
  commit    - Commit changes to git with V9 formatting
  prepare   - Prepare startup context for next session
  status    - Show current agent and system status
  help      - Show detailed help information
  exit      - Exit the agent

Enter command: preserve
```

### Programmatic Usage
```python
from src.agents.session_preservation import SessionPreservationAgent

# Initialize agent
agent = SessionPreservationAgent()

# Complete session preservation
result = agent.preserve_session()

if result.success:
    print(f"Session preserved successfully!")
    print(f"- {len(result.agent_states)} agent states captured")
    print(f"- {len(result.documents_updated)} context documents updated")
    print(f"- Git commit: {result.commit_hash}")
else:
    print(f"Session preservation failed: {result.error}")
```

---

## 📋 Overview

### What This Agent Does
- **Primary Function:** Preserve complete V9 development session state across local-claude instances
- **Secondary Functions:** Git workflow automation, context document management, startup preparation
- **Input:** Current V11 system state, agent configurations, development progress
- **Output:** Updated context documents, git commits, session handoff documentation

### Key Features
- ✅ **Complete State Capture:** Collects state from all 18 V9 agents automatically
- ✅ **Context Document Management:** Updates CLAUDE.md, session files, and startup instructions
- ✅ **Git Automation:** Automated staging, committing, and pushing with V9 standard formatting
- ✅ **Session Handoff:** Prepares comprehensive handoff documentation for next developer
- ✅ **Interactive CLI:** User-friendly command-line interface with progress reporting

### Performance Characteristics
- **Processing Time:** <30 seconds for complete session preservation
- **Agent Collection:** <10 seconds to capture all 18 agent states
- **Git Operations:** <15 seconds for commit and push
- **Memory Usage:** <100MB during operation

---

## 💡 Usage Examples

### Example 1: Complete Session Preservation
```python
from src.agents.session_preservation import SessionPreservationAgent

# Initialize with project root
agent = SessionPreservationAgent()

# Perform complete session preservation
options = {
    "include_git_push": True,
    "update_startup_context": True,
    "capture_performance_metrics": True
}

result = agent.preserve_session(options)

# Check results
print(f"Session ID: {result.session_id}")
print(f"Agents Captured: {len(result.agent_states)}")
print(f"Documents Updated: {result.documents_updated}")
print(f"Git Commit: {result.commit_hash}")

# Display summary
if result.success:
    print("\n✅ Session preserved successfully!")
    print(f"Next session can resume with context from {result.timestamp}")
else:
    print(f"\n❌ Session preservation failed: {result.error}")
    print(f"Recovery action: {result.recovery_action}")
```

### Example 2: Agent State Collection Only
```python
from src.agents.session_preservation import SessionCollector

# Initialize collector
collector = SessionCollector(project_root=".")

# Collect current states without preservation
session_data = collector.collect_complete_session_state()

# Analyze agent states
print("Agent Status Summary:")
for agent_name, state in session_data.agent_states.items():
    status_emoji = "✅" if state.status == "active" else "⚠️"
    print(f"  {status_emoji} {agent_name}: {state.status}")
    
    if state.current_tasks:
        print(f"    Tasks: {', '.join(state.current_tasks)}")
    
    if state.error_status:
        print(f"    Error: {state.error_status}")

# Show system metrics
metrics = session_data.system_metrics
print(f"\nSystem Performance:")
print(f"  Memory Usage: {metrics.memory_usage_mb:.1f} MB")
print(f"  CPU Usage: {metrics.cpu_usage_percent:.1f}%")
print(f"  Disk Usage: {metrics.disk_usage_mb:.1f} MB")
```

### Example 3: Git Operations Only
```python
from src.agents.session_preservation import GitAutomation

# Initialize git automation
git_automation = GitAutomation(repo_path=".")

# Check current git status
git_status = git_automation.get_repository_status()
print(f"Branch: {git_status.current_branch}")
print(f"Modified files: {len(git_status.modified_files)}")
print(f"Untracked files: {len(git_status.untracked_files)}")

# Create session commit
session_data = create_test_session_data()
commit_result = git_automation.commit_session_changes(session_data)

if commit_result.success:
    print(f"✅ Committed: {commit_result.commit_hash}")
    print(f"Files: {', '.join(commit_result.files_committed)}")
else:
    print(f"❌ Commit failed: {commit_result.error}")
    print(f"Suggested action: {commit_result.suggested_action}")
```

---

## ⚙️ Configuration

### Default Configuration
```python
# Default session preservation configuration
DEFAULT_CONFIG = {
    # Operation settings
    "timeout_seconds": 30,
    "max_retry_attempts": 3,
    "enable_parallel_collection": True,
    
    # Git settings
    "auto_push_enabled": True,
    "commit_author": "V9 Session Agent",
    "commit_email": "v9-session@anthropic.com",
    "include_claude_attribution": True,
    
    # Document settings
    "backup_context_files": True,
    "validate_document_updates": True,
    "update_timestamps": True,
    
    # Collection settings
    "collect_performance_metrics": True,
    "include_error_logs": True,
    "capture_agent_configs": True,
    
    # Output settings
    "verbose_logging": True,
    "show_progress": True,
    "save_session_backup": True
}
```

### Environment Variables
```bash
# Optional environment configuration
export V8_SESSION_CONFIG_PATH="/path/to/config.yaml"
export V8_SESSION_LOG_LEVEL="INFO"
export V8_SESSION_GIT_REMOTE="origin"
export V8_SESSION_AUTO_PUSH="true"
export V8_SESSION_BACKUP_DIR="/tmp/v8_session_backups"
```

### Configuration File (config.yaml)
```yaml
session_preservation:
  # Core operation settings
  timeout_seconds: 30
  max_retry_attempts: 3
  enable_backup: true
  
  # Git configuration
  git:
    auto_push: true
    remote_name: "origin"
    commit_author: "V9 Session Agent"
    commit_email: "v9-session@anthropic.com"
    include_attribution: true
  
  # Agent collection settings
  collection:
    parallel_enabled: true
    max_workers: 4
    include_metrics: true
    timeout_per_agent: 5
  
  # Document management
  documents:
    backup_before_update: true
    validate_after_update: true
    preserve_formatting: true
    
  # Logging and monitoring
  logging:
    level: "INFO"
    file: "session_preservation.log"
    include_timestamps: true
```

---

## 🔧 API Reference

### Main Class: SessionPreservationAgent

#### Constructor
```python
def __init__(self, project_root: str = ".", config: Dict = None):
    """
    Initialize Session Preservation Agent.
    
    Args:
        project_root: Path to V9 project root directory
        config: Optional configuration dictionary
    """
```

#### Core Methods

##### preserve_session(options: PreservationOptions = None) → PreservationResult
```python
def preserve_session(self, options: PreservationOptions = None) -> PreservationResult:
    """
    Complete session preservation workflow.
    
    Performs comprehensive session preservation including:
    1. Agent state collection from all V9 components
    2. System metrics and performance data capture
    3. Context document updates with current information
    4. Git operations with standardized V9 commit format
    5. Next session preparation and handoff documentation
    
    Args:
        options: Optional preservation configuration
            - include_git_push: Whether to push to remote (default: True)
            - update_startup_context: Update startup files (default: True)
            - capture_performance_metrics: Include metrics (default: True)
            - create_backup: Create session backup (default: True)
        
    Returns:
        PreservationResult:
        {
            "success": bool,
            "session_id": str,
            "timestamp": datetime,
            "agent_states": Dict[str, AgentState],
            "documents_updated": List[str],
            "commit_hash": str,
            "files_committed": List[str],
            "performance_metrics": Dict,
            "error": Optional[str],
            "recovery_action": Optional[str]
        }
    
    Example:
        >>> agent = SessionPreservationAgent()
        >>> result = agent.preserve_session()
        >>> print(f"Session {result.session_id} preserved with commit {result.commit_hash}")
    """
```

##### capture_session_state() → SessionData
```python
def capture_session_state(self) -> SessionData:
    """
    Capture current session state without preservation actions.
    
    Collects comprehensive state information including:
    - All V9 agent states and configurations
    - System performance metrics and resource usage
    - Current development priorities and issues
    - Git repository status and pending changes
    - File system state and recent activity
    
    Returns:
        SessionData object with complete session information
        
    Example:
        >>> data = agent.capture_session_state()
        >>> print(f"Captured state from {len(data.agent_states)} agents")
    """
```

##### commit_changes(message: str = None) → CommitResult
```python
def commit_changes(self, message: str = None) -> CommitResult:
    """
    Commit current changes to git with V9 standard formatting.
    
    Creates git commit with:
    - Proper V9 conventional commit format
    - Claude co-authorship attribution
    - Detailed change description
    - Session context information
    
    Args:
        message: Optional custom commit message (auto-generated if None)
        
    Returns:
        CommitResult with commit hash and operation status
        
    Example:
        >>> result = agent.commit_changes("Fix table detection algorithm")
        >>> if result.success:
        ...     print(f"Committed: {result.commit_hash}")
    """
```

##### prepare_next_session() → PreparationResult
```python
def prepare_next_session(self) -> PreparationResult:
    """
    Prepare comprehensive context for next development session.
    
    Creates:
    - Updated startup instructions with current priorities
    - Session handoff documentation with context
    - System status summary and health metrics
    - Development progress tracking and metrics
    - Issue summaries and recommended actions
    
    Returns:
        PreparationResult with preparation status and file locations
    """
```

### Utility Classes

#### SessionCollector
```python
class SessionCollector:
    """Collect comprehensive session state from V11 system."""
    
    def collect_agent_states(self) -> Dict[str, AgentState]:
        """Collect state from all discoverable V9 agents."""
        pass
    
    def collect_system_metrics(self) -> SystemMetrics:
        """Collect system performance and resource metrics."""
        pass
    
    def collect_development_context(self) -> DevelopmentContext:
        """Collect current development priorities and issues."""
        pass
```

#### GitAutomation
```python
class GitAutomation:
    """Automated git operations with V9 standards."""
    
    def get_repository_status(self) -> GitStatus:
        """Get current git repository status."""
        pass
    
    def stage_session_files(self) -> List[str]:
        """Stage all session-related files for commit."""
        pass
    
    def push_to_remote(self, remote: str = "origin") -> PushResult:
        """Push committed changes to remote repository."""
        pass
```

---

## 📊 Input/Output Specifications

### Input Sources
```python
# Agent state collection from all V9 agents
{
    "agents_directory": "src/agents/",
    "agent_discovery_pattern": "*/static_context.md",
    "system_config": "V8_SOFTWARE_DESIGN.md",
    "current_session_files": [
        "CLAUDE.md",
        "V8_SESSION_STATE.json", 
        "V8_SESSION_HANDOFF.md"
    ]
}
```

### Output Specifications
```python
# Session preservation result structure
{
    "preservation_result": {
        "success": True,
        "session_id": "session_20250827_142530",
        "timestamp": "2025-08-27T14:25:30Z",
        "duration": 28.5,  # seconds
        
        "agent_states": {
            "enhanced_table": {
                "status": "broken",
                "issues": ["100% false positive rate"],
                "priority": "critical"
            },
            "session_preservation": {
                "status": "active", 
                "last_operation": "preserve_session",
                "priority": "normal"
            }
            # ... 16 more agents
        },
        
        "documents_updated": [
            "CLAUDE.md",
            "V8_SESSION_STATE.json",
            "V8_SESSION_HANDOFF.md",
            "V8_STARTUP_CONTEXT.txt",
            "V8_STARTUP_MESSAGE.txt"
        ],
        
        "git_operations": {
            "files_staged": 12,
            "commit_hash": "a1b2c3d4e5f6",
            "commit_message": "feat(session): Preserve session state...",
            "pushed_to_remote": True,
            "remote_url": "https://github.com/user/v9-project.git"
        },
        
        "performance_metrics": {
            "total_time": 28.5,
            "agent_collection_time": 8.2,
            "document_update_time": 4.1,
            "git_operations_time": 12.8,
            "validation_time": 3.4
        }
    }
}
```

### Error Response Format
```python
# Error result structure
{
    "success": False,
    "error": "Git operation failed: merge conflict detected",
    "error_code": "GIT_CONFLICT",
    "recovery_action": "Resolve merge conflicts manually and retry",
    "partial_results": {
        "agent_states_collected": True,
        "documents_updated": False,
        "git_committed": False
    },
    "recovery_commands": [
        "git status",
        "git diff --name-only --diff-filter=U",
        "# Resolve conflicts then:",
        "python session_preservation_agent.py preserve"
    ]
}
```

---

## 🧪 Testing

### Running Tests
```bash
# Run all session preservation tests
python -m pytest src/agents/session_preservation/tests/ -v

# Run specific test categories
python -m pytest src/agents/session_preservation/tests/test_session_collection.py -v
python -m pytest src/agents/session_preservation/tests/test_git_automation.py -v
python -m pytest src/agents/session_preservation/tests/test_context_management.py -v

# Run integration tests
python -m pytest src/agents/session_preservation/tests/test_integration.py -v

# Run with coverage
python -m pytest --cov=src.agents.session_preservation --cov-report=html tests/
```

### Test Categories

#### Unit Tests
```python
def test_agent_state_collection():
    """Test individual agent state collection."""
    collector = SessionCollector()
    states = collector.collect_agent_states()
    
    assert len(states) > 0
    for agent_name, state in states.items():
        assert state.name == agent_name
        assert state.status in ['active', 'idle', 'error', 'unknown']
        
def test_git_commit_message_generation():
    """Test V9 standard commit message generation."""
    git_automation = GitAutomation(".")
    session_data = create_test_session_data()
    
    message = git_automation._generate_commit_message(session_data, ['CLAUDE.md'])
    
    assert message.startswith('feat(session):') or message.startswith('docs(session):')
    assert 'Co-Authored-By: Claude' in message
    assert '🤖 Generated with [Claude Code]' in message
```

#### Integration Tests
```python
def test_complete_preservation_workflow():
    """Test end-to-end session preservation."""
    with TemporaryGitRepo() as repo:
        agent = SessionPreservationAgent(repo.working_dir)
        
        # Create test agent states
        setup_mock_agents(repo.working_dir)
        
        # Run preservation
        result = agent.preserve_session()
        
        # Validate results
        assert result.success
        assert len(result.agent_states) > 0
        assert result.commit_hash is not None
        
        # Validate git state
        assert repo.head.commit.message.startswith('feat(session):')
```

### Manual Testing
```bash
# Test basic functionality
python session_preservation_agent.py status

# Test session capture without preservation
python session_preservation_agent.py capture

# Test git operations only
python session_preservation_agent.py commit

# Test complete workflow
python session_preservation_agent.py preserve

# Test with custom configuration
V8_SESSION_CONFIG_PATH=./test_config.yaml python session_preservation_agent.py preserve
```

---

## 🔍 Troubleshooting

### Common Issues and Solutions

#### Issue: Agent State Collection Fails
**Symptoms:** Some agents show "error" status or missing states  
**Cause:** Agent directories not accessible or malformed configuration  
**Solution:**
```bash
# Check agent directories
ls -la src/agents/*/

# Verify agent configurations
find src/agents -name "static_context.md" -exec echo "Found: {}" \;

# Test individual agent access
python -c "
from src.agents.session_preservation import SessionCollector
collector = SessionCollector()
states = collector.collect_agent_states()
for name, state in states.items():
    if state.status == 'error':
        print(f'ERROR: {name}: {state.error_status}')
"
```

#### Issue: Git Operations Fail
**Symptoms:** Commit or push operations fail with error messages  
**Cause:** Git conflicts, permissions, or network issues  
**Solution:**
```bash
# Check git status
git status

# Check for conflicts
git diff --name-only --diff-filter=U

# Check remote connectivity
git remote -v
git fetch origin

# Reset if needed
git stash push -m "Session preservation backup"
python session_preservation_agent.py preserve
```

#### Issue: Document Updates Fail
**Symptoms:** Context documents not updated or corrupted  
**Cause:** File permissions or template issues  
**Solution:**
```bash
# Check file permissions
ls -la CLAUDE.md V8_SESSION_*.json V8_SESSION_*.md

# Backup and restore
cp CLAUDE.md CLAUDE.md.backup
python session_preservation_agent.py capture  # Test without git

# Validate document format
python -c "
import json
with open('V8_SESSION_STATE.json') as f:
    data = json.load(f)
    print(f'Session data loaded: {len(data)} keys')
"
```

#### Issue: Performance Too Slow
**Symptoms:** Session preservation takes longer than 30 seconds  
**Solution:**
```python
# Enable performance monitoring
agent = SessionPreservationAgent()
agent.config['enable_performance_logging'] = True

# Reduce scope if needed
agent.config['collect_performance_metrics'] = False
agent.config['skip_large_files'] = True
agent.config['parallel_collection'] = True

result = agent.preserve_session()
print(f"Performance breakdown: {result.performance_metrics}")
```

### Debug Mode
```python
# Enable comprehensive debugging
import logging
logging.basicConfig(level=logging.DEBUG)

agent = SessionPreservationAgent()
agent.config.update({
    'debug_mode': True,
    'verbose_logging': True,
    'save_debug_info': True
})

result = agent.preserve_session()

# Check debug output
print(f"Debug info saved to: {result.debug_file_path}")
```

---

## 📚 Integration Guide

### V11 system Integration
```python
# Integration with V9 startup/shutdown workflow
from src.agents.session_preservation import SessionPreservationAgent

def v8_system_shutdown():
    """V10 system shutdown with automatic session preservation."""
    
    # Preserve session state before shutdown
    session_agent = SessionPreservationAgent()
    result = session_agent.preserve_session({
        'include_git_push': True,
        'update_startup_context': True,
        'create_backup': True
    })
    
    if result.success:
        print(f"✅ Session preserved: {result.session_id}")
        print(f"Next session context: {result.startup_context_file}")
    else:
        print(f"⚠️ Session preservation failed: {result.error}")
        print(f"Manual backup recommended")
    
    return result.success

def v8_system_startup():
    """V10 system startup with session restoration."""
    
    # Load previous session context
    session_agent = SessionPreservationAgent()
    context = session_agent.load_startup_context()
    
    if context:
        print(f"📋 Resuming from session: {context.session_id}")
        print(f"Previous priorities: {context.priorities}")
        print(f"Outstanding issues: {len(context.issues)}")
        
        return context
    else:
        print("🆕 Starting new session")
        return None
```

### Custom Automation Integration
```python
# Custom development workflow integration
class V8DevelopmentWorkflow:
    """Enhanced development workflow with session management."""
    
    def __init__(self):
        self.session_agent = SessionPreservationAgent()
    
    def development_checkpoint(self, milestone: str):
        """Create development checkpoint with session state."""
        result = self.session_agent.preserve_session({
            'milestone': milestone,
            'include_git_push': True,
            'create_tag': True
        })
        
        return result
    
    def daily_handoff(self):
        """Daily development handoff with complete context."""
        handoff_options = {
            'include_daily_summary': True,
            'update_priorities': True,
            'prepare_next_day_context': True,
            'create_progress_report': True
        }
        
        return self.session_agent.preserve_session(handoff_options)
    
    def emergency_backup(self):
        """Emergency session backup for critical work."""
        return self.session_agent.preserve_session({
            'emergency_mode': True,
            'skip_validations': True,
            'force_push': True
        })
```

---

## 🤝 Contributing

### Development Setup
```bash
# Clone and setup development environment
cd src/agents/session_preservation
python -m venv session_env
source session_env/bin/activate  # On Windows: session_env\Scripts\activate

# Install development dependencies
pip install -r requirements-dev.txt

# Run tests to verify setup
python -m pytest tests/ -v
```

### Code Standards
- Follow V11 software Engineering Principles
- Maintain >95% test coverage for all new functionality
- Include comprehensive docstrings with examples
- Use type hints for all function parameters and returns
- Document all configuration options and error conditions

### Adding New Features
1. **Session Collection Enhancement:** Add new agent state collection methods
2. **Document Template Updates:** Enhance context document templates
3. **Git Operation Extensions:** Add new git workflow automation
4. **Integration Improvements:** Better V11 system component integration
5. **Performance Optimizations:** Reduce session preservation time

---

## 📄 Documentation

### Related Documentation
- **[Requirements](AGENT_REQUIREMENTS.md):** Complete functional and non-functional requirements
- **[Specification](AGENT_SPECIFICATION.md):** Technical architecture and implementation details
- **[Static Context](static_context.md):** Dependencies and operational context
- **[Testing Requirements](TESTING_REQUIREMENTS.md):** Comprehensive testing specifications

### V11 system Documentation
- **[Engineering Principles](../../V8_SOFTWARE_ENGINEERING_PRINCIPLES.md):** V9 development standards
- **[System Architecture](../../V8_SOFTWARE_DESIGN.md):** Overall V11 system design
- **[Context Preservation](../../V8_LOCAL_CLAUDE_CONTEXT_PRESERVATION.md):** Session management patterns

---

## 📞 Support

### Getting Help
- **Usage Questions:** Check examples and API documentation in this README
- **Integration Issues:** Review V11 system integration guides
- **Performance Problems:** Enable debug mode and check performance metrics
- **Git Issues:** Verify git repository access and remote connectivity

### Reporting Issues
When reporting issues, include:
- Session preservation agent version and configuration
- Complete error messages and stack traces
- Git repository status and recent commits
- V11 system status and agent states
- Steps to reproduce the issue

### Common Support Scenarios
- **Context Loss:** Use emergency backup and recovery procedures
- **Git Conflicts:** Follow conflict resolution workflow
- **Agent Access Issues:** Verify agent directory structure and permissions
- **Performance Issues:** Review configuration and enable optimization settings

---

## 📋 Changelog

### Version 10.0.0 (Current)
- **Complete Session Preservation:** Full workflow implementation with all 18 V9 agents
- **Git Automation:** Automated staging, committing, and pushing with V9 standards
- **Interactive CLI:** User-friendly command-line interface with progress reporting
- **Context Management:** Comprehensive context document updates and validation
- **Error Handling:** Robust error handling with recovery guidance
- **Performance Optimization:** Sub-30-second session preservation workflow

### Future Enhancements
- **Cloud Backup Integration:** Automatic cloud backup of session state
- **Advanced Conflict Resolution:** Enhanced git conflict resolution automation
- **Session Analytics:** Detailed session analytics and productivity metrics
- **Multi-Developer Coordination:** Enhanced coordination for team development

---

## 📜 License

This agent is part of the V11 Document Translator system and follows V9 licensing terms.

---

*This README provides comprehensive guidance for using the Session Preservation Agent to maintain complete development context and enable seamless session handoffs in the V11 Document Translator system.*