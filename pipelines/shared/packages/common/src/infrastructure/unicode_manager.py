"""
Unicode Safety Display Manager - V9 Document Translator
Safe handling and display of Unicode characters including Greek letters

This module provides comprehensive Unicode safety for displaying content with
Greek letters and other special characters across different platforms, preventing
the recurring UnicodeEncodeError issues documented in CLAUDE_UTF8_MANDATORY_CHECKLIST.md

Author: V9 Development Team
Version: 8.2.0
Date: 2025-08-30

Critical Safety Implementation:
- Console-safe ASCII representations for Windows compatibility
- Full Unicode preservation in file outputs
- Multiple format support (LaTeX, HTML, ASCII)
- Platform-aware display decisions
"""

import sys
import io
import os
import json
from typing import Dict, Any, Optional, List
from pathlib import Path
from dataclasses import dataclass
import logging

# MANDATORY UTF-8 SETUP - CRITICAL FOR WINDOWS
# Following CLAUDE_UTF8_MANDATORY_CHECKLIST.md exactly
if sys.platform == 'win32':
    # Safer UTF-8 setup - only wrap if not already wrapped
    if not hasattr(sys.stdout, '_wrapped_utf8'):
        try:
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', line_buffering=True)
            sys.stdout._wrapped_utf8 = True
        except (AttributeError, ValueError):
            # Fallback - just set console encoding
            os.system('chcp 65001')
    
    # Handle stderr separately - important for complete UTF-8 support
    if not hasattr(sys.stderr, '_wrapped_utf8'):
        try:
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', line_buffering=True)
            sys.stderr._wrapped_utf8 = True
        except (AttributeError, ValueError):
            pass

# Import V9 base components
try:
    from ..core.logger import get_logger
except ImportError:
    # Fallback for direct execution
    import logging
    def get_logger(name):
        return logging.getLogger(name)

logger = get_logger("UnicodeSafetyManager")


# Greek letter mappings for safe display
GREEK_TO_ASCII = {
    # Lowercase Greek letters
    'α': 'alpha', 'β': 'beta', 'γ': 'gamma', 'δ': 'delta',
    'ε': 'epsilon', 'ζ': 'zeta', 'η': 'eta', 'θ': 'theta',
    'ι': 'iota', 'κ': 'kappa', 'λ': 'lambda', 'μ': 'mu',
    'ν': 'nu', 'ξ': 'xi', 'ο': 'omicron', 'π': 'pi',
    'ρ': 'rho', 'σ': 'sigma', 'τ': 'tau', 'υ': 'upsilon',
    'φ': 'phi', 'χ': 'chi', 'ψ': 'psi', 'ω': 'omega',
    
    # Uppercase Greek letters
    'Α': 'Alpha', 'Β': 'Beta', 'Γ': 'Gamma', 'Δ': 'Delta',
    'Ε': 'Epsilon', 'Ζ': 'Zeta', 'Η': 'Eta', 'Θ': 'Theta',
    'Ι': 'Iota', 'Κ': 'Kappa', 'Λ': 'Lambda', 'Μ': 'Mu',
    'Ν': 'Nu', 'Ξ': 'Xi', 'Ο': 'Omicron', 'Π': 'Pi',
    'Ρ': 'Rho', 'Σ': 'Sigma', 'Τ': 'Tau', 'Υ': 'Upsilon',
    'Φ': 'Phi', 'Χ': 'Chi', 'Ψ': 'Psi', 'Ω': 'Omega',
    
    # Mathematical symbols
    '∞': 'infinity', '∇': 'nabla', '∂': 'partial',
    '∫': 'integral', '∑': 'sum', '∏': 'product',
    '√': 'sqrt', '±': 'plusminus', '≈': 'approx',
    '≠': 'notequal', '≤': 'leq', '≥': 'geq',
    '⊥': 'perpendicular', '∥': 'parallel', '∈': 'in',
    '∉': 'notin', '⊂': 'subset', '⊃': 'superset',
    '∩': 'intersection', '∪': 'union', '∅': 'emptyset'
}

# LaTeX mappings for equations
GREEK_TO_LATEX = {
    # Lowercase
    'α': '\\alpha', 'β': '\\beta', 'γ': '\\gamma', 'δ': '\\delta',
    'ε': '\\epsilon', 'ζ': '\\zeta', 'η': '\\eta', 'θ': '\\theta',
    'ι': '\\iota', 'κ': '\\kappa', 'λ': '\\lambda', 'μ': '\\mu',
    'ν': '\\nu', 'ξ': '\\xi', 'ο': 'o', 'π': '\\pi',
    'ρ': '\\rho', 'σ': '\\sigma', 'τ': '\\tau', 'υ': '\\upsilon',
    'φ': '\\phi', 'χ': '\\chi', 'ψ': '\\psi', 'ω': '\\omega',
    
    # Uppercase
    'Γ': '\\Gamma', 'Δ': '\\Delta', 'Θ': '\\Theta', 'Λ': '\\Lambda',
    'Ξ': '\\Xi', 'Π': '\\Pi', 'Σ': '\\Sigma', 'Υ': '\\Upsilon',
    'Φ': '\\Phi', 'Ψ': '\\Psi', 'Ω': '\\Omega',
    
    # Mathematical
    '∞': '\\infty', '∇': '\\nabla', '∂': '\\partial',
    '∫': '\\int', '∑': '\\sum', '∏': '\\prod',
    '√': '\\sqrt', '±': '\\pm', '≈': '\\approx',
    '≠': '\\neq', '≤': '\\leq', '≥': '\\geq',
    '⊥': '\\perp', '∥': '\\parallel', '∈': '\\in'
}

# HTML entity mappings
GREEK_TO_HTML = {
    'α': '&alpha;', 'β': '&beta;', 'γ': '&gamma;', 'δ': '&delta;',
    'ε': '&epsilon;', 'ζ': '&zeta;', 'η': '&eta;', 'θ': '&theta;',
    'μ': '&mu;', 'π': '&pi;', 'σ': '&sigma;', 'ρ': '&rho;',
    'Δ': '&Delta;', 'Σ': '&Sigma;', 'Ω': '&Omega;',
    '∞': '&infin;', '∇': '&nabla;', '±': '&plusmn;',
    '≈': '&asymp;', '≠': '&ne;', '≤': '&le;', '≥': '&ge;'
}


@dataclass
class SafeContent:
    """
    Container for content with multiple safe representations.
    
    This structure ensures content can be displayed safely across
    different platforms while preserving the original for file output.
    """
    original: str  # Original Unicode content
    ascii_safe: str  # Console-safe ASCII representation
    latex: Optional[str] = None  # LaTeX format for equations
    html: Optional[str] = None  # HTML format for web display
    contains_unicode: bool = False
    greek_letters_found: List[str] = None
    

class UnicodeSafetyManager:
    """
    Comprehensive Unicode safety management for V9 Document Translator.
    
    This class provides safe handling of Unicode content, especially Greek
    letters and mathematical symbols, ensuring no console crashes on Windows
    while preserving full content for file outputs.
    
    Key Features:
    - Platform-aware display decisions
    - Multiple representation formats
    - Graceful degradation on Windows
    - Full Unicode preservation in files
    """
    
    def __init__(self, force_ascii: bool = None):
        """
        Initialize Unicode safety manager.
        
        Args:
            force_ascii: Force ASCII output regardless of platform (None=auto-detect)
        """
        self.force_ascii = force_ascii
        if force_ascii is None:
            # Auto-detect based on platform
            self.force_ascii = sys.platform == 'win32'
        
        # Setup UTF-8 encoding for the environment
        self._setup_utf8_environment()
        
        # Track conversion statistics
        self.stats = {
            'total_conversions': 0,
            'greek_letters_converted': 0,
            'files_written': 0,
            'console_outputs': 0
        }
        
        logger.info(f"UnicodeSafetyManager initialized - ASCII mode: {self.force_ascii}")
    
    def _setup_utf8_environment(self):
        """Apply mandatory UTF-8 setup following V9 standards"""
        # Already done at module level, but ensure it's set
        if sys.platform == 'win32':
            try:
                # Set console code page to UTF-8
                os.system('chcp 65001 >nul 2>&1')
            except:
                pass
    
    def make_safe(self, content: str, include_latex: bool = False, 
                  include_html: bool = False) -> SafeContent:
        """
        Create safe representations of content with Unicode characters.
        
        Args:
            content: Original content potentially containing Unicode
            include_latex: Generate LaTeX representation
            include_html: Generate HTML representation
            
        Returns:
            SafeContent object with multiple representations
        """
        self.stats['total_conversions'] += 1
        
        # Detect Greek letters and special characters
        greek_found = []
        contains_unicode = False
        
        for char in content:
            if char in GREEK_TO_ASCII:
                contains_unicode = True
                if char not in greek_found:
                    greek_found.append(char)
                    self.stats['greek_letters_converted'] += 1
        
        # Generate ASCII-safe version
        ascii_safe = self.to_ascii_safe(content)
        
        # Generate optional formats
        latex = self.to_latex(content) if include_latex else None
        html = self.to_html(content) if include_html else None
        
        return SafeContent(
            original=content,
            ascii_safe=ascii_safe,
            latex=latex,
            html=html,
            contains_unicode=contains_unicode,
            greek_letters_found=greek_found
        )
    
    def to_ascii_safe(self, text: str) -> str:
        """
        Convert text to ASCII-safe representation for console output.
        
        Args:
            text: Original text with potential Unicode
            
        Returns:
            ASCII-safe text with Greek letters replaced by names in brackets
        """
        result = text
        for greek, ascii_name in GREEK_TO_ASCII.items():
            result = result.replace(greek, f'[{ascii_name}]')
        return result
    
    def to_latex(self, text: str) -> str:
        """
        Convert text to LaTeX format for equation rendering.
        
        Args:
            text: Original text with Greek letters
            
        Returns:
            LaTeX-formatted text
        """
        result = text
        for greek, latex in GREEK_TO_LATEX.items():
            result = result.replace(greek, latex)
        return result
    
    def to_html(self, text: str) -> str:
        """
        Convert text to HTML entities for web display.
        
        Args:
            text: Original text with Greek letters
            
        Returns:
            HTML-formatted text with entities
        """
        result = text
        for greek, html_entity in GREEK_TO_HTML.items():
            result = result.replace(greek, html_entity)
        return result
    
    def safe_print(self, content: Any, force_original: bool = False):
        """
        Safely print content to console with automatic Unicode handling.
        
        Args:
            content: Content to print (string, SafeContent, or dict)
            force_original: Force printing original Unicode (risky on Windows)
        """
        self.stats['console_outputs'] += 1
        
        # Handle different content types
        if isinstance(content, SafeContent):
            if force_original or not self.force_ascii:
                try:
                    print(content.original)
                except UnicodeEncodeError:
                    # Fallback to ASCII if Unicode fails
                    print(content.ascii_safe)
                    logger.debug("Fell back to ASCII due to UnicodeEncodeError")
            else:
                print(content.ascii_safe)
                
        elif isinstance(content, dict) and 'display_safe' in content:
            print(content['display_safe'])
            
        elif isinstance(content, str):
            if self.force_ascii:
                safe_text = self.to_ascii_safe(content)
                print(safe_text)
            else:
                try:
                    print(content)
                except UnicodeEncodeError:
                    safe_text = self.to_ascii_safe(content)
                    print(safe_text)
                    logger.debug("Auto-converted to ASCII due to UnicodeEncodeError")
        else:
            # Default print for other types
            print(content)
    
    def write_safe_file(self, filepath: Path, content: Any, 
                       create_ascii_version: bool = True) -> Dict[str, Path]:
        """
        Write content to file with full Unicode preservation.
        
        Args:
            filepath: Output file path
            content: Content to write (SafeContent, dict, or string)
            create_ascii_version: Also create ASCII-safe version
            
        Returns:
            Dictionary of created file paths
        """
        self.stats['files_written'] += 1
        created_files = {}
        
        # Ensure path object
        filepath = Path(filepath)
        
        # Determine content to write
        if isinstance(content, SafeContent):
            unicode_content = content.original
            ascii_content = content.ascii_safe
        elif isinstance(content, dict):
            # JSON content
            unicode_content = json.dumps(content, ensure_ascii=False, indent=2)
            # Create ASCII version of JSON
            ascii_dict = self._make_dict_ascii_safe(content)
            ascii_content = json.dumps(ascii_dict, ensure_ascii=True, indent=2)
        else:
            unicode_content = str(content)
            ascii_content = self.to_ascii_safe(unicode_content)
        
        # Write Unicode version (UTF-8 encoded)
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(unicode_content)
            created_files['unicode'] = filepath
            logger.info(f"Wrote Unicode content to {filepath}")
        except Exception as e:
            logger.error(f"Failed to write Unicode file: {e}")
        
        # Write ASCII version if requested
        if create_ascii_version:
            ascii_path = filepath.parent / f"{filepath.stem}_ascii_safe{filepath.suffix}"
            try:
                with open(ascii_path, 'w', encoding='utf-8') as f:
                    f.write(ascii_content)
                created_files['ascii'] = ascii_path
                logger.info(f"Wrote ASCII-safe content to {ascii_path}")
            except Exception as e:
                logger.error(f"Failed to write ASCII file: {e}")
        
        return created_files
    
    def _make_dict_ascii_safe(self, data: Any) -> Any:
        """Recursively convert dictionary values to ASCII-safe representations"""
        if isinstance(data, dict):
            return {k: self._make_dict_ascii_safe(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._make_dict_ascii_safe(item) for item in data]
        elif isinstance(data, str):
            return self.to_ascii_safe(data)
        else:
            return data
    
    def create_extraction_output(self, extraction_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create multi-format extraction output for RAG systems.
        
        Args:
            extraction_data: Raw extraction data with potential Unicode
            
        Returns:
            Enhanced output with multiple representations
        """
        output = {
            'metadata': {
                'unicode_safety': True,
                'platform': sys.platform,
                'ascii_mode': self.force_ascii,
                'representations_available': ['original', 'ascii', 'latex', 'html']
            },
            'content': {}
        }
        
        # Process each section
        for section_key, section_data in extraction_data.items():
            if isinstance(section_data, str):
                safe_content = self.make_safe(section_data, 
                                            include_latex=True, 
                                            include_html=True)
                output['content'][section_key] = {
                    'original': safe_content.original,
                    'ascii_safe': safe_content.ascii_safe,
                    'latex': safe_content.latex,
                    'html': safe_content.html,
                    'contains_greek': safe_content.contains_unicode,
                    'greek_letters': safe_content.greek_letters_found
                }
            else:
                output['content'][section_key] = section_data
        
        return output
    
    def get_statistics(self) -> Dict[str, int]:
        """Return usage statistics"""
        return self.stats.copy()
    
    def is_console_safe(self, text: str) -> bool:
        """
        Check if text is safe for console output without conversion.
        
        Args:
            text: Text to check
            
        Returns:
            True if safe for console, False if needs conversion
        """
        if not self.force_ascii:
            return True  # Assume safe on non-Windows platforms
        
        for char in text:
            if char in GREEK_TO_ASCII:
                return False
        return True


def main():
    """
    Test Unicode safety manager with sample content.
    """
    print("Testing Unicode Safety Manager")
    print("=" * 50)
    
    # Create manager
    manager = UnicodeSafetyManager()
    
    # Test content with Greek letters (from Docling output)
    test_content = """
    Nomenclature:
    α - absorptivity, or total absorptance
    β - volume coefficient of expansion, 1/R (1/K)
    μ - dynamic viscosity, lbm/ft s (kg/m s)
    σ - Stefan-Boltzmann constant, 0.1713 × 10⁻⁸ Btu/h ft²
    ∇T - temperature gradient
    ∞ - free stream conditions
    ⊥ - perpendicular to flow
    """
    
    print("\n1. Testing safe print (console output):")
    print("-" * 40)
    safe_content = manager.make_safe(test_content, include_latex=True)
    manager.safe_print(safe_content)
    
    print("\n2. Testing file output:")
    print("-" * 40)
    output_path = Path("test_unicode_output.txt")
    files = manager.write_safe_file(output_path, safe_content)
    print(f"Created files: {files}")
    
    print("\n3. Testing extraction output format:")
    print("-" * 40)
    extraction_data = {
        'nomenclature': test_content,
        'table_1': "Material | Btu/h ft F | W/m C",
        'equations': "qc = -kA dT/dx where α = 0.5"
    }
    
    enhanced_output = manager.create_extraction_output(extraction_data)
    manager.safe_print(json.dumps(enhanced_output, indent=2))
    
    print("\n4. Statistics:")
    print("-" * 40)
    print(manager.get_statistics())
    
    print("\n✓ Unicode Safety Manager test complete!")


if __name__ == "__main__":
    main()