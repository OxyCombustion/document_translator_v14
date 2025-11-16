"""
V9 Image Extraction Agent
Extracts images and diagrams from PDFs with spatial awareness
Associates images with tables and interprets technical diagrams
"""

import os
import time
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
import json

try:
    import fitz  # PyMuPDF
    import PIL.Image
    import numpy as np
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False
    fitz = None

from ..core.logger import get_logger

logger = get_logger("ImageExtractor")


@dataclass
class ImageElement:
    """Extracted image with metadata"""
    image_id: str
    page_number: int
    bbox: Tuple[float, float, float, float]  # x0, y0, x1, y1
    width: int
    height: int
    image_data: bytes
    image_format: str  # 'png', 'jpeg', etc.
    
    # Spatial context
    nearby_text: Optional[str] = None
    figure_caption: Optional[str] = None
    figure_number: Optional[str] = None
    
    # Technical classification
    diagram_type: Optional[str] = None  # 'heat_flow', 'electrical', 'mechanical'
    confidence: float = 0.0


@dataclass
class TableImageAssociation:
    """Association between table and its related images"""
    table_id: int
    table_title: str
    associated_images: List[ImageElement]
    spatial_relationship: str  # 'adjacent', 'embedded', 'nearby'
    confidence: float


class V8ImageExtractor:
    """
    V9 Image Extraction Agent
    Extracts images from PDFs with spatial awareness for table association
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.pymupdf_available = PYMUPDF_AVAILABLE
        
        logger.info("V9 Image Extractor initialized")
        logger.info(f"PyMuPDF: {'Available' if self.pymupdf_available else 'Not Available'}")
        
        if not self.pymupdf_available:
            logger.warning("PyMuPDF not available - install with: pip install PyMuPDF")
    
    def extract_all_images(self, pdf_path: str) -> List[ImageElement]:
        """Extract all images from PDF with spatial metadata"""
        if not self.pymupdf_available:
            logger.error("PyMuPDF required for image extraction")
            return []
        
        pdf_path = Path(pdf_path)
        logger.info(f"Extracting images from: {pdf_path.name}")
        
        try:
            doc = fitz.open(str(pdf_path))
            all_images = []
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                page_images = self._extract_page_images(page, page_num)
                all_images.extend(page_images)
            
            doc.close()
            
            logger.info(f"Extracted {len(all_images)} images from {len(doc)} pages")
            return all_images
            
        except Exception as e:
            logger.error(f"Error extracting images: {e}")
            return []
    
    def _extract_page_images(self, page, page_num: int) -> List[ImageElement]:
        """Extract images from a single page"""
        images = []
        
        try:
            # Get image list from page
            image_list = page.get_images()
            
            for img_index, img in enumerate(image_list):
                try:
                    # Get image metadata
                    xref = img[0]  # Image xref number
                    
                    # Get image rectangle (position on page)
                    image_rects = page.get_image_rects(xref)
                    
                    if not image_rects:
                        continue
                    
                    # Use first rectangle if multiple
                    rect = image_rects[0]
                    bbox = (rect.x0, rect.y0, rect.x1, rect.y1)
                    
                    # Extract image data
                    base_image = page.parent.extract_image(xref)
                    image_data = base_image["image"]
                    image_format = base_image["ext"]
                    
                    # Get image dimensions
                    width = base_image["width"]
                    height = base_image["height"]
                    
                    # Create image element
                    image_element = ImageElement(
                        image_id=f"page_{page_num+1}_img_{img_index+1}",
                        page_number=page_num + 1,
                        bbox=bbox,
                        width=width,
                        height=height,
                        image_data=image_data,
                        image_format=image_format
                    )
                    
                    # Extract nearby text for context
                    image_element.nearby_text = self._extract_nearby_text(page, rect)
                    
                    # Try to identify figure caption/number
                    self._identify_figure_info(image_element, page, rect)
                    
                    images.append(image_element)
                    
                except Exception as e:
                    logger.warning(f"Error extracting image {img_index} from page {page_num+1}: {e}")
                    continue
            
            logger.info(f"Page {page_num+1}: extracted {len(images)} images")
            
        except Exception as e:
            logger.error(f"Error processing page {page_num+1}: {e}")
        
        return images
    
    def _extract_nearby_text(self, page, image_rect, context_margin: float = 50) -> str:
        """Extract text near the image for context"""
        try:
            # Expand rectangle to include nearby text
            expanded_rect = fitz.Rect(
                image_rect.x0 - context_margin,
                image_rect.y0 - context_margin,
                image_rect.x1 + context_margin,
                image_rect.y1 + context_margin
            )
            
            # Extract text from expanded area
            text_dict = page.get_textbox(expanded_rect)
            return text_dict.strip() if text_dict else ""
            
        except Exception as e:
            logger.warning(f"Error extracting nearby text: {e}")
            return ""
    
    def _identify_figure_info(self, image_element: ImageElement, page, image_rect):
        """Try to identify figure number and caption"""
        try:
            # Look for "Figure X" or "Fig. X" patterns near the image
            nearby_text = image_element.nearby_text
            
            if nearby_text:
                import re
                
                # Look for figure patterns
                fig_patterns = [
                    r'Figure\s+(\d+)',
                    r'Fig\.\s+(\d+)',
                    r'FIGURE\s+(\d+)',
                    r'FIG\.\s+(\d+)'
                ]
                
                for pattern in fig_patterns:
                    match = re.search(pattern, nearby_text, re.IGNORECASE)
                    if match:
                        image_element.figure_number = match.group(1)
                        # Extract potential caption (text after figure number)
                        caption_start = match.end()
                        potential_caption = nearby_text[caption_start:caption_start+200].strip()
                        if potential_caption:
                            image_element.figure_caption = potential_caption
                        break
                        
        except Exception as e:
            logger.warning(f"Error identifying figure info: {e}")
    
    def associate_with_tables(self, images: List[ImageElement], tables_data: List[Dict]) -> List[TableImageAssociation]:
        """Associate images with tables based on spatial proximity"""
        associations = []
        
        logger.info(f"Associating {len(images)} images with {len(tables_data)} tables")
        
        for table_idx, table in enumerate(tables_data):
            table_id = table.get('table_number', table_idx + 1)
            table_title = table.get('title', f'Table {table_id}')
            
            # Find images that might be associated with this table
            # For now, use simple page-based association
            # TODO: Implement more sophisticated spatial analysis
            
            page_based_images = []
            
            # Look for images that mention this table number in nearby text
            for image in images:
                if image.nearby_text and f"Table {table_id}" in image.nearby_text:
                    page_based_images.append(image)
                elif image.nearby_text and table_title.lower() in image.nearby_text.lower():
                    page_based_images.append(image)
            
            if page_based_images:
                association = TableImageAssociation(
                    table_id=table_id,
                    table_title=table_title,
                    associated_images=page_based_images,
                    spatial_relationship="text_reference",
                    confidence=0.8
                )
                associations.append(association)
                
                logger.info(f"Table {table_id}: associated with {len(page_based_images)} images")
        
        return associations
    
    def save_extracted_images(self, images: List[ImageElement], output_dir: str = "extracted_images"):
        """Save extracted images to disk for inspection"""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        metadata = []
        
        for image in images:
            try:
                # Save image file
                filename = f"{image.image_id}.{image.image_format}"
                image_file = output_path / filename
                
                with open(image_file, 'wb') as f:
                    f.write(image.image_data)
                
                # Collect metadata
                metadata.append({
                    "image_id": image.image_id,
                    "filename": filename,
                    "page_number": image.page_number,
                    "bbox": image.bbox,
                    "dimensions": [image.width, image.height],
                    "figure_number": image.figure_number,
                    "figure_caption": image.figure_caption,
                    "nearby_text": image.nearby_text[:200] if image.nearby_text else None
                })
                
            except Exception as e:
                logger.error(f"Error saving image {image.image_id}: {e}")
        
        # Save metadata
        metadata_file = output_path / "image_metadata.json"
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2)
        
        logger.info(f"Saved {len(images)} images and metadata to: {output_path}")
        return output_path
    
    def get_capabilities(self) -> Dict[str, bool]:
        """Get extractor capabilities"""
        return {
            "image_extraction": self.pymupdf_available,
            "spatial_analysis": True,
            "figure_recognition": True,
            "table_association": True
        }


def main():
    """Test image extraction with Chapter 4"""
    extractor = V8ImageExtractor()
    
    # Test file
    test_file = Path("tests/test_data/Ch-04_Heat_Transfer.pdf")
    
    if not test_file.exists():
        print("❌ Test file not found!")
        print(f"Expected: {test_file}")
        return
    
    print(f"🖼️  Testing V9 image extraction with: {test_file.name}")
    print("=" * 60)
    
    # Extract images
    images = extractor.extract_all_images(str(test_file))
    
    if images:
        print(f"\n✅ Extracted {len(images)} images")
        
        # Save images for inspection
        output_dir = extractor.save_extracted_images(images)
        
        # Show summary
        print(f"\nIMAGE EXTRACTION SUMMARY:")
        print("-" * 30)
        for i, img in enumerate(images[:10]):  # Show first 10
            print(f"Image {i+1}: {img.image_id}")
            print(f"  - Page: {img.page_number}")
            print(f"  - Size: {img.width}x{img.height}")
            print(f"  - Format: {img.image_format}")
            if img.figure_number:
                print(f"  - Figure: {img.figure_number}")
            if img.figure_caption:
                print(f"  - Caption: {img.figure_caption[:50]}...")
            print()
        
        if len(images) > 10:
            print(f"... and {len(images) - 10} more images")
        
        print(f"\n💾 Images saved to: {output_dir}")
        print(f"📊 Target: 41 figures (V7 baseline)")
        print(f"🎯 V9 Result: {len(images)} images extracted")
        
        coverage = (len(images) / 41) * 100 if len(images) <= 41 else 100
        print(f"📈 Coverage: {coverage:.1f}% of V7 target")
        
    else:
        print("❌ No images extracted")
    
    print("=" * 60)


if __name__ == "__main__":
    main()