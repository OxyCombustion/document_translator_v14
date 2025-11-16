#!/usr/bin/env python3
from __future__ import annotations

from typing import Dict, Any, Tuple


class RasterTightenerAgent:
    """Tighten equation boxes by raster analysis within a coarse corridor.

    Steps (per box):
    - Render the page region at ~3x scale.
    - Binarize (OTSU), invert (text as white), and compute horizontal projection.
    - Find top/bottom rows with sufficient ink to snap vertical bounds.
    - Optionally shrink left bound to leftmost ink, but keep right bound as-is (hard edge near number).
    """

    def __init__(self, scale: float = 3.0, margin_y: float = 12.0, margin_x: float = 6.0) -> None:
        self.scale = float(scale)
        self.margin_y = float(margin_y)
        self.margin_x = float(margin_x)

    def tighten(self, page, bbox_pt: Tuple[float, float, float, float]) -> Tuple[float, float, float, float]:
        try:
            import fitz  # PyMuPDF
            import numpy as np
            import cv2
        except Exception:
            return bbox_pt

        x0, y0, x1, y1 = map(float, bbox_pt)
        # Ensure valid rect
        if x1 <= x0 or y1 <= y0:
            return bbox_pt
        try:
            # Expand clip slightly to capture full math bands
            clip = fitz.Rect(
                max(0.0, x0 - self.margin_x),
                max(0.0, y0 - self.margin_y),
                x1 + self.margin_x,
                y1 + self.margin_y,
            )
            mat = fitz.Matrix(self.scale, self.scale)
            pix = page.get_pixmap(matrix=mat, clip=clip, alpha=False)
            img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
            if img.shape[2] == 4:
                img = img[:, :, :3]
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            # Otsu binary inverse: text is white
            _, bw = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
            h, w = bw.shape[:2]
            # Enhance horizontal structures
            hk = max(15, int(0.15 * w))
            horiz_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (hk, 1))
            bw_h = cv2.morphologyEx(bw, cv2.MORPH_CLOSE, horiz_kernel, iterations=1)
            # Canny + Hough to detect horizontal lines (fraction bars)
            bars_top = []
            bars_bot = []
            try:
                edges = cv2.Canny(bw_h, 50, 150)
                lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=100, minLineLength=int(0.3*w), maxLineGap=8)
                if lines is not None:
                    for ln in lines[:,0,:]:
                        xA, yA, xB, yB = map(int, ln)
                        if abs(yA - yB) <= 2 and abs(xB - xA) >= int(0.3*w):
                            ybar = int((yA + yB)//2)
                            bars_top.append(ybar)
                            bars_bot.append(ybar)
            except Exception:
                pass
            # Horizontal projection (use enhanced image)
            proj = bw_h.sum(axis=1)
            if proj.max() <= 0:
                return bbox_pt
            # Threshold at small fraction of max to find bands
            thr = 0.05 * float(proj.max())
            rows = np.where(proj >= thr)[0]
            if rows.size == 0:
                return bbox_pt
            # group contiguous row runs and merge gaps <= 6 px
            runs = []
            start = int(rows[0]); prev = int(rows[0])
            for r in rows[1:]:
                r = int(r)
                if r - prev > 6:
                    runs.append((start, prev))
                    start = r
                prev = r
            runs.append((start, prev))
            new_top = min(r[0] for r in runs)
            new_bot = max(r[1] for r in runs)
            # If we detected horizontal lines (bars), extend to them
            if bars_top and bars_bot:
                new_top = min(new_top, max(0, min(bars_top) - 2))
                new_bot = max(new_bot, min(h-1, max(bars_bot) + 2))
            # Optional left tightening (keep hard right bound)
            col_proj = bw.sum(axis=0)
            cthr = 0.03 * float(col_proj.max()) if col_proj.max() > 0 else 0
            cols = np.where(col_proj >= cthr)[0]
            if cols.size > 0:
                new_left = int(cols.min())
            else:
                new_left = 0
            # Also use CCs to avoid narrow centers: find leftmost contour that intersects the math band
            try:
                band = bw[new_top:new_bot+1, :]
                num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(band, connectivity=8)
                left_cc = new_left
                band_area = band.shape[0] * band.shape[1]
                for i in range(1, num_labels):
                    x, y, cw, ch, area = stats[i]
                    if area < max(15, 0.002 * band_area):
                        continue
                    # require some horizontal extent or height
                    if cw < max(5, int(0.02 * w)) and ch < max(4, int(0.01 * h)):
                        continue
                    left_cc = min(left_cc, int(x))
                new_left = min(new_left, left_cc)
            except Exception:
                pass
            # Map back to PDF points
            # account for clip margins: y0m/x0m are the expanded clip origin
            x0m = max(0.0, x0 - self.margin_x)
            y0m = max(0.0, y0 - self.margin_y)
            ty0 = y0m + (new_top / self.scale)
            ty1 = y0m + (new_bot / self.scale)
            tx0 = x0m + (new_left / self.scale)
            tx1 = x1  # keep hard right edge anchored at number side
            # Keep within original
            # Allow moving right (if coarse left was too far left), but not past right-1
            tx0 = min(tx1 - 1.0, max(0.0, tx0))
            ty0 = max(y0, min(ty0, ty1 - 1.0))
            tx1 = min(x1, max(tx0 + 1.0, tx1))
            ty1 = min(y1, max(ty0 + 1.0, ty1))
            return (tx0, ty0, tx1, ty1)
        except Exception:
            return bbox_pt
