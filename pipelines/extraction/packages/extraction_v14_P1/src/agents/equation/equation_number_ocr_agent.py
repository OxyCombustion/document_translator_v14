#!/usr/bin/env python3
from __future__ import annotations

"""
EquationNumberOCRAgent

Purpose
- Given a PyMuPDF page and a vertical band in a given column, rasterize a
  right-corridor ROI and use OCR to locate equation-number tokens like
  "(79)" or "(79a)". Returns the token and its bbox in PDF points.

Design
- Engines: prefers pytesseract if available; otherwise returns None gracefully.
- ROI: column corridor (gutter±), optionally narrowed to [y0,y1] with margin.
- Filters: regex for "(dddd[a-z]?)", right-column gate, optional band proximity.
- Output: {'token': str, 'bbox': [x0,y0,x1,y1], 'engine': str, 'confidence': float}
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple
import re


@dataclass
class EquationNumberOCRConfig:
    dpi: int = 200
    margin_pt: float = 6.0
    pattern: str = r"\((\d{1,3})([a-z])?\)"  # e.g., (79) or (79a)
    engine: str = "auto"  # currently only pytesseract when available


class EquationNumberOCRAgent:
    def __init__(self, config: EquationNumberOCRConfig | None = None) -> None:
        self.cfg = config or EquationNumberOCRConfig()
        self._ocr_ready = None  # lazy probe

    def _ocr_available(self) -> bool:
        if self._ocr_ready is not None:
            return self._ocr_ready
        try:
            import os, platform, json
            import pytesseract  # noqa: F401
            # Resolve tesseract_cmd robustly without relying on PATH
            try:
                # 1) Respect explicit configuration via environment variable
                env_keys = ("TESSERACT_CMD", "TESSERACT_EXE")
                for k in env_keys:
                    p = os.environ.get(k)
                    if p and os.path.exists(p):
                        pytesseract.pytesseract.tesseract_cmd = p
                        break
                # 2) Project config file (config/ocr_config.json) with {"tesseract_cmd": "..."}
                if getattr(pytesseract.pytesseract, 'tesseract_cmd', 'tesseract') == 'tesseract':
                    try:
                        from pathlib import Path
                        cfg_path = Path('config') / 'ocr_config.json'
                        if cfg_path.exists():
                            data = json.loads(cfg_path.read_text(encoding='utf-8'))
                            tcmd = data.get('tesseract_cmd')
                            if isinstance(tcmd, str) and os.path.exists(tcmd):
                                pytesseract.pytesseract.tesseract_cmd = tcmd
                    except Exception:
                        pass
                # 3) OS-specific defaults
                import shutil
                if getattr(pytesseract.pytesseract, 'tesseract_cmd', 'tesseract') == 'tesseract':
                    # If on PATH, shutil.which will find it
                    found = shutil.which('tesseract')
                    if found:
                        pytesseract.pytesseract.tesseract_cmd = found
                # 4) Windows standard install locations as last resort
            try:
                if platform.system().lower().startswith('win'):
                    cmd = getattr(pytesseract.pytesseract, 'tesseract_cmd', 'tesseract')
                    if cmd == 'tesseract':
                        candidates = [
                            r"C:\\Program Files\\Tesseract-OCR\\tesseract.exe",
                            r"C:\\Program Files (x86)\\Tesseract-OCR\\tesseract.exe",
                        ]
                        for p in candidates:
                            if os.path.exists(p):
                                pytesseract.pytesseract.tesseract_cmd = p
                                break
            except Exception:
                pass
            from PIL import Image  # noqa: F401
            self._ocr_ready = True
        except Exception:
            self._ocr_ready = False
        return self._ocr_ready

    def anchor(
        self,
        page: Any,  # fitz.Page
        column: str = "right",
        band: Optional[Tuple[float, float]] = None,
    ) -> Optional[Dict[str, Any]]:
        if not self._ocr_available():
            return None
        import fitz
        import numpy as np
        from PIL import Image
        cfg = self.cfg
        rect = page.rect
        gutter = float(rect.width) / 2.0
        margin = float(cfg.margin_pt)
        # Horizontal corridor per column
        if column == "left":
            x0 = margin
            x1 = max(margin + 10.0, gutter - margin)
        else:
            x0 = min(gutter + margin, rect.width - margin)
            x1 = rect.width - margin
        # Vertical corridor
        if band and len(band) == 2:
            y0 = max(0.0, min(band[0], band[1]) - margin)
            y1 = min(rect.height, max(band[0], band[1]) + margin)
        else:
            y0 = margin
            y1 = rect.height - margin
        if x1 <= x0 + 2.0 or y1 <= y0 + 2.0:
            return None
        # Rasterize
        scale = float(cfg.dpi) / 72.0
        clip = fitz.Rect(x0, y0, x1, y1)
        try:
            pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), clip=clip, alpha=False)
        except Exception:
            return None
        img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        # OCR
        try:
            import pytesseract
            data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT, config="--psm 6")
        except Exception:
            return None
        # Parse tokens
        patt = re.compile(cfg.pattern)
        best = None
        for i in range(len(data.get("level", []))):
            text = (data.get("text", [""])[i] or "").strip()
            if not text:
                continue
            if not patt.fullmatch(text):
                continue
            try:
                conf = float(data.get("conf", ["0"])[i])
            except Exception:
                conf = 0.0
            left = int(data.get("left", [0])[i]); top = int(data.get("top", [0])[i])
            width = int(data.get("width", [0])[i]); height = int(data.get("height", [0])[i])
            # Convert to PDF points
            ax0 = x0 + (left / scale)
            ay0 = y0 + (top / scale)
            ax1 = x0 + ((left + width) / scale)
            ay1 = y0 + ((top + height) / scale)
            # Prefer the rightmost occurrence within corridor
            if (best is None) or (ax0 > best["bbox"][0]) or (conf > best.get("confidence", 0)):
                best = {"token": text, "bbox": [ax0, ay0, ax1, ay1], "engine": "pytesseract", "confidence": conf}
        return best
