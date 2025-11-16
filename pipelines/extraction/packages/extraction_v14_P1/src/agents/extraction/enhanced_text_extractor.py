#!/usr/bin/env python3
"""
Enhanced Text Extractor - Complete Document Coverage
Advanced text extraction with structure preservation and multi-format support

Features:
- Multi-column layout handling
- Reading order preservation
- Header/paragraph hierarchy
- Formatting retention (bold, italic, font sizes)
- Cross-reference tracking
- Multi-language support
"""

import sys
import os

# Set UTF-8 encoding for Windows console
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
    
    if not hasattr(sys.stderr, '_wrapped_utf8'):
        try:
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
            sys.stderr._wrapped_utf8 = True
        except (AttributeError, ValueError):
            pass

import re
import json
import logging
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional, Tuple
import fitz  # PyMuPDF
from collections import defaultdict

@dataclass
class TextElement:
    """Represents a text element with structure and formatting"""
    element_type: str  # 'header', 'paragraph', 'caption', 'footnote', 'list_item'
    page_number: int
    bbox: Tuple[float, float, float, float]
    text: str
    font_name: str = ""
    font_size: float = 0.0
    is_bold: bool = False
    is_italic: bool = False
    text_color: Optional[Tuple[int, int, int]] = None
    reading_order: int = 0
    hierarchy_level: int = 0  # 0=main text, 1=h1, 2=h2, etc.
    references: List[str] = None  # Cross-references found in text

@dataclass
class DocumentStructure:
    """Complete document structure with hierarchical text"""
    document_path: str
    total_pages: int
    extraction_method: str
    text_elements: List[TextElement]
    reading_order_map: Dict[int, List[int]]  # page -> element indices
    cross_references: Dict[str, List[int]]  # reference -> element indices
    metadata: Dict[str, Any]

class EnhancedTextExtractor:
    """Advanced text extraction with structure preservation"""
    
    def __init__(self):
        self.logger = self._setup_logging()
        
        # Text classification patterns
        self.header_patterns = [
            r'^\d+\.\s+[A-Z][^.]*$',  # "1. INTRODUCTION"
            r'^[A-Z][A-Z\s]{5,}$',    # "HEAT TRANSFER"
            r'^\d+\.\d+\s+[A-Z]',     # "1.1 Overview"
        ]
        
        self.reference_patterns = [
            r'\b(?:Table|Figure|Equation|Section)\s+\d+(?:\.\d+)*\b',
            r'\b(?:Eq\.|Fig\.|Tab\.)\s*\(\d+\)',
            r'\(\d+\)',  # Simple numbered references
        ]
        
        # Font size thresholds for hierarchy
        self.font_thresholds = {
            'title': 16.0,
            'header1': 14.0,
            'header2': 12.0,
            'body': 10.0
        }
    
    def _setup_logging(self) -> logging.Logger:
        """Setup logging for the extractor"""
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def extract_text_structure(self, pdf_path: str) -> DocumentStructure:
        """Extract complete text structure from PDF"""
        self.logger.info(f"Starting enhanced text extraction from {pdf_path}")
        
        try:
            doc = fitz.open(pdf_path)
            text_elements = []
            reading_order_map = defaultdict(list)
            cross_references = defaultdict(list)
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                page_elements = self._extract_page_text(page, page_num)
                
                # Sort by reading order
                page_elements.sort(key=lambda x: (x.bbox[1], x.bbox[0]))  # Top to bottom, left to right
                
                # Assign reading order indices
                for i, element in enumerate(page_elements):
                    element.reading_order = len(text_elements) + i
                    reading_order_map[page_num].append(element.reading_order)
                    
                    # Extract cross-references
                    refs = self._extract_references(element.text)
                    element.references = refs
                    for ref in refs:
                        cross_references[ref].append(element.reading_order)
                
                text_elements.extend(page_elements)
            
            doc.close()
            
            # Create document structure
            structure = DocumentStructure(
                document_path=pdf_path,
                total_pages=len(doc),
                extraction_method="Enhanced Text Extractor",
                text_elements=text_elements,
                reading_order_map=dict(reading_order_map),
                cross_references=dict(cross_references),
                metadata={
                    'total_elements': len(text_elements),
                    'extraction_date': str(datetime.now()),
                    'font_analysis': self._analyze_fonts(text_elements)
                }
            )
            
            self.logger.info(f"Extracted {len(text_elements)} text elements from {len(doc)} pages")
            return structure
            
        except Exception as e:
            self.logger.error(f"Text extraction failed: {str(e)}")
            raise
    
    def _extract_page_text(self, page: fitz.Page, page_num: int) -> List[TextElement]:
        """Extract structured text from a single page"""
        elements = []
        
        # Get text blocks with formatting
        blocks = page.get_text("dict")
        
        for block in blocks['blocks']:
            if 'lines' in block:  # Text block
                block_text = ""
                font_info = None
                bbox = block['bbox']
                
                for line in block['lines']:
                    for span in line['spans']:
                        block_text += span['text']
                        
                        # Capture font information from first span
                        if font_info is None:
                            font_info = {
                                'font': span['font'],
                                'size': span['size'],
                                'flags': span['flags'],
                                'color': span['color']
                            }
                
                if block_text.strip():
                    # Determine element type
                    element_type = self._classify_text_element(block_text, font_info)
                    
                    # Determine hierarchy level
                    hierarchy_level = self._get_hierarchy_level(block_text, font_info)
                    
                    element = TextElement(
                        element_type=element_type,
                        page_number=page_num,
                        bbox=tuple(bbox),
                        text=block_text.strip(),
                        font_name=font_info['font'] if font_info else "",
                        font_size=font_info['size'] if font_info else 0.0,
                        is_bold=bool(font_info['flags'] & 2**4) if font_info else False,
                        is_italic=bool(font_info['flags'] & 2**1) if font_info else False,
                        text_color=self._parse_color(font_info['color']) if font_info else None,
                        hierarchy_level=hierarchy_level
                    )
                    
                    elements.append(element)
        
        return elements
    
    def _classify_text_element(self, text: str, font_info: Dict) -> str:
        """Classify text element type based on content and formatting"""
        text_clean = text.strip()
        
        # Check for headers
        for pattern in self.header_patterns:
            if re.match(pattern, text_clean):
                return 'header'
        
        # Check font size for headers
        if font_info and font_info['size'] >= self.font_thresholds['header2']:
            return 'header'
        
        # Check for captions
        if re.match(r'^(?:Table|Figure|Equation)\s+\d+', text_clean):
            return 'caption'
        
        # Check for footnotes (small font, bottom of page)
        if font_info and font_info['size'] < self.font_thresholds['body']:
            return 'footnote'
        
        # Check for list items
        if re.match(r'^[\u2022\u25cf\u25aa\u25ab•·]\s+', text_clean) or re.match(r'^\d+\.\s+', text_clean):
            return 'list_item'
        
        return 'paragraph'
    
    def _get_hierarchy_level(self, text: str, font_info: Dict) -> int:
        """Determine text hierarchy level"""
        if not font_info:
            return 0
        
        font_size = font_info['size']
        is_bold = bool(font_info['flags'] & 2**4)
        
        # Title level
        if font_size >= self.font_thresholds['title']:
            return 1
        
        # Header levels based on font size and formatting
        if font_size >= self.font_thresholds['header1']:
            return 1 if is_bold else 2
        
        if font_size >= self.font_thresholds['header2']:
            return 2 if is_bold else 3
        
        # Check for numbered sections
        if re.match(r'^\d+\.\s+', text.strip()):
            return 1
        
        if re.match(r'^\d+\.\d+\s+', text.strip()):
            return 2
        
        return 0  # Body text
    
    def _extract_references(self, text: str) -> List[str]:
        """Extract cross-references from text"""
        references = []
        
        for pattern in self.reference_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            references.extend(matches)
        
        return list(set(references))  # Remove duplicates
    
    def _parse_color(self, color_int: int) -> Tuple[int, int, int]:
        """Parse color integer to RGB tuple"""
        if color_int == 0:
            return (0, 0, 0)  # Black
        
        # Convert from integer to RGB
        r = (color_int >> 16) & 255
        g = (color_int >> 8) & 255
        b = color_int & 255
        
        return (r, g, b)
    
    def _analyze_fonts(self, elements: List[TextElement]) -> Dict[str, Any]:
        """Analyze font usage across document"""
        font_stats = defaultdict(int)
        size_stats = defaultdict(int)
        
        for element in elements:
            if element.font_name:
                font_stats[element.font_name] += 1
            if element.font_size:
                size_stats[int(element.font_size)] += 1
        
        return {
            'font_distribution': dict(font_stats),
            'size_distribution': dict(size_stats),
            'most_common_font': max(font_stats.items(), key=lambda x: x[1])[0] if font_stats else None,
            'most_common_size': max(size_stats.items(), key=lambda x: x[1])[0] if size_stats else None
        }
    
    def export_structure(self, structure: DocumentStructure, output_path: str):
        """Export document structure to JSON"""
        try:
            structure_dict = asdict(structure)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(structure_dict, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Document structure exported to {output_path}")
            
        except Exception as e:
            self.logger.error(f"Failed to export structure: {str(e)}")
            raise
    
    def get_text_by_hierarchy(self, structure: DocumentStructure, level: int) -> List[TextElement]:
        """Get text elements by hierarchy level"""
        return [elem for elem in structure.text_elements if elem.hierarchy_level == level]
    
    def get_reading_order_text(self, structure: DocumentStructure) -> str:
        """Get complete text in reading order"""
        sorted_elements = sorted(structure.text_elements, key=lambda x: x.reading_order)
        return '\n\n'.join(elem.text for elem in sorted_elements)
    
    def get_structured_text(self, structure: DocumentStructure) -> Dict[str, List[str]]:
        """Get text organized by structure type"""
        structured = defaultdict(list)
        
        for element in structure.text_elements:
            structured[element.element_type].append(element.text)
        
        return dict(structured)

def main():
    """Main function for testing"""
    import argparse
    from datetime import datetime
    
    parser = argparse.ArgumentParser(description="Enhanced Text Extraction")
    parser.add_argument("pdf_path", help="Path to PDF document")
    parser.add_argument("--output", help="Output JSON file", default="text_structure.json")
    
    args = parser.parse_args()
    
    if not Path(args.pdf_path).exists():
        print(f"Error: PDF file not found: {args.pdf_path}")
        return
    
    # Run extraction
    extractor = EnhancedTextExtractor()
    structure = extractor.extract_text_structure(args.pdf_path)
    
    # Export results
    extractor.export_structure(structure, args.output)
    
    # Print summary
    print(f"\n{'='*60}")
    print(f"ENHANCED TEXT EXTRACTION RESULTS")
    print(f"{'='*60}")
    print(f"Document: {Path(args.pdf_path).name}")
    print(f"Pages: {structure.total_pages}")
    print(f"Text Elements: {len(structure.text_elements)}")
    print()
    
    # Element type distribution
    type_counts = defaultdict(int)
    for elem in structure.text_elements:
        type_counts[elem.element_type] += 1
    
    print("Element Type Distribution:")
    for elem_type, count in sorted(type_counts.items()):
        print(f"  {elem_type.title()}: {count}")
    
    # Hierarchy analysis
    hierarchy_counts = defaultdict(int)
    for elem in structure.text_elements:
        hierarchy_counts[elem.hierarchy_level] += 1
    
    print("\nHierarchy Level Distribution:")
    for level, count in sorted(hierarchy_counts.items()):
        level_name = {0: 'Body Text', 1: 'Main Headers', 2: 'Sub Headers', 3: 'Minor Headers'}.get(level, f'Level {level}')
        print(f"  {level_name}: {count}")
    
    print(f"\nCross-references found: {len(structure.cross_references)}")
    print(f"Structure exported to: {args.output}")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()