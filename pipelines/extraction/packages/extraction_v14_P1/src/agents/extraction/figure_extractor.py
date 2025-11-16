#!/usr/bin/env python3
"""
Figure Extractor - Complete Figure Detection with Caption Association
Advanced figure extraction with caption matching and boundary detection

Features:
- Image boundary detection (raster and vector)
- Caption association using proximity and text analysis
- Figure type classification (charts, diagrams, photos, etc.)
- Cross-reference extraction from document text
- Multi-format support (embedded images, drawings, graphs)
- Spatial relationship analysis
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
import base64
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional, Tuple
import fitz  # PyMuPDF
import numpy as np
from collections import defaultdict

@dataclass
class FigureElement:
    """Individual figure with metadata and content"""
    figure_id: str
    page_number: int
    bbox: Tuple[float, float, float, float]
    figure_type: str  # 'image', 'chart', 'diagram', 'drawing'
    content_type: str  # 'raster', 'vector', 'mixed'
    caption: Optional[str] = None
    title: Optional[str] = None
    figure_number: Optional[str] = None  # "Figure 1", "Fig. 2", etc.
    references: List[str] = None  # Cross-references in text
    image_data: Optional[str] = None  # Base64 encoded image
    confidence: float = 0.0
    extraction_method: str = ""
    metadata: Dict[str, Any] = None

@dataclass
class DocumentFigures:
    """Complete figure extraction results"""
    document_path: str
    total_pages: int
    extraction_method: str
    figures: List[FigureElement]
    caption_associations: Dict[str, str]  # figure_id -> caption
    cross_references: Dict[str, List[str]]  # reference -> figure_ids
    metadata: Dict[str, Any]

class FigureExtractor:
    """Advanced figure extraction with caption association"""
    
    def __init__(self):
        self.logger = self._setup_logging()
        
        # Caption detection patterns
        self.caption_patterns = [
            r'^Figure\s+(\d+(?:\.\d+)?)[:\.]?\s*(.*?)$',
            r'^Fig\.\s*(\d+(?:\.\d+)?)[:\.]?\s*(.*?)$',
            r'^FIG\.\s*(\d+(?:\.\d+)?)[:\.]?\s*(.*?)$',
            r'^(\d+(?:\.\d+)?)[:\.]?\s*(.*?)$',  # Just number and text
        ]
        
        # Figure reference patterns in text
        self.reference_patterns = [
            r'\bFigure\s+(\d+(?:\.\d+)?)\b',
            r'\bFig\.\s*(\d+(?:\.\d+)?)\b',
            r'\(see\s+Figure\s+(\d+(?:\.\d+)?)\)',
            r'\(Figure\s+(\d+(?:\.\d+)?)\)',
        ]
        
        # Thresholds
        self.min_figure_size = 2000  # Square pixels
        self.caption_proximity_threshold = 100  # Pixels
        self.min_confidence = 0.3
        
        # Figure type keywords
        self.figure_type_keywords = {
            'chart': ['chart', 'graph', 'plot', 'distribution', 'curve'],
            'diagram': ['diagram', 'schematic', 'flow', 'process', 'system'],
            'photo': ['photograph', 'photo', 'image', 'picture'],
            'drawing': ['drawing', 'sketch', 'illustration', 'figure']
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
    
    def extract_figures(self, pdf_path: str, extract_images: bool = True) -> DocumentFigures:
        """Extract all figures from PDF document"""
        self.logger.info(f"Starting figure extraction from {pdf_path}")
        
        try:
            doc = fitz.open(pdf_path)
            figures = []
            all_text_elements = []
            
            # First pass: extract images and collect text
            for page_num in range(len(doc)):
                page = doc[page_num]
                
                # Extract images
                page_figures = self._extract_page_figures(page, page_num, extract_images)
                figures.extend(page_figures)
                
                # Collect text elements for caption detection
                text_elements = self._extract_text_elements(page, page_num)
                all_text_elements.extend(text_elements)
            
            doc.close()
            
            # Associate captions with figures
            caption_associations = self._associate_captions(figures, all_text_elements)
            
            # Extract cross-references
            cross_references = self._extract_cross_references(all_text_elements)
            
            # Create document figures
            doc_figures = DocumentFigures(
                document_path=pdf_path,
                total_pages=len(doc),
                extraction_method="Figure Extractor",
                figures=figures,
                caption_associations=caption_associations,
                cross_references=cross_references,
                metadata={
                    'total_figures': len(figures),
                    'extraction_date': str(datetime.now()),
                    'image_extraction_enabled': extract_images
                }
            )
            
            self.logger.info(f"Extracted {len(figures)} figures with {len(caption_associations)} caption associations")
            return doc_figures
            
        except Exception as e:
            self.logger.error(f"Figure extraction failed: {str(e)}")
            raise
    
    def _extract_page_figures(self, page: fitz.Page, page_num: int, extract_images: bool) -> List[FigureElement]:
        """Extract figures from a single page"""
        figures = []
        
        # Method 1: Extract embedded images
        image_figures = self._extract_embedded_images(page, page_num, extract_images)
        figures.extend(image_figures)
        
        # Method 2: Detect drawing/vector graphics
        drawing_figures = self._extract_drawings(page, page_num)
        figures.extend(drawing_figures)
        
        # Method 3: Detect figure-like text arrangements (for text-based diagrams)
        text_figures = self._extract_text_figures(page, page_num)
        figures.extend(text_figures)
        
        return figures
    
    def _extract_embedded_images(self, page: fitz.Page, page_num: int, extract_images: bool) -> List[FigureElement]:
        """Extract embedded images from page"""
        figures = []
        
        try:
            # Get image list
            image_list = page.get_images()
            
            for img_index, img in enumerate(image_list):
                try:
                    # Get image info
                    xref = img[0]
                    base_image = page.parent.extract_image(xref)
                    image_bytes = base_image["image"]
                    image_bbox = page.get_image_bbox(img)
                    
                    # Check minimum size
                    width = image_bbox.x1 - image_bbox.x0
                    height = image_bbox.y1 - image_bbox.y0
                    
                    if width * height < self.min_figure_size:
                        continue
                    
                    # Create figure element
                    figure = FigureElement(
                        figure_id=f"img_{page_num}_{img_index}",
                        page_number=page_num,
                        bbox=(image_bbox.x0, image_bbox.y0, image_bbox.x1, image_bbox.y1),
                        figure_type='image',
                        content_type='raster',
                        confidence=0.9,  # High confidence for embedded images
                        extraction_method='embedded_image',
                        metadata={
                            'width': width,
                            'height': height,
                            'xref': xref,
                            'image_format': base_image.get('ext', 'unknown')
                        }
                    )
                    
                    # Store image data if requested
                    if extract_images:
                        figure.image_data = base64.b64encode(image_bytes).decode()
                    
                    figures.append(figure)
                    
                except Exception as e:
                    self.logger.warning(f"Failed to extract image {img_index} on page {page_num}: {str(e)}")
        
        except Exception as e:
            self.logger.warning(f"Failed to get images from page {page_num}: {str(e)}")
        
        return figures
    
    def _extract_drawings(self, page: fitz.Page, page_num: int) -> List[FigureElement]:
        """Extract vector drawings and graphics"""
        figures = []
        
        try:
            # Get drawing commands
            drawings = page.get_drawings()
            
            if not drawings:
                return figures
            
            # Group drawings into potential figures
            drawing_groups = self._group_drawings(drawings)
            
            for group_idx, group in enumerate(drawing_groups):
                if len(group) < 3:  # Need at least 3 drawing elements for a figure
                    continue
                
                # Calculate bounding box for group
                min_x = min(item['rect'][0] for item in group)
                min_y = min(item['rect'][1] for item in group)
                max_x = max(item['rect'][2] for item in group)
                max_y = max(item['rect'][3] for item in group)
                
                width = max_x - min_x
                height = max_y - min_y
                
                if width * height < self.min_figure_size:
                    continue
                
                figure = FigureElement(
                    figure_id=f"drawing_{page_num}_{group_idx}",
                    page_number=page_num,
                    bbox=(min_x, min_y, max_x, max_y),
                    figure_type='drawing',
                    content_type='vector',
                    confidence=0.7,  # Medium confidence for drawings
                    extraction_method='vector_analysis',
                    metadata={
                        'width': width,
                        'height': height,
                        'drawing_count': len(group),
                        'has_text': any('text' in item for item in group)
                    }
                )
                
                figures.append(figure)
        
        except Exception as e:
            self.logger.warning(f"Failed to extract drawings from page {page_num}: {str(e)}")
        
        return figures
    
    def _group_drawings(self, drawings: List[Dict]) -> List[List[Dict]]:
        """Group related drawing elements"""
        if not drawings:
            return []
        
        groups = []
        processed = set()
        proximity_threshold = 50  # pixels
        
        for i, drawing in enumerate(drawings):
            if i in processed:
                continue
            
            group = [drawing]
            processed.add(i)
            
            # Find nearby drawings
            for j, other in enumerate(drawings):
                if j in processed or i == j:
                    continue
                
                if self._drawings_are_close(drawing, other, proximity_threshold):
                    group.append(other)
                    processed.add(j)
            
            groups.append(group)
        
        return groups
    
    def _drawings_are_close(self, drawing1: Dict, drawing2: Dict, threshold: float) -> bool:
        """Check if two drawings are spatially close"""
        rect1 = drawing1['rect']
        rect2 = drawing2['rect']
        
        # Calculate center points
        center1 = ((rect1[0] + rect1[2]) / 2, (rect1[1] + rect1[3]) / 2)
        center2 = ((rect2[0] + rect2[2]) / 2, (rect2[1] + rect2[3]) / 2)
        
        # Calculate distance
        distance = ((center1[0] - center2[0]) ** 2 + (center1[1] - center2[1]) ** 2) ** 0.5
        
        return distance <= threshold
    
    def _extract_text_figures(self, page: fitz.Page, page_num: int) -> List[FigureElement]:
        """Extract text-based figures (ASCII art, diagrams made with text)"""
        # This would be for detecting figures made entirely of text characters
        # Like flow charts made with ASCII characters
        return []  # Placeholder for now
    
    def _extract_text_elements(self, page: fitz.Page, page_num: int) -> List[Dict]:
        """Extract text elements for caption detection"""
        text_elements = []
        
        blocks = page.get_text("dict")
        
        for block in blocks['blocks']:
            if 'lines' in block:
                block_text = ""
                for line in block['lines']:
                    for span in line['spans']:
                        block_text += span['text'] + " "
                
                if block_text.strip():
                    text_elements.append({
                        'text': block_text.strip(),
                        'bbox': block['bbox'],
                        'page': page_num,
                        'font_size': line['spans'][0]['size'] if line['spans'] else 0
                    })
        
        return text_elements
    
    def _associate_captions(self, figures: List[FigureElement], text_elements: List[Dict]) -> Dict[str, str]:
        """Associate captions with figures using proximity and pattern matching"""
        associations = {}
        
        # Find potential captions
        potential_captions = []
        for text_elem in text_elements:
            for pattern in self.caption_patterns:
                match = re.match(pattern, text_elem['text'], re.IGNORECASE)
                if match:
                    figure_num = match.group(1) if match.lastindex >= 1 else ""
                    caption_text = match.group(2) if match.lastindex >= 2 else text_elem['text']
                    
                    potential_captions.append({
                        'text': text_elem['text'],
                        'caption': caption_text.strip(),
                        'figure_num': figure_num,
                        'bbox': text_elem['bbox'],
                        'page': text_elem['page']
                    })
                    break
        
        # Associate captions with figures
        for figure in figures:
            best_caption = None
            best_distance = float('inf')
            
            for caption in potential_captions:
                if caption['page'] != figure.page_number:
                    continue
                
                # Calculate distance between figure and caption
                distance = self._calculate_spatial_distance(figure.bbox, caption['bbox'])
                
                if distance < self.caption_proximity_threshold and distance < best_distance:
                    best_caption = caption
                    best_distance = distance
            
            if best_caption:
                associations[figure.figure_id] = best_caption['caption']
                figure.caption = best_caption['caption']
                figure.figure_number = best_caption['figure_num']
                
                # Update confidence based on caption quality
                figure.confidence = min(1.0, figure.confidence + 0.2)
        
        return associations
    
    def _calculate_spatial_distance(self, bbox1: Tuple[float, float, float, float], 
                                   bbox2: Tuple[float, float, float, float]) -> float:
        """Calculate spatial distance between two bounding boxes"""
        # Calculate center points
        center1 = ((bbox1[0] + bbox1[2]) / 2, (bbox1[1] + bbox1[3]) / 2)
        center2 = ((bbox2[0] + bbox2[2]) / 2, (bbox2[1] + bbox2[3]) / 2)
        
        # Euclidean distance
        distance = ((center1[0] - center2[0]) ** 2 + (center1[1] - center2[1]) ** 2) ** 0.5
        
        return distance
    
    def _extract_cross_references(self, text_elements: List[Dict]) -> Dict[str, List[str]]:
        """Extract figure references from document text"""
        references = defaultdict(list)
        
        for text_elem in text_elements:
            text = text_elem['text']
            
            for pattern in self.reference_patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                for match in matches:
                    ref_text = f"Figure {match}"
                    references[ref_text].append(text_elem.get('id', 'unknown'))
        
        return dict(references)
    
    def _classify_figure_type(self, figure: FigureElement, caption: str = "") -> str:
        """Classify figure type based on content and caption"""
        caption_lower = caption.lower() if caption else ""
        
        for fig_type, keywords in self.figure_type_keywords.items():
            for keyword in keywords:
                if keyword in caption_lower:
                    return fig_type
        
        # Default classification based on extraction method
        if figure.content_type == 'raster':
            return 'image'
        elif figure.content_type == 'vector':
            return 'diagram'
        
        return 'figure'  # Generic fallback
    
    def export_figures(self, doc_figures: DocumentFigures, output_path: str, include_images: bool = False):
        """Export figures to JSON"""
        try:
            # Prepare data for export
            export_data = asdict(doc_figures)
            
            # Remove image data if not requested (to reduce file size)
            if not include_images:
                for figure in export_data['figures']:
                    if 'image_data' in figure:
                        figure['image_data'] = None
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Figures exported to {output_path}")
            
        except Exception as e:
            self.logger.error(f"Failed to export figures: {str(e)}")
            raise
    
    def extract_figure_images(self, doc_figures: DocumentFigures, output_dir: str):
        """Extract individual figure images to files"""
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        for figure in doc_figures.figures:
            if figure.image_data:
                try:
                    image_bytes = base64.b64decode(figure.image_data)
                    
                    # Determine file extension
                    ext = figure.metadata.get('image_format', 'png')
                    filename = f"{figure.figure_id}.{ext}"
                    
                    with open(output_path / filename, 'wb') as f:
                        f.write(image_bytes)
                    
                    self.logger.info(f"Saved figure image: {filename}")
                    
                except Exception as e:
                    self.logger.warning(f"Failed to save image for {figure.figure_id}: {str(e)}")

def main():
    """Main function for testing"""
    import argparse
    from datetime import datetime
    
    parser = argparse.ArgumentParser(description="Figure Extraction")
    parser.add_argument("pdf_path", help="Path to PDF document")
    parser.add_argument("--output", help="Output JSON file", default="extracted_figures.json")
    parser.add_argument("--extract-images", action="store_true", help="Extract image data")
    parser.add_argument("--image-dir", help="Directory to save extracted images")
    
    args = parser.parse_args()
    
    if not Path(args.pdf_path).exists():
        print(f"Error: PDF file not found: {args.pdf_path}")
        return
    
    # Run extraction
    extractor = FigureExtractor()
    doc_figures = extractor.extract_figures(args.pdf_path, args.extract_images)
    
    # Export results
    extractor.export_figures(doc_figures, args.output, args.extract_images)
    
    # Save individual images if requested
    if args.image_dir and args.extract_images:
        extractor.extract_figure_images(doc_figures, args.image_dir)
    
    # Print summary
    print(f"\n{'='*60}")
    print(f"FIGURE EXTRACTION RESULTS")
    print(f"{'='*60}")
    print(f"Document: {Path(args.pdf_path).name}")
    print(f"Pages: {doc_figures.total_pages}")
    print(f"Figures found: {len(doc_figures.figures)}")
    print(f"Caption associations: {len(doc_figures.caption_associations)}")
    print(f"Cross-references: {len(doc_figures.cross_references)}")
    print()
    
    # Figure type distribution
    type_counts = defaultdict(int)
    for figure in doc_figures.figures:
        type_counts[figure.figure_type] += 1
    
    print("Figure Type Distribution:")
    for fig_type, count in sorted(type_counts.items()):
        print(f"  {fig_type.title()}: {count}")
    
    print(f"\nResults exported to: {args.output}")
    if args.image_dir and args.extract_images:
        print(f"Images saved to: {args.image_dir}")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()