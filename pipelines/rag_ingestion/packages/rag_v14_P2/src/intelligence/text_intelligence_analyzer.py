#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Text Intelligence Analyzer - Isolated Module
Analyzes text structure, layout patterns, and semantic organization in PDF documents
MODULAR DESIGN: Changes to this module cannot affect figure, equation, or table analysis
"""

import sys
import os
import re
from typing import Dict, List, Set, Tuple
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

class TextIntelligenceAnalyzer:
    """
    ISOLATED TEXT ANALYSIS MODULE
    
    Single Responsibility: Analyze text structure, layout patterns, and semantic organization for embedding optimization
    High Cohesion: All text-related intelligence analysis in one place
    Loose Coupling: No dependencies on figure, equation, or table analysis
    """
    
    def __init__(self):
        """Initialize the text intelligence analyzer"""
        self.text_profile = {
            "total_text_blocks": 0,
            "total_text_characters": 0,
            "reading_order_analysis": {},
            "content_hierarchy": {},
            "text_density_patterns": {},
            "font_intelligence": {},
            "semantic_segments": [],
            "embedding_strategy": {},
            "cross_page_continuity": {},
            "text_quality_metrics": {}
        }
    
    def analyze_text(self, doc: fitz.Document) -> Dict:
        """
        Main entry point: Analyze text structure and semantic organization in document
        
        Returns:
            dict: Complete text intelligence profile optimized for embeddings
        """
        print("📝 Analyzing Text Structure Intelligence...")
        
        # Reset profile for new analysis
        self._reset_profile()
        
        # Core text analysis phases
        text_blocks = self._extract_structured_text_blocks(doc)
        hierarchy = self._analyze_content_hierarchy(text_blocks)
        reading_order = self._analyze_reading_order_patterns(text_blocks)
        font_patterns = self._analyze_font_intelligence(text_blocks)
        
        # Advanced semantic analysis
        semantic_segments = self._identify_semantic_segments(text_blocks)
        continuity = self._analyze_cross_page_continuity(doc, text_blocks)
        quality_metrics = self._assess_text_quality(text_blocks)
        
        # Update profile with results
        self._update_profile(text_blocks, hierarchy, reading_order, font_patterns, 
                           semantic_segments, continuity, quality_metrics)
        
        # Generate embedding optimization strategy
        self._generate_embedding_strategy()
        
        # Display results
        self._display_text_analysis()
        
        return self.text_profile.copy()  # Return copy to prevent external modification
    
    def _reset_profile(self):
        """Reset profile for new analysis"""
        self.text_profile = {
            "total_text_blocks": 0,
            "total_text_characters": 0,
            "reading_order_analysis": {},
            "content_hierarchy": {},
            "text_density_patterns": {},
            "font_intelligence": {},
            "semantic_segments": [],
            "embedding_strategy": {},
            "cross_page_continuity": {},
            "text_quality_metrics": {}
        }
    
    def _extract_structured_text_blocks(self, doc: fitz.Document) -> List[Dict]:
        """
        Extract text blocks with structural and spatial metadata
        
        Returns:
            list: Text blocks with spatial, font, and content metadata
        """
        text_blocks = []
        
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            text_dict = page.get_text("dict")
            
            for block_idx, block in enumerate(text_dict["blocks"]):
                if "lines" not in block:
                    continue
                
                # Extract full text content from block
                block_text = ""
                fonts_used = []
                line_count = len(block["lines"])
                
                for line in block["lines"]:
                    for span in line["spans"]:
                        block_text += span["text"]
                        fonts_used.append({
                            "font": span["font"],
                            "size": span["size"],
                            "flags": span.get("flags", 0)
                        })
                
                if block_text.strip():  # Only non-empty blocks
                    text_block_data = {
                        "page": page_num + 1,
                        "block_id": f"{page_num+1}_{block_idx}",
                        "bbox": block["bbox"],
                        "text": block_text.strip(),
                        "char_count": len(block_text.strip()),
                        "line_count": line_count,
                        "fonts": fonts_used,
                        "spatial": {
                            "x": block["bbox"][0],
                            "y": block["bbox"][1],
                            "width": block["bbox"][2] - block["bbox"][0],
                            "height": block["bbox"][3] - block["bbox"][1],
                            "area": (block["bbox"][2] - block["bbox"][0]) * (block["bbox"][3] - block["bbox"][1])
                        }
                    }
                    
                    text_blocks.append(text_block_data)
        
        return text_blocks
    
    def _analyze_content_hierarchy(self, text_blocks: List[Dict]) -> Dict:
        """
        Analyze document content hierarchy based on font patterns and spatial layout
        
        Args:
            text_blocks: List of structured text blocks
            
        Returns:
            dict: Content hierarchy analysis
        """
        hierarchy = {
            "headers": [],
            "subheaders": [],
            "body_paragraphs": [],
            "captions": [],
            "references": []
        }
        
        # Analyze font sizes to identify hierarchy patterns
        font_sizes = [max(f["size"] for f in block["fonts"]) for block in text_blocks if block["fonts"]]
        if font_sizes:
            size_threshold_large = sorted(set(font_sizes), reverse=True)[0] if len(set(font_sizes)) > 0 else 12
            size_threshold_medium = sorted(set(font_sizes), reverse=True)[1] if len(set(font_sizes)) > 1 else 11
        else:
            size_threshold_large = 14
            size_threshold_medium = 12
        
        for block in text_blocks:
            if not block["fonts"]:
                continue
                
            max_font_size = max(f["size"] for f in block["fonts"])
            text = block["text"]
            
            # Classify based on patterns and font size
            if max_font_size >= size_threshold_large and len(text) < 100:
                hierarchy["headers"].append(block["block_id"])
            elif max_font_size >= size_threshold_medium and len(text) < 150:
                hierarchy["subheaders"].append(block["block_id"])
            elif any(pattern in text.lower() for pattern in ["fig.", "figure", "table"]):
                hierarchy["captions"].append(block["block_id"])
            elif any(pattern in text.lower() for pattern in ["references", "bibliography", "ref."]):
                hierarchy["references"].append(block["block_id"])
            else:
                hierarchy["body_paragraphs"].append(block["block_id"])
        
        return hierarchy
    
    def _analyze_reading_order_patterns(self, text_blocks: List[Dict]) -> Dict:
        """
        Analyze reading order patterns including multi-column layouts
        
        Args:
            text_blocks: List of structured text blocks
            
        Returns:
            dict: Reading order analysis
        """
        reading_order = {
            "layout_type": "unknown",
            "column_count": 1,
            "column_boundaries": [],
            "reading_flow": "top-to-bottom"
        }
        
        if not text_blocks:
            return reading_order
        
        # Group blocks by page for layout analysis
        pages = defaultdict(list)
        for block in text_blocks:
            pages[block["page"]].append(block)
        
        # Analyze layout patterns across pages
        column_counts = []
        for page_blocks in pages.values():
            if len(page_blocks) < 3:
                column_counts.append(1)
                continue
                
            # Sort by Y-position to find horizontal alignment groups
            sorted_blocks = sorted(page_blocks, key=lambda b: b["spatial"]["y"])
            
            # Detect column patterns by X-position clustering
            x_positions = [block["spatial"]["x"] for block in sorted_blocks]
            x_clusters = self._cluster_positions(x_positions, threshold=50)
            column_counts.append(len(x_clusters))
        
        # Determine dominant layout pattern
        if column_counts:
            dominant_columns = max(set(column_counts), key=column_counts.count)
            reading_order["column_count"] = dominant_columns
            reading_order["layout_type"] = "multi_column" if dominant_columns > 1 else "single_column"
        
        return reading_order
    
    def _cluster_positions(self, positions: List[float], threshold: float = 50) -> List[List[float]]:
        """
        Cluster positions within threshold distance
        
        Args:
            positions: List of positions to cluster
            threshold: Distance threshold for clustering
            
        Returns:
            list: List of position clusters
        """
        if not positions:
            return []
            
        sorted_positions = sorted(positions)
        clusters = [[sorted_positions[0]]]
        
        for pos in sorted_positions[1:]:
            if pos - clusters[-1][-1] <= threshold:
                clusters[-1].append(pos)
            else:
                clusters.append([pos])
        
        return clusters
    
    def _analyze_font_intelligence(self, text_blocks: List[Dict]) -> Dict:
        """
        Analyze font usage patterns for semantic understanding
        
        Args:
            text_blocks: List of structured text blocks
            
        Returns:
            dict: Font intelligence analysis
        """
        font_intelligence = {
            "font_families": Counter(),
            "size_distribution": Counter(),
            "emphasis_patterns": {},
            "consistency_score": 0.0
        }
        
        for block in text_blocks:
            for font_info in block["fonts"]:
                font_intelligence["font_families"][font_info["font"]] += 1
                font_intelligence["size_distribution"][font_info["size"]] += 1
                
                # Analyze emphasis (bold, italic)
                flags = font_info.get("flags", 0)
                if flags & 2**4:  # Bold
                    font_intelligence["emphasis_patterns"]["bold"] = \
                        font_intelligence["emphasis_patterns"].get("bold", 0) + 1
                if flags & 2**6:  # Italic
                    font_intelligence["emphasis_patterns"]["italic"] = \
                        font_intelligence["emphasis_patterns"].get("italic", 0) + 1
        
        # Calculate consistency score
        total_fonts = sum(font_intelligence["font_families"].values())
        if total_fonts > 0:
            dominant_font_usage = max(font_intelligence["font_families"].values())
            font_intelligence["consistency_score"] = dominant_font_usage / total_fonts
        
        return font_intelligence
    
    def _identify_semantic_segments(self, text_blocks: List[Dict]) -> List[Dict]:
        """
        Identify semantic segments for embedding optimization
        
        Args:
            text_blocks: List of structured text blocks
            
        Returns:
            list: Semantic segments with metadata
        """
        segments = []
        
        # Group consecutive blocks into logical segments
        current_segment = []
        current_page = None
        
        for block in text_blocks:
            # Start new segment on page breaks or significant spatial gaps
            if (current_page is not None and block["page"] != current_page) or \
               (current_segment and self._is_significant_gap(current_segment[-1], block)):
                if current_segment:
                    segments.append(self._create_segment(current_segment))
                current_segment = [block]
            else:
                current_segment.append(block)
            
            current_page = block["page"]
        
        # Add final segment
        if current_segment:
            segments.append(self._create_segment(current_segment))
        
        return segments
    
    def _is_significant_gap(self, block1: Dict, block2: Dict) -> bool:
        """
        Determine if there's a significant spatial gap between blocks
        
        Args:
            block1: First text block
            block2: Second text block
            
        Returns:
            bool: True if significant gap exists
        """
        if block1["page"] != block2["page"]:
            return True
            
        # Calculate vertical gap
        block1_bottom = block1["bbox"][3]
        block2_top = block2["bbox"][1]
        gap = block2_top - block1_bottom
        
        # Significant if gap > 2x average line height
        avg_line_height = block1["spatial"]["height"] / max(block1["line_count"], 1)
        return gap > (2 * avg_line_height)
    
    def _create_segment(self, blocks: List[Dict]) -> Dict:
        """
        Create semantic segment from blocks
        
        Args:
            blocks: List of text blocks to segment
            
        Returns:
            dict: Semantic segment metadata
        """
        full_text = " ".join(block["text"] for block in blocks)
        total_chars = sum(block["char_count"] for block in blocks)
        
        return {
            "segment_id": f"seg_{blocks[0]['page']}_{len(blocks)}",
            "pages": list(set(block["page"] for block in blocks)),
            "block_count": len(blocks),
            "text": full_text,
            "char_count": total_chars,
            "blocks": [block["block_id"] for block in blocks],
            "embedding_readiness": self._assess_embedding_readiness(full_text)
        }
    
    def _assess_embedding_readiness(self, text: str) -> Dict:
        """
        Assess text readiness for embedding processing
        
        Args:
            text: Text content to assess
            
        Returns:
            dict: Embedding readiness metrics
        """
        return {
            "word_count": len(text.split()),
            "sentence_count": len(re.split(r'[.!?]+', text)),
            "optimal_chunk_size": min(max(len(text), 100), 1000),  # 100-1000 chars optimal
            "complexity_score": len(set(text.split())) / max(len(text.split()), 1)  # Unique word ratio
        }
    
    def _analyze_cross_page_continuity(self, doc: fitz.Document, text_blocks: List[Dict]) -> Dict:
        """
        Analyze cross-page text continuity for embedding context preservation
        
        Args:
            doc: PDF document
            text_blocks: List of structured text blocks
            
        Returns:
            dict: Cross-page continuity analysis
        """
        continuity = {
            "page_breaks": [],
            "continuous_segments": 0,
            "context_preservation_needed": False
        }
        
        # Group blocks by page
        pages = defaultdict(list)
        for block in text_blocks:
            pages[block["page"]].append(block)
        
        # Analyze continuity between adjacent pages
        page_numbers = sorted(pages.keys())
        for i in range(len(page_numbers) - 1):
            current_page = page_numbers[i]
            next_page = page_numbers[i + 1]
            
            if current_page + 1 == next_page:  # Adjacent pages
                current_blocks = pages[current_page]
                next_blocks = pages[next_page]
                
                if current_blocks and next_blocks:
                    # Check if last block of current page continues to first block of next
                    last_block = max(current_blocks, key=lambda b: b["spatial"]["y"])
                    first_block = min(next_blocks, key=lambda b: b["spatial"]["y"])
                    
                    # Simple heuristic: if last block doesn't end with sentence terminator
                    if not re.search(r'[.!?]\s*$', last_block["text"].strip()):
                        continuity["page_breaks"].append({
                            "from_page": current_page,
                            "to_page": next_page,
                            "continuation_likely": True
                        })
                        continuity["context_preservation_needed"] = True
        
        return continuity
    
    def _assess_text_quality(self, text_blocks: List[Dict]) -> Dict:
        """
        Assess overall text quality for extraction confidence
        
        Args:
            text_blocks: List of structured text blocks
            
        Returns:
            dict: Text quality metrics
        """
        if not text_blocks:
            return {"overall_score": 0.0, "issues": ["no_text_found"]}
        
        quality_metrics = {
            "overall_score": 0.0,
            "character_recognition_score": 0.0,
            "layout_preservation_score": 0.0,
            "issues": []
        }
        
        # Calculate character recognition quality
        total_chars = sum(block["char_count"] for block in text_blocks)
        suspicious_chars = 0
        
        for block in text_blocks:
            # Count potentially mis-recognized characters
            suspicious_patterns = ['�', '□', '???', 'ﬁ', 'ﬂ']  # Common OCR artifacts
            for pattern in suspicious_patterns:
                suspicious_chars += block["text"].count(pattern)
        
        quality_metrics["character_recognition_score"] = max(0.0, 1.0 - (suspicious_chars / max(total_chars, 1)))
        
        # Calculate layout preservation (based on reading order coherence)
        sorted_blocks = sorted(text_blocks, key=lambda b: (b["page"], b["spatial"]["y"], b["spatial"]["x"]))
        layout_coherence = 0.8  # Assume good layout preservation for PDF text
        quality_metrics["layout_preservation_score"] = layout_coherence
        
        # Overall score
        quality_metrics["overall_score"] = (quality_metrics["character_recognition_score"] + 
                                          quality_metrics["layout_preservation_score"]) / 2
        
        # Identify issues
        if quality_metrics["character_recognition_score"] < 0.9:
            quality_metrics["issues"].append("potential_ocr_errors")
        if total_chars < 1000:
            quality_metrics["issues"].append("low_text_content")
        
        return quality_metrics
    
    def _update_profile(self, text_blocks: List[Dict], hierarchy: Dict, reading_order: Dict,
                       font_patterns: Dict, semantic_segments: List[Dict], 
                       continuity: Dict, quality_metrics: Dict):
        """Update text profile with analysis results"""
        
        self.text_profile["total_text_blocks"] = len(text_blocks)
        self.text_profile["total_text_characters"] = sum(block["char_count"] for block in text_blocks)
        self.text_profile["reading_order_analysis"] = reading_order
        self.text_profile["content_hierarchy"] = hierarchy
        self.text_profile["font_intelligence"] = font_patterns
        self.text_profile["semantic_segments"] = semantic_segments
        self.text_profile["cross_page_continuity"] = continuity
        self.text_profile["text_quality_metrics"] = quality_metrics
    
    def _generate_embedding_strategy(self):
        """Generate embedding optimization strategy based on text analysis"""
        
        strategy = {
            "chunking_method": "semantic_aware",
            "optimal_chunk_size": 500,  # Default
            "preserve_context": False,
            "hierarchical_processing": False,
            "preprocessing_needed": []
        }
        
        # Adjust strategy based on analysis
        avg_segment_size = (self.text_profile["total_text_characters"] / 
                          max(len(self.text_profile["semantic_segments"]), 1))
        
        if avg_segment_size > 1000:
            strategy["chunking_method"] = "sliding_window"
            strategy["optimal_chunk_size"] = 800
        elif avg_segment_size < 200:
            strategy["chunking_method"] = "paragraph_merge"
            strategy["optimal_chunk_size"] = 400
        
        # Context preservation for cross-page continuity
        if self.text_profile["cross_page_continuity"]["context_preservation_needed"]:
            strategy["preserve_context"] = True
            strategy["preprocessing_needed"].append("cross_page_linking")
        
        # Hierarchical processing for complex documents
        hierarchy = self.text_profile["content_hierarchy"]
        if len(hierarchy["headers"]) > 5 or len(hierarchy["subheaders"]) > 10:
            strategy["hierarchical_processing"] = True
            strategy["preprocessing_needed"].append("hierarchy_mapping")
        
        # Quality-based preprocessing
        quality = self.text_profile["text_quality_metrics"]
        if quality["overall_score"] < 0.8:
            strategy["preprocessing_needed"].append("quality_enhancement")
        
        self.text_profile["embedding_strategy"] = strategy
    
    def _display_text_analysis(self):
        """Display text analysis results"""
        total_blocks = self.text_profile["total_text_blocks"]
        total_chars = self.text_profile["total_text_characters"]
        segments = len(self.text_profile["semantic_segments"])
        quality_score = self.text_profile["text_quality_metrics"]["overall_score"]
        
        print(f"   📊 Found: {total_blocks} text blocks, {total_chars:,} characters")
        print(f"   🧩 Semantic segments: {segments}")
        print(f"   📏 Layout: {self.text_profile['reading_order_analysis']['layout_type']} "
              f"({self.text_profile['reading_order_analysis']['column_count']} columns)")
        print(f"   ⭐ Quality score: {quality_score:.2f}")
        print(f"   🎯 Embedding strategy: {self.text_profile['embedding_strategy']['chunking_method']}")

def test_text_analyzer():
    """Test the text intelligence analyzer independently"""
    print("🧪 Testing Text Intelligence Analyzer (Isolated)")
    print("=" * 55)
    
    pdf_path = "tests/test_data/Ch-04_Heat_Transfer.pdf"
    
    if not os.path.exists(pdf_path):
        print(f"❌ Test PDF not found: {pdf_path}")
        return
    
    try:
        # Test isolated text analyzer
        analyzer = TextIntelligenceAnalyzer()
        
        doc = fitz.open(pdf_path)
        text_profile = analyzer.analyze_text(doc)
        doc.close()
        
        print(f"\\n📊 ISOLATED TEXT ANALYSIS RESULTS:")
        print(f"   Total text blocks: {text_profile['total_text_blocks']}")
        print(f"   Total characters: {text_profile['total_text_characters']:,}")
        print(f"   Semantic segments: {len(text_profile['semantic_segments'])}")
        print(f"   Layout type: {text_profile['reading_order_analysis']['layout_type']}")
        print(f"   Column count: {text_profile['reading_order_analysis']['column_count']}")
        print(f"   Quality score: {text_profile['text_quality_metrics']['overall_score']:.2f}")
        print(f"   Embedding strategy: {text_profile['embedding_strategy']}")
        
        print(f"\\n✅ Text analyzer test completed successfully!")
        return text_profile
        
    except Exception as e:
        print(f"❌ Text analyzer test failed: {e}")
        import traceback
        traceback.print_exc()

def main():
    """Main function"""
    test_text_analyzer()

if __name__ == "__main__":
    main()