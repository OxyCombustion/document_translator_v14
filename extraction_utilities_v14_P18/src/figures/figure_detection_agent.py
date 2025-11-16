#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Figure Detection Agent - Stage 1 of Figure Extraction
Detects figures using multiple complementary methods following proven patterns
"""

import sys
import os
import re
from typing import List, Dict, Optional, Tuple, Any

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    import io
    if not hasattr(sys.stdout, '_wrapped_utf8'):
        try:
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
            sys.stdout._wrapped_utf8 = True
        except (AttributeError, ValueError):
            os.system('chcp 65001')
    if not hasattr(sys.stderr, '_wrapped_utf8'):
        try:
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
            sys.stderr._wrapped_utf8 = True
        except (AttributeError, ValueError):
            pass

import fitz  # PyMuPDF
from extraction_v14_P1.src.agents.figure.figure_data_structures import (
    FigureCandidate, BoundingBox, DetectionMethod,
    FigureDetectionError, QualityMetrics
)

class FigureDetectionAgent:
    """
    Stage 1: Multi-method figure detection agent
    Follows the proven pattern: Detection → Analysis → Extraction
    """
    
    def __init__(self):
        """Initialize the figure detection agent"""
        self.detection_methods = [
            self.detect_embedded_images,
            self.detect_by_captions,
            self.detect_vector_graphics,
            self.detect_by_whitespace
        ]
        
        # Caption patterns (similar to equation detection regex success)
        self.caption_patterns = [
            r'Fig\.?\s*(\d+)',           # Fig. 1, Fig 2
            r'Figure\s*(\d+)',           # Figure 1, Figure 2
            r'Fig\.?\s*(\d+\w*)',        # Fig. 1a, Fig 2b
            r'Figure\s*(\d+\w*)',        # Figure 1a, Figure 2b
        ]
    
    def detect_figures(self, page: fitz.Page, page_num: int) -> List[FigureCandidate]:
        """
        Main detection method combining all approaches
        Returns consolidated list of figure candidates
        """
        all_candidates = []
        
        print(f"   🔍 Detecting figures on page {page_num + 1}...")
        
        try:
            # Method 1: Embedded images (most reliable)
            embedded_candidates = self.detect_embedded_images(page, page_num)
            all_candidates.extend(embedded_candidates)
            if embedded_candidates:
                print(f"      📷 Found {len(embedded_candidates)} embedded images")
            
            # Method 2: Caption-based detection (proven pattern from equations)
            caption_candidates = self.detect_by_captions(page, page_num)
            all_candidates.extend(caption_candidates)
            if caption_candidates:
                print(f"      📝 Found {len(caption_candidates)} caption-based figures")
            
            # Method 3: Vector graphics detection
            vector_candidates = self.detect_vector_graphics(page, page_num)
            all_candidates.extend(vector_candidates)
            if vector_candidates:
                print(f"      📐 Found {len(vector_candidates)} vector graphics")
            
            # Method 4: Whitespace analysis
            whitespace_candidates = self.detect_by_whitespace(page, page_num)
            all_candidates.extend(whitespace_candidates)
            if whitespace_candidates:
                print(f"      ⬜ Found {len(whitespace_candidates)} whitespace regions")
            
            # Remove duplicates and merge overlapping candidates
            consolidated_candidates = self._consolidate_candidates(all_candidates)
            
            print(f"      ✅ Total unique figures: {len(consolidated_candidates)}")
            return consolidated_candidates
            
        except Exception as e:
            print(f"      ❌ Error detecting figures: {e}")
            raise FigureDetectionError(f"Failed to detect figures on page {page_num}: {e}")
    
    def detect_embedded_images(self, page: fitz.Page, page_num: int) -> List[FigureCandidate]:
        """
        Detect embedded raster images in PDF
        Most reliable method for photograph and raster-based figures
        """
        candidates = []
        
        try:
            # Get all images on the page
            image_list = page.get_images(full=True)
            
            for img_index, img in enumerate(image_list):
                # Extract image reference info
                xref = img[0]  # Image xref number
                pix = fitz.Pixmap(page.parent, xref)
                
                # Skip mask images and very small images
                if pix.n < 4 or pix.width < 50 or pix.height < 50:
                    pix = None
                    continue
                
                # Find image placement on page
                image_rects = page.get_image_rects(xref)
                
                for rect in image_rects:
                    bbox = BoundingBox(rect.x0, rect.y0, rect.x1, rect.y1)
                    
                    # Calculate quality metrics
                    quality_metrics = QualityMetrics(
                        width_pixels=pix.width,
                        height_pixels=pix.height,
                        resolution_dpi=pix.xres if hasattr(pix, 'xres') else None,
                        content_density=bbox.area
                    )
                    
                    candidate = FigureCandidate(
                        bbox=bbox,
                        page_number=page_num,
                        detection_method=DetectionMethod.EMBEDDED_IMAGE,
                        confidence_score=0.9,  # High confidence for embedded images
                        metadata={
                            "image_xref": xref,
                            "image_index": img_index,
                            "image_width": pix.width,
                            "image_height": pix.height,
                            "image_format": pix.colorspace.name if pix.colorspace else "unknown"
                        },
                        quality_metrics=quality_metrics
                    )
                    
                    candidates.append(candidate)
                
                pix = None  # Clean up
                
        except Exception as e:
            print(f"         Error in embedded image detection: {e}")
        
        return candidates
    
    def detect_by_captions(self, page: fitz.Page, page_num: int) -> List[FigureCandidate]:
        """
        Detect figures by finding ACTUAL captions (not text references)
        Distinguishes real figure captions from references in body text
        """
        candidates = []
        
        try:
            # Get text content with position information
            text_dict = page.get_text("dict")
            
            for block in text_dict["blocks"]:
                if "lines" not in block:
                    continue
                    
                for line in block["lines"]:
                    for span in line["spans"]:
                        text = span["text"].strip()
                        
                        # Test each caption pattern
                        for pattern in self.caption_patterns:
                            match = re.search(pattern, text, re.IGNORECASE)
                            if match:
                                # CRITICAL: Filter out text references vs real captions
                                if not self._is_real_figure_caption(span, text, line):
                                    continue
                                
                                figure_number = match.group(1)
                                span_bbox = BoundingBox(*span["bbox"])
                                
                                # Estimate figure area based on caption position
                                # Figures are typically ABOVE their captions
                                figure_bbox = self._estimate_figure_from_caption(span_bbox, page)
                                
                                candidate = FigureCandidate(
                                    bbox=figure_bbox,
                                    page_number=page_num,
                                    detection_method=DetectionMethod.CAPTION_BASED,
                                    confidence_score=0.8,  # Good confidence for caption-based
                                    metadata={
                                        "caption_text": text,
                                        "figure_number": figure_number,
                                        "caption_bbox": [span_bbox.x0, span_bbox.y0, span_bbox.x1, span_bbox.y1],
                                        "pattern_used": pattern
                                    },
                                    caption_text=text,
                                    figure_number=figure_number
                                )
                                
                                candidates.append(candidate)
                                break  # Found match, move to next span
                                
        except Exception as e:
            print(f"         Error in caption detection: {e}")
        
        return candidates
    
    def _is_real_figure_caption(self, span: dict, text: str, line: dict) -> bool:
        """
        Determine if this is a real figure caption vs a text reference
        Based on comprehensive analysis of actual document patterns
        """
        
        # Get font characteristics
        font_name = span.get('font', '')
        font_size = span.get('size', 0)
        text_lower = text.lower()
        
        # STRICT RULE 1: Real captions MUST use caption fonts (Arial-BoldMT, Size 8.0)
        # From analysis: ALL real captions use Arial-BoldMT at size 8.0
        # Text references use CenturySchoolbook at size 10.0
        is_caption_font = (
            'Arial' in font_name and 
            'Bold' in font_name and
            abs(font_size - 8.0) < 0.5  # Allow slight variation in font size
        )
        
        # If not using caption font, it's almost certainly a text reference
        if not is_caption_font:
            return False
        
        # STRICT RULE 2: Reject clear text reference patterns
        # These patterns indicate text definitely embedded in sentences
        text_reference_patterns = [
            # Clear embedded reference patterns
            'illustrates',
            'described by', 
            'shown in fig',
            'see fig', 
            'referring to fig',
            'given in fig',
            'shown in chapter',
            # Clear equation confusion patterns
            'equation (',
            'eq. (',
            'eqn (',
            'equations (',
            # Clear sentence structure indicators  
            'is shown',
            'cannot be obtained',
            'have long been',
            # Clear partial sentence fragments
            'the top portion',
            'the bottom',
            'other,',
        ]
        
        # Check for any text reference indicators
        for pattern in text_reference_patterns:
            if pattern in text_lower:
                return False
        
        # STRICT RULE 3: Real captions have specific structural patterns
        # From analysis: Real captions are either:
        # 1. "Fig. X   Descriptive title" (with descriptive content)
        # 2. Standalone figure number with clear context
        
        # Check if this looks like a complete descriptive caption
        # Real captions have substantive descriptive content after the number
        caption_content_indicators = [
            'temperature', 'distribution', 'composite', 'wall', 'fluid',
            'energy', 'balance', 'system',
            'shape', 'factors', 'calculating', 'radiation',
            'electric', 'circuit', 'analogy', 'thermal',
            'conductivity', 'steels', 'commonly', 'used',
            'effect', 'composition', 'structure', 'coal',
            'emissivity', 'water', 'vapor', 'carbon', 'dioxide',
            'correction', 'factor', 'associated',
            'turbulent', 'flow', 'field', 'boundary',
            'convection', 'velocity', 'geometry',
            'arrangement', 'crossflow', 'reynolds',
            'transfer', 'depth', 'tube', 'rows',
            'effective', 'difference', 'single-pass',
            'fin', 'efficiency', 'function', 'parameter',
            'coefficient', 'ratio', 'simultaneous',
            'heat', 'mass', 'dehumidification',
            'control', 'volume', 'layout', 'notation',
            'vertical', 'horizontal', 'furnace',
            'circumferential', 'membrane',
            'area', 'effectiveness', 'completely',
            'approximate', 'relationship', 'exit',
            'general', 'range', 'absorption',
            'utility', 'boiler', 'schematic', 'numerical',
            'predicted', 'projected', 'comparison',
            'radiative', 'convective', 'contribution',
            'example', 'insulated', 'pipe',
            'radiation', 'cavity'
        ]
        
        # Check if caption has substantive descriptive content
        has_descriptive_content = any(indicator in text_lower for indicator in caption_content_indicators)
        
        # RULE 4: Length and structure checks
        words = text.split()
        
        # Real captions should have some substance beyond bare references
        is_substantial = len(words) >= 3  # At least "Fig. X description" 
        
        # Check for typical caption structure: "Fig. X   Description..."
        # Look for figure number followed by descriptive content
        fig_pattern = re.search(r'fig\.?\s*(\d+)', text_lower)
        if fig_pattern:
            # Get text after figure number
            fig_num_pos = fig_pattern.end()
            remaining_text = text[fig_num_pos:].strip()
            
            # Real captions have some text after the number (allow shorter descriptions)
            has_description_after_number = len(remaining_text.split()) >= 1
            
            # Final decision for captions with figure numbers
            # More lenient: accept if has descriptive content OR is substantial
            return (
                (has_descriptive_content or is_substantial) and 
                has_description_after_number
            )
        
        # If no clear figure number pattern, probably not a caption
        return False
    
    def detect_vector_graphics(self, page: fitz.Page, page_num: int) -> List[FigureCandidate]:
        """
        Detect vector-based figures (diagrams, charts, schematics)
        Analyzes drawing commands and geometric patterns
        """
        candidates = []
        
        try:
            # Get drawing commands from page
            drawings = page.get_drawings()
            
            if not drawings:
                return candidates
            
            # Group drawings into potential figures
            drawing_groups = self._group_drawings(drawings)
            
            for group in drawing_groups:
                if len(group) < 3:  # Skip very simple drawing groups
                    continue
                
                # Calculate bounding box for entire group
                min_x = min(item["rect"].x0 for item in group)
                min_y = min(item["rect"].y0 for item in group)
                max_x = max(item["rect"].x1 for item in group)
                max_y = max(item["rect"].y1 for item in group)
                
                bbox = BoundingBox(min_x, min_y, max_x, max_y)
                
                # Filter out very small or very large areas
                if bbox.area < 1000 or bbox.area > page.rect.area * 0.8:
                    continue
                
                candidate = FigureCandidate(
                    bbox=bbox,
                    page_number=page_num,
                    detection_method=DetectionMethod.VECTOR_GRAPHICS,
                    confidence_score=0.7,  # Moderate confidence for vector detection
                    metadata={
                        "drawing_count": len(group),
                        "drawing_types": [item.get("type", "unknown") for item in group],
                        "vector_complexity": len(group)
                    }
                )
                
                candidates.append(candidate)
                
        except Exception as e:
            print(f"         Error in vector graphics detection: {e}")
        
        return candidates
    
    def detect_by_whitespace(self, page: fitz.Page, page_num: int) -> List[FigureCandidate]:
        """
        Detect figures by analyzing whitespace patterns
        Identifies large non-text regions that might contain figures
        """
        candidates = []
        
        try:
            # Get text blocks to identify non-text areas
            text_blocks = page.get_text("dict")["blocks"]
            text_rects = []
            
            for block in text_blocks:
                if "bbox" in block:
                    text_rects.append(fitz.Rect(block["bbox"]))
            
            # Analyze page grid for large whitespace areas
            page_rect = page.rect
            grid_size = 50  # 50 pixel grid
            
            potential_areas = []
            
            for x in range(0, int(page_rect.width), grid_size):
                for y in range(0, int(page_rect.height), grid_size):
                    test_rect = fitz.Rect(x, y, x + grid_size, y + grid_size)
                    
                    # Check if this area overlaps with text
                    overlaps_text = any(test_rect.intersects(text_rect) for text_rect in text_rects)
                    
                    if not overlaps_text and test_rect.area > 2500:  # Minimum area threshold
                        potential_areas.append(test_rect)
            
            # Merge adjacent whitespace areas
            merged_areas = self._merge_adjacent_rects(potential_areas)
            
            for area in merged_areas:
                if area.area > 10000:  # Only consider substantial areas
                    bbox = BoundingBox(area.x0, area.y0, area.x1, area.y1)
                    
                    candidate = FigureCandidate(
                        bbox=bbox,
                        page_number=page_num,
                        detection_method=DetectionMethod.WHITESPACE_ANALYSIS,
                        confidence_score=0.5,  # Lower confidence for whitespace-based
                        metadata={
                            "whitespace_area": area.area,
                            "grid_analysis": True
                        }
                    )
                    
                    candidates.append(candidate)
                    
        except Exception as e:
            print(f"         Error in whitespace detection: {e}")
        
        return candidates
    
    def _estimate_figure_from_caption(self, caption_bbox: BoundingBox, page: fitz.Page) -> BoundingBox:
        """
        Estimate figure location based on caption position
        Assumes figures are typically above their captions
        """
        # Standard assumption: figure is above caption
        estimated_height = 150  # Default figure height estimate
        margin = 10
        
        figure_bbox = BoundingBox(
            x0=caption_bbox.x0 - margin,
            y0=max(0, caption_bbox.y0 - estimated_height - margin),
            x1=caption_bbox.x1 + margin,
            y1=caption_bbox.y0 - margin
        )
        
        # Ensure bounds are within page
        figure_bbox.x1 = min(figure_bbox.x1, page.rect.width)
        figure_bbox.y1 = min(figure_bbox.y1, page.rect.height)
        
        return figure_bbox
    
    def _group_drawings(self, drawings: List[Dict]) -> List[List[Dict]]:
        """
        Group related drawing elements into potential figures
        """
        if not drawings:
            return []
        
        groups = []
        tolerance = 20  # Pixel tolerance for grouping
        
        for drawing in drawings:
            added_to_group = False
            drawing_rect = drawing["rect"]
            
            for group in groups:
                # Check if drawing is close to any drawing in the group
                for group_drawing in group:
                    group_rect = group_drawing["rect"]
                    
                    # Simple distance-based grouping
                    if (abs(drawing_rect.x0 - group_rect.x1) < tolerance or
                        abs(drawing_rect.x1 - group_rect.x0) < tolerance or
                        abs(drawing_rect.y0 - group_rect.y1) < tolerance or
                        abs(drawing_rect.y1 - group_rect.y0) < tolerance):
                        
                        group.append(drawing)
                        added_to_group = True
                        break
                
                if added_to_group:
                    break
            
            if not added_to_group:
                groups.append([drawing])
        
        return groups
    
    def _merge_adjacent_rects(self, rects: List[fitz.Rect]) -> List[fitz.Rect]:
        """
        Merge adjacent rectangles into larger areas
        """
        if not rects:
            return []
        
        merged = []
        tolerance = 10
        
        for rect in rects:
            merged_with_existing = False
            
            for i, existing in enumerate(merged):
                # Check if rectangles are adjacent or overlapping
                if (abs(rect.x0 - existing.x1) < tolerance or
                    abs(rect.x1 - existing.x0) < tolerance or
                    abs(rect.y0 - existing.y1) < tolerance or
                    abs(rect.y1 - existing.y0) < tolerance or
                    rect.intersects(existing)):
                    
                    # Merge rectangles
                    merged_rect = fitz.Rect(
                        min(rect.x0, existing.x0),
                        min(rect.y0, existing.y0),
                        max(rect.x1, existing.x1),
                        max(rect.y1, existing.y1)
                    )
                    merged[i] = merged_rect
                    merged_with_existing = True
                    break
            
            if not merged_with_existing:
                merged.append(rect)
        
        return merged
    
    def _consolidate_candidates(self, candidates: List[FigureCandidate]) -> List[FigureCandidate]:
        """
        Remove duplicates and merge overlapping candidates
        Prioritizes higher confidence detections
        """
        if not candidates:
            return []
        
        # Sort by confidence score (highest first)
        sorted_candidates = sorted(candidates, key=lambda x: x.confidence_score, reverse=True)
        
        consolidated = []
        overlap_threshold = 0.5  # 50% overlap threshold
        
        for candidate in sorted_candidates:
            is_duplicate = False
            
            for existing in consolidated:
                # Calculate overlap
                overlap_area = self._calculate_overlap(candidate.bbox, existing.bbox)
                
                if overlap_area > overlap_threshold:
                    # This is a duplicate, skip it
                    is_duplicate = True
                    
                    # Update existing candidate with additional metadata if useful
                    if candidate.detection_method != existing.detection_method:
                        existing.metadata["additional_detection_methods"] = existing.metadata.get(
                            "additional_detection_methods", []
                        ) + [candidate.detection_method.value]
                    
                    break
            
            if not is_duplicate:
                consolidated.append(candidate)
        
        return consolidated
    
    def _calculate_overlap(self, bbox1: BoundingBox, bbox2: BoundingBox) -> float:
        """
        Calculate overlap ratio between two bounding boxes
        Returns value between 0 (no overlap) and 1 (complete overlap)
        """
        # Calculate intersection
        x_overlap = max(0, min(bbox1.x1, bbox2.x1) - max(bbox1.x0, bbox2.x0))
        y_overlap = max(0, min(bbox1.y1, bbox2.y1) - max(bbox1.y0, bbox2.y0))
        
        intersection_area = x_overlap * y_overlap
        
        if intersection_area == 0:
            return 0.0
        
        # Calculate union
        union_area = bbox1.area + bbox2.area - intersection_area
        
        if union_area == 0:
            return 0.0
        
        return intersection_area / union_area