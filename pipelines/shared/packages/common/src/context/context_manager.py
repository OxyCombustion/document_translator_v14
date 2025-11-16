#!/usr/bin/env python3
"""
V9 Context Management System
Handles optimal context handoff for local-claude and agent systems
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
import sys

class ContextManager:
    """
    Manages context profiles and optimal information handoff for V9 agents
    """
    
    def __init__(self, profiles_file: str = "V8_CONTEXT_PROFILES.json"):
        """
        Initialize context manager with agent profiles
        
        Args:
            profiles_file: Path to agent context profiles JSON file
        """
        self.profiles_file = Path(profiles_file)
        self.profiles = self._load_profiles()
        self.context_cache = {}
        self.session_data = self._load_session_data()
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
    
    def _load_profiles(self) -> Dict[str, Any]:
        """Load agent context profiles from JSON file"""
        try:
            if self.profiles_file.exists():
                with open(self.profiles_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                self.logger.warning(f"Context profiles file not found: {self.profiles_file}")
                return {}
        except Exception as e:
            self.logger.error(f"Failed to load context profiles: {e}")
            return {}
    
    def _load_session_data(self) -> Dict[str, Any]:
        """Load current session data for dynamic context"""
        session_data = {}
        
        # Load session state
        session_file = Path("V8_SESSION_STATE.json")
        if session_file.exists():
            try:
                with open(session_file, 'r') as f:
                    session_data['session_state'] = json.load(f)
            except Exception as e:
                self.logger.warning(f"Could not load session state: {e}")
        
        # Load ML metrics
        ml_metrics_file = Path("V8_ML_METRICS.json")
        if ml_metrics_file.exists():
            try:
                with open(ml_metrics_file, 'r') as f:
                    session_data['ml_metrics'] = json.load(f)
            except Exception as e:
                self.logger.warning(f"Could not load ML metrics: {e}")
        
        # Load current priorities from handoff
        handoff_file = Path("V8_SESSION_HANDOFF.md")
        if handoff_file.exists():
            try:
                with open(handoff_file, 'r', encoding='utf-8') as f:
                    handoff_content = f.read()
                    session_data['handoff_content'] = handoff_content
                    # Extract critical priorities
                    session_data['critical_priorities'] = self._extract_priorities(handoff_content)
            except Exception as e:
                self.logger.warning(f"Could not load session handoff: {e}")
        
        return session_data
    
    def _extract_priorities(self, handoff_content: str) -> List[str]:
        """Extract critical priorities from session handoff"""
        priorities = []
        try:
            if "Next Session Priorities" in handoff_content:
                priorities_section = handoff_content.split("Next Session Priorities")[1].split("## ")[0]
                priorities = [
                    line.strip() 
                    for line in priorities_section.split('\n') 
                    if line.strip().startswith(('1.', '2.', '3.', '4.', '5.'))
                ][:5]  # Top 5 priorities
        except Exception as e:
            self.logger.warning(f"Could not extract priorities: {e}")
        return priorities
    
    def get_agent_context(self, agent_name: str) -> Dict[str, Any]:
        """
        Get optimized context for a specific agent
        
        Args:
            agent_name: Name of the agent (e.g., 'EnhancedTableAgent')
            
        Returns:
            Dictionary containing agent-specific context
        """
        if agent_name in self.context_cache:
            self.logger.info(f"Using cached context for {agent_name}")
            return self.context_cache[agent_name]
        
        # Get agent profile
        agent_profile = self.profiles.get('agent_profiles', {}).get(agent_name)
        if not agent_profile:
            self.logger.warning(f"No context profile found for {agent_name}")
            return self._get_default_context()
        
        # Assemble agent-specific context
        context = {
            'agent_name': agent_name,
            'context_generated': datetime.now().isoformat(),
            'size_target_kb': agent_profile.get('size_target_kb', 5),
            'priority': agent_profile.get('priority', 'MEDIUM')
        }
        
        # Add required context based on profile
        required_context = agent_profile.get('required_context', {})
        
        if agent_name == 'ContextAwareDocumentationAgent':
            # Special case: needs complete context
            context['complete_context'] = self._get_complete_context()
        else:
            # Standard agents: get focused context
            context.update(self._assemble_focused_context(required_context))
        
        # Add current session data
        context['current_session'] = {
            'session_start': self.session_data.get('session_state', {}).get('startup_timestamp'),
            'gpu_available': self.session_data.get('session_state', {}).get('gpu_available', False),
            'ml_confidence': self.session_data.get('ml_metrics', {}).get('average_confidence', 0.0),
            'documents_processed': self.session_data.get('ml_metrics', {}).get('documents_processed', 0),
            'critical_priorities': self.session_data.get('critical_priorities', [])
        }
        
        # Cache the context
        self.context_cache[agent_name] = context
        
        # Log context size
        context_size = self._estimate_context_size(context)
        self.logger.info(f"Generated context for {agent_name}: {context_size:.1f}KB")
        
        if context_size > agent_profile.get('size_target_kb', 5) * 1.2:
            self.logger.warning(f"Context size ({context_size:.1f}KB) exceeds target for {agent_name}")
        
        return context
    
    def _assemble_focused_context(self, required_context: Dict[str, Any]) -> Dict[str, Any]:
        """Assemble focused context based on agent requirements"""
        context = {}
        
        # Add engineering principles if required
        if 'engineering_principles' in required_context:
            context['engineering_principles'] = self._get_engineering_principles_subset(
                required_context['engineering_principles']
            )
        
        # Add current priorities if required
        if 'current_priorities' in required_context:
            context['current_priorities'] = required_context['current_priorities']
        
        # Add performance targets if required
        if 'performance_targets' in required_context:
            context['performance_targets'] = required_context['performance_targets']
        
        # Add ML requirements if required
        if 'ml_requirements' in required_context:
            context['ml_requirements'] = required_context['ml_requirements']
            # Enhance with current ML metrics
            if 'ml_metrics' in self.session_data:
                context['ml_requirements']['current_metrics'] = self.session_data['ml_metrics']
        
        # Add spatial metadata if required
        if 'spatial_metadata' in required_context:
            context['spatial_metadata'] = required_context['spatial_metadata']
        
        # Add processing standards if required
        if 'processing_standards' in required_context:
            context['processing_standards'] = required_context['processing_standards']
        
        return context
    
    def _get_engineering_principles_subset(self, principles_spec: Dict[str, Any]) -> Dict[str, Any]:
        """Get subset of engineering principles based on agent needs"""
        # This would normally read from V8_SOFTWARE_ENGINEERING_PRINCIPLES.md
        # For now, return the spec with a note to reference the full file
        return {
            'required_sections': principles_spec.get('sections', []),
            'why_needed': principles_spec.get('why'),
            'reference_file': principles_spec.get('file', 'V8_SOFTWARE_ENGINEERING_PRINCIPLES.md'),
            'note': 'Agent should reference full engineering principles file for complete standards'
        }
    
    def _get_complete_context(self) -> Dict[str, Any]:
        """Get complete project context for documentation agent"""
        return {
            'note': 'Documentation agent requires complete project context',
            'session_data': self.session_data,
            'full_documentation_files': [
                'V8_SOFTWARE_ENGINEERING_PRINCIPLES.md',
                'V8_EXTERNAL_DEPENDENCIES.md',
                'V8_SOFTWARE_REQUIREMENTS.md',
                'V8_SOFTWARE_DESIGN.md',
                'V8_TRIPLE_METHOD_ARCHITECTURE.md',
                'V8_CONTEXT_MANAGEMENT.md'
            ],
            'current_context_size': '169.3KB total across 15 files',
            'access_method': 'Agent should read all referenced documentation files'
        }
    
    def _get_default_context(self) -> Dict[str, Any]:
        """Get default context for agents without specific profiles"""
        return {
            'agent_name': 'Unknown',
            'context_generated': datetime.now().isoformat(),
            'warning': 'No specific context profile found - using default minimal context',
            'basic_session_data': {
                'session_start': self.session_data.get('session_state', {}).get('startup_timestamp'),
                'gpu_available': self.session_data.get('session_state', {}).get('gpu_available', False)
            },
            'recommendation': 'Add agent profile to V8_CONTEXT_PROFILES.json for optimal context'
        }
    
    def _estimate_context_size(self, context: Dict[str, Any]) -> float:
        """Estimate context size in KB"""
        try:
            context_json = json.dumps(context, indent=2)
            return len(context_json.encode('utf-8')) / 1024
        except Exception:
            return 0.0
    
    def save_agent_context(self, agent_name: str, context: Dict[str, Any]) -> bool:
        """
        Save agent context to file for debugging/analysis
        
        Args:
            agent_name: Name of the agent
            context: Context dictionary to save
            
        Returns:
            True if successful, False otherwise
        """
        try:
            context_file = Path(f"V8_AGENT_CONTEXT_{agent_name}.json")
            with open(context_file, 'w', encoding='utf-8') as f:
                json.dump(context, f, indent=2)
            
            context_size = self._estimate_context_size(context)
            self.logger.info(f"Saved context for {agent_name} ({context_size:.1f}KB): {context_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to save context for {agent_name}: {e}")
            return False
    
    def get_context_summary(self) -> Dict[str, Any]:
        """Get summary of all agent context profiles and sizes"""
        summary = {
            'total_agents': len(self.profiles.get('agent_profiles', {})),
            'context_profiles_loaded': bool(self.profiles),
            'session_data_available': bool(self.session_data),
            'agent_summaries': {}
        }
        
        for agent_name, profile in self.profiles.get('agent_profiles', {}).items():
            summary['agent_summaries'][agent_name] = {
                'size_target_kb': profile.get('size_target_kb', 0),
                'priority': profile.get('priority', 'UNKNOWN'),
                'context_cached': agent_name in self.context_cache
            }
        
        return summary
    
    def clear_context_cache(self):
        """Clear cached contexts (useful when session data changes)"""
        self.context_cache = {}
        self.logger.info("Context cache cleared")
    
    def refresh_session_data(self):
        """Refresh session data from files"""
        self.session_data = self._load_session_data()
        self.clear_context_cache()  # Clear cache since session data changed
        self.logger.info("Session data refreshed")


def get_agent_context(agent_name: str) -> Dict[str, Any]:
    """
    Convenience function to get agent context
    
    Args:
        agent_name: Name of the agent
        
    Returns:
        Agent-specific context dictionary
    """
    context_manager = ContextManager()
    return context_manager.get_agent_context(agent_name)


def main():
    """Test the context management system"""
    context_manager = ContextManager()
    
    print("V9 Context Management System Test")
    print("=" * 40)
    
    # Test context summary
    summary = context_manager.get_context_summary()
    print(f"Total agents: {summary['total_agents']}")
    print(f"Context profiles loaded: {summary['context_profiles_loaded']}")
    print(f"Session data available: {summary['session_data_available']}")
    
    # Test specific agent contexts
    test_agents = ['EnhancedTableAgent', 'DocumentObjectAgent', 'ContextAwareDocumentationAgent']
    
    for agent in test_agents:
        print(f"\nTesting context for {agent}:")
        context = context_manager.get_agent_context(agent)
        size = context_manager._estimate_context_size(context)
        print(f"  Context size: {size:.1f}KB")
        print(f"  Priority: {context.get('priority', 'UNKNOWN')}")
        
        # Save context for inspection
        context_manager.save_agent_context(agent, context)


if __name__ == "__main__":
    main()