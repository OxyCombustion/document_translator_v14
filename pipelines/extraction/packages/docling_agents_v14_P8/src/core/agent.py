#!/usr/bin/env python3
"""
DoclingAgent

Single-responsibility helper for interacting with Docling locally.

Capabilities
- Convert a PDF once per process run (caching by absolute path)
- Provide per-page tables and pictures with PyMuPDF-style coordinates
- Emit sidecar JSON with raw Docling provenance for auditing
- Expose Docling version and format options in use

Notes
- Docling coordinates (prov[0].bbox) are bottom-left origin with fields l,t,r,b
- PyMuPDF uses top-left origin (0,0 at top-left). We flip Y via page height.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any

import fitz  # PyMuPDF
from src.infra.agent_logger import AgentLogger, AgentRunRecord
import time


@dataclass
class DoclingConfig:
    do_ocr: bool = True
    do_table_structure: bool = True


class DoclingAgent:
    def __init__(self, config: Optional[DoclingConfig] = None) -> None:
        self.config = config or DoclingConfig()
        self._doc_cache: Dict[Path, Any] = {}
        self._failed: Dict[Path, str] = {}
        self._version: Optional[str] = None
        self._timing: Dict[str, Optional[float]] = {"import_ms": None, "init_ms": None, "convert_ms": None, "cached": False}
        # Lazy import to keep caller lightweight if Docling not installed
        try:
            t0 = time.time()
            from docling.document_converter import DocumentConverter, PdfFormatOption  # type: ignore
            self._DocumentConverter = DocumentConverter
            self._PdfFormatOption = PdfFormatOption
            self._timing["import_ms"] = (time.time() - t0) * 1000.0
        except Exception as e:
            self._DocumentConverter = None
            self._PdfFormatOption = None
            self._import_error = str(e)
        try:
            import docling  # type: ignore
            self._version = getattr(docling, "__version__", None)
        except Exception:
            self._version = None

    def version(self) -> Optional[str]:
        return self._version

    def _ensure_converted(self, pdf_path: Path) -> Optional[Any]:
        pdf_path = pdf_path.resolve()
        if pdf_path in self._doc_cache:
            self._timing["cached"] = True
            return self._doc_cache[pdf_path]
        if getattr(self, "_DocumentConverter", None) is None:
            self._failed[pdf_path] = getattr(self, "_import_error", "Docling not available")
            return None
        try:
            t_init0 = time.time()
            conv = self._DocumentConverter(
                format_options={'pdf': self._PdfFormatOption(
                    do_ocr=self.config.do_ocr,
                    do_table_structure=self.config.do_table_structure,
                )}
            )
            self._timing["init_ms"] = (time.time() - t_init0) * 1000.0
            t_conv0 = time.time()
            res = conv.convert(str(pdf_path))
            self._timing["convert_ms"] = (time.time() - t_conv0) * 1000.0
            # Log a conversion record (per-document)
            try:
                logger = AgentLogger("docling_agent")
                record = AgentRunRecord(
                    timestamp=AgentLogger.now_ts(),
                    agent="docling_agent",
                    change_id=AgentLogger.short_change_id("convert+cache"),
                    rationale="Convert PDF and cache results for page-level table/picture queries.",
                    params={"do_ocr": self.config.do_ocr, "do_table_structure": self.config.do_table_structure, "version": self._version},
                    pages=[],
                    metrics={
                        "converted": True,
                        "timing_ms": {
                            "import_ms": self._timing.get("import_ms"),
                            "init_ms": self._timing.get("init_ms"),
                            "convert_ms": self._timing.get("convert_ms"),
                        }
                    },
                    status="ok",
                    artifacts={"pdf": str(pdf_path)},
                    tags=["docling", "convert", "cache"],
                )
                logger.append(record)
            except Exception:
                pass
            self._doc_cache[pdf_path] = res.document
            return res.document
        except Exception as e:
            self._failed[pdf_path] = str(e)
            return None

    def timings(self) -> Dict[str, Optional[float]]:
        return dict(self._timing)

    @staticmethod
    def _flip_bbox_bottomleft_to_topleft(bb: Any, page_height: float) -> Tuple[float, float, float, float]:
        # bb has l, t, r, b in bottom-left origin
        l = float(bb.l); r = float(bb.r); tY = float(bb.t); bY = float(bb.b)
        x0, x1 = l, r
        y0, y1 = page_height - tY, page_height - bY
        y0, y1 = (min(y0, y1), max(y0, y1))
        return (x0, y0, x1, y1)

    def get_tables_for_page(self, pdf_path: Path, fitz_doc: fitz.Document, page_index_zero: int) -> List[Tuple[float, float, float, float]]:
        d = self._ensure_converted(pdf_path)
        if d is None:
            return []
        pno = page_index_zero + 1
        H = float(fitz_doc[page_index_zero].rect.height)
        out: List[Tuple[float, float, float, float]] = []
        for t in getattr(d, 'tables', []) or []:
            try:
                prov = getattr(t, 'prov', None)
                if not prov:
                    continue
                if prov[0].page_no != pno:
                    continue
                out.append(self._flip_bbox_bottomleft_to_topleft(prov[0].bbox, H))
            except Exception:
                continue
        return out

    def get_pictures_for_page(self, pdf_path: Path, fitz_doc: fitz.Document, page_index_zero: int) -> List[Tuple[float, float, float, float]]:
        d = self._ensure_converted(pdf_path)
        if d is None:
            return []
        pno = page_index_zero + 1
        H = float(fitz_doc[page_index_zero].rect.height)
        out: List[Tuple[float, float, float, float]] = []
        for pic in getattr(d, 'pictures', []) or []:
            try:
                prov = getattr(pic, 'prov', None)
                if not prov:
                    continue
                if prov[0].page_no != pno:
                    continue
                out.append(self._flip_bbox_bottomleft_to_topleft(prov[0].bbox, H))
            except Exception:
                continue
        return out

    def emit_sidecar(self, pdf_path: Path, page_index_zero: int, fitz_doc: fitz.Document, out_dir: Path) -> None:
        """Write raw docling tables/pictures for the page to JSON sidecars."""
        out_dir.mkdir(parents=True, exist_ok=True)
        d = self._ensure_converted(pdf_path)
        if d is None:
            return
        pno = page_index_zero + 1
        H = float(fitz_doc[page_index_zero].rect.height)
        # Tables
        try:
            raw_tables = []
            for t in getattr(d, 'tables', []) or []:
                prov = getattr(t, 'prov', None)
                if not prov or prov[0].page_no != pno:
                    continue
                bb = prov[0].bbox
                raw_tables.append({'bbox_pt': self._flip_bbox_bottomleft_to_topleft(bb, H), 'prov': {'page_no': pno}})
            import json
            with (out_dir / 'docling_tables_raw.json').open('w', encoding='utf-8') as f:
                json.dump({'docling_boxes': [rt['bbox_pt'] for rt in raw_tables]}, f, indent=2)
        except Exception:
            pass
        # Pictures
        try:
            raw_pics = []
            for pic in getattr(d, 'pictures', []) or []:
                prov = getattr(pic, 'prov', None)
                if not prov or prov[0].page_no != pno:
                    continue
                bb = prov[0].bbox
                raw_pics.append({'bbox_pt': self._flip_bbox_bottomleft_to_topleft(bb, H), 'prov': {'page_no': pno}})
            import json
            with (out_dir / 'docling_pictures_raw.json').open('w', encoding='utf-8') as f:
                json.dump({'docling_boxes': [rp['bbox_pt'] for rp in raw_pics]}, f, indent=2)
        except Exception:
            pass
