"""
Intelligent Document Chunker for V9
Logical chunking on page boundaries while detecting content that spans pages
"""

import logging
from typing import Dict, List, Any, Optional, Tuple, Iterator
from dataclasses import dataclass, field
from enum import Enum
import re
from pathlib import Path
import numpy as np
from collections import defaultdict

from .logger import setup_logger
from .document_types import DocumentChunk, ChunkType

logger = setup_logger(__name__)


@dataclass
class ContentElement:
    """Represents a content element within a document"""
    element_id: str
    element_type: str  # 'text', 'table', 'figure', 'header', 'footer'
    page_number: int
    bbox: Dict[str, float]  # x, y, width, height
    content: Any
    confidence: float = 1.0
    references: List[str] = field(default_factory=list)  # References to other elements
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SpanningContent:
    """Content that spans multiple pages"""
    content_id: str
    content_type: str
    start_page: int
    end_page: int
    elements: List[ContentElement]
    is_complete: bool = False


class LogicalChunker:
    """Intelligently chunks documents on logical boundaries"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.min_chunk_size = config.get('min_chunk_size_mb', 0.5) * 1024 * 1024
        self.max_chunk_size = config.get('max_chunk_size_mb', 10) * 1024 * 1024
        self.preserve_tables = config.get('preserve_tables', True)
        self.preserve_figures = config.get('preserve_figures', True)
        
        # Patterns for detecting content types
        self._compile_patterns()
    
    def _compile_patterns(self):
        """Compile regex patterns for content detection"""
        self.patterns = {
            'table_reference': re.compile(r'Table\s+(\d+(?:\.\d+)?)', re.IGNORECASE),
            'figure_reference': re.compile(r'Figure\s+(\d+(?:\.\d+)?)', re.IGNORECASE),
            'equation_reference': re.compile(r'Equation\s+(\d+(?:\.\d+)?)', re.IGNORECASE),
            'section_header': re.compile(r'^(\d+(?:\.\d+)*)\s+[A-Z]', re.MULTILINE),
            'page_header': re.compile(r'^.{1,100}$', re.MULTILINE),  # Short lines at top
            'page_footer': re.compile(r'^\s*\d+\s*$', re.MULTILINE),  # Page numbers
            'table_continuation': re.compile(r'(continued|cont\.)', re.IGNORECASE),
            'figure_caption': re.compile(r'^(Figure|Fig\.)\s+\d+', re.IGNORECASE | re.MULTILINE)
        }
    
    def chunk_document_intelligently(self, document_path: str) -> Iterator[DocumentChunk]:
        """
        Chunk document using intelligent logical boundaries
        
        Args:
            document_path: Path to document file
            
        Yields:
            DocumentChunk: Logically organized chunks
        """
        file_ext = Path(document_path).suffix.lower()
        
        if file_ext == '.pdf':
            yield from self._chunk_pdf_intelligently(document_path)
        else:
            # Fallback to simple chunking for other formats
            yield from self._chunk_generic(document_path)
    
    def _chunk_pdf_intelligently(self, pdf_path: str) -> Iterator[DocumentChunk]:
        """Intelligent PDF chunking with logical boundaries"""
        try:
            import fitz  # PyMuPDF
            doc = fitz.open(pdf_path)
            
            logger.info(f"Analyzing PDF structure: {Path(pdf_path).name} ({len(doc)} pages)")
            
            # Phase 1: Extract all content elements
            all_elements = self._extract_all_elements(doc, pdf_path)
            
            # Phase 2: Detect spanning content (tables, figures across pages)
            spanning_content = self._detect_spanning_content(all_elements)
            
            # Phase 3: Group elements into logical chunks
            logical_chunks = self._create_logical_chunks(all_elements, spanning_content)
            
            # Phase 4: Generate document chunks
            for chunk_data in logical_chunks:
                yield self._create_document_chunk(chunk_data, pdf_path)
            
            doc.close()
            
        except ImportError:
            logger.error("PyMuPDF not available - falling back to simple chunking")
            yield from self._chunk_generic(pdf_path)
        except Exception as e:
            logger.error(f"Error in intelligent PDF chunking: {e}")
            yield from self._chunk_generic(pdf_path)
    
    def _extract_all_elements(self, doc, pdf_path: str) -> List[ContentElement]:
        """Extract all content elements from PDF"""
        elements = []
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            
            # Extract text blocks with positioning
            text_dict = page.get_text("dict")
            
            for block_idx, block in enumerate(text_dict.get("blocks", [])):
                if "lines" not in block:
                    continue
                
                bbox = block["bbox"]
                text_content = ""
                
                for line in block["lines"]:
                    for span in line["spans"]:
                        text_content += span["text"] + " "
                
                text_content = text_content.strip()
                if not text_content:
                    continue
                
                # Classify content type
                content_type = self._classify_text_content(text_content, bbox, page)
                
                element = ContentElement(
                    element_id=f"page_{page_num}_block_{block_idx}",
                    element_type=content_type,
                    page_number=page_num,
                    bbox={
                        "x": bbox[0], "y": bbox[1], 
                        "width": bbox[2] - bbox[0], "height": bbox[3] - bbox[1]
                    },
                    content=text_content,
                    metadata={
                        "source_file": pdf_path,
                        "font_info": self._extract_font_info(block)
                    }
                )
                
                # Extract references
                element.references = self._extract_references(text_content)
                
                elements.append(element)
            
            # Extract images/figures
            image_list = page.get_images()
            for img_idx, img in enumerate(image_list):
                try:
                    # Get image position
                    img_bbox = page.get_image_bbox(img)
                    
                    element = ContentElement(
                        element_id=f"page_{page_num}_img_{img_idx}",
                        element_type="figure",
                        page_number=page_num,
                        bbox={
                            "x": img_bbox.x0, "y": img_bbox.y0,
                            "width": img_bbox.width, "height": img_bbox.height
                        },
                        content=img,  # Store image reference
                        metadata={"source_file": pdf_path, "image_index": img_idx}
                    )
                    
                    elements.append(element)
                    
                except Exception as e:
                    logger.warning(f"Could not extract image {img_idx} from page {page_num}: {e}")
            
            # Detect tables using heuristics
            tables = self._detect_tables_on_page(page, page_num)
            elements.extend(tables)
        
        logger.info(f"Extracted {len(elements)} content elements")
        return elements
    
    def _classify_text_content(self, text: str, bbox: Tuple, page) -> str:
        """Classify text content type"""
        # Check position for headers/footers
        page_rect = page.rect
        y_pos = bbox[1]
        
        # Header detection (top 10% of page)
        if y_pos < page_rect.height * 0.1:
            return "header"
        
        # Footer detection (bottom 10% of page)
        if y_pos > page_rect.height * 0.9:
            return "footer"
        
        # Caption detection
        if self.patterns['figure_caption'].match(text):
            return "caption"
        
        # Section header detection
        if self.patterns['section_header'].match(text):
            return "section_header"
        
        # Default to body text
        return "text"
    
    def _extract_font_info(self, block: Dict) -> Dict[str, Any]:
        """Extract font information from text block"""
        fonts = set()
        sizes = set()
        
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                fonts.add(span.get("font", ""))
                sizes.add(span.get("size", 0))
        
        return {
            "fonts": list(fonts),
            "sizes": list(sizes),
            "is_bold": any("bold" in font.lower() for font in fonts),
            "is_italic": any("italic" in font.lower() for font in fonts)
        }
    
    def _extract_references(self, text: str) -> List[str]:
        """Extract references to tables, figures, equations"""
        references = []
        
        # Table references
        for match in self.patterns['table_reference'].finditer(text):
            references.append(f"table_{match.group(1)}")
        
        # Figure references
        for match in self.patterns['figure_reference'].finditer(text):
            references.append(f"figure_{match.group(1)}")
        
        # Equation references
        for match in self.patterns['equation_reference'].finditer(text):
            references.append(f"equation_{match.group(1)}")
        
        return references
    
    def _detect_tables_on_page(self, page, page_num: int) -> List[ContentElement]:
        """Detect tables on a page using layout analysis"""
        tables = []
        
        try:
            # Simple table detection using text positioning
            text_dict = page.get_text("dict")
            
            # Group text by vertical position (rows)
            rows = defaultdict(list)
            
            for block in text_dict.get("blocks", []):
                if "lines" not in block:
                    continue
                
                bbox = block["bbox"]
                y_center = (bbox[1] + bbox[3]) / 2
                
                # Round y-position to group into rows
                row_key = round(y_center / 5) * 5  # 5-point grid
                
                rows[row_key].append({
                    "text": " ".join(span["text"] for line in block["lines"] for span in line["spans"]),
                    "bbox": bbox
                })
            
            # Look for table patterns (multiple aligned columns)
            potential_tables = []
            for row_y, row_blocks in rows.items():
                if len(row_blocks) >= 3:  # At least 3 columns
                    # Check if blocks are roughly aligned vertically
                    x_positions = [block["bbox"][0] for block in row_blocks]
                    if self._is_tabular_layout(x_positions):
                        potential_tables.append((row_y, row_blocks))
            
            # Group consecutive table rows
            if potential_tables:
                table_groups = self._group_consecutive_table_rows(potential_tables)
                
                for group_idx, table_group in enumerate(table_groups):
                    if len(table_group) >= 2:  # At least 2 rows for a table
                        table_bbox = self._calculate_table_bbox(table_group)
                        
                        table_element = ContentElement(
                            element_id=f"page_{page_num}_table_{group_idx}",
                            element_type="table",
                            page_number=page_num,
                            bbox=table_bbox,
                            content=table_group,
                            metadata={
                                "row_count": len(table_group),
                                "col_count": max(len(row[1]) for row in table_group)
                            }
                        )
                        
                        tables.append(table_element)
        
        except Exception as e:
            logger.warning(f"Error detecting tables on page {page_num}: {e}")
        
        return tables
    
    def _is_tabular_layout(self, x_positions: List[float]) -> bool:
        """Check if x-positions suggest tabular layout"""
        if len(x_positions) < 3:
            return False
        
        # Sort positions
        sorted_x = sorted(x_positions)
        
        # Check for regular spacing
        gaps = [sorted_x[i+1] - sorted_x[i] for i in range(len(sorted_x)-1)]
        
        # If gaps are roughly similar, it's likely tabular
        mean_gap = np.mean(gaps)
        gap_variance = np.var(gaps)
        
        return gap_variance < (mean_gap * 0.5) ** 2  # Low variance in gaps
    
    def _group_consecutive_table_rows(self, potential_tables: List) -> List[List]:
        """Group consecutive table rows"""
        if not potential_tables:
            return []
        
        # Sort by y-position
        sorted_tables = sorted(potential_tables, key=lambda x: x[0])
        
        groups = []
        current_group = [sorted_tables[0]]
        
        for i in range(1, len(sorted_tables)):
            prev_y = sorted_tables[i-1][0]
            curr_y = sorted_tables[i][0]
            
            # If rows are close together (within ~20 points), group them
            if curr_y - prev_y < 20:
                current_group.append(sorted_tables[i])
            else:
                if len(current_group) >= 2:
                    groups.append(current_group)
                current_group = [sorted_tables[i]]
        
        if len(current_group) >= 2:
            groups.append(current_group)
        
        return groups
    
    def _calculate_table_bbox(self, table_group: List) -> Dict[str, float]:
        """Calculate bounding box for entire table"""
        all_bboxes = []
        
        for row_y, row_blocks in table_group:
            for block in row_blocks:
                all_bboxes.append(block["bbox"])
        
        if not all_bboxes:
            return {"x": 0, "y": 0, "width": 0, "height": 0}
        
        min_x = min(bbox[0] for bbox in all_bboxes)
        min_y = min(bbox[1] for bbox in all_bboxes)
        max_x = max(bbox[2] for bbox in all_bboxes)
        max_y = max(bbox[3] for bbox in all_bboxes)
        
        return {
            "x": min_x,
            "y": min_y,
            "width": max_x - min_x,
            "height": max_y - min_y
        }
    
    def _detect_spanning_content(self, elements: List[ContentElement]) -> List[SpanningContent]:
        """Detect content that spans multiple pages"""
        spanning_items = []
        
        # Group elements by type
        by_type = defaultdict(list)
        for element in elements:
            by_type[element.element_type].append(element)
        
        # Check for spanning tables
        spanning_items.extend(self._detect_spanning_tables(by_type.get("table", [])))
        
        # Check for spanning figures
        spanning_items.extend(self._detect_spanning_figures(by_type.get("figure", [])))
        
        logger.info(f"Detected {len(spanning_items)} spanning content items")
        return spanning_items
    
    def _detect_spanning_tables(self, table_elements: List[ContentElement]) -> List[SpanningContent]:
        """Detect tables that span multiple pages"""
        spanning_tables = []
        
        # Look for tables on consecutive pages with similar characteristics
        by_page = defaultdict(list)
        for table in table_elements:
            by_page[table.page_number].append(table)
        
        # Check for continuation patterns
        for page_num in sorted(by_page.keys()):
            if page_num + 1 in by_page:
                current_tables = by_page[page_num]
                next_tables = by_page[page_num + 1]
                
                for curr_table in current_tables:
                    for next_table in next_tables:
                        # Check if tables are likely continuations
                        if self._are_tables_connected(curr_table, next_table):
                            spanning_table = SpanningContent(
                                content_id=f"spanning_table_{curr_table.element_id}",
                                content_type="table",
                                start_page=page_num,
                                end_page=page_num + 1,
                                elements=[curr_table, next_table]
                            )
                            spanning_tables.append(spanning_table)
        
        return spanning_tables
    
    def _are_tables_connected(self, table1: ContentElement, table2: ContentElement) -> bool:
        """Check if two tables are likely parts of the same spanning table"""
        # Check column alignment
        bbox1 = table1.bbox
        bbox2 = table2.bbox
        
        # Similar x-position and width suggests same table
        x_diff = abs(bbox1["x"] - bbox2["x"])
        width_diff = abs(bbox1["width"] - bbox2["width"])
        
        # Allow some tolerance
        return x_diff < 20 and width_diff < 50
    
    def _detect_spanning_figures(self, figure_elements: List[ContentElement]) -> List[SpanningContent]:
        """Detect figures that span multiple pages"""
        # Most figures don't span pages, but could check for related figures
        # or figure parts across pages
        return []  # Simplified for now
    
    def _create_logical_chunks(self, elements: List[ContentElement], 
                             spanning_content: List[SpanningContent]) -> List[Dict[str, Any]]:
        """Create logical chunks from elements"""
        chunks = []
        
        # Group elements by page first
        by_page = defaultdict(list)
        for element in elements:
            by_page[element.page_number].append(element)
        
        # Handle spanning content first
        spanning_element_ids = set()
        for spanning in spanning_content:
            chunk_data = {
                "chunk_type": "spanning_" + spanning.content_type,
                "pages": list(range(spanning.start_page, spanning.end_page + 1)),
                "elements": spanning.elements,
                "primary_content": spanning.content_type
            }
            chunks.append(chunk_data)
            
            # Mark elements as part of spanning content
            for elem in spanning.elements:
                spanning_element_ids.add(elem.element_id)
        
        # Create page-based chunks for remaining elements
        for page_num in sorted(by_page.keys()):
            page_elements = [e for e in by_page[page_num] 
                           if e.element_id not in spanning_element_ids]
            
            if not page_elements:
                continue
            
            # Group elements by content type within page
            page_chunks = self._group_page_elements(page_elements, page_num)
            chunks.extend(page_chunks)
        
        logger.info(f"Created {len(chunks)} logical chunks")
        return chunks
    
    def _group_page_elements(self, elements: List[ContentElement], page_num: int) -> List[Dict[str, Any]]:
        """Group elements within a page into logical chunks"""
        chunks = []
        
        # Filter out headers and footers for main content
        main_elements = [e for e in elements if e.element_type not in ["header", "footer"]]
        headers_footers = [e for e in elements if e.element_type in ["header", "footer"]]
        
        # Group by content type and proximity
        by_type = defaultdict(list)
        for element in main_elements:
            by_type[element.element_type].append(element)
        
        # Create chunks for each content type
        for content_type, type_elements in by_type.items():
            if content_type in ["table", "figure"]:
                # Keep tables and figures as separate chunks
                for element in type_elements:
                    chunks.append({
                        "chunk_type": content_type,
                        "pages": [page_num],
                        "elements": [element],
                        "primary_content": content_type
                    })
            else:
                # Group text elements together
                if type_elements:
                    chunks.append({
                        "chunk_type": "page_content",
                        "pages": [page_num],
                        "elements": type_elements + headers_footers,  # Include headers/footers with text
                        "primary_content": "text"
                    })
        
        return chunks
    
    def _create_document_chunk(self, chunk_data: Dict[str, Any], source_file: str) -> DocumentChunk:
        """Create DocumentChunk from logical chunk data"""
        pages = chunk_data["pages"]
        elements = chunk_data["elements"]
        
        # Create chunk ID
        if len(pages) == 1:
            chunk_id = f"{Path(source_file).stem}_page_{pages[0]}_{chunk_data['chunk_type']}"
        else:
            chunk_id = f"{Path(source_file).stem}_pages_{pages[0]}-{pages[-1]}_{chunk_data['chunk_type']}"
        
        # Determine chunk type
        if chunk_data["primary_content"] == "table":
            chunk_type = ChunkType.TABLE
        elif chunk_data["primary_content"] == "figure":
            chunk_type = ChunkType.IMAGE
        else:
            chunk_type = ChunkType.PAGE
        
        # Combine content from all elements
        combined_content = self._combine_element_content(elements)
        
        # Calculate overall bounding box
        overall_bbox = self._calculate_overall_bbox(elements)
        
        # Create metadata
        metadata = {
            "source_file": source_file,
            "pages": pages,
            "element_count": len(elements),
            "content_types": list(set(e.element_type for e in elements)),
            "is_spanning": len(pages) > 1
        }
        
        return DocumentChunk(
            chunk_id=chunk_id,
            chunk_type=chunk_type,
            page_number=pages[0],  # Primary page
            bbox=overall_bbox,
            content=combined_content,
            metadata=metadata
        )
    
    def _combine_element_content(self, elements: List[ContentElement]) -> Any:
        """Combine content from multiple elements"""
        if len(elements) == 1:
            return elements[0].content
        
        # For multiple elements, create a structured combination
        combined = {
            "type": "multi_element",
            "elements": []
        }
        
        for element in elements:
            combined["elements"].append({
                "type": element.element_type,
                "content": element.content,
                "bbox": element.bbox,
                "page": element.page_number
            })
        
        return combined
    
    def _calculate_overall_bbox(self, elements: List[ContentElement]) -> Dict[str, float]:
        """Calculate overall bounding box for multiple elements"""
        if not elements:
            return {"x": 0, "y": 0, "width": 0, "height": 0}
        
        if len(elements) == 1:
            return elements[0].bbox
        
        # Calculate union of all bounding boxes
        min_x = min(e.bbox["x"] for e in elements)
        min_y = min(e.bbox["y"] for e in elements)
        max_x = max(e.bbox["x"] + e.bbox["width"] for e in elements)
        max_y = max(e.bbox["y"] + e.bbox["height"] for e in elements)
        
        return {
            "x": min_x,
            "y": min_y,
            "width": max_x - min_x,
            "height": max_y - min_y
        }
    
    def _chunk_generic(self, file_path: str) -> Iterator[DocumentChunk]:
        """Fallback generic chunking"""
        with open(file_path, 'rb') as f:
            content = f.read()
        
        chunk = DocumentChunk(
            chunk_id=f"{Path(file_path).stem}_full",
            chunk_type=ChunkType.SECTION,
            page_number=0,
            content=content,
            metadata={"source_file": file_path, "chunking_method": "generic"}
        )
        yield chunk