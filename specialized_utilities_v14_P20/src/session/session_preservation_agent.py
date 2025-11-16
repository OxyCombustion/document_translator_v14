#!/usr/bin/env python3
"""
Session Preservation Agent - V9 Document Translator
Comprehensive session state preservation and startup context management

Purpose:
- Remove token-expensive context operations from main Claude interface
- Provide comprehensive session state capture and git management
- Ensure zero progress loss between Claude Code sessions
- Handle all file I/O and documentation updates independently

This agent operates as a CLI tool for session management operations.
"""

# Set UTF-8 encoding for Windows console
# CRITICAL: This setup is required for emoji/Unicode characters to display properly
import sys
import os

if sys.platform == 'win32':
    import io
    # Safer UTF-8 setup - only wrap if not already wrapped
    if not hasattr(sys.stdout, '_wrapped_utf8'):
        try:
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
            sys.stdout._wrapped_utf8 = True
        except (AttributeError, ValueError):
            # Fallback - just set console encoding
            os.system('chcp 65001')
    
    # Handle stderr separately - important for complete UTF-8 support
    if not hasattr(sys.stderr, '_wrapped_utf8'):
        try:
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
            sys.stderr._wrapped_utf8 = True
        except (AttributeError, ValueError):
            pass

import argparse
import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import glob
import hashlib
import logging

# V9 imports
# V14 imports (updated from v13 imports)
from common.src.base.base_agent import BaseAgent, AgentResult, AgentStatus
from common.src.logging.logger import setup_logger
from common.src.context.context_loader import load_agent_context


class SessionPreservationAgent(BaseAgent):
    """
    Session Preservation Agent for comprehensive context capture and git management
    
    Handles all token-expensive operations for session continuity:
    - Context capture and analysis
    - Documentation updates and handoff files
    - Git operations with comprehensive commit messages
    - Progress tracking and session state preservation
    - Startup context preparation
    
    This agent operates independently to preserve Claude's token budget for core development.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize Session Preservation Agent
        
        Args:
            config: Agent configuration (uses defaults if None)
        """
        if config is None:
            config = {
                "name": "SessionPreservationAgent",
                "type": "session_management",
                "capabilities": ["context_capture", "git_management", "documentation", "state_preservation"],
                "working_directory": os.getcwd(),
                "session_files_pattern": "*SESSION*",
                "handoff_files_pattern": "*HANDOFF*",
                "state_files_pattern": "*STATE*"
            }
        
        super().__init__(config, "SessionPreservationAgent")
        
        # Session preservation specific attributes
        self.working_dir = Path(config.get("working_directory", os.getcwd()))
        self.logger = setup_logger(f"{self.name}")
        
        # File patterns for session management
        self.session_patterns = [
            "*SESSION*",
            "*HANDOFF*", 
            "*STATE*",
            "*CONTEXT*",
            "*AGENT*",
            "CLAUDE*.md",
            "V8_*.json",
            "V8_*.md"
        ]
        
        # Git management settings
        self.git_enabled = self._check_git_availability()
        
        # Context files to monitor for changes
        self.critical_files = [
            "CLAUDE.md",
            "CLAUDE_STARTUP_INSTRUCTIONS.md",
            "V8_SESSION_HANDOFF.md",
            "V8_SESSION_STATE.json",
            "V8_FINAL_SESSION_STATE.json",
            "V8_AGENT_CONTEXT_STATE.json"
        ]
        
        self.logger.info(f"Session Preservation Agent initialized (Git: {'available' if self.git_enabled else 'unavailable'})")
    
    def _initialize_model(self):
        """Session preservation agent doesn't use ML models"""
        pass
    
    def _preprocess(self, input_data: Any) -> Any:
        """Preprocess command input"""
        return input_data
    
    def _postprocess(self, model_output: Any) -> Dict[str, Any]:
        """Postprocess command results"""
        return {"result": model_output}
    
    def _extract_features(self, input_data: Any) -> Any:
        """No feature extraction needed"""
        return input_data
    
    def _train_model(self, training_data: Any, validation_data: Any = None) -> Dict[str, float]:
        """Session preservation agent doesn't train"""
        return {}
    
    def _evaluate_model(self, test_data: Any) -> Dict[str, float]:
        """Session preservation agent doesn't evaluate models"""
        return {}
    
    def _check_git_availability(self) -> bool:
        """Check if git is available and working directory is a git repository"""
        try:
            result = subprocess.run(['git', 'status'], 
                                    cwd=self.working_dir, 
                                    capture_output=True, 
                                    text=True)
            return result.returncode == 0
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    def capture_session_context(self) -> Dict[str, Any]:
        """
        Capture comprehensive session context and progress state
        
        Returns:
            Dictionary containing complete session context
        """
        self.logger.info("Capturing session context...")
        
        context = {
            "timestamp": datetime.now().isoformat(),
            "session_files": {},
            "git_status": {},
            "agent_status": {},
            "progress_analysis": {},
            "file_changes": {}
        }
        
        try:
            # 1. Capture session files
            context["session_files"] = self._capture_session_files()
            
            # 2. Capture git status
            if self.git_enabled:
                context["git_status"] = self._capture_git_status()
            
            # 3. Analyze agent status
            context["agent_status"] = self._analyze_agent_status()
            
            # 4. Analyze progress and achievements
            context["progress_analysis"] = self._analyze_session_progress()
            
            # 5. Track file changes
            context["file_changes"] = self._track_file_changes()
            
            self.logger.info("Session context capture completed successfully")
            
        except Exception as e:
            self.logger.error(f"Error during context capture: {e}")
            context["errors"] = [str(e)]
        
        return context
    
    def _capture_session_files(self) -> Dict[str, Any]:
        """Capture content of all session-related files"""
        session_files = {}
        
        for pattern in self.session_patterns:
            for file_path in glob.glob(str(self.working_dir / pattern)):
                file_path = Path(file_path)
                if file_path.is_file():
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        session_files[str(file_path)] = {
                            "size": len(content),
                            "lines": len(content.split('\n')),
                            "modified": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat(),
                            "hash": hashlib.md5(content.encode('utf-8')).hexdigest()[:8]
                        }
                        
                        # Store content for critical files
                        if file_path.name in self.critical_files:
                            session_files[str(file_path)]["content"] = content
                            
                    except Exception as e:
                        self.logger.warning(f"Could not read {file_path}: {e}")
        
        return session_files
    
    def _capture_git_status(self) -> Dict[str, Any]:
        """Capture comprehensive git status"""
        if not self.git_enabled:
            return {"available": False}
        
        git_info = {"available": True}
        
        try:
            # Git status
            result = subprocess.run(['git', 'status', '--porcelain'], 
                                    cwd=self.working_dir, capture_output=True, text=True)
            git_info["status"] = result.stdout.strip().split('\n') if result.stdout.strip() else []
            
            # Current branch
            result = subprocess.run(['git', 'branch', '--show-current'], 
                                    cwd=self.working_dir, capture_output=True, text=True)
            git_info["current_branch"] = result.stdout.strip()
            
            # Recent commits
            result = subprocess.run(['git', 'log', '--oneline', '-10'], 
                                    cwd=self.working_dir, capture_output=True, text=True)
            git_info["recent_commits"] = result.stdout.strip().split('\n') if result.stdout.strip() else []
            
            # Staged files
            result = subprocess.run(['git', 'diff', '--cached', '--name-only'], 
                                    cwd=self.working_dir, capture_output=True, text=True)
            git_info["staged_files"] = result.stdout.strip().split('\n') if result.stdout.strip() else []
            
            # Modified files
            result = subprocess.run(['git', 'diff', '--name-only'], 
                                    cwd=self.working_dir, capture_output=True, text=True)
            git_info["modified_files"] = result.stdout.strip().split('\n') if result.stdout.strip() else []
            
        except Exception as e:
            self.logger.error(f"Error capturing git status: {e}")
            git_info["error"] = str(e)
        
        return git_info
    
    def _analyze_agent_status(self) -> Dict[str, Any]:
        """Analyze status of all V9 agents"""
        agent_status = {
            "agents_discovered": 0,
            "agents_operational": 0,
            "agent_details": {}
        }
        
        try:
            # Check agent directories
            agents_dir = self.working_dir / "src" / "agents"
            if agents_dir.exists():
                agent_dirs = [d for d in agents_dir.iterdir() if d.is_dir() and not d.name.startswith('__')]
                agent_status["agents_discovered"] = len(agent_dirs)
                
                for agent_dir in agent_dirs:
                    agent_name = agent_dir.name
                    agent_status["agent_details"][agent_name] = {
                        "directory": str(agent_dir),
                        "files": [f.name for f in agent_dir.rglob('*.py')],
                        "has_init": (agent_dir / "__init__.py").exists(),
                        "has_readme": (agent_dir / "README.md").exists()
                    }
            
            # Check config/agents.yaml
            agents_config = self.working_dir / "config" / "agents.yaml"
            if agents_config.exists():
                with open(agents_config, 'r', encoding='utf-8') as f:
                    config_content = f.read()
                    agent_status["config_file_size"] = len(config_content)
                    agent_status["config_lines"] = len(config_content.split('\n'))
                    
        except Exception as e:
            self.logger.error(f"Error analyzing agent status: {e}")
            agent_status["error"] = str(e)
        
        return agent_status
    
    def _analyze_session_progress(self) -> Dict[str, Any]:
        """Analyze what was accomplished in the current session"""
        progress = {
            "breakthroughs": [],
            "achievements": [],
            "issues_identified": [],
            "next_priorities": [],
            "context_preservation_needs": []
        }
        
        try:
            # Check session handoff file
            handoff_file = self.working_dir / "V8_SESSION_HANDOFF.md"
            if handoff_file.exists():
                with open(handoff_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Extract key information sections
                if "### Key Achievements" in content:
                    progress["achievements"] = self._extract_bullet_points(content, "### Key Achievements")
                
                if "### CRITICAL Issues" in content:
                    progress["issues_identified"] = self._extract_bullet_points(content, "### CRITICAL Issues")
                
                if "### DYNAMIC AGENT DISCOVERY SYSTEM" in content:
                    progress["breakthroughs"].append("Dynamic Agent Discovery System Implementation")
            
            # Check CLAUDE.md for current priorities
            claude_file = self.working_dir / "CLAUDE.md"
            if claude_file.exists():
                with open(claude_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                if "## 🎯 Current Priorities" in content:
                    progress["next_priorities"] = self._extract_bullet_points(content, "## 🎯 Current Priorities")
            
            # Analyze file modification times to understand recent activity
            recent_files = []
            for pattern in ["*.py", "*.md", "*.json"]:
                for file_path in self.working_dir.rglob(pattern):
                    if file_path.is_file():
                        modified = datetime.fromtimestamp(file_path.stat().st_mtime)
                        if (datetime.now() - modified).days == 0:  # Modified today
                            recent_files.append({
                                "file": str(file_path.relative_to(self.working_dir)),
                                "modified": modified.isoformat()
                            })
            
            progress["recent_activity"] = sorted(recent_files, key=lambda x: x["modified"], reverse=True)[:10]
            
        except Exception as e:
            self.logger.error(f"Error analyzing session progress: {e}")
            progress["error"] = str(e)
        
        return progress
    
    def _extract_bullet_points(self, content: str, section_header: str) -> List[str]:
        """Extract bullet points from a markdown section"""
        lines = content.split('\n')
        bullet_points = []
        in_section = False
        
        for line in lines:
            if line.strip() == section_header:
                in_section = True
                continue
            
            if in_section:
                if line.startswith('###') and line != section_header:
                    break  # Next section
                
                stripped = line.strip()
                if stripped.startswith('- ') or stripped.startswith('* '):
                    bullet_points.append(stripped[2:])
                elif stripped.startswith('1. ') or stripped.startswith('2. '):
                    bullet_points.append(stripped[3:])
        
        return bullet_points
    
    def _track_file_changes(self) -> Dict[str, Any]:
        """Track changes in critical files"""
        changes = {
            "modified_files": [],
            "new_files": [],
            "critical_file_status": {}
        }
        
        if not self.git_enabled:
            return changes
        
        try:
            # Get git diff info
            result = subprocess.run(['git', 'status', '--porcelain'], 
                                    cwd=self.working_dir, capture_output=True, text=True)
            
            for line in result.stdout.strip().split('\n'):
                if not line:
                    continue
                
                status = line[:2]
                filename = line[3:]
                
                if status[0] == 'M' or status[1] == 'M':
                    changes["modified_files"].append(filename)
                elif status[0] == 'A' or status[0] == '?':
                    changes["new_files"].append(filename)
            
            # Check critical files
            for critical_file in self.critical_files:
                file_path = self.working_dir / critical_file
                if file_path.exists():
                    stat = file_path.stat()
                    changes["critical_file_status"][critical_file] = {
                        "exists": True,
                        "size": stat.st_size,
                        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
                    }
                else:
                    changes["critical_file_status"][critical_file] = {"exists": False}
                    
        except Exception as e:
            self.logger.error(f"Error tracking file changes: {e}")
            changes["error"] = str(e)
        
        return changes
    
    def update_documentation(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update all session handoff and documentation files
        
        Args:
            context: Session context from capture_session_context()
            
        Returns:
            Dictionary with update results
        """
        self.logger.info("Updating documentation files...")
        
        results = {
            "updated_files": [],
            "errors": [],
            "handoff_updated": False,
            "session_state_updated": False,
            "claude_updated": False
        }
        
        try:
            # 1. Update session handoff file
            handoff_result = self._update_session_handoff(context)
            results.update(handoff_result)
            
            # 2. Update session state JSON
            state_result = self._update_session_state(context)
            results.update(state_result)
            
            # 3. Update CLAUDE.md with session notes
            claude_result = self._update_claude_md(context)
            results.update(claude_result)
            
            # 4. Update startup instructions if needed
            startup_result = self._update_startup_instructions(context)
            results.update(startup_result)
            
            self.logger.info(f"Documentation update completed. Updated {len(results['updated_files'])} files.")
            
        except Exception as e:
            self.logger.error(f"Error updating documentation: {e}")
            results["errors"].append(str(e))
        
        return results
    
    def _update_session_handoff(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Update V8_SESSION_HANDOFF.md with current session information"""
        handoff_file = self.working_dir / "V8_SESSION_HANDOFF.md"
        result = {"handoff_updated": False, "handoff_errors": []}
        
        try:
            # Generate handoff content
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            handoff_content = f"""# V9 Session Handoff - {timestamp}

## Session Overview
- **Session End Time**: {timestamp}
- **Session Type**: {'Development' if context.get('progress_analysis', {}).get('recent_activity') else 'Maintenance'}
- **Git Status**: {'Active' if context.get('git_status', {}).get('available') else 'Unavailable'}
- **Agents Status**: {context.get('agent_status', {}).get('agents_discovered', 0)} agents discovered

## Key Achievements This Session
"""
            
            achievements = context.get('progress_analysis', {}).get('achievements', [])
            if achievements:
                for achievement in achievements[:5]:  # Top 5
                    handoff_content += f"- {achievement}\n"
            else:
                handoff_content += "- Session preservation and context capture implemented\n"
            
            handoff_content += f"""
## Breakthroughs and Major Progress
"""
            breakthroughs = context.get('progress_analysis', {}).get('breakthroughs', [])
            if breakthroughs:
                for breakthrough in breakthroughs:
                    handoff_content += f"- **{breakthrough}**: Implementation completed\n"
            else:
                handoff_content += "- Session Preservation Agent: Complete CLI tool for context management\n"
            
            handoff_content += f"""
## Current Issues and Blockers
"""
            issues = context.get('progress_analysis', {}).get('issues_identified', [])
            if issues:
                for issue in issues:
                    handoff_content += f"- {issue}\n"
            else:
                handoff_content += "- No critical blockers identified in current session\n"
            
            handoff_content += f"""
## Next Session Priorities
"""
            priorities = context.get('progress_analysis', {}).get('next_priorities', [])
            if priorities:
                for priority in priorities[:5]:  # Top 5
                    handoff_content += f"- {priority}\n"
            else:
                handoff_content += "- Test Session Preservation Agent functionality\n"
                handoff_content += "- Continue with table detection algorithm fixes\n"
            
            handoff_content += f"""
## File Changes Summary
- **Modified Files**: {len(context.get('file_changes', {}).get('modified_files', []))}
- **New Files**: {len(context.get('file_changes', {}).get('new_files', []))}
- **Session Files Tracked**: {len(context.get('session_files', {}))}

## Context for Next Session
- All session state preserved in Session Preservation Agent
- Complete project context available via `python load_context_for_claude.py`
- Git repository status: {'Clean' if not context.get('git_status', {}).get('status') else 'Has changes'}

---
*Auto-generated by Session Preservation Agent*
*Context capture completed at {timestamp}*
"""
            
            # Write handoff file
            with open(handoff_file, 'w', encoding='utf-8') as f:
                f.write(handoff_content)
            
            result["handoff_updated"] = True
            result["handoff_file"] = str(handoff_file)
            
        except Exception as e:
            result["handoff_errors"].append(str(e))
            self.logger.error(f"Error updating session handoff: {e}")
        
        return result
    
    def _update_session_state(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Update V8_SESSION_STATE.json with current state"""
        state_file = self.working_dir / "V8_FINAL_SESSION_STATE.json"
        result = {"session_state_updated": False, "state_errors": []}
        
        try:
            session_state = {
                "timestamp": datetime.now().isoformat(),
                "session_id": f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "agent_discovery": {
                    "total_agents": context.get('agent_status', {}).get('agents_discovered', 0),
                    "operational_agents": context.get('agent_status', {}).get('agents_operational', 0)
                },
                "git_status": context.get('git_status', {}),
                "critical_files": context.get('file_changes', {}).get('critical_file_status', {}),
                "session_metrics": {
                    "files_modified": len(context.get('file_changes', {}).get('modified_files', [])),
                    "files_created": len(context.get('file_changes', {}).get('new_files', [])),
                    "context_files_tracked": len(context.get('session_files', {}))
                },
                "preservation_agent": {
                    "version": "1.0.0",
                    "capabilities": ["context_capture", "git_management", "documentation", "state_preservation"],
                    "last_run": datetime.now().isoformat()
                }
            }
            
            # Write session state
            with open(state_file, 'w', encoding='utf-8') as f:
                json.dump(session_state, f, indent=2, ensure_ascii=False)
            
            result["session_state_updated"] = True
            result["session_state_file"] = str(state_file)
            
        except Exception as e:
            result["state_errors"].append(str(e))
            self.logger.error(f"Error updating session state: {e}")
        
        return result
    
    def _update_claude_md(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Update CLAUDE.md session notes"""
        claude_file = self.working_dir / "CLAUDE.md"
        result = {"claude_updated": False, "claude_errors": []}
        
        if not claude_file.exists():
            result["claude_errors"].append("CLAUDE.md not found")
            return result
        
        try:
            # Read current content
            with open(claude_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Find session notes section
            session_notes_marker = "## 📝 Session Notes"
            if session_notes_marker not in content:
                result["claude_errors"].append("Session Notes section not found in CLAUDE.md")
                return result
            
            # Generate new session note
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            new_note = f"\n### Session Preserved: {timestamp}\n"
            new_note += "Session state captured by Session Preservation Agent.\n"
            
            if context.get('progress_analysis', {}).get('breakthroughs'):
                breakthroughs = context['progress_analysis']['breakthroughs']
                if breakthroughs:
                    new_note += f"Key breakthrough: {breakthroughs[0]}\n"
            
            if context.get('git_status', {}).get('modified_files'):
                mod_count = len(context['git_status']['modified_files'])
                new_note += f"Modified files: {mod_count}\n"
            
            # Insert new note after session notes header
            lines = content.split('\n')
            new_lines = []
            inserted = False
            
            for i, line in enumerate(lines):
                new_lines.append(line)
                if line.strip() == session_notes_marker and not inserted:
                    new_lines.append(new_note)
                    inserted = True
            
            # Write updated content
            with open(claude_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(new_lines))
            
            result["claude_updated"] = True
            result["claude_file"] = str(claude_file)
            
        except Exception as e:
            result["claude_errors"].append(str(e))
            self.logger.error(f"Error updating CLAUDE.md: {e}")
        
        return result
    
    def _update_startup_instructions(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Update startup instructions if needed"""
        startup_file = self.working_dir / "CLAUDE_STARTUP_INSTRUCTIONS.md"
        result = {"startup_updated": False, "startup_errors": []}
        
        # For now, just verify the file exists and is readable
        if startup_file.exists():
            try:
                with open(startup_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                result["startup_updated"] = True
                result["startup_file_size"] = len(content)
                
            except Exception as e:
                result["startup_errors"].append(str(e))
        else:
            result["startup_errors"].append("CLAUDE_STARTUP_INSTRUCTIONS.md not found")
        
        return result
    
    def perform_git_operations(self, context: Dict[str, Any], commit_message: Optional[str] = None) -> Dict[str, Any]:
        """
        Perform git operations: stage changes and create comprehensive commit
        
        Args:
            context: Session context
            commit_message: Optional custom commit message
            
        Returns:
            Dictionary with git operation results
        """
        if not self.git_enabled:
            return {"error": "Git not available"}
        
        self.logger.info("Performing git operations...")
        
        results = {
            "staged_files": [],
            "commit_created": False,
            "commit_hash": None,
            "errors": []
        }
        
        try:
            # 1. Stage relevant files
            files_to_stage = []
            
            # Stage session files
            for file_path in context.get('file_changes', {}).get('modified_files', []):
                if any(pattern.replace('*', '') in file_path for pattern in self.session_patterns):
                    files_to_stage.append(file_path)
            
            # Stage new files
            for file_path in context.get('file_changes', {}).get('new_files', []):
                files_to_stage.append(file_path)
            
            # Stage critical files if they were modified
            for critical_file in self.critical_files:
                if critical_file in context.get('file_changes', {}).get('modified_files', []):
                    files_to_stage.append(critical_file)
            
            # Add Session Preservation Agent files
            agent_files = [
                "src/agents/session_preservation/__init__.py",
                "src/agents/session_preservation/session_preservation_agent.py",
                "src/agents/session_preservation/static_context.md"
            ]
            
            for agent_file in agent_files:
                if Path(self.working_dir / agent_file).exists():
                    files_to_stage.append(agent_file)
            
            # Stage files
            if files_to_stage:
                for file_path in files_to_stage:
                    result = subprocess.run(['git', 'add', file_path], 
                                            cwd=self.working_dir, capture_output=True, text=True)
                    if result.returncode == 0:
                        results["staged_files"].append(file_path)
            
            # 2. Create commit
            if results["staged_files"]:
                if commit_message is None:
                    commit_message = self._generate_commit_message(context)
                
                result = subprocess.run(['git', 'commit', '-m', commit_message], 
                                        cwd=self.working_dir, capture_output=True, text=True)
                
                if result.returncode == 0:
                    results["commit_created"] = True
                    
                    # Get commit hash
                    result = subprocess.run(['git', 'rev-parse', 'HEAD'], 
                                            cwd=self.working_dir, capture_output=True, text=True)
                    if result.returncode == 0:
                        results["commit_hash"] = result.stdout.strip()[:8]
                else:
                    results["errors"].append(f"Commit failed: {result.stderr}")
            else:
                results["errors"].append("No files to commit")
            
            self.logger.info(f"Git operations completed. Staged {len(results['staged_files'])} files.")
            
        except Exception as e:
            self.logger.error(f"Error performing git operations: {e}")
            results["errors"].append(str(e))
        
        return results
    
    def _generate_commit_message(self, context: Dict[str, Any]) -> str:
        """Generate comprehensive commit message from context"""
        timestamp = datetime.now().strftime("%Y-%m-%d")
        
        # Start with session type
        breakthroughs = context.get('progress_analysis', {}).get('breakthroughs', [])
        if breakthroughs:
            commit_type = "feat"
            main_feature = breakthroughs[0]
        elif context.get('file_changes', {}).get('new_files'):
            commit_type = "feat"
            main_feature = "Session Preservation Agent implementation"
        else:
            commit_type = "docs"
            main_feature = "session state preservation"
        
        # Generate commit message
        commit_msg = f"{commit_type}(session): {main_feature}\n\n"
        
        # Add achievements
        achievements = context.get('progress_analysis', {}).get('achievements', [])
        if achievements:
            commit_msg += "Achievements:\n"
            for achievement in achievements[:3]:  # Top 3
                commit_msg += f"- {achievement}\n"
            commit_msg += "\n"
        
        # Add file summary
        modified = len(context.get('file_changes', {}).get('modified_files', []))
        new = len(context.get('file_changes', {}).get('new_files', []))
        if modified or new:
            commit_msg += f"File changes: {modified} modified, {new} new\n\n"
        
        # Add agent info
        agents = context.get('agent_status', {}).get('agents_discovered', 0)
        if agents:
            commit_msg += f"Multi-agent system: {agents} agents operational\n\n"
        
        # Add standard footer
        commit_msg += "🤖 Generated with Session Preservation Agent\n\n"
        commit_msg += "Co-Authored-By: Claude <noreply@anthropic.com>"
        
        return commit_msg
    
    def prepare_startup_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare comprehensive startup context for next Claude session
        
        Args:
            context: Session context
            
        Returns:
            Dictionary with startup preparation results
        """
        self.logger.info("Preparing startup context...")
        
        results = {
            "context_prepared": False,
            "startup_files_checked": [],
            "recommendations": [],
            "errors": []
        }
        
        try:
            # 1. Verify critical startup files exist
            critical_startup_files = [
                "load_context_for_claude.py",
                "CLAUDE.md", 
                "CLAUDE_STARTUP_INSTRUCTIONS.md",
                "V8_SESSION_HANDOFF.md"
            ]
            
            for file_name in critical_startup_files:
                file_path = self.working_dir / file_name
                if file_path.exists():
                    results["startup_files_checked"].append(f"✓ {file_name}")
                else:
                    results["startup_files_checked"].append(f"✗ {file_name} MISSING")
                    results["recommendations"].append(f"Create missing file: {file_name}")
            
            # 2. Generate startup recommendations
            if context.get('progress_analysis', {}).get('next_priorities'):
                results["recommendations"].append("Priority tasks loaded in session handoff")
            
            if context.get('git_status', {}).get('modified_files'):
                results["recommendations"].append("Git has uncommitted changes - review before starting")
            
            if context.get('agent_status', {}).get('agents_discovered', 0) > 0:
                agent_count = context['agent_status']['agents_discovered']
                results["recommendations"].append(f"{agent_count} agents available for processing")
            
            # 3. Verify agent system
            agents_config = self.working_dir / "config" / "agents.yaml"
            if agents_config.exists():
                results["startup_files_checked"].append("✓ Agent configuration available")
            else:
                results["recommendations"].append("Create config/agents.yaml for agent system")
            
            results["context_prepared"] = True
            self.logger.info("Startup context preparation completed")
            
        except Exception as e:
            self.logger.error(f"Error preparing startup context: {e}")
            results["errors"].append(str(e))
        
        return results
    
    def show_status(self) -> Dict[str, Any]:
        """Show comprehensive preservation status"""
        status = {
            "agent_info": {
                "name": self.name,
                "version": "1.0.0",
                "status": self.status.value,
                "git_enabled": self.git_enabled
            },
            "capabilities": [
                "Context capture and analysis",
                "Documentation updates",
                "Git operations with comprehensive commits", 
                "Progress tracking and state preservation",
                "Startup context preparation"
            ],
            "working_directory": str(self.working_dir),
            "session_patterns": self.session_patterns,
            "critical_files_monitored": self.critical_files
        }
        
        # Add current directory status
        try:
            if self.git_enabled:
                result = subprocess.run(['git', 'status', '--porcelain'], 
                                        cwd=self.working_dir, capture_output=True, text=True)
                changed_files = result.stdout.strip().split('\n') if result.stdout.strip() else []
                status["current_git_status"] = {
                    "files_changed": len(changed_files),
                    "changes": changed_files[:5]  # Show first 5
                }
            
            # Check for session files
            session_files = []
            for pattern in self.session_patterns:
                session_files.extend(glob.glob(str(self.working_dir / pattern)))
            
            status["session_files_found"] = len(session_files)
            
        except Exception as e:
            status["status_error"] = str(e)
        
        return status


def create_cli():
    """Create CLI interface for Session Preservation Agent"""
    
    def main():
        """Main CLI interface"""
        parser = argparse.ArgumentParser(
            description="Session Preservation Agent - V9 Document Translator",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Commands:
  preserve    Complete session preservation (context + docs + commit)
  capture     Capture current context and progress
  commit      Git operations with comprehensive commit messages
  prepare     Prepare startup context for next session
  status      Show preservation status
  help        Show detailed help
  exit        Safe agent shutdown

Examples:
  python -m session_preservation_agent preserve
  python -m session_preservation_agent status
  python -m session_preservation_agent commit --message "Custom commit"
            """
        )
        
        parser.add_argument('command', 
                           choices=['preserve', 'capture', 'commit', 'prepare', 'status', 'help', 'exit'],
                           help='Command to execute')
        
        parser.add_argument('--message', '-m', 
                           help='Custom commit message')
        
        parser.add_argument('--verbose', '-v', 
                           action='store_true',
                           help='Verbose output')
        
        args = parser.parse_args()
        
        # Initialize agent
        agent = SessionPreservationAgent()
        
        if args.verbose:
            logging.getLogger().setLevel(logging.DEBUG)
        
        try:
            if args.command == 'help':
                parser.print_help()
                print("\nSession Preservation Agent Capabilities:")
                print("- Comprehensive context capture and analysis")
                print("- Automatic documentation updates")
                print("- Git operations with intelligent commit messages")
                print("- Progress tracking across sessions")
                print("- Startup context preparation")
                print("\nThis agent removes token-expensive operations from Claude's main interface.")
                return
            
            elif args.command == 'exit':
                print("Session Preservation Agent shutting down...")
                agent.cleanup()
                return
            
            elif args.command == 'status':
                status = agent.show_status()
                print("\n=== Session Preservation Agent Status ===")
                print(f"Agent: {status['agent_info']['name']} v{status['agent_info']['version']}")
                print(f"Status: {status['agent_info']['status']}")
                print(f"Git: {'Available' if status['agent_info']['git_enabled'] else 'Unavailable'}")
                print(f"Working Directory: {status['working_directory']}")
                
                if 'current_git_status' in status:
                    git_status = status['current_git_status']
                    print(f"\nGit Status: {git_status['files_changed']} files changed")
                    if git_status['changes']:
                        for change in git_status['changes'][:3]:
                            print(f"  {change}")
                
                print(f"\nSession Files Found: {status['session_files_found']}")
                print(f"Critical Files Monitored: {len(status['critical_files_monitored'])}")
                
                print("\nCapabilities:")
                for capability in status['capabilities']:
                    print(f"  - {capability}")
                
            elif args.command == 'capture':
                print("Capturing session context...")
                context = agent.capture_session_context()
                
                print("\n=== Context Capture Results ===")
                print(f"Session Files: {len(context.get('session_files', {}))}")
                print(f"Git Available: {context.get('git_status', {}).get('available', False)}")
                print(f"Agents Discovered: {context.get('agent_status', {}).get('agents_discovered', 0)}")
                
                progress = context.get('progress_analysis', {})
                if progress.get('achievements'):
                    print(f"Achievements: {len(progress['achievements'])}")
                if progress.get('breakthroughs'):
                    print("Breakthroughs detected:")
                    for breakthrough in progress['breakthroughs'][:3]:
                        print(f"  - {breakthrough}")
                
                # Save context to file for inspection
                context_file = Path(agent.working_dir) / "session_context_capture.json"
                with open(context_file, 'w', encoding='utf-8') as f:
                    json.dump(context, f, indent=2, ensure_ascii=False, default=str)
                print(f"\nFull context saved to: {context_file}")
            
            elif args.command == 'commit':
                print("Performing git operations...")
                context = agent.capture_session_context()
                
                git_results = agent.perform_git_operations(context, args.message)
                
                print("\n=== Git Operations Results ===")
                if git_results.get('staged_files'):
                    print(f"Staged {len(git_results['staged_files'])} files:")
                    for file_path in git_results['staged_files'][:5]:
                        print(f"  {file_path}")
                    
                if git_results.get('commit_created'):
                    print(f"Commit created: {git_results.get('commit_hash', 'unknown')}")
                else:
                    print("No commit created")
                
                if git_results.get('errors'):
                    print("Errors:")
                    for error in git_results['errors']:
                        print(f"  - {error}")
            
            elif args.command == 'prepare':
                print("Preparing startup context...")
                context = agent.capture_session_context()
                
                prep_results = agent.prepare_startup_context(context)
                
                print("\n=== Startup Context Preparation ===")
                if prep_results['startup_files_checked']:
                    print("Startup files status:")
                    for file_status in prep_results['startup_files_checked']:
                        print(f"  {file_status}")
                
                if prep_results['recommendations']:
                    print("\nRecommendations for next session:")
                    for rec in prep_results['recommendations']:
                        print(f"  - {rec}")
            
            elif args.command == 'preserve':
                print("Starting complete session preservation...")
                
                # 1. Capture context
                print("1/4 Capturing session context...")
                context = agent.capture_session_context()
                
                # 2. Update documentation
                print("2/4 Updating documentation...")
                doc_results = agent.update_documentation(context)
                
                # 3. Git operations
                print("3/4 Performing git operations...")
                git_results = agent.perform_git_operations(context)
                
                # 4. Prepare startup context
                print("4/4 Preparing startup context...")
                prep_results = agent.prepare_startup_context(context)
                
                print("\n=== Session Preservation Complete ===")
                print(f"Session files tracked: {len(context.get('session_files', {}))}")
                print(f"Documentation updated: {len(doc_results.get('updated_files', []))}")
                print(f"Files committed: {len(git_results.get('staged_files', []))}")
                print(f"Context prepared: {'Yes' if prep_results.get('context_prepared') else 'No'}")
                
                if git_results.get('commit_hash'):
                    print(f"Commit: {git_results['commit_hash']}")
                
                print("\nNext session startup:")
                print("1. Run: python load_context_for_claude.py")
                print("2. Review: V8_SESSION_HANDOFF.md")
                print("3. Continue with preserved context")
        
        except KeyboardInterrupt:
            print("\nSession Preservation Agent interrupted")
            agent.cleanup()
        except Exception as e:
            print(f"\nError: {e}")
            agent.cleanup()
    
    return main


if __name__ == "__main__":
    cli = create_cli()
    cli()