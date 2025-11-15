#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple, Dict, Any, Optional


BBox = Tuple[float, float, float, float]


@dataclass
class DoclingROIConfig:
    dpi: int = 200  # higher DPI to improve Docling table cell detection in ROI
    min_table_w: float = 120.0
    min_table_h: float = 80.0


class DoclingROIExtractor:
    def __init__(self, cfg: DoclingROIConfig | None = None) -> None:
        self.cfg = cfg or DoclingROIConfig()

    def extract_tables_in_roi(
        self,
        pdf_path: str,
        page_index: int,
        roi: BBox,
    ) -> List[Dict[str, Any]]:
        """Run Docling on a rasterized ROI PDF of a single page and return table bboxes in page coords.

        Returns list of { 'bbox': [x0,y0,x1,y1], 'source': 'docling_roi', 'confidence': float }
        """
        try:
            import fitz
            import tempfile
            from docling.document_converter import DocumentConverter
        except Exception:
            return []

        rx0, ry0, rx1, ry1 = map(float, roi)
        if rx1 <= rx0 + 2.0 or ry1 <= ry0 + 2.0:
            return []
        # Rasterize ROI
        src = fitz.open(pdf_path)
        try:
            page = src[page_index]
            scale = float(self.cfg.dpi) / 72.0
            clip = fitz.Rect(rx0, ry0, rx1, ry1)
            pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), clip=clip, alpha=False)
            if pix.width <= 0 or pix.height <= 0:
                return []
            # Build ROI PDF from the raster image
            tmp_png = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
            tmp_png.close()
            pix.save(tmp_png.name)
            roidoc = fitz.open()
            try:
                # Create page in pixels mapped to points 1:1 for simplicity
                pw, ph = float(pix.width), float(pix.height)
                p = roidoc.new_page(width=pw, height=ph)
                p.insert_image(p.rect, filename=tmp_png.name)
                tmp_pdf = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False)
                tmp_pdf.close()
                roidoc.save(tmp_pdf.name)
            finally:
                roidoc.close()
        finally:
            src.close()

        # Run Docling on ROI PDF
        tables_out: List[Dict[str, Any]] = []
        try:
            conv = DocumentConverter()
            res = conv.convert(tmp_pdf.name)
            d = getattr(res, 'document', None)
            tables = getattr(d, 'tables', []) if d is not None else []
            for t in tables or []:
                # Build bbox from table cells if available
                data = getattr(t, 'data', None)
                cells = getattr(data, 'table_cells', None) if data is not None else None
                xs0: List[float] = []
                ys0: List[float] = []
                xs1: List[float] = []
                ys1: List[float] = []
                if cells:
                    for c in cells:
                        bb = getattr(c, 'bbox', None)
                        if bb is None:
                            bb = getattr(c, 'box', None)
                        if bb is None:
                            bb = getattr(c, 'region', None)
                        if bb is None:
                            bb = getattr(c, 'region_bbox', None)
                        if bb is None:
                            continue
                        try:
                            x0, y0, x1, y1 = map(float, bb)
                        except Exception:
                            continue
                        xs0.append(x0); ys0.append(y0); xs1.append(x1); ys1.append(y1)
                if xs0 and ys0 and xs1 and ys1:
                    # Map from ROI PDF pixels back to page points: inverse of earlier mapping
                    # We built ROI PDF with 1:1 pixels->points relative to pixmap, so convert by scale
                    minx = min(xs0); miny = min(ys0); maxx = max(xs1); maxy = max(ys1)
                    # Convert to original page points from ROI coordinates
                    x0p = rx0 + (minx / scale)
                    y0p = ry0 + (miny / scale)
                    x1p = rx1 if (maxx/scale) >= (rx1 - rx0) else (rx0 + (maxx / scale))
                    y1p = ry1 if (maxy/scale) >= (ry1 - ry0) else (ry0 + (maxy / scale))
                    if (x1p - x0p) >= self.cfg.min_table_w and (y1p - y0p) >= self.cfg.min_table_h:
                        tables_out.append({
                            'bbox': [x0p, y0p, x1p, y1p],
                            'source': 'docling_roi',
                            'confidence': 0.7,
                        })
        except Exception:
            pass
        return tables_out
