#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Figure Intelligence Analyzer - Isolated Module
Analyzes figure content patterns and formats in PDF documents
MODULAR DESIGN: Changes to this module cannot affect equation or table analysis
"""

import sys
import os
import re
from typing import Dict, List, Set

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

class FigureIntelligenceAnalyzer:
    """
    ISOLATED FIGURE ANALYSIS MODULE
    
    Single Responsibility: Analyze figure content types, formats, and patterns
    High Cohesion: All figure-related analysis in one place
    Loose Coupling: No dependencies on equation or table analysis
    """
    
    def __init__(self):
        """Initialize the figure intelligence analyzer"""
        self.figure_profile = {
            "total_embedded_images": 0,
            "total_vector_elements": 0,
            "total_figures": 0,
            "figure_numbers": [],
            "image_pages": [],
            "image_formats": {},
            "size_distribution": [],
            "recommended_method": "unknown"
        }
    
    def analyze_figures(self, doc: fitz.Document) -> Dict:
        """
        Main entry point: Analyze figure content in document
        
        Returns:
            dict: Complete figure intelligence profile
        """
        print("🖼️ Analyzing Figure Content Intelligence...")
        
        # Reset profile for new analysis
        self._reset_profile()
        
        # Caption-based figure detection (PRIMARY METHOD)
        figure_captions = self._detect_figure_captions(doc)
        
        # Embedded image analysis (SECONDARY - for format understanding)
        embedded_images = self._analyze_embedded_images(doc)
        
        # Vector graphics analysis
        total_vector_elements = self._analyze_vector_graphics(doc)
        
        # Update profile with results
        self._update_profile(figure_captions, embedded_images, total_vector_elements)
        
        # Generate extraction recommendations
        self._generate_figure_strategy()
        
        # NEW: Classify figures as graphs vs diagrams
        self._classify_figure_zones(doc, figure_captions)
        
        # Display results
        self._display_figure_analysis()
        
        return self.figure_profile.copy()  # Return copy to prevent external modification
    
    def _reset_profile(self):
        """Reset profile for new analysis"""
        self.figure_profile = {
            "total_embedded_images": 0,
            "total_vector_elements": 0,
            "total_figures": 0,
            "figure_numbers": [],
            "image_pages": [],
            "image_formats": {},
            "size_distribution": [],
            "recommended_method": "unknown",
            "figure_classification": {},  # NEW: Figure vs Graph classification
            "graph_zones": [],           # NEW: Identified graph zones with extractable data
            "diagram_zones": []          # NEW: General figure zones
        }
    
    def _detect_figure_captions(self, doc: fitz.Document) -> Set[int]:
        """
        Detect figures via caption analysis (PRIMARY method for accuracy)
        
        Returns:
            set: Unique figure numbers found in document
        """
        figure_captions = set()
        
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            text_dict = page.get_text("dict")
            
            for block in text_dict["blocks"]:
                if "lines" not in block:
                    continue
                    
                for line in block["lines"]:
                    for span in line["spans"]:
                        text = span["text"].strip()
                        
                        # Look for figure captions using proven patterns
                        patterns = [
                            r'Fig\.?\s*(\d+)',
                            r'Figure\s*(\d+)'
                        ]
                        
                        for pattern in patterns:
                            matches = re.finditer(pattern, text, re.IGNORECASE)
                            for match in matches:
                                figure_num = int(match.group(1))
                                if 1 <= figure_num <= 100:  # Reasonable range
                                    figure_captions.add(figure_num)
        
        return figure_captions
    
    def _analyze_embedded_images(self, doc: fitz.Document) -> List[Dict]:
        """
        Analyze embedded raster images (SECONDARY method for format understanding)
        
        Returns:
            list: Image metadata for format distribution analysis
        """
        embedded_images = []
        
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            
            images = page.get_images(full=True)
            if images:
                self.figure_profile["image_pages"].append(page_num + 1)
                
                for img in images:
                    try:
                        xref = img[0]
                        pix = fitz.Pixmap(doc, xref)
                        
                        image_data = {
                            "page": page_num + 1,
                            "width": pix.width,
                            "height": pix.height,
                            "colorspace": pix.colorspace.name if pix.colorspace else "unknown",
                            "size_bytes": len(pix.tobytes()),
                            "dpi_estimate": max(pix.width, pix.height) / max(page.rect.width, page.rect.height) * 72
                        }
                        
                        embedded_images.append(image_data)
                        
                        # Track format distribution
                        colorspace = image_data["colorspace"]
                        self.figure_profile["image_formats"][colorspace] = \
                            self.figure_profile["image_formats"].get(colorspace, 0) + 1
                        
                        pix = None
                        
                    except Exception as e:
                        print(f"   Warning: Could not analyze image on page {page_num + 1}: {e}")
        
        return embedded_images
    
    def _analyze_vector_graphics(self, doc: fitz.Document) -> int:
        """
        Analyze vector graphics content
        
        Returns:
            int: Total vector elements found
        """
        total_vector_elements = 0
        vector_pages = []
        
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            
            drawings = page.get_drawings()
            if drawings and len(drawings) > 10:  # Significant vector content
                vector_pages.append(page_num + 1)
                total_vector_elements += len(drawings)
        
        return total_vector_elements
    
    def _update_profile(self, figure_captions: Set[int], embedded_images: List[Dict], 
                       total_vector_elements: int):
        """Update figure profile with analysis results"""
        
        # Caption-based counting (PRIMARY - most accurate)
        total_figures = len(figure_captions)
        self.figure_profile["total_figures"] = total_figures
        self.figure_profile["figure_numbers"] = sorted(list(figure_captions))
        
        # Embedded image analysis (SECONDARY - format understanding)
        self.figure_profile["total_embedded_images"] = len(embedded_images)
        self.figure_profile["size_distribution"] = embedded_images
        
        # Vector graphics analysis
        self.figure_profile["total_vector_elements"] = total_vector_elements
    
    def _generate_figure_strategy(self):
        """Generate extraction strategy recommendations based on analysis"""
        
        total_figures = self.figure_profile["total_figures"]
        embedded_images = self.figure_profile["total_embedded_images"]
        vector_elements = self.figure_profile["total_vector_elements"]
        
        # Determine recommended extraction method based on content analysis
        if embedded_images >= total_figures * 0.7:  # If 70%+ are embedded images
            self.figure_profile["recommended_method"] = "embedded_image_primary"
        elif vector_elements > 500:
            self.figure_profile["recommended_method"] = "vector_graphics_primary"
        else:
            self.figure_profile["recommended_method"] = "caption_based_hybrid"
    
    def _classify_figure_zones(self, doc: fitz.Document, figure_captions: Set[int]):
        """
        Classify detected figures as graphs (data extractable) vs diagrams (visual only)
        Phase 1: Caption-based classification using keywords with extended context analysis
        """
        print("🔍 Classifying figure zones (graphs vs diagrams)...")
        
        # Graph identification keywords - indicating data-rich content
        graph_keywords = [
            'factor', 'factors', 'correlation', 'correlations',
            'chart', 'plot', 'graph', 'curve', 'curves',
            'coefficient', 'coefficients', 'ratio', 'ratios',
            'distribution', 'profile', 'relationship',
            'vs', 'versus', 'against', 'contour', 'contours',
            'shape factor', 'shape factors', 'f12', 'f21', 'fij',
            'data', 'values', 'tabulated', 'nomograph', 'nomograms'
        ]
        
        # Track processed figures to avoid duplicates
        processed_figures = set()
        
        # Scan document for figure captions and classify
        for page_num in range(doc.page_count):
            page = doc[page_num]
            
            # Get full page text for extended caption analysis
            full_page_text = page.get_text()
            
            # Find figure references and extract extended captions
            fig_patterns = [
                r'Fig\.?\s*(\d+(?:\.\d+)?)',
                r'Figure\s*(\d+(?:\.\d+)?)'
            ]
            
            for pattern in fig_patterns:
                for match in re.finditer(pattern, full_page_text, re.IGNORECASE):
                    fig_number = match.group(1)
                    
                    # Extract extended caption context (next 300 characters after figure reference)
                    start_pos = match.end()
                    extended_context = full_page_text[start_pos:start_pos + 300]
                    
                    # Clean up the extended context
                    extended_context = re.sub(r'\s+', ' ', extended_context).strip()
                    
                    # Also get the immediate context before the figure reference (for leading text)
                    pre_context = full_page_text[max(0, match.start() - 100):match.start()]
                    full_context = pre_context + " " + match.group(0) + " " + extended_context
                    
                    # Classify based on extended caption content
                    context_lower = full_context.lower()
                    found_keywords = [kw for kw in graph_keywords if kw.lower() in context_lower]
                    is_graph = len(found_keywords) > 0
                    
                    # Only process if not already processed OR if this instance has graph keywords and previous didn't
                    should_process = fig_number not in processed_figures
                    if not should_process and is_graph:
                        # Check if existing classification was diagram - upgrade to graph if we found keywords
                        if self.figure_profile['figure_classification'].get(fig_number) == 'diagram':
                            # Remove from diagram zones
                            self.figure_profile['diagram_zones'] = [
                                zone for zone in self.figure_profile['diagram_zones'] 
                                if zone['figure_number'] != fig_number
                            ]
                            should_process = True
                    
                    if should_process:
                        zone_info = {
                            'figure_number': fig_number,
                            'page': page_num + 1,
                            'caption': extended_context[:150] + ("..." if len(extended_context) > 150 else ""),
                            'extended_context': full_context,
                            'bbox': [match.start(), 0, match.end(), 20],  # Approximate bbox
                            'classification_reason': self._get_classification_reason(full_context, graph_keywords),
                            'found_keywords': found_keywords
                        }
                        
                        if is_graph:
                            self.figure_profile['graph_zones'].append(zone_info)
                            self.figure_profile['figure_classification'][fig_number] = 'graph'
                        else:
                            self.figure_profile['diagram_zones'].append(zone_info)
                            self.figure_profile['figure_classification'][fig_number] = 'diagram'
                        
                        processed_figures.add(fig_number)
    
    def _get_classification_reason(self, caption_text: str, graph_keywords: list) -> str:
        """Get the reason why a figure was classified as graph or diagram"""
        caption_lower = caption_text.lower()
        found_keywords = [kw for kw in graph_keywords if kw.lower() in caption_lower]
        
        if found_keywords:
            return f"Graph keywords found: {', '.join(found_keywords)}"
        else:
            return "No graph keywords detected - classified as diagram"

    def _display_figure_analysis(self):
        """Display figure analysis results"""
        total_figures = self.figure_profile["total_figures"]
        embedded_images = self.figure_profile["total_embedded_images"]
        vector_elements = self.figure_profile["total_vector_elements"]
        
        print(f"   📊 Found: {total_figures} total figures (caption-based), "
              f"{embedded_images} embedded images, {vector_elements} vector elements")
        print(f"   📝 Figure numbers: {self.figure_profile['figure_numbers']}")
        print(f"   🎯 Recommended method: {self.figure_profile['recommended_method']}")
        
        # NEW: Display graph vs diagram classification
        graph_count = len(self.figure_profile['graph_zones'])
        diagram_count = len(self.figure_profile['diagram_zones'])
        print(f"   📊 Graph zones (data extractable): {graph_count}")
        print(f"   🖼️  Diagram zones (visual only): {diagram_count}")
        
        if graph_count > 0:
            print(f"   📈 Identified graphs: {[zone['figure_number'] for zone in self.figure_profile['graph_zones']]}")

def test_figure_analyzer():
    """Test the figure intelligence analyzer independently"""
    print("🧪 Testing Figure Intelligence Analyzer (Isolated)")
    print("=" * 55)
    
    pdf_path = "tests/test_data/Ch-04_Heat_Transfer.pdf"
    
    if not os.path.exists(pdf_path):
        print(f"❌ Test PDF not found: {pdf_path}")
        return
    
    try:
        # Test isolated figure analyzer
        analyzer = FigureIntelligenceAnalyzer()
        
        doc = fitz.open(pdf_path)
        figure_profile = analyzer.analyze_figures(doc)
        doc.close()
        
        print(f"\\n📊 ISOLATED FIGURE ANALYSIS RESULTS:")
        print(f"   Total figures detected: {figure_profile['total_figures']}")
        print(f"   Embedded images: {figure_profile['total_embedded_images']}")
        print(f"   Vector elements: {figure_profile['total_vector_elements']}")
        print(f"   Recommended method: {figure_profile['recommended_method']}")
        
        print(f"\\n✅ Figure analyzer test completed successfully!")
        return figure_profile
        
    except Exception as e:
        print(f"❌ Figure analyzer test failed: {e}")
        import traceback
        traceback.print_exc()

def main():
    """Main function"""
    test_figure_analyzer()

if __name__ == "__main__":
    main()