#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Table Intelligence Analyzer - Isolated Module
Analyzes table structure hints and extraction methods in PDF documents
MODULAR DESIGN: Changes to this module cannot affect figure or equation analysis
"""

import sys
import os
from typing import Dict, List

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

class TableIntelligenceAnalyzer:
    """
    ISOLATED TABLE ANALYSIS MODULE
    
    Single Responsibility: Analyze table structure hints and extraction methods
    High Cohesion: All table-related analysis in one place
    Loose Coupling: No dependencies on figure or equation analysis
    """
    
    def __init__(self):
        """Initialize the table intelligence analyzer"""
        self.table_profile = {
            "estimated_count": 0,
            "structure_hints": [],
            "extraction_method": "unknown",
            "keyword_references": 0,
            "complexity_indicators": {}
        }
    
    def analyze_tables(self, doc: fitz.Document) -> Dict:
        """
        Main entry point: Analyze table structure hints in document
        
        Returns:
            dict: Complete table intelligence profile
        """
        print("📊 Analyzing Table Structure Intelligence...")
        
        # Reset profile for new analysis
        self._reset_profile()
        
        # Analyze table indicators and keywords
        keyword_references = self._analyze_table_keywords(doc)
        
        # Analyze structural indicators
        structure_hints = self._analyze_structure_hints(doc)
        
        # Estimate table count using heuristics
        estimated_count = self._estimate_table_count(keyword_references, structure_hints)
        
        # Update profile with results
        self._update_profile(keyword_references, structure_hints, estimated_count)
        
        # Generate extraction recommendations
        self._generate_table_strategy()
        
        # Display results
        self._display_table_analysis()
        
        return self.table_profile.copy()  # Return copy to prevent external modification
    
    def _reset_profile(self):
        """Reset profile for new analysis"""
        self.table_profile = {
            "estimated_count": 0,
            "structure_hints": [],
            "extraction_method": "unknown",
            "keyword_references": 0,
            "complexity_indicators": {}
        }
    
    def _analyze_table_keywords(self, doc: fitz.Document) -> int:
        """
        Analyze table-related keywords in document text
        
        Returns:
            int: Total count of table-related keyword references
        """
        table_keywords = [
            "Table", "table", "tabular", "data", 
            "column", "row", "cells", "grid"
        ]
        total_references = 0
        
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            text = page.get_text()
            
            for keyword in table_keywords:
                references = text.count(keyword)
                total_references += references
        
        return total_references
    
    def _analyze_structure_hints(self, doc: fitz.Document) -> List[str]:
        """
        Analyze structural hints that suggest table presence
        
        Returns:
            list: List of structural indicators found
        """
        structure_hints = []
        
        # Look for alignment patterns that suggest tabular data
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            text_dict = page.get_text("dict")
            
            # Check for repeated alignment patterns
            line_positions = []
            for block in text_dict["blocks"]:
                if "lines" in block:
                    for line in block["lines"]:
                        if len(line["spans"]) > 1:  # Multiple spans suggest columns
                            x_positions = [span["bbox"][0] for span in line["spans"]]
                            line_positions.append(x_positions)
            
            # Detect consistent column alignment
            if len(line_positions) > 5:  # At least 5 lines with multiple columns
                structure_hints.append(f"Consistent column alignment on page {page_num + 1}")
        
        # Look for numeric data patterns
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            text = page.get_text()
            
            # Count numeric patterns that suggest tabular data
            import re
            numeric_patterns = len(re.findall(r'\d+\.\d+', text))  # Decimal numbers
            percentage_patterns = len(re.findall(r'\d+%', text))    # Percentages
            
            if numeric_patterns > 20 or percentage_patterns > 10:
                structure_hints.append(f"High numeric content on page {page_num + 1}")
        
        return structure_hints
    
    def _estimate_table_count(self, keyword_references: int, structure_hints: List[str]) -> int:
        """
        Estimate table count using heuristic analysis
        
        Args:
            keyword_references: Total table keyword references
            structure_hints: List of structural indicators
            
        Returns:
            int: Estimated number of tables
        """
        # Conservative heuristic: keyword count divided by typical references per table
        keyword_based_estimate = min(keyword_references // 10, 20)
        
        # Structure-based estimate
        structure_based_estimate = min(len(structure_hints) // 2, 15)
        
        # Take the maximum of both estimates (more conservative)
        estimated_count = max(keyword_based_estimate, structure_based_estimate)
        
        # Ensure minimum reasonable estimate
        if keyword_references > 5 and estimated_count == 0:
            estimated_count = 1
        
        return estimated_count
    
    def _update_profile(self, keyword_references: int, structure_hints: List[str], 
                       estimated_count: int):
        """Update table profile with analysis results"""
        
        self.table_profile["estimated_count"] = estimated_count
        self.table_profile["structure_hints"] = structure_hints
        self.table_profile["keyword_references"] = keyword_references
        
        # Add complexity indicators
        self.table_profile["complexity_indicators"] = {
            "high_keyword_density": keyword_references > 50,
            "multiple_structure_hints": len(structure_hints) > 5,
            "cross_page_tables": any("page" in hint for hint in structure_hints)
        }
    
    def _generate_table_strategy(self):
        """Generate extraction strategy recommendations based on analysis"""
        
        estimated_count = self.table_profile["estimated_count"]
        complexity = self.table_profile["complexity_indicators"]
        
        # Determine extraction method based on complexity and count
        if estimated_count > 8 and complexity.get("high_keyword_density", False):
            self.table_profile["extraction_method"] = "docling_primary"
        elif estimated_count > 3:
            self.table_profile["extraction_method"] = "hybrid_approach"
        else:
            self.table_profile["extraction_method"] = "manual_analysis"
    
    def _display_table_analysis(self):
        """Display table analysis results"""
        estimated_count = self.table_profile["estimated_count"]
        keyword_refs = self.table_profile["keyword_references"]
        hints_count = len(self.table_profile["structure_hints"])
        
        print(f"   📊 Estimated tables: {estimated_count}")
        print(f"   🔍 Keyword references: {keyword_refs}")
        print(f"   📋 Structure hints: {hints_count}")
        print(f"   🎯 Recommended method: {self.table_profile['extraction_method']}")

def test_table_analyzer():
    """Test the table intelligence analyzer independently"""
    print("🧪 Testing Table Intelligence Analyzer (Isolated)")
    print("=" * 55)
    
    pdf_path = "tests/test_data/Ch-04_Heat_Transfer.pdf"
    
    if not os.path.exists(pdf_path):
        print(f"❌ Test PDF not found: {pdf_path}")
        return
    
    try:
        # Test isolated table analyzer
        analyzer = TableIntelligenceAnalyzer()
        
        doc = fitz.open(pdf_path)
        table_profile = analyzer.analyze_tables(doc)
        doc.close()
        
        print(f"\\n📊 ISOLATED TABLE ANALYSIS RESULTS:")
        print(f"   Estimated tables: {table_profile['estimated_count']}")
        print(f"   Keyword references: {table_profile['keyword_references']}")
        print(f"   Structure hints: {len(table_profile['structure_hints'])}")
        print(f"   Extraction method: {table_profile['extraction_method']}")
        print(f"   Complexity indicators: {table_profile['complexity_indicators']}")
        
        if table_profile['structure_hints']:
            print(f"   \\n📋 Structure hints found:")
            for hint in table_profile['structure_hints'][:5]:  # Show first 5
                print(f"      - {hint}")
        
        print(f"\\n✅ Table analyzer test completed successfully!")
        return table_profile
        
    except Exception as e:
        print(f"❌ Table analyzer test failed: {e}")
        import traceback
        traceback.print_exc()

def main():
    """Main function"""
    test_table_analyzer()

if __name__ == "__main__":
    main()