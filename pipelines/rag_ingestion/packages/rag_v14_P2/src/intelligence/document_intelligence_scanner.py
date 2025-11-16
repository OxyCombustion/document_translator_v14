#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Document Intelligence Scanner - Phase 1 Analysis
Scans entire document to understand content patterns and layout
Creates extraction strategy profile for Phase 2 adaptive extraction
"""

import sys
import os
import json
from datetime import datetime
from pathlib import Path
from collections import defaultdict, Counter

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
import re

class DocumentIntelligenceScanner:
    """
    Phase 1: Comprehensive document analysis to understand content patterns
    Creates intelligent extraction strategy for Phase 2
    """
    
    def __init__(self):
        """Initialize the document intelligence scanner"""
        self.content_profile = {
            "figures": {
                "total_embedded_images": 0,
                "total_vector_elements": 0,
                "image_pages": [],
                "image_formats": {},
                "size_distribution": [],
                "recommended_method": "unknown"
            },
            "equations": {
                "total_found": 0,
                "complexity_distribution": {},
                "spatial_patterns": {},
                "size_recommendations": {}
            },
            "tables": {
                "estimated_count": 0,
                "structure_hints": [],
                "extraction_method": "unknown"
            },
            "layout": {
                "page_dimensions": [],
                "content_density": [],
                "spatial_relationships": {}
            },
            "extraction_strategy": {}
        }
    
    def scan_document(self, pdf_path: str) -> dict:
        """
        Main entry point: Comprehensive document intelligence scan
        Returns complete document profile with extraction recommendations
        """
        print("🧠 Document Intelligence Scanner - Phase 1 Analysis")
        print("=" * 65)
        
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
        try:
            doc = fitz.open(pdf_path)
            print(f"📖 Scanning {len(doc)} pages for content intelligence...\n")
            
            # Comprehensive content analysis
            self._analyze_figure_content(doc)
            self._analyze_equation_patterns(doc)
            self._analyze_table_indicators(doc)
            self._analyze_layout_patterns(doc)
            
            # Generate intelligent extraction strategy
            self._generate_extraction_strategy()
            
            doc.close()
            
            # Save and display profile
            self._save_document_profile(pdf_path)
            self._display_intelligence_summary()
            
            return self.content_profile
            
        except Exception as e:
            print(f"❌ Document intelligence scan failed: {e}")
            raise
    
    def _analyze_figure_content(self, doc: fitz.Document):
        """
        Analyze figure content types, formats, and patterns
        """
        print("🖼️ Analyzing Figure Content Intelligence...")
        
        embedded_images = []
        vector_pages = []
        total_vector_elements = 0
        figure_captions = set()  # Track unique figure numbers
        
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            
            # Caption-based figure detection (PRIMARY METHOD)
            text_dict = page.get_text("dict")
            for block in text_dict["blocks"]:
                if "lines" not in block:
                    continue
                    
                for line in block["lines"]:
                    for span in line["spans"]:
                        text = span["text"].strip()
                        
                        # Look for figure captions using proven patterns
                        import re
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
            
            # Embedded image analysis (SECONDARY - for format understanding)
            images = page.get_images(full=True)
            if images:
                self.content_profile["figures"]["image_pages"].append(page_num + 1)
                
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
                        self.content_profile["figures"]["image_formats"][colorspace] = \
                            self.content_profile["figures"]["image_formats"].get(colorspace, 0) + 1
                        
                        pix = None
                        
                    except Exception as e:
                        print(f"   Warning: Could not analyze image on page {page_num + 1}: {e}")
            
            # Vector graphics analysis
            drawings = page.get_drawings()
            if drawings and len(drawings) > 10:  # Significant vector content
                vector_pages.append(page_num + 1)
                total_vector_elements += len(drawings)
        
        # Update profile with CAPTION-BASED counting (primary)
        total_figures = len(figure_captions)
        self.content_profile["figures"]["total_figures"] = total_figures
        self.content_profile["figures"]["figure_numbers"] = sorted(list(figure_captions))
        self.content_profile["figures"]["total_embedded_images"] = len(embedded_images)
        self.content_profile["figures"]["total_vector_elements"] = total_vector_elements
        self.content_profile["figures"]["size_distribution"] = embedded_images
        
        # Determine recommended extraction method based on actual figure count
        if len(embedded_images) >= total_figures * 0.7:  # If 70%+ are embedded images
            self.content_profile["figures"]["recommended_method"] = "embedded_image_primary"
        elif total_vector_elements > 500:
            self.content_profile["figures"]["recommended_method"] = "vector_graphics_primary"
        else:
            self.content_profile["figures"]["recommended_method"] = "caption_based_hybrid"
        
        print(f"   📊 Found: {total_figures} total figures (caption-based), {len(embedded_images)} embedded images, {total_vector_elements} vector elements")
        print(f"   📝 Figure numbers: {sorted(list(figure_captions))}")
        print(f"   🎯 Recommended method: {self.content_profile['figures']['recommended_method']}")
    
    def _analyze_equation_patterns(self, doc: fitz.Document):
        """
        Analyze equation complexity and spatial patterns
        """
        print("📐 Analyzing Equation Pattern Intelligence...")
        
        equation_candidates = []
        complexity_distribution = defaultdict(int)
        
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
                        
                        # Use successful equation detection pattern
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
                                complexity_distribution[complexity["level"]] += 1
        
        # Get unique equation numbers (eliminate duplicates)
        unique_equation_numbers = set()
        unique_equation_candidates = []
        
        for eq in equation_candidates:
            eq_key = (eq["number"], eq["suffix"])  # Use number + suffix as unique key
            if eq_key not in unique_equation_numbers:
                unique_equation_numbers.add(eq_key)
                unique_equation_candidates.append(eq)
        
        # Update profile with UNIQUE equation count
        self.content_profile["equations"]["total_found"] = len(unique_equation_candidates)
        self.content_profile["equations"]["equation_numbers"] = sorted([eq["number"] for eq in unique_equation_candidates])
        self.content_profile["equations"]["complexity_distribution"] = dict(complexity_distribution)
        self.content_profile["equations"]["duplicate_detections"] = len(equation_candidates) - len(unique_equation_candidates)
        
        # Generate size recommendations based on complexity
        if complexity_distribution["very_complex"] > 5:
            self.content_profile["equations"]["size_recommendations"]["adaptive_sizing"] = True
            self.content_profile["equations"]["size_recommendations"]["max_height"] = 300
        else:
            self.content_profile["equations"]["size_recommendations"]["adaptive_sizing"] = False
            self.content_profile["equations"]["size_recommendations"]["max_height"] = 60
        
        print(f"   📊 Found: {len(unique_equation_candidates)} unique equations (filtered from {len(equation_candidates)} candidates)")
        print(f"   🔍 Duplicates filtered: {len(equation_candidates) - len(unique_equation_candidates)}")
        print(f"   📝 Equation numbers: {sorted([eq['number'] for eq in unique_equation_candidates])}")
        print(f"   📈 Complexity: {dict(complexity_distribution)}")
    
    def _estimate_equation_complexity(self, page: fitz.Page, number_bbox: list) -> dict:
        """
        Estimate equation complexity around a number (simplified version)
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
    
    def _analyze_table_indicators(self, doc: fitz.Document):
        """
        Analyze table presence and structure hints
        """
        print("📊 Analyzing Table Structure Intelligence...")
        
        # Look for table indicators
        table_keywords = ["Table", "table", "tabular", "data"]
        table_references = 0
        
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            text = page.get_text()
            
            for keyword in table_keywords:
                table_references += text.count(keyword)
        
        # Estimate table count (rough heuristic)
        estimated_tables = min(table_references // 10, 20)  # Conservative estimate
        
        self.content_profile["tables"]["estimated_count"] = estimated_tables
        self.content_profile["tables"]["extraction_method"] = "docling_primary" if estimated_tables > 5 else "manual_analysis"
        
        print(f"   📊 Estimated tables: {estimated_tables}")
    
    def _analyze_layout_patterns(self, doc: fitz.Document):
        """
        Analyze document layout patterns and spatial relationships
        """
        print("📏 Analyzing Layout Pattern Intelligence...")
        
        page_dimensions = []
        content_densities = []
        
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            
            page_dimensions.append({
                "width": page.rect.width,
                "height": page.rect.height,
                "area": page.rect.width * page.rect.height
            })
            
            # Estimate content density
            text_blocks = page.get_text("dict")["blocks"]
            text_area = sum(
                (block["bbox"][2] - block["bbox"][0]) * (block["bbox"][3] - block["bbox"][1])
                for block in text_blocks if "bbox" in block
            )
            
            page_area = page.rect.width * page.rect.height
            content_densities.append({
                "page": page_num + 1,
                "text_coverage": text_area / page_area if page_area > 0 else 0
            })
        
        self.content_profile["layout"]["page_dimensions"] = page_dimensions
        self.content_profile["layout"]["content_density"] = content_densities
        
        # Calculate average content density
        avg_density = sum(d["text_coverage"] for d in content_densities) / len(content_densities)
        print(f"   📊 Average content density: {avg_density:.2f}")
    
    def _generate_extraction_strategy(self):
        """
        Generate intelligent extraction strategy based on analysis
        """
        print("🎯 Generating Adaptive Extraction Strategy...")
        
        strategy = {}
        
        # Figure extraction strategy - use ACTUAL figure count from captions
        figures = self.content_profile["figures"]
        total_figures = figures["total_figures"]
        embedded_images = figures["total_embedded_images"]
        
        if embedded_images >= total_figures * 0.7:  # 70%+ are embedded images
            strategy["figures"] = {
                "primary_method": "embedded_image_detection",
                "target_dpi": 300,
                "expected_count": total_figures,
                "embedded_count": embedded_images,
                "quality_threshold": 0.8
            }
        else:
            strategy["figures"] = {
                "primary_method": "caption_based_hybrid_detection",
                "target_dpi": 300,
                "expected_count": total_figures,
                "embedded_count": embedded_images,
                "quality_threshold": 0.6
            }
        
        # Equation extraction strategy
        equations = self.content_profile["equations"]
        if equations["complexity_distribution"].get("very_complex", 0) > 3:
            strategy["equations"] = {
                "method": "adaptive_smart_extraction",
                "crop_sizing": "dynamic",
                "max_height": 300,
                "expected_count": equations["total_found"]
            }
        else:
            strategy["equations"] = {
                "method": "focused_hybrid_extraction",
                "crop_sizing": "fixed",
                "max_height": 40,
                "expected_count": equations["total_found"]
            }
        
        # Table extraction strategy
        tables = self.content_profile["tables"]
        strategy["tables"] = {
            "method": tables["extraction_method"],
            "expected_count": tables["estimated_count"]
        }
        
        self.content_profile["extraction_strategy"] = strategy
        
        print(f"   ✅ Strategy generated for figures, equations, and tables")
    
    def _save_document_profile(self, pdf_path: str):
        """
        Save complete document profile
        """
        profile_data = {
            "scan_timestamp": datetime.now().isoformat(),
            "pdf_path": pdf_path,
            "document_profile": self.content_profile
        }
        
        output_path = "document_intelligence_profile.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(profile_data, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Document profile saved: {output_path}")
    
    def _display_intelligence_summary(self):
        """
        Display comprehensive intelligence summary
        """
        print(f"\n" + "=" * 65)
        print(f"🧠 DOCUMENT INTELLIGENCE SUMMARY")
        print(f"=" * 65)
        
        figures = self.content_profile["figures"]
        equations = self.content_profile["equations"]
        tables = self.content_profile["tables"]
        strategy = self.content_profile["extraction_strategy"]
        
        print(f"🖼️ FIGURES:")
        print(f"   Total figures: {figures['total_figures']} (caption-based detection)")
        print(f"   Embedded images: {figures['total_embedded_images']}")
        print(f"   Vector elements: {figures['total_vector_elements']}")
        print(f"   Figure numbers: {figures['figure_numbers']}")
        print(f"   Recommended method: {figures['recommended_method']}")
        
        print(f"\n📐 EQUATIONS:")
        print(f"   Total found: {equations['total_found']}")
        print(f"   Complexity distribution: {equations['complexity_distribution']}")
        
        print(f"\n📊 TABLES:")
        print(f"   Estimated count: {tables['estimated_count']}")
        print(f"   Recommended method: {tables['extraction_method']}")
        
        print(f"\n🎯 EXTRACTION STRATEGY:")
        for content_type, config in strategy.items():
            print(f"   {content_type.upper()}: {config}")
        
        print(f"\n✅ Phase 1 Complete - Ready for intelligent Phase 2 extraction")

def test_document_intelligence():
    """
    Test the document intelligence scanner
    """
    print("🧪 Testing Document Intelligence Scanner")
    print("=" * 50)
    
    pdf_path = "tests/test_data/Ch-04_Heat_Transfer.pdf"
    
    if not os.path.exists(pdf_path):
        print(f"❌ Test PDF not found: {pdf_path}")
        return
    
    try:
        scanner = DocumentIntelligenceScanner()
        profile = scanner.scan_document(pdf_path)
        
        print(f"\n✅ Document intelligence scan completed successfully!")
        
    except Exception as e:
        print(f"❌ Intelligence scan failed: {e}")
        import traceback
        traceback.print_exc()

def main():
    """Main function"""
    test_document_intelligence()

if __name__ == "__main__":
    main()