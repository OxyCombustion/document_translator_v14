"""
Project Context Loader for V9 Agents
Provides comprehensive project context to ensure agents follow established principles and requirements
"""

import json
import re
from pathlib import Path
from typing import Dict, Any, Optional, List
import logging
from dataclasses import dataclass
from enum import Enum
import time

logger = logging.getLogger(__name__)


class ContextType(Enum):
    """Types of project context"""
    ENGINEERING_PRINCIPLES = "engineering_principles"
    REQUIREMENTS = "requirements"
    ARCHITECTURE = "architecture"
    EXTERNAL_DEPENDENCIES = "external_dependencies"
    SOFTWARE_DESIGN = "software_design"


@dataclass
class ContextSection:
    """Parsed context section with metadata"""
    title: str
    content: str
    guidelines: List[str]
    examples: List[str]
    requirements: List[str]
    priority: str = "normal"


@dataclass
class ProjectContext:
    """Complete project context for agents"""
    engineering_principles: Dict[str, Any]
    requirements: Dict[str, Any]
    architecture: Dict[str, Any]
    external_dependencies: Dict[str, Any]
    software_design: Dict[str, Any]
    last_updated: str
    context_version: str = "1.0"
    
    def get_selective_context(self, sections: List[str]) -> 'ProjectContext':
        """Create a new ProjectContext with only specified sections"""
        return ProjectContext(
            engineering_principles=self.engineering_principles if 'engineering_principles' in sections else {},
            requirements=self.requirements if 'requirements' in sections else {},
            architecture=self.architecture if 'architecture' in sections else {},
            external_dependencies=self.external_dependencies if 'external_dependencies' in sections else {},
            software_design=self.software_design if 'software_design' in sections else {},
            last_updated=self.last_updated,
            context_version=f"{self.context_version}-selective"
        )
        
    def get_summarized_context(self) -> Dict[str, Any]:
        """Get a memory-efficient summary of the context"""
        return {
            'principles_summary': self._summarize_dict(self.engineering_principles),
            'requirements_summary': self._summarize_dict(self.requirements),
            'architecture_summary': self._summarize_dict(self.architecture),
            'dependencies_summary': self._summarize_dict(self.external_dependencies),
            'design_summary': self._summarize_dict(self.software_design),
            'version': self.context_version,
            'last_updated': self.last_updated
        }
        
    def _summarize_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a summary of a dictionary section"""
        if not data:
            return {}
            
        return {
            'sections': list(data.keys()),
            'size': len(str(data)),
            'last_modified': self.last_updated
        }


class ProjectContextLoader:
    """Loads and parses project context for agent use"""
    
    def __init__(self, project_root: Optional[Path] = None):
        self.project_root = project_root or Path(".")
        self.context_cache = {}
        self.cache_timestamps = {}
        self.section_cache = {}
        self.summary_cache = None
        
        # Define critical context files
        self.context_files = {
            ContextType.ENGINEERING_PRINCIPLES: "V8_SOFTWARE_ENGINEERING_PRINCIPLES.md",
            ContextType.REQUIREMENTS: ["V8_SOFTWARE_REQUIREMENTS.md", "V8_ENHANCED_REQUIREMENTS.md"],
            ContextType.ARCHITECTURE: "V8_TRIPLE_METHOD_ARCHITECTURE.md",
            ContextType.EXTERNAL_DEPENDENCIES: "V8_EXTERNAL_DEPENDENCIES.md",
            ContextType.SOFTWARE_DESIGN: "V8_SOFTWARE_DESIGN.md"
        }
        
        logger.info("ProjectContextLoader initialized")
    
    def load_complete_context(self, force_reload: bool = False) -> ProjectContext:
        """
        Load complete project context for agent use
        
        Args:
            force_reload: Force reload even if cached
            
        Returns:
            ProjectContext with all critical information
        """
        if not force_reload and self._is_cache_valid():
            logger.debug("Using cached project context")
            return self._get_cached_context()
        
        logger.info("Loading fresh project context")
        start_time = time.time()
        
        try:
            # Load all context types
            engineering_principles = self._load_engineering_principles()
            requirements = self._load_requirements()
            architecture = self._load_architecture()
            external_dependencies = self._load_external_dependencies()
            software_design = self._load_software_design()
            
            # Create complete context
            context = ProjectContext(
                engineering_principles=engineering_principles,
                requirements=requirements,
                architecture=architecture,
                external_dependencies=external_dependencies,
                software_design=software_design,
                last_updated=time.strftime("%Y-%m-%d %H:%M:%S"),
                context_version="1.0"
            )
            
            # Cache the context
            self._cache_context(context)
            
            load_time = time.time() - start_time
            logger.info(f"Project context loaded successfully in {load_time:.2f}s")
            
            return context
            
        except Exception as e:
            logger.error(f"Failed to load project context: {e}")
            # Return minimal context to prevent agent failure
            return self._create_minimal_context()
    
    def _load_engineering_principles(self) -> Dict[str, Any]:
        """Load software engineering principles"""
        file_path = self.project_root / self.context_files[ContextType.ENGINEERING_PRINCIPLES]
        
        if not file_path.exists():
            logger.warning(f"Engineering principles file not found: {file_path}")
            return self._get_default_principles()
        
        try:
            content = file_path.read_text(encoding='utf-8')
            
            principles = {
                'documentation_standards': self._extract_documentation_standards(content),
                'error_handling_patterns': self._extract_error_handling_patterns(content),
                'naming_conventions': self._extract_naming_conventions(content),
                'timeout_protocols': self._extract_timeout_protocols(content),
                'logging_requirements': self._extract_logging_requirements(content),
                'code_quality_metrics': self._extract_quality_metrics(content),
                'testing_standards': self._extract_testing_standards(content),
                'anti_patterns': self._extract_anti_patterns(content)
            }
            
            logger.debug("Engineering principles loaded successfully")
            return principles
            
        except Exception as e:
            logger.error(f"Failed to parse engineering principles: {e}")
            return self._get_default_principles()
    
    def _load_requirements(self) -> Dict[str, Any]:
        """Load project requirements from multiple files"""
        requirements = {}
        
        # Handle multiple requirement files
        files = self.context_files[ContextType.REQUIREMENTS]
        if isinstance(files, str):
            files = [files]
        
        for req_file in files:
            file_path = self.project_root / req_file
            
            if not file_path.exists():
                logger.warning(f"Requirements file not found: {file_path}")
                continue
            
            try:
                content = file_path.read_text(encoding='utf-8')
                
                # Parse different types of requirements
                file_requirements = {
                    'functional_requirements': self._extract_functional_requirements(content),
                    'performance_targets': self._extract_performance_targets(content),
                    'quality_standards': self._extract_quality_standards(content),
                    'integration_requirements': self._extract_integration_requirements(content),
                    'ml_requirements': self._extract_ml_requirements(content)
                }
                
                # Merge requirements
                for key, value in file_requirements.items():
                    if key not in requirements:
                        requirements[key] = {}
                    requirements[key].update(value)
                
                logger.debug(f"Requirements loaded from {req_file}")
                
            except Exception as e:
                logger.error(f"Failed to parse requirements from {req_file}: {e}")
        
        return requirements
    
    def _load_architecture(self) -> Dict[str, Any]:
        """Load architecture principles and patterns"""
        file_path = self.project_root / self.context_files[ContextType.ARCHITECTURE]
        
        if not file_path.exists():
            logger.warning(f"Architecture file not found: {file_path}")
            return self._get_default_architecture()
        
        try:
            content = file_path.read_text(encoding='utf-8')
            
            architecture = {
                'triple_method_principle': self._extract_triple_method_principle(content),
                'agent_communication_protocols': self._extract_communication_protocols(content),
                'spatial_metadata_standards': self._extract_spatial_standards(content),
                'processing_patterns': self._extract_processing_patterns(content),
                'integration_patterns': self._extract_integration_patterns(content)
            }
            
            logger.debug("Architecture context loaded successfully")
            return architecture
            
        except Exception as e:
            logger.error(f"Failed to parse architecture: {e}")
            return self._get_default_architecture()
    
    def _load_external_dependencies(self) -> Dict[str, Any]:
        """Load external dependency integration patterns"""
        file_path = self.project_root / self.context_files[ContextType.EXTERNAL_DEPENDENCIES]
        
        if not file_path.exists():
            logger.warning(f"External dependencies file not found: {file_path}")
            return {}
        
        try:
            content = file_path.read_text(encoding='utf-8')
            
            dependencies = {
                'mathematica_integration': self._extract_mathematica_patterns(content),
                'pymupdf_patterns': self._extract_pymupdf_patterns(content),
                'docling_integration': self._extract_docling_patterns(content),
                'gemini_integration': self._extract_gemini_patterns(content),
                'ml_libraries': self._extract_ml_library_patterns(content),
                'hardware_requirements': self._extract_hardware_requirements(content)
            }
            
            logger.debug("External dependencies loaded successfully")
            return dependencies
            
        except Exception as e:
            logger.error(f"Failed to parse external dependencies: {e}")
            return {}
    
    def _load_software_design(self) -> Dict[str, Any]:
        """Load detailed software design specifications"""
        file_path = self.project_root / self.context_files[ContextType.SOFTWARE_DESIGN]
        
        if not file_path.exists():
            logger.warning(f"Software design file not found: {file_path}")
            return {}
        
        try:
            content = file_path.read_text(encoding='utf-8')
            
            design = {
                'system_architecture': self._extract_system_architecture(content),
                'data_flow_patterns': self._extract_data_flow(content),
                'component_interfaces': self._extract_interfaces(content),
                'scalability_patterns': self._extract_scalability(content)
            }
            
            logger.debug("Software design loaded successfully")
            return design
            
        except Exception as e:
            logger.error(f"Failed to parse software design: {e}")
            return {}
    
    def _extract_documentation_standards(self, content: str) -> Dict[str, Any]:
        """Extract documentation standards from content"""
        standards = {}
        
        # Look for documentation sections
        doc_patterns = [
            r"### \d+\. Comprehensive Documentation Standards(.*?)(?=###|\Z)",
            r"## Documentation Standards(.*?)(?=##|\Z)",
            r"- \*\*Every public function must have docstrings\*\*(.*?)(?=\n- |\Z)"
        ]
        
        for pattern in doc_patterns:
            matches = re.findall(pattern, content, re.DOTALL | re.IGNORECASE)
            if matches:
                standards['docstring_requirements'] = "Every public function must have docstrings with purpose, parameters, returns, and examples"
                standards['comment_focus'] = "Comments should explain WHY, not WHAT - the code shows what, comments explain why"
                standards['architecture_decisions'] = "Architectural decisions must be documented with rationale and alternatives considered"
                break
        
        # Extract Unicode/encoding standards
        unicode_pattern = r"### \d+\. Unicode and Encoding Standards.*?CRITICAL\)(.*?)(?=###|\Z)"
        unicode_matches = re.findall(unicode_pattern, content, re.DOTALL | re.IGNORECASE)
        if unicode_matches:
            standards['unicode_encoding'] = {
                'utf8_required': "Always use UTF-8 encoding for all file operations",
                'windows_compatibility': "Set UTF-8 encoding for stdout/stderr on Windows",
                'file_operations': "Always specify encoding='utf-8' when reading/writing files",
                'console_output': "Avoid Unicode symbols in print statements on Windows",
                'required_pattern': "Every Python script should include UTF-8 setup for Windows compatibility"
            }
        
        # Extract specific examples
        example_pattern = r"```python(.*?)```"
        examples = re.findall(example_pattern, content, re.DOTALL)
        if examples:
            standards['examples'] = examples[:3]  # Keep first 3 examples
        
        return standards
    
    def _extract_error_handling_patterns(self, content: str) -> Dict[str, Any]:
        """Extract error handling patterns"""
        patterns = {}
        
        # Look for error handling sections
        error_patterns = [
            r"### \d+\. Error Handling and Robustness(.*?)(?=###|\Z)",
            r"## Error Handling(.*?)(?=##|\Z)",
            r"- \*\*Graceful Degradation\*\*(.*?)(?=\n- |\Z)"
        ]
        
        for pattern in error_patterns:
            matches = re.findall(pattern, content, re.DOTALL | re.IGNORECASE)
            if matches:
                patterns['graceful_degradation'] = "System continues with reduced functionality when components fail"
                patterns['circuit_breakers'] = "Prevent cascade failures across agents"
                patterns['timeout_protection'] = "All operations must have reasonable time limits"
                patterns['retry_logic'] = "Automatic retry with exponential backoff for transient failures"
                break
        
        # Extract timeout decorator if present
        timeout_pattern = r"@with_timeout_and_retry.*?def.*?:"
        if re.search(timeout_pattern, content, re.DOTALL):
            patterns['timeout_decorator'] = "Use @with_timeout_and_retry decorator for operations"
        
        return patterns
    
    def _extract_timeout_protocols(self, content: str) -> Dict[str, Any]:
        """Extract timeout and safety protocols"""
        protocols = {}
        
        # Look for timeout-related content
        timeout_patterns = [
            r"timeout_seconds.*?(\d+)",
            r"max_retries.*?(\d+)",
            r"exponential backoff",
            r"Operation-Based Development.*?time-boxing.*?(\d+-\d+)\s*minutes"
        ]
        
        for pattern in timeout_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches:
                if "timeout_seconds" in pattern:
                    protocols['default_timeout'] = int(matches[0])
                elif "max_retries" in pattern:
                    protocols['default_retries'] = int(matches[0])
                elif "time-boxing" in pattern and matches:
                    protocols['operation_time_limit'] = matches[0] + " minutes"
        
        # Set defaults if not found
        if 'default_timeout' not in protocols:
            protocols['default_timeout'] = 30
        if 'default_retries' not in protocols:
            protocols['default_retries'] = 3
        if 'operation_time_limit' not in protocols:
            protocols['operation_time_limit'] = "5-10 minutes"
        
        return protocols
    
    def _extract_performance_targets(self, content: str) -> Dict[str, Any]:
        """Extract performance requirements"""
        targets = {}
        
        # Look for performance targets
        perf_patterns = [
            r"(\d+)% confidence",
            r"(\d+)x faster",
            r"(\d+)% memory reduction",
            r"<(\d+)s.*?processing",
            r">(\d+)% accuracy"
        ]
        
        for pattern in perf_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches:
                if "confidence" in pattern:
                    targets['min_confidence'] = float(matches[0]) / 100
                elif "faster" in pattern:
                    targets['speed_improvement'] = f"{matches[0]}x"
                elif "memory reduction" in pattern:
                    targets['memory_efficiency'] = f"{matches[0]}% reduction"
                elif "processing" in pattern:
                    targets['max_processing_time'] = f"{matches[0]}s"
                elif "accuracy" in pattern:
                    targets['min_accuracy'] = float(matches[0]) / 100
        
        return targets
    
    def _extract_triple_method_principle(self, content: str) -> Dict[str, Any]:
        """Extract Triple-Method Architecture principle"""
        principle = {}
        
        # Look for triple method description
        triple_pattern = r"(Docling.*?Gemini.*?Mathematica.*?equal|three.*?equal.*?extraction|Triple-Method.*?principle)"
        matches = re.findall(triple_pattern, content, re.DOTALL | re.IGNORECASE)
        
        if matches:
            principle['description'] = "V9 treats Docling, Google Gemini, and Mathematica as three equal extraction methods"
            principle['partners'] = ["Docling", "Google Gemini", "Mathematica"]
            principle['comparison_engine'] = "A comparison engine determines the best result for each content type"
            principle['equality'] = "All three methods are treated as equals, not fallbacks"
        
        return principle
    
    def _extract_anti_patterns(self, content: str) -> List[str]:
        """Extract documented anti-patterns"""
        anti_patterns = []
        
        # Look for anti-patterns section
        pattern = r"## .*Anti-Patterns.*?What NOT to Do\)(.*?)(?=##|\Z)"
        matches = re.findall(pattern, content, re.DOTALL | re.IGNORECASE)
        
        if matches:
            # Extract numbered items
            items = re.findall(r"\d+\.\s+\*\*(.*?)\*\*", matches[0])
            anti_patterns.extend(items)
        
        return anti_patterns
    
    def _get_default_principles(self) -> Dict[str, Any]:
        """Get default engineering principles if file not available"""
        return {
            'documentation_standards': {
                'docstring_requirements': "Every public function must have docstrings",
                'comment_focus': "Comments should explain WHY, not WHAT"
            },
            'error_handling_patterns': {
                'graceful_degradation': "System continues with reduced functionality",
                'timeout_protection': "All operations must have time limits"
            },
            'timeout_protocols': {
                'default_timeout': 30,
                'default_retries': 3
            }
        }
    
    def _get_default_architecture(self) -> Dict[str, Any]:
        """Get default architecture if file not available"""
        return {
            'triple_method_principle': {
                'description': "Three equal extraction methods",
                'partners': ["Docling", "Google Gemini", "Mathematica"]
            }
        }
    
    def _create_minimal_context(self) -> ProjectContext:
        """Create minimal context for fallback"""
        return ProjectContext(
            engineering_principles=self._get_default_principles(),
            requirements={},
            architecture=self._get_default_architecture(),
            external_dependencies={},
            software_design={},
            last_updated=time.strftime("%Y-%m-%d %H:%M:%S"),
            context_version="minimal"
        )
    
    def _is_cache_valid(self) -> bool:
        """Check if cached context is still valid"""
        if not self.context_cache:
            return False
        
        # Check if any context files have been modified
        for context_type, file_path in self.context_files.items():
            if isinstance(file_path, list):
                paths = [self.project_root / f for f in file_path]
            else:
                paths = [self.project_root / file_path]
            
            for path in paths:
                if path.exists():
                    file_time = path.stat().st_mtime
                    cached_time = self.cache_timestamps.get(str(path), 0)
                    
                    if file_time > cached_time:
                        return False
        
        return True
    
    def _cache_context(self, context: ProjectContext):
        """Cache the loaded context and sections"""
        self.context_cache = context
        
        # Cache individual sections
        self.section_cache['engineering_principles'] = context.engineering_principles
        self.section_cache['requirements'] = context.requirements
        self.section_cache['architecture'] = context.architecture
        self.section_cache['external_dependencies'] = context.external_dependencies
        self.section_cache['software_design'] = context.software_design
        
        # Cache summary
        self.summary_cache = context.get_summarized_context()
        
        # Update timestamps
        for context_type, file_path in self.context_files.items():
            if isinstance(file_path, list):
                paths = [self.project_root / f for f in file_path]
            else:
                paths = [self.project_root / file_path]
            
            for path in paths:
                if path.exists():
                    self.cache_timestamps[str(path)] = path.stat().st_mtime
    
    def _get_cached_context(self) -> ProjectContext:
        """Get complete cached context"""
        return self.context_cache
        
    def _get_cached_sections(self, sections: List[str]) -> ProjectContext:
        """Get cached context for specific sections"""
        return ProjectContext(
            engineering_principles=self.section_cache.get('engineering_principles', {}) if 'engineering_principles' in sections else {},
            requirements=self.section_cache.get('requirements', {}) if 'requirements' in sections else {},
            architecture=self.section_cache.get('architecture', {}) if 'architecture' in sections else {},
            external_dependencies=self.section_cache.get('external_dependencies', {}) if 'external_dependencies' in sections else {},
            software_design=self.section_cache.get('software_design', {}) if 'software_design' in sections else {},
            last_updated=self.context_cache.last_updated if self.context_cache else time.strftime("%Y-%m-%d %H:%M:%S"),
            context_version=f"{self.context_cache.context_version if self.context_cache else '1.0'}-selective"
        )
        
    def get_context_summary(self, force_reload: bool = False) -> Dict[str, Any]:
        """Get a memory-efficient summary of the context"""
        if self.summary_cache is None or force_reload:
            context = self.load_complete_context(force_reload=force_reload)
            return context.get_summarized_context()
        return self.summary_cache
    
    # Placeholder methods for extracting specific patterns
    # These would be implemented based on the actual content structure
    
    def _extract_naming_conventions(self, content: str) -> Dict[str, Any]: return {}
    def _extract_logging_requirements(self, content: str) -> Dict[str, Any]: return {}
    def _extract_quality_metrics(self, content: str) -> Dict[str, Any]: return {}
    def _extract_testing_standards(self, content: str) -> Dict[str, Any]: return {}
    def _extract_functional_requirements(self, content: str) -> Dict[str, Any]: return {}
    def _extract_quality_standards(self, content: str) -> Dict[str, Any]: return {}
    def _extract_integration_requirements(self, content: str) -> Dict[str, Any]: return {}
    def _extract_ml_requirements(self, content: str) -> Dict[str, Any]: return {}
    def _extract_communication_protocols(self, content: str) -> Dict[str, Any]: return {}
    def _extract_spatial_standards(self, content: str) -> Dict[str, Any]: return {}
    def _extract_processing_patterns(self, content: str) -> Dict[str, Any]: return {}
    def _extract_integration_patterns(self, content: str) -> Dict[str, Any]: return {}
    def _extract_mathematica_patterns(self, content: str) -> Dict[str, Any]: return {}
    def _extract_pymupdf_patterns(self, content: str) -> Dict[str, Any]: return {}
    def _extract_docling_patterns(self, content: str) -> Dict[str, Any]: return {}
    def _extract_gemini_patterns(self, content: str) -> Dict[str, Any]: return {}
    def _extract_ml_library_patterns(self, content: str) -> Dict[str, Any]: return {}
    def _extract_hardware_requirements(self, content: str) -> Dict[str, Any]: return {}
    def _extract_system_architecture(self, content: str) -> Dict[str, Any]: return {}
    def _extract_data_flow(self, content: str) -> Dict[str, Any]: return {}
    def _extract_interfaces(self, content: str) -> Dict[str, Any]: return {}
    def _extract_scalability(self, content: str) -> Dict[str, Any]: return {}


# Global context loader instance
_context_loader = None

def get_project_context_loader(project_root: Optional[Path] = None) -> ProjectContextLoader:
    """Get global project context loader instance"""
    global _context_loader
    
    if _context_loader is None:
        _context_loader = ProjectContextLoader(project_root)
    
    return _context_loader

def load_agent_context(force_reload: bool = False) -> ProjectContext:
    """Convenience function to load complete project context for agents"""
    loader = get_project_context_loader()
    return loader.load_complete_context(force_reload)