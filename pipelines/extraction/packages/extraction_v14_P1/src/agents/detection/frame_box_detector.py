#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple, Dict, Any, Optional


BBox = Tuple[float, float, float, float]


def _inter(a: BBox, b: BBox) -> float:
    ax0, ay0, ax1, ay1 = a
    bx0, by0, bx1, by1 = b
    ix0 = max(ax0, bx0)
    iy0 = max(ay0, by0)
    ix1 = min(ax1, bx1)
    iy1 = min(ay1, by1)
    if ix1 <= ix0 or iy1 <= iy0:
        return 0.0
    return (ix1 - ix0) * (iy1 - iy0)


def _contains(outer: BBox, inner: BBox, tol: float = 0.0) -> bool:
    x0, y0, x1, y1 = outer
    a0, b0, a1, b1 = inner
    return (a0 >= x0 - tol) and (a1 <= x1 + tol) and (b0 >= y0 - tol) and (b1 <= y1 + tol)


@dataclass
class FrameDetectionConfig:
    pad_pt: float = 2.0  # outward pad on returned frame
    min_w: float = 120.0
    min_h: float = 80.0


class FrameBoxDetector:
    def __init__(self, cfg: FrameDetectionConfig | None = None) -> None:
        self.cfg = cfg or FrameDetectionConfig()

    def detect(
        self,
        page: Any,
        *,
        region_hint: Optional[BBox] = None,
        caption_bbox: Optional[BBox] = None,
        kind: str = "table",  # or "figure"
        column_band: Optional[Tuple[float, float]] = None,
    ) -> List[Dict[str, Any]]:
        """Detect rectangular frames from vector drawings. Returns list of candidates.

        Heuristics:
        - Restrict to column_band [x_left, x_right] if provided
        - For tables: frame should contain caption (near top area), and extend below it
        - For figures: frame should be above caption
        """
        cfg = self.cfg
        frames: List[Dict[str, Any]] = []
        xL, xR = (None, None)
        if column_band and len(column_band) == 2:
            xL, xR = float(column_band[0]), float(column_band[1])

        try:
            drawings = page.get_drawings()
        except Exception:
            drawings = []
        for d in drawings or []:
            rect = None
            if isinstance(d, dict):
                rect = d.get("rect")
            if not (isinstance(rect, (list, tuple)) and len(rect) == 4):
                continue
            x0, y0, x1, y1 = map(float, rect)
            if x1 - x0 < cfg.min_w or y1 - y0 < cfg.min_h:
                continue
            if xL is not None and (x1 < xL or x0 > xR):
                continue
            # Caption gating
            if isinstance(caption_bbox, (list, tuple)) and len(caption_bbox) == 4:
                cx0, cy0, cx1, cy1 = map(float, caption_bbox)
                if kind == "table":
                    # Caption expected inside top part of frame
                    if not _contains((x0, y0, x1, y1), (cx0, cy0, cx1, cy1), tol=4.0):
                        continue
                    if cy1 + 6.0 > y1:  # caption must be well above bottom of frame
                        continue
                else:  # figure: caption below frame
                    if cy0 < y1 - 4.0:  # caption should start below frame
                        continue
            area = (x1 - x0) * (y1 - y0)
            frames.append({
                "bbox": [x0 - cfg.pad_pt, y0 - cfg.pad_pt, x1 + cfg.pad_pt, y1 + cfg.pad_pt],
                "source": "vector",
                "score": area,
            })
        # If no vector frames found, try raster fallback in the column band under/over caption
        if not frames:
            try:
                import fitz
                import numpy as np
                import cv2
                # Build a clip region for raster scan
                page_h = float(page.rect.height)
                if column_band and len(column_band) == 2:
                    xL, xR = float(column_band[0]), float(column_band[1])
                else:
                    xL, xR = 0.0, float(page.rect.width)
                if isinstance(caption_bbox, (list, tuple)) and len(caption_bbox) == 4:
                    cx0, cy0, cx1, cy1 = map(float, caption_bbox)
                    if kind == "table":
                        y0 = max(0.0, cy1 + 4.0)
                        y1 = page_h
                    else:  # figure: look above caption
                        y0 = 0.0
                        y1 = max(0.0, cy0 - 4.0)
                else:
                    y0, y1 = 0.0, page_h
                if y1 <= y0 + 8.0 or xR <= xL + 8.0:
                    raise RuntimeError("Invalid clip region for raster frame detection")
                clip = fitz.Rect(xL, y0, xR, y1)
                dpi = 150
                scale = float(dpi) / 72.0
                pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), clip=clip, alpha=False)
                if pix.width <= 0 or pix.height <= 0:
                    raise RuntimeError("Empty pixmap for raster frame detection")
                arr = np.frombuffer(pix.samples, dtype=np.uint8)
                img = arr.reshape(pix.height, pix.width, pix.n)
                gray = (0.299 * img[:,:,0] + 0.587 * img[:,:,1] + 0.114 * img[:,:,2]).astype(np.uint8) if img.shape[2] > 1 else img[:,:,0]
                # Preserve edges while smoothing
                try:
                    gray = cv2.bilateralFilter(gray, d=7, sigmaColor=50, sigmaSpace=50)
                except Exception:
                    pass
                # Edge detection and contour extraction
                edges = cv2.Canny(gray, 60, 160)
                # Connect broken borders: dilate then close
                k3 = cv2.getStructuringElement(cv2.MORPH_RECT, (3,3))
                k5 = cv2.getStructuringElement(cv2.MORPH_RECT, (5,5))
                edges = cv2.dilate(edges, k3, iterations=1)
                edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, k5, iterations=1)
                # Stronger close to bridge faint/broken borders
                k7 = cv2.getStructuringElement(cv2.MORPH_RECT, (7,7))
                edges_strong = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, k7, iterations=1)
                contours, _ = cv2.findContours(edges_strong, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                candidates: List[Tuple[float, float, float, float, float]] = []  # x0,y0,x1,y1,score
                for cnt in contours or []:
                    if cv2.contourArea(cnt) < 500:  # filter tiny
                        continue
                    # Use convex hull to stabilize rectangle fit
                    hull = cv2.convexHull(cnt)
                    rect = cv2.minAreaRect(hull)
                    (cx, cy), (w, h), angle = rect
                    bw, bh = max(w, h), min(w, h)
                    if bw < (self.cfg.min_w * scale * 0.5) or bh < (self.cfg.min_h * scale * 0.5):
                        continue
                    box = cv2.boxPoints(rect)
                    box = np.int0(box)
                    x0p, y0p = np.min(box[:,0]), np.min(box[:,1])
                    x1p, y1p = np.max(box[:,0]), np.max(box[:,1])
                    # Map back to page points
                    rx0 = clip.x0 + (x0p / scale)
                    ry0 = clip.y0 + (y0p / scale)
                    rx1 = clip.x0 + (x1p / scale)
                    ry1 = clip.y0 + (y1p / scale)
                    # Column gating already enforced by clip; caption gating:
                    if isinstance(caption_bbox, (list, tuple)) and len(caption_bbox) == 4:
                        cx0, cy0, cx1, cy1 = map(float, caption_bbox)
                        if kind == "table":
                            if not _contains((rx0, ry0, rx1, ry1), (cx0, cy0, cx1, cy1), tol=6.0):
                                continue
                            if cy1 + 6.0 > ry1:
                                continue
                        else:
                            if cy0 < ry1 - 4.0:
                                continue
                    # Score by area and squareness
                    area = (rx1 - rx0) * (ry1 - ry0)
                    ar = max((rx1 - rx0), (ry1 - ry0)) / max(1.0, min((rx1 - rx0), (ry1 - ry0)))
                    score = area / ar
                    candidates.append((rx0, ry0, rx1, ry1, score))
                if candidates:
                    candidates.sort(key=lambda t: t[4], reverse=True)
                    rx0, ry0, rx1, ry1, score = candidates[0]
                    frames.append({
                        "bbox": [rx0 - self.cfg.pad_pt, ry0 - self.cfg.pad_pt, rx1 + self.cfg.pad_pt, ry1 + self.cfg.pad_pt],
                        "source": "raster",
                        "score": score,
                    })
                else:
                    # Fallback: axis-aligned bounding rectangles of the largest edge component
                    contours2, _ = cv2.findContours(edges_strong, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                    rect_cands: List[Tuple[float,float,float,float,float]] = []
                    for cnt in contours2 or []:
                        a = cv2.contourArea(cnt)
                        if a < 800:
                            continue
                        x, y, w, h = cv2.boundingRect(cnt)
                        if w < int(self.cfg.min_w * scale * 0.4) or h < int(self.cfg.min_h * scale * 0.4):
                            continue
                        rx0 = clip.x0 + (x / scale)
                        ry0 = clip.y0 + (y / scale)
                        rx1 = clip.x0 + ((x + w) / scale)
                        ry1 = clip.y0 + ((y + h) / scale)
                        # Caption gating similar to above
                        ok = True
                        if isinstance(caption_bbox, (list, tuple)) and len(caption_bbox) == 4:
                            cx0, cy0, cx1, cy1 = map(float, caption_bbox)
                            if kind == "table":
                                if not _contains((rx0, ry0, rx1, ry1), (cx0, cy0, cx1, cy1), tol=6.0):
                                    ok = False
                                # Caption near top: within top 35% of box height
                                if (cy1 - ry0) > 0.35 * (ry1 - ry0):
                                    ok = False
                            else:
                                if cy0 < ry1 - 4.0:
                                    ok = False
                        if not ok:
                            continue
                        rect_cands.append((rx0, ry0, rx1, ry1, a))
                    if rect_cands:
                        rect_cands.sort(key=lambda t: t[4], reverse=True)
                        rx0, ry0, rx1, ry1, score = rect_cands[0]
                        frames.append({
                            "bbox": [rx0 - self.cfg.pad_pt, ry0 - self.cfg.pad_pt, rx1 + self.cfg.pad_pt, ry1 + self.cfg.pad_pt],
                            "source": "raster",
                            "score": score,
                        })
            except Exception:
                pass

        # Sort by score (area), descending
        frames.sort(key=lambda f: f.get("score", 0.0), reverse=True)
        return frames
