"""
Mathematica Document Structure Analyzer
Uses Mathematica's advanced document analysis to identify table zones vs text sections
Part of the Triple-Method Architecture for V9
"""

import json
import time
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import logging

# Import Mathematica integration
try:
    from wolframclient.evaluation import WolframLanguageSession
    from wolframclient.language import wl
    MATHEMATICA_AVAILABLE = True
except ImportError:
    MATHEMATICA_AVAILABLE = False
    wl = None

logger = logging.getLogger(__name__)


class MathematicaDocumentAnalyzer:
    """
    Mathematica-powered document structure analysis
    
    Provides high-level document overview to identify:
    - Table zones vs text sections
    - Page layouts and structure
    - Mathematical content regions
    - Figure and diagram areas
    """
    
    def __init__(self, kernel_path: str = None):
        self.session = None
        self.kernel_path = kernel_path
        self.is_available = MATHEMATICA_AVAILABLE
        
    def start_session(self) -> bool:
        """Initialize Mathematica session"""
        if not self.is_available:
            logger.warning("Mathematica not available - falling back to alternative analysis")
            return False
            
        try:
            if self.kernel_path:
                self.session = WolframLanguageSession(self.kernel_path)
            else:
                self.session = WolframLanguageSession()
                
            # Test session
            test_result = self.session.evaluate(wl.Plus(2, 2))
            if test_result != 4:
                raise ConnectionError("Mathematica session test failed")
                
            logger.info("Mathematica session started successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start Mathematica session: {e}")
            self.session = None
            return False
    
    def analyze_document_structure(self, pdf_path: str) -> Dict[str, Any]:
        """
        Get comprehensive document structure overview using Mathematica
        
        Args:
            pdf_path: Path to PDF document
            
        Returns:
            Dictionary with document structure analysis
        """
        if not self.session and not self.start_session():
            return self._fallback_analysis(pdf_path)
            
        try:
            # Mathematica code for comprehensive document analysis
            analysis_code = f'''
            Module[{{doc, pages, elements, tableZones, textZones, analysis}},
                
                (* Import document *)
                doc = Import["{pdf_path}"];
                
                (* Get document elements and structure *)
                elements = Import["{pdf_path}", "Elements"];
                pages = Import["{pdf_path}", "PageCount"];
                
                (* Get page images for layout analysis *)
                pageImages = Import["{pdf_path}", "ImageList"];
                
                (* Analyze each page structure *)
                pageAnalysis = Table[
                    Module[{{img, components, textRegions, tableRegions, bounds}},
                        img = pageImages[[page]];
                        
                        (* Find connected components *)
                        components = MorphologicalComponents[Binarize[img]];
                        
                        (* Identify text regions (smaller, scattered components) *)
                        textRegions = Select[
                            ComponentMeasurements[components, {{"Area", "BoundingBox", "Centroid"}}],
                            #[[2, 1]] < 10000 && AspectRatio[#[[2, 2]]] > 2 &
                        ];
                        
                        (* Identify table regions (larger, rectangular components) *)
                        tableRegions = Select[
                            ComponentMeasurements[components, {{"Area", "BoundingBox", "Centroid"}}],
                            #[[2, 1]] > 10000 && 0.5 < AspectRatio[#[[2, 2]]] < 3 &
                        ];
                        
                        (* Get bounding boxes *)
                        textBounds = textRegions[[All, 2, 2]];
                        tableBounds = tableRegions[[All, 2, 2]];
                        
                        Association[
                            "page" -> page,
                            "text_regions" -> Length[textRegions],
                            "table_regions" -> Length[tableRegions],
                            "text_bounds" -> textBounds,
                            "table_bounds" -> tableBounds,
                            "layout_density" -> Length[components]/Apply[Times, ImageDimensions[img]]
                        ]
                    ],
                    {{page, 1, pages}}
                ];
                
                (* Overall document analysis *)
                totalTextRegions = Total[pageAnalysis[[All, "text_regions"]]];
                totalTableRegions = Total[pageAnalysis[[All, "table_regions"]]];
                avgDensity = Mean[pageAnalysis[[All, "layout_density"]]];
                
                (* Classify document type *)
                documentType = Which[
                    totalTableRegions > totalTextRegions/2, "table_heavy",
                    totalTableRegions > 10, "mixed_content", 
                    totalTableRegions > 0, "text_with_tables",
                    True, "text_only"
                ];
                
                (* Export results *)
                Association[
                    "total_pages" -> pages,
                    "document_type" -> documentType,
                    "total_text_regions" -> totalTextRegions,
                    "total_table_regions" -> totalTableRegions,
                    "average_layout_density" -> avgDensity,
                    "page_analysis" -> pageAnalysis,
                    "elements_available" -> elements
                ]
            ]
            '''
            
            # Execute analysis
            result = self.session.evaluate(analysis_code)
            
            if result:
                # Convert Mathematica result to Python format
                return self._process_mathematica_result(result)
            else:
                logger.warning("Mathematica analysis returned no result")
                return self._fallback_analysis(pdf_path)
                
        except Exception as e:
            logger.error(f"Mathematica document analysis failed: {e}")
            return self._fallback_analysis(pdf_path)
    
    def identify_table_zones(self, pdf_path: str, page_num: int = None) -> List[Dict[str, Any]]:
        """
        Identify specific table zones on a page or entire document
        
        Args:
            pdf_path: Path to PDF document
            page_num: Specific page number (None for all pages)
            
        Returns:
            List of table zone descriptions with coordinates
        """
        if not self.session and not self.start_session():
            return []
            
        try:
            page_filter = f", {{{page_num}}}" if page_num else ""
            
            zone_analysis_code = f'''
            Module[{{doc, pageImages, tableZones}},
                
                (* Import specific page(s) *)
                pageImages = Import["{pdf_path}", "ImageList"{page_filter}];
                
                tableZones = Map[
                    Module[{{img, binary, components, candidates, tableRegions}},
                        img = #;
                        
                        (* Preprocessing for table detection *)
                        binary = Binarize[img, Method -> "Otsu"];
                        components = MorphologicalComponents[binary];
                        
                        (* Find rectangular components that could be tables *)
                        candidates = ComponentMeasurements[components, 
                            {{"Area", "BoundingBox", "Centroid", "EquivalentDiskRadius"}}
                        ];
                        
                        (* Filter for table-like regions *)
                        tableRegions = Select[candidates,
                            Module[{{area, bbox, ratio}},
                                area = #[[2, 1]];
                                bbox = #[[2, 2]];
                                ratio = (bbox[[2, 1]] - bbox[[1, 1]])/(bbox[[2, 2]] - bbox[[1, 2]]);
                                
                                (* Table criteria: reasonable size, aspect ratio *)
                                area > 5000 && 0.3 < ratio < 4.0
                            ] &
                        ];
                        
                        (* Format results *)
                        Map[
                            Association[
                                "bbox" -> #[[2, 2]],
                                "area" -> #[[2, 1]],
                                "centroid" -> #[[2, 3]],
                                "confidence" -> Min[1.0, #[[2, 1]]/50000]
                            ] &,
                            tableRegions
                        ]
                    ] &,
                    If[ListQ[pageImages], pageImages, {{pageImages}}]
                ];
                
                Flatten[tableZones, 1]
            ]
            '''
            
            zones = self.session.evaluate(zone_analysis_code)
            return self._format_zone_results(zones) if zones else []
            
        except Exception as e:
            logger.error(f"Table zone identification failed: {e}")
            return []
    
    def _process_mathematica_result(self, result) -> Dict[str, Any]:
        """Convert Mathematica Association to Python dict"""
        try:
            # Handle Mathematica Association format
            if hasattr(result, 'keys') and hasattr(result, 'values'):
                processed = {}
                for key in result.keys():
                    value = result[key]
                    # Convert Mathematica types to Python types
                    if hasattr(value, 'keys'):  # Nested Association
                        processed[str(key)] = self._process_mathematica_result(value)
                    elif isinstance(value, (list, tuple)):
                        processed[str(key)] = [self._convert_value(v) for v in value]
                    else:
                        processed[str(key)] = self._convert_value(value)
                return processed
            else:
                return self._convert_value(result)
                
        except Exception as e:
            logger.error(f"Failed to process Mathematica result: {e}")
            return {"error": str(e), "raw_result": str(result)}
    
    def _convert_value(self, value):
        """Convert individual Mathematica values to Python"""
        if hasattr(value, 'keys'):
            return self._process_mathematica_result(value)
        elif isinstance(value, (int, float, str, bool)):
            return value
        else:
            return str(value)
    
    def _format_zone_results(self, zones) -> List[Dict[str, Any]]:
        """Format zone detection results"""
        formatted = []
        for i, zone in enumerate(zones):
            if hasattr(zone, 'keys'):
                formatted.append({
                    "zone_id": i,
                    "bbox": self._convert_value(zone.get("bbox", [])),
                    "area": self._convert_value(zone.get("area", 0)),
                    "centroid": self._convert_value(zone.get("centroid", [])),
                    "confidence": self._convert_value(zone.get("confidence", 0.5)),
                    "method": "mathematica"
                })
        return formatted
    
    def _fallback_analysis(self, pdf_path: str) -> Dict[str, Any]:
        """Fallback analysis when Mathematica is not available"""
        logger.info("Using fallback analysis (PyMuPDF-based)")
        
        try:
            import fitz  # PyMuPDF
            
            doc = fitz.open(pdf_path)
            page_count = len(doc)
            
            text_regions = 0
            table_regions = 0
            
            for page_num in range(page_count):
                page = doc[page_num]
                
                # Get text blocks
                blocks = page.get_text("dict")["blocks"]
                
                for block in blocks:
                    if "lines" in block:  # Text block
                        text_regions += 1
                    elif block.get("type") == 1:  # Image block (potential table)
                        table_regions += 1
            
            doc.close()
            
            # Simple classification
            if table_regions > text_regions / 2:
                doc_type = "table_heavy"
            elif table_regions > 5:
                doc_type = "mixed_content"
            elif table_regions > 0:
                doc_type = "text_with_tables"
            else:
                doc_type = "text_only"
            
            return {
                "total_pages": page_count,
                "document_type": doc_type,
                "total_text_regions": text_regions,
                "total_table_regions": table_regions,
                "method": "fallback_pymupdf",
                "mathematica_available": False
            }
            
        except Exception as e:
            logger.error(f"Fallback analysis failed: {e}")
            return {
                "error": str(e),
                "method": "failed_fallback",
                "mathematica_available": False
            }
    
    def close_session(self):
        """Clean up Mathematica session"""
        if self.session:
            try:
                self.session.terminate()
                logger.info("Mathematica session closed")
            except Exception as e:
                logger.error(f"Error closing Mathematica session: {e}")
            finally:
                self.session = None


def main():
    """Test the Mathematica document analyzer"""
    import sys
    import io
    
    # Set UTF-8 encoding for Windows
    if sys.platform == 'win32':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
    
    analyzer = MathematicaDocumentAnalyzer()
    
    # Test with Chapter 4 PDF
    pdf_path = "tests/test_data/Ch-04_Heat_Transfer.pdf"
    
    print("🔬 Testing Mathematica Document Structure Analysis")
    print("=" * 60)
    
    # Get document overview
    start_time = time.time()
    structure = analyzer.analyze_document_structure(pdf_path)
    analysis_time = time.time() - start_time
    
    print(f"Analysis completed in {analysis_time:.2f}s")
    print(f"Document Type: {structure.get('document_type', 'unknown')}")
    print(f"Total Pages: {structure.get('total_pages', 0)}")
    print(f"Text Regions: {structure.get('total_text_regions', 0)}")
    print(f"Table Regions: {structure.get('total_table_regions', 0)}")
    print(f"Method Used: {structure.get('method', 'mathematica')}")
    
    # Test table zone identification
    print("\n🎯 Identifying Table Zones...")
    zones = analyzer.identify_table_zones(pdf_path)
    print(f"Found {len(zones)} potential table zones")
    
    for i, zone in enumerate(zones[:3]):  # Show first 3 zones
        print(f"  Zone {i+1}: Area={zone.get('area', 0):.0f}, Confidence={zone.get('confidence', 0):.2f}")
    
    # Save results
    results = {
        "structure_analysis": structure,
        "table_zones": zones,
        "analysis_time": analysis_time,
        "timestamp": time.time()
    }
    
    output_path = "results/Ch-04_Heat_Transfer_mathematica_structure.json"
    Path(output_path).parent.mkdir(exist_ok=True)
    
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n💾 Results saved to: {output_path}")
    
    analyzer.close_session()


if __name__ == "__main__":
    main()