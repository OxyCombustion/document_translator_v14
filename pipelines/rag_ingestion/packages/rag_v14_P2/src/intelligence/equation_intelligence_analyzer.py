#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Equation Intelligence Analyzer - Isolated Module
Analyzes equation patterns, complexity, and spatial relationships in PDF documents
MODULAR DESIGN: Changes to this module cannot affect figure or table analysis
"""

import sys
import os
import re
from typing import Dict, List, Set, Tuple
from collections import defaultdict

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    import io
    if not hasattr(sys.stdout, '_wrapped_utf8'):
        try:
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
            sys.stdout._wrapped_utf8 = True
        except (AttributeError, ValueError):
            os.system('chcp 65001')

import fitz  # PyMuPDF

class EquationIntelligenceAnalyzer:
    """
    ISOLATED EQUATION ANALYSIS MODULE
    
    Single Responsibility: Analyze equation patterns, complexity, and spatial relationships
    High Cohesion: All equation-related analysis in one place
    Loose Coupling: No dependencies on figure or table analysis
    """
    
    def __init__(self):
        """Initialize the equation intelligence analyzer"""
        self.equation_profile = {
            "total_found": 0,
            "equation_numbers": [],
            "complexity_distribution": {},
            "spatial_patterns": {},
            "size_recommendations": {},
            "duplicate_detections": 0
        }
    
    def analyze_equations(self, doc: fitz.Document) -> Dict:
        """
        Main entry point: Analyze equation patterns in document
        
        Returns:
            dict: Complete equation intelligence profile
        """
        print("📐 Analyzing Equation Pattern Intelligence...")
        
        # Reset profile for new analysis
        self._reset_profile()
        
        # Find equation candidates using proven patterns
        equation_candidates = self._detect_equation_candidates(doc)
        
        # Filter duplicates and false positives
        unique_equations = self._filter_duplicates(equation_candidates)
        
        # Analyze complexity distribution
        complexity_distribution = self._analyze_complexity_distribution(unique_equations)
        
        # Update profile with results
        self._update_profile(unique_equations, equation_candidates, complexity_distribution)
        
        # Generate extraction recommendations
        self._generate_equation_strategy()
        
        # Display results
        self._display_equation_analysis()
        
        return self.equation_profile.copy()  # Return copy to prevent external modification
    
    def _reset_profile(self):
        """Reset profile for new analysis"""
        self.equation_profile = {
            "total_found": 0,
            "equation_numbers": [],
            "complexity_distribution": {},
            "spatial_patterns": {},
            "size_recommendations": {},
            "duplicate_detections": 0
        }
    
    def _detect_equation_candidates(self, doc: fitz.Document) -> List[Dict]:
        """
        Detect equation candidates using proven pattern matching
        
        Returns:
            list: All equation candidates found (including potential duplicates)
        """
        equation_candidates = []
        
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            text_dict = page.get_text("dict")
            
            # Find equation numbers using proven pattern
            for block in text_dict["blocks"]:
                if "lines" not in block:
                    continue
                    
                for line in block["lines"]:
                    for span in line["spans"]:
                        text = span["text"].strip()
                        
                        # Use successful equation detection pattern from working scanner
                        match = re.match(r'^\((\d+)([a-z]?)\)$', text)
                        if match:
                            equation_num = int(match.group(1))
                            letter_suffix = match.group(2)
                            
                            if 1 <= equation_num <= 200:  # Reasonable range
                                # Analyze surrounding mathematical content
                                complexity = self._estimate_equation_complexity(page, span["bbox"])
                                
                                equation_data = {
                                    "page": page_num + 1,
                                    "number": equation_num,
                                    "suffix": letter_suffix,
                                    "bbox": span["bbox"],
                                    "complexity": complexity,
                                    "estimated_lines": complexity.get("lines", 1)
                                }
                                
                                equation_candidates.append(equation_data)
        
        return equation_candidates
    
    def _filter_duplicates(self, equation_candidates: List[Dict]) -> List[Dict]:
        """
        Filter duplicate equation detections to get unique equations
        
        Args:
            equation_candidates: Raw equation candidates (may contain duplicates)
            
        Returns:
            list: Unique equation candidates with duplicates removed
        """
        unique_equation_numbers = set()
        unique_equation_candidates = []
        
        for eq in equation_candidates:
            eq_key = (eq["number"], eq["suffix"])  # Use number + suffix as unique key
            if eq_key not in unique_equation_numbers:
                unique_equation_numbers.add(eq_key)
                unique_equation_candidates.append(eq)
        
        return unique_equation_candidates
    
    def _analyze_complexity_distribution(self, unique_equations: List[Dict]) -> Dict:
        """
        Analyze the complexity distribution of equations
        
        Args:
            unique_equations: Filtered unique equation candidates
            
        Returns:
            dict: Complexity distribution statistics
        """
        complexity_distribution = defaultdict(int)
        
        for eq in unique_equations:
            complexity_level = eq["complexity"]["level"]
            complexity_distribution[complexity_level] += 1
        
        return dict(complexity_distribution)
    
    def _estimate_equation_complexity(self, page: fitz.Page, number_bbox: List) -> Dict:
        """
        Estimate equation complexity around a number (isolated from other analyzers)
        
        Args:
            page: PDF page object
            number_bbox: Bounding box of equation number
            
        Returns:
            dict: Complexity analysis with level and metrics
        """
        center_x = (number_bbox[0] + number_bbox[2]) / 2
        center_y = (number_bbox[1] + number_bbox[3]) / 2
        
        # Analyze area left of equation number
        analysis_rect = fitz.Rect(
            max(0, center_x - 200),
            max(0, center_y - 75),
            center_x + 20,
            center_y + 75
        )
        
        text_dict = page.get_text("dict", clip=analysis_rect)
        
        # Count mathematical spans
        math_span_count = 0
        line_positions = []
        
        for block in text_dict["blocks"]:
            if "lines" in block:
                for line in block["lines"]:
                    for span in line["spans"]:
                        text = span["text"].strip()
                        if any(char in text for char in "=+-*/()[]{}^_∑∫∂√"):
                            math_span_count += 1
                            line_positions.append((span["bbox"][1] + span["bbox"][3]) / 2)
        
        # Estimate lines based on Y-position clustering
        if line_positions:
            line_positions.sort()
            lines = 1
            for i in range(1, len(line_positions)):
                if abs(line_positions[i] - line_positions[i-1]) > 10:
                    lines += 1
        else:
            lines = 1
        
        # Classify complexity
        if lines >= 6:
            level = "very_complex"
        elif lines >= 3:
            level = "complex"
        elif lines >= 2:
            level = "moderate"
        else:
            level = "simple"
        
        return {
            "level": level,
            "lines": lines,
            "math_spans": math_span_count
        }
    
    def _update_profile(self, unique_equations: List[Dict], equation_candidates: List[Dict], 
                       complexity_distribution: Dict):
        """Update equation profile with analysis results"""
        
        # Update profile with UNIQUE equation count (accurate)
        self.equation_profile["total_found"] = len(unique_equations)
        self.equation_profile["equation_numbers"] = sorted([eq["number"] for eq in unique_equations])
        self.equation_profile["complexity_distribution"] = complexity_distribution
        self.equation_profile["duplicate_detections"] = len(equation_candidates) - len(unique_equations)
    
    def _generate_equation_strategy(self):
        """Generate extraction strategy recommendations based on analysis"""
        
        complexity_dist = self.equation_profile["complexity_distribution"]
        
        # Generate size recommendations based on complexity
        if complexity_dist.get("very_complex", 0) > 5:
            self.equation_profile["size_recommendations"] = {
                "adaptive_sizing": True,
                "max_height": 300
            }
        else:
            self.equation_profile["size_recommendations"] = {
                "adaptive_sizing": False,
                "max_height": 60
            }
    
    def _display_equation_analysis(self):
        """Display equation analysis results"""
        total_found = self.equation_profile["total_found"]
        duplicates = self.equation_profile["duplicate_detections"]
        total_candidates = total_found + duplicates
        
        print(f"   📊 Found: {total_found} unique equations (filtered from {total_candidates} candidates)")
        print(f"   🔍 Duplicates filtered: {duplicates}")
        print(f"   📝 Equation numbers: {self.equation_profile['equation_numbers']}")
        print(f"   📈 Complexity: {self.equation_profile['complexity_distribution']}")

def test_equation_analyzer():
    """Test the equation intelligence analyzer independently"""
    print("🧪 Testing Equation Intelligence Analyzer (Isolated)")
    print("=" * 58)
    
    pdf_path = "tests/test_data/Ch-04_Heat_Transfer.pdf"
    
    if not os.path.exists(pdf_path):
        print(f"❌ Test PDF not found: {pdf_path}")
        return
    
    try:
        # Test isolated equation analyzer
        analyzer = EquationIntelligenceAnalyzer()
        
        doc = fitz.open(pdf_path)
        equation_profile = analyzer.analyze_equations(doc)
        doc.close()
        
        print(f"\\n📊 ISOLATED EQUATION ANALYSIS RESULTS:")
        print(f"   Total equations detected: {equation_profile['total_found']}")
        print(f"   Duplicates filtered: {equation_profile['duplicate_detections']}")
        print(f"   Complexity distribution: {equation_profile['complexity_distribution']}")
        print(f"   Size recommendations: {equation_profile['size_recommendations']}")
        
        print(f"\\n✅ Equation analyzer test completed successfully!")
        return equation_profile
        
    except Exception as e:
        print(f"❌ Equation analyzer test failed: {e}")
        import traceback
        traceback.print_exc()

def main():
    """Main function"""
    test_equation_analyzer()

if __name__ == "__main__":
    main()