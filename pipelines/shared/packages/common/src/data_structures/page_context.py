#!/usr/bin/env python3
from __future__ import annotations

"""
PageContext: Single-pass, reusable per-page acquisition context.

Collects and caches PyMuPDF primitives (rawdict/words/drawings), Docling tables/pictures
for the page, basic geometry (page size, gutter/columns), and a rendering service hook
for efficient raster crops. All coordinates are in PDF points.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class PageGeometry:
    width: float
    height: float
    gutter_x: float  # midline between columns


@dataclass
class PageContext:
    # PyMuPDF
    rawdict: Dict[str, Any]
    words: List[Any]
    drawings: List[Any]
    # Docling (already in PDF-point space)
    docling_tables: List[Tuple[float, float, float, float]]
    docling_pictures: List[Tuple[float, float, float, float]]
    # Geometry
    geom: PageGeometry
    # Backreferences (not used by detectors directly)
    pdf_path: Path
    page_index: int  # 0-based
    fitz_page: Any
    # Rendering service, injected lazily to avoid circular import
    rendering: Any = field(default=None)


def _safe_get_rawdict(page) -> Dict[str, Any]:
    try:
        raw = page.get_text("rawdict")
        return raw if isinstance(raw, dict) else {}
    except Exception:
        return {}


def _safe_get_words(page) -> List[Any]:
    try:
        w = page.get_text("words")
        return w if isinstance(w, list) else []
    except Exception:
        return []


def _safe_get_drawings(page) -> List[Any]:
    try:
        d = page.get_drawings()
        return d if isinstance(d, list) else []
    except Exception:
        return []


def build_page_context(
    pdf_path: Path,
    fitz_doc: Any,
    page_index_zero: int,
    docling_agent: Optional[Any] = None,
) -> PageContext:
    page = fitz_doc[page_index_zero]
    rect = page.rect
    geom = PageGeometry(width=float(rect.width), height=float(rect.height), gutter_x=float(rect.width) / 2.0)

    rawdict = _safe_get_rawdict(page)
    words = _safe_get_words(page)
    drawings = _safe_get_drawings(page)

    # Docling tables/pictures in PDF point coords
    docling_tables: List[Tuple[float, float, float, float]] = []
    docling_pictures: List[Tuple[float, float, float, float]] = []
    if docling_agent is not None:
        try:
            docling_tables = docling_agent.get_tables_for_page(pdf_path, fitz_doc, page_index_zero) or []
        except Exception:
            docling_tables = []
        try:
            docling_pictures = docling_agent.get_pictures_for_page(pdf_path, fitz_doc, page_index_zero) or []
        except Exception:
            docling_pictures = []

    ctx = PageContext(
        rawdict=rawdict,
        words=words,
        drawings=drawings,
        docling_tables=docling_tables,
        docling_pictures=docling_pictures,
        geom=geom,
        pdf_path=Path(pdf_path),
        page_index=page_index_zero,
        fitz_page=page,
        rendering=None,
    )
    return ctx

