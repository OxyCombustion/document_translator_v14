#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple
import re
import time
from pathlib import Path

# TODO: agent_logger is infrastructure - will be migrated in future phase
# from common.src.logging.agent_logger import AgentLogger, AgentRunRecord
# Stubbed for now - logging functionality not critical for extraction
AgentLogger = None  # type: ignore
AgentRunRecord = None  # type: ignore

try:
    from ..equation_number_ocr_agent.agent import EquationNumberOCRAgent, EquationNumberOCRConfig
except Exception:
    EquationNumberOCRAgent = None  # type: ignore
    EquationNumberOCRConfig = None  # type: ignore


@dataclass
class EquationRefineOptions:
    left_width: float = 500.0
    right_eps: float = 5.0
    min_width: float = 60.0
    pad: float = 6.0
    env_height_ratio: float = 0.98


class EquationRefinementAgent:
    def __init__(self, options: EquationRefineOptions | None = None) -> None:
        self.opt = options or EquationRefineOptions()
        self._ocr_agent = None

    def _get_ocr_agent(self):
        if self._ocr_agent is not None:
            return self._ocr_agent
        try:
            if EquationNumberOCRAgent is None:
                self._ocr_agent = None
            else:
                self._ocr_agent = EquationNumberOCRAgent(EquationNumberOCRConfig())
        except Exception:
            self._ocr_agent = None
        return self._ocr_agent

    def _snap_left_edge(self, page, y0: float, y1: float, gutter: float, x1_limit: float, in_left_col: bool, *, thr: int = 242, percentile: float = 0.0, margin: float = 12.0) -> float | None:
        """Raster-scan a thin corridor near the gutter to find the first ink column.
        Returns snapped x0 (points) or None if not found. Right column only for now.
        """
        try:
            import fitz
            import numpy as np
        except Exception:
            return None
        # Only apply to right column for now, per operator request
        if in_left_col:
            return None
        # Corridor from just right of gutter toward number/union right edge
        x0 = gutter + 2.0
        x1 = max(x0 + 20.0, min(x1_limit, x0 + 400.0))
        if x1 <= x0 + 4.0:
            return None
        # Clip rect and rasterize at modest DPI for speed
        dpi = 150
        scale = float(dpi) / 72.0
        clip = fitz.Rect(x0, y0, x1, y1)
        try:
            pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), clip=clip, alpha=False)
        except Exception:
            return None
        arr = np.frombuffer(pix.samples, dtype=np.uint8)
        if arr.size == 0:
            return None
        img = arr.reshape(pix.height, pix.width, pix.n)
        if img.shape[2] > 1:
            # grayscale approximation
            gray = (0.299 * img[:,:,0] + 0.587 * img[:,:,1] + 0.114 * img[:,:,2]).astype(np.uint8)
        else:
            gray = img[:,:,0]
        # Binarize: treat near-white as background
        ink = gray < int(thr)
        if not ink.any():
            return None
        # Compute earliest ink index per row, then take requested percentile for robustness
        rows_have = ink.any(axis=1)
        if not rows_have.any():
            return None
        earliest = []
        for r in range(ink.shape[0]):
            row = ink[r]
            if row.any():
                earliest.append(int(np.argmax(row)))
        if not earliest:
            return None
        k = 0
        if percentile > 0.0:
            k = max(0, min(len(earliest) - 1, int(round(percentile * (len(earliest) - 1)))))
        left_col_idx = sorted(earliest)[k]
        snapped_x0 = x0 + (left_col_idx / scale)
        # Add left margin but do not cross gutter
        snapped_x0 = max(gutter + 2.0, snapped_x0 - float(margin))
        return snapped_x0

    def _raster_expand_vert(self, page, x0: float, x1: float, y0: float, y1: float) -> Tuple[float, float] | None:
        """Raster-based vertical expansion: within [x0,x1], find top/bottom ink rows and return expanded (y0,y1).
        Returns None on failure.
        """
        try:
            import fitz
            import numpy as np
        except Exception:
            return None
        # Add modest vertical margin around current band
        vm = 24.0
        top = max(0.0, min(y0, y1) - vm)
        bot = max(y0, y1) + vm
        if bot <= top + 2.0:
            return None
        dpi = 150
        scale = float(dpi) / 72.0
        clip = fitz.Rect(x0, top, x1, bot)
        try:
            pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), clip=clip, alpha=False)
        except Exception:
            return None
        arr = np.frombuffer(pix.samples, dtype=np.uint8)
        if arr.size == 0:
            return None
        img = arr.reshape(pix.height, pix.width, pix.n)
        if img.shape[2] > 1:
            gray = (0.299 * img[:,:,0] + 0.587 * img[:,:,1] + 0.114 * img[:,:,2]).astype(np.uint8)
        else:
            gray = img[:,:,0]
        ink = gray < 235
        if not ink.any():
            return None
        # Row density thresholding to avoid spurious sparse rows
        row_counts = ink.sum(axis=1).astype(np.int32)
        width_px = ink.shape[1]
        dens_thresh = max(3, int(0.06 * width_px))
        dense = row_counts >= dens_thresh
        # require small smoothing to avoid isolated single rows
        if dense.size >= 3:
            dense[1:-1] = dense[1:-1] & (dense[0:-2] | dense[2:])
        if not dense.any():
            return None
        try:
            first = int(np.argmax(dense))
            last = int(len(dense) - 1 - np.argmax(dense[::-1]))
        except Exception:
            return None
        if last <= first:
            return None
        new_y0 = top + (first / scale)
        new_y1 = top + (last / scale)
        return (new_y0, new_y1)

    def _left_bound_from_chars_and_slices(
        self,
        page,
        y0: float,
        y1: float,
        gutter: float,
        x1_limit: float,
        in_left_col: bool,
        *,
        dpi: int = 150,
        char_percentile: float = 0.10,
        slice_count: int = 5,
        raster_thr: int = 245,
        margin_pt: float = 12.0,
    ) -> float | None:
        """Combine char-cloud and slice-aware raster to propose a robust left x0.
        Returns None if neither signal yields a candidate. Column clamps are applied by the caller.
        """
        if in_left_col:
            return None
        # 1) Char/word cloud within band
        char_x0s: List[float] = []
        try:
            words = page.get_text("words") or []
            for w in words:
                if not (isinstance(w, (list, tuple)) and len(w) >= 8):
                    continue
                x0w, y0w, x1w, y1w, word = float(w[0]), float(w[1]), float(w[2]), float(w[3]), str(w[4])
                # Column gate (right column only)
                if x0w < (gutter + 6.0):
                    continue
                # Vertical band overlap (≥30%)
                vy = max(0.0, min(y1w, y1) - max(y0w, y0))
                if vy < 0.3 * max(1.0, y1 - y0):
                    continue
                # Prefer math-like words to avoid units-only bias
                if (not self._is_mathy(word)) and ('(' not in word and ')' not in word):
                    continue
                char_x0s.append(x0w)
        except Exception:
            pass
        char_x0 = None
        if char_x0s:
            xs = sorted(char_x0s)
            idx = max(0, min(len(xs) - 1, int(round(char_percentile * (len(xs) - 1)))))
            char_x0 = xs[idx] - margin_pt
        # 2) Slice-aware raster over the band
        slice_x0 = None
        try:
            import fitz, numpy as np  # noqa: F401
            total_h = max(1.0, y1 - y0)
            slices = max(1, slice_count)
            candidates: List[float] = []
            for i in range(slices):
                sy0 = y0 + (i * total_h / slices)
                sy1 = y0 + ((i + 1) * total_h / slices)
                snap = self._snap_left_edge(page, sy0, sy1, gutter, x1_limit, in_left_col, thr=raster_thr, percentile=0.0, margin=margin_pt)
                if isinstance(snap, float):
                    candidates.append(snap)
            if candidates:
                # take the 10th percentile across slices to capture earliest ink
                xs = sorted(candidates)
                j = max(0, min(len(xs) - 1, int(round(0.10 * (len(xs) - 1)))))
                slice_x0 = xs[j]
        except Exception:
            pass
        # Combine signals: prefer the minimum (furthest left) among valid candidates
        best = None
        for v in (char_x0, slice_x0):
            if isinstance(v, float):
                best = v if best is None else min(best, v)
        return best

    def _collect_lines(self, page) -> List[Dict[str, Any]]:
        try:
            raw = page.get_text("rawdict")
        except Exception:
            raw = None
        lines: List[Dict[str, Any]] = []
        if not isinstance(raw, dict):
            return lines
        for blk in raw.get("blocks", []) or []:
            if blk.get("type") != 0:
                continue
            for line in blk.get("lines", []) or []:
                x0 = y0 = float("inf"); x1 = y1 = float("-inf")
                texts: List[str] = []
                for sp in line.get("spans", []) or []:
                    bb = sp.get("bbox"); t = sp.get("text")
                    if isinstance(bb, (list, tuple)) and len(bb) == 4:
                        sx0, sy0, sx1, sy1 = map(float, bb)
                        if (sx1 - sx0) < 0.5 or (sy1 - sy0) < 0.5:
                            continue
                        x0 = min(x0, sx0); y0 = min(y0, sy0)
                        x1 = max(x1, sx1); y1 = max(y1, sy1)
                        if isinstance(t, str):
                            texts.append(t)
                if x1 > x0 and y1 > y0:
                    cy = (y0 + y1) / 2.0
                    h = (y1 - y0)
                    text = "".join(texts)
                    lines.append({'bbox': [x0, y0, x1, y1], 'cy': cy, 'h': h, 'text': text})
        return lines

    # --- Lettered token detectors ---
    def _lettered_from_raw(self, page) -> List[Tuple[str, Tuple[float,float,float,float]]]:
        patt1 = re.compile(r"\((\d{1,3}[a-z])\)")
        patt2 = re.compile(r"\((\d{1,3})\s*([a-z])\)")
        out: List[Tuple[str, Tuple[float,float,float,float]]] = []
        try:
            raw = page.get_text("rawdict")
        except Exception:
            raw = None
        if not isinstance(raw, dict):
            return out
        for blk in raw.get("blocks", []) or []:
            if blk.get("type") != 0:
                continue
            for line in blk.get("lines", []) or []:
                spans = line.get("spans", []) or []
                line_text = "".join([(sp.get("text") or "") for sp in spans])
                if not (patt1.search(line_text) or patt2.search(line_text)):
                    continue
                # span-level
                hit = False
                bx = [float('inf'), float('inf'), float('-inf'), float('-inf')]
                for sp in spans:
                    t = sp.get("text") or ""; bb = sp.get("bbox")
                    if not (isinstance(bb, (list, tuple)) and len(bb) == 4):
                        continue
                    if patt1.search(t):
                        out.append((patt1.search(t).group(1), tuple(map(float, bb))))
                        hit = True
                    elif patt2.search(t):
                        m = patt2.search(t); tok = f"{m.group(1)}{m.group(2)}"
                        out.append((tok, tuple(map(float, bb))))
                        hit = True
                if not hit and spans:
                    # fallback to line bbox
                    xs0 = [float(sp.get("bbox")[0]) for sp in spans if sp.get("bbox")]
                    ys0 = [float(sp.get("bbox")[1]) for sp in spans if sp.get("bbox")]
                    xs1 = [float(sp.get("bbox")[2]) for sp in spans if sp.get("bbox")]
                    ys1 = [float(sp.get("bbox")[3]) for sp in spans if sp.get("bbox")]
                    lb = (min(xs0), min(ys0), max(xs1), max(ys1))
                    for m in patt1.finditer(line_text):
                        out.append((m.group(1), lb))
                    for m in patt2.finditer(line_text):
                        tok = f"{m.group(1)}{m.group(2)}"
                        out.append((tok, lb))
        return out

    def _lettered_from_words(self, page) -> List[Tuple[str, Tuple[float,float,float,float]]]:
        out: List[Tuple[str, Tuple[float,float,float,float]]] = []
        try:
            words = page.get_text("words")
        except Exception:
            words = []
        if not words:
            return out
        from collections import defaultdict
        by_line: Dict[Tuple[int,int], List[Tuple[float,float,float,float,str]]] = defaultdict(list)
        for w in words:
            if not (isinstance(w, (list, tuple)) and len(w) >= 8):
                continue
            x0,y0,x1,y1,word,blk,ln,wn = w[:8]
            if not isinstance(word, str):
                continue
            by_line[(int(blk), int(ln))].append((float(x0), float(y0), float(x1), float(y1), word))
        patt1 = re.compile(r"^\((\d{1,3}[a-z])\)$")
        patt2 = re.compile(r"^\((\d{1,3})\s*([a-z])\)$")
        for key, arr in by_line.items():
            arr.sort(key=lambda t: t[0])
            n = len(arr)
            for i in range(n):
                x0,y0,x1,y1,w0 = arr[i]
                m1 = patt1.match(w0)
                if m1:
                    out.append((m1.group(1), (x0,y0,x1,y1)))
                    continue
                m2 = patt2.match(w0)
                if m2:
                    tok = f"{m2.group(1)}{m2.group(2)}"
                    out.append((tok, (x0,y0,x1,y1)))
                    continue
                comp = w0; bx0,by0,bx1,by1 = x0,y0,x1,y1
                for k in range(i+1, min(i+5, n)):
                    tx0,ty0,tx1,ty1,tw = arr[k]
                    comp += tw
                    bx0 = min(bx0, tx0); by0 = min(by0, ty0)
                    bx1 = max(bx1, tx1); by1 = max(by1, ty1)
                    m1c = patt1.match(comp)
                    if m1c:
                        out.append((m1c.group(1), (bx0,by0,bx1,by1)))
                        break
                    m2c = patt2.match(comp)
                    if m2c:
                        tok = f"{m2c.group(1)}{m2c.group(2)}"
                        out.append((tok, (bx0,by0,bx1,by1)))
                        break
        return out

    def _is_mathy(self, s: str) -> bool:
        if not s:
            return False
        ascii_tokens = ['=', '/', '\\', '^', '_', '+', '-', '*']
        if any(tok in s for tok in ascii_tokens):
            return True
        unicode_tokens = ['×', '÷', '±', '≤', '≥', '≠', '≈', '≡', '∝', '√', '∞', '∫', '∮', '∬', '∂', '∇', '∑', '∏', '∧', '∨', '⊕', '⊗', '→', '←', '↔', '⋯', '…', '•', '·', '°']
        if any(tok in s for tok in unicode_tokens):
            return True
        greek = 'αβγδεζηθικλμνξοπρστυφχψω' + 'ΑΒΓΔΕΖΗΘΙΚΛΜΝΞΟΠΡΣΤΥΦΧΨΩ'
        if any(ch in s for ch in greek):
            return True
        return False

    def _build_candidates(self, page, lines, num_bbox) -> Tuple[List[Dict[str, Any]], Tuple[float,float,float,float], float, float, float, float]:
        x0N, y0N, x1N, y1N = map(float, num_bbox)
        opt = self.opt
        left_width = opt.left_width; eps = opt.right_eps
        page_rect = page.rect
        cyN = (y0N + y1N) / 2.0; hN = (y1N - y0N)
        # Use the equation number's LEFT edge as the corridor anchor (operator guidance)
        num_left = min(x0N, x1N)
        x0N = num_left  # downstream logic and final clamp will reference x0N
        gutter = float(page_rect.width) / 2.0
        in_left_col = (num_left < gutter)
        # Column-aware coarse corridor (do not span across gutter)
        cx0 = max(0.0, num_left - left_width)
        cx1 = max(0.0, num_left - eps)
        if in_left_col:
            # keep corridor within left column
            cx0 = max(0.0, min(cx0, gutter - 8.0))
            cx1 = max(0.0, min(cx1, gutter - 8.0))
        else:
            # keep corridor within right column
            cx0 = max(gutter + 8.0, cx0)
            cx1 = max(gutter + 8.0, cx1)
        coarse = (
            cx0,
            max(0.0, cyN - (hN * 1.5)),
            cx1,
            min(page_rect.height, cyN + (hN * 1.5)),
        )
        base_candidates: List[Dict[str, Any]] = []
        for ln in lines:
            bx0, by0, bx1, by1 = ln['bbox']
            # must lie strictly to the left of the number's LEFT edge
            if bx1 >= (num_left - eps):
                continue
            # Column gate: only accept lines from the same column as the number
            if in_left_col and bx1 > (gutter - 6.0):
                continue
            if (not in_left_col) and bx0 < (gutter + 6.0):
                continue
            cyB = ln['cy']; hB = ln['h']
            tol = max(8.0, 0.6 * max(hN, hB))
            if not (abs(cyB - cyN) <= tol or (by0 <= cyN <= by1)):
                continue
            if bx0 < (num_left - left_width - 50.0):
                continue
            width = (bx1 - bx0)
            if width < self.opt.min_width:
                continue
            text = ln.get('text') or ''
            gap = (num_left - eps) - bx1  # smaller gap means closer to the number's left edge
            base_candidates.append({'bbox': [bx0, by0, bx1, by1], 'cy': cyB, 'h': hB, 'text': text, 'right_gap': gap, 'width': width})
        # Pick candidates closest to the number's left edge first (no math filter for the anchor)
        candidates: List[Dict[str, Any]] = []
        if base_candidates:
            thresholds = [40.0, 60.0, 80.0, 120.0]
            for t in thresholds:
                near = [c for c in base_candidates if c['right_gap'] <= t]
                if near:
                    candidates = near
                    break
            candidates = candidates or base_candidates
        return candidates, coarse, num_left, cyN, left_width, eps

    def _choose_seed(self, candidates) -> Dict[str, Any] | None:
        if not candidates:
            return None
        # Anchor seed to the first text to the left of the number: minimal gap, then widest.
        candidates.sort(key=lambda d: (abs(d.get('right_gap', 1e9)), -d.get('width', 0)))
        return candidates[0]

    def _grow_union(self, candidates, x0N, eps, seed, lines, left_width, cyN) -> List[Tuple[float,float,float,float]]:
        union: List[Tuple[float,float,float,float]] = [tuple(seed['bbox'])]
        max_vert_delta = max(12.0, 1.6 * seed['h'])
        max_right_gap = max(14.0, abs(seed['right_gap']) + 8.0)
        # Seed band (for continuation/fraction overlap checks)
        seed_x0 = float(seed['bbox'][0])
        seed_x1 = min(float(seed['bbox'][2]), float(x0N - eps))
        seed_band_w = max(1.0, (seed_x1 - seed_x0))
        # pass 1: aligned neighbors near number center with right-edge consistency
        for cand in candidates:
            if cand is seed:
                continue
            cx0, cy0, cx1, cy1 = cand['bbox']
            if abs(cand['right_gap']) <= max_right_gap and abs(((cy0 + cy1)/2.0) - cyN) <= (max_vert_delta * 1.6):
                # keep candidates whose right edge aligns close to the seed's right edge
                if abs(cand['right_gap'] - seed['right_gap']) > 10.0:
                    continue
                union.append((cx0, cy0, cx1, cy1))
        # expansion loop
        changed = True
        continuations_used = 0
        while changed:
            changed = False
            merged = self._merge(union)
            if not merged:
                break
            ux0, uy0, ux1, uy1 = merged
            ux1 = min(ux1, x0N - eps)
            v_gap = max(14.0, 1.8 * seed['h'])
            for cand in candidates:
                cx0, cy0, cx1, cy1 = cand['bbox']
                # horizontal overlap with band
                if cx1 < (ux0 - 14.0) or cx0 > (ux1 + 14.0):
                    continue
                # vertical contiguity
                if (cy1 < (uy0 - v_gap)) or (cy0 > (uy1 + v_gap)):
                    continue
                # right alignment (absolute and relative to seed)
                if abs(cand['right_gap']) > (max_right_gap * 2.0):
                    continue
                if abs(cand['right_gap'] - seed['right_gap']) > 10.0:
                    continue
                # content gate: math-like or '='
                txt = cand.get('text') or ''
                if not self._is_mathy(txt) and '=' not in txt:
                    # allow up to two wide continuations if width-aligned AND overlaps seed band >= 50%
                    if continuations_used < 2:
                        bw = (ux1 - ux0)
                        overlap = max(0.0, min(cx1, seed_x1) - max(cx0, seed_x0))
                        if (cand['width'] >= 0.6 * bw) and (overlap >= 0.35 * seed_band_w):
                            continuations_used += 1
                        else:
                            continue
                    else:
                        continue
                rect = (cx0, cy0, cx1, cy1)
                if rect not in union:
                    union.append(rect)
                    changed = True
        # Fraction/continuation: include wide lines nearby to cover stacked parts
        merged = self._merge(union)
        if merged:
            bw = merged[2] - merged[0]; uy0 = merged[1]; uy1 = merged[3]
            v_gap = max(14.0, 1.8 * seed['h'])
            for ln in lines:
                lx0, ly0, lx1, ly1 = ln['bbox']
                if lx1 > (x0N - eps):
                    continue
                # near vertically
                if ly1 < (uy0 - v_gap*1.2) or ly0 > (uy1 + v_gap*1.2):
                    continue
                # wide enough and overlaps seed band sufficiently
                overlap = max(0.0, min(lx1, seed_x1) - max(lx0, seed_x0))
                if (lx1 - lx0) >= (0.6 * bw) and (overlap >= 0.35 * seed_band_w):
                    rect = (lx0, ly0, lx1, ly1)
                    if rect not in union:
                        union.append(rect)
            # If the union is still unusually narrow (as with 79b), widen left using narrow lines
            merged = self._merge(union)
            if merged:
                merged_w = merged[2] - merged[0]
                seed_w = seed_x1 - seed_x0
                # Case A: narrow union (e.g., 79b) — widen left using aligned lines or candidates
                if merged_w < max(140.0, 1.20 * seed_w):
                    aligned_lefts = []
                    # from page lines
                    for ln in lines:
                        bx0, by0, bx1, by1 = ln['bbox']
                        if bx1 > (x0N - eps):
                            continue
                        if by1 < (uy0 - v_gap) or by0 > (uy1 + v_gap):
                            continue
                        rg = (x0N - eps) - bx1
                        if abs(rg - seed['right_gap']) <= 10.0:
                            aligned_lefts.append(bx0)
                    # from candidate set (ensures we consider filtered mathy lines)
                    for cand in candidates:
                        cx0, cy0, cx1, cy1 = cand['bbox']
                        if abs(cand['right_gap'] - seed['right_gap']) <= 10.0:
                            aligned_lefts.append(cx0)
                    if aligned_lefts:
                        widened_left = min(aligned_lefts)
                        merged = (min(merged[0], widened_left), merged[1], merged[2], merged[3])
                else:
                    # Case B: union looks wide but drifts left (e.g., 79a/80) — tighten left to aligned percentile
                    def _rg(rect):
                        return (x0N - eps) - rect[2]
                    aligned_rects = [r for r in union if abs(_rg(r) - seed['right_gap']) <= 8.0]
                    if aligned_rects:
                        xs = sorted(r[0] for r in aligned_rects)
                        idx = int(round(0.90 * (len(xs) - 1)))
                        left_p = xs[max(0, min(len(xs)-1, idx))]
                        # tighten left inward (raise x0); keep within seed-left guard
                        merged = (max(merged[0], max(left_p, seed_x0 - 25.0)), merged[1], merged[2], merged[3])
        return union

    def _merge(self, rects: List[Tuple[float,float,float,float]]):
        if not rects:
            return None
        x0 = min(r[0] for r in rects); y0 = min(r[1] for r in rects)
        x1 = max(r[2] for r in rects); y1 = max(r[3] for r in rects)
        return (x0,y0,x1,y1)

    def refine_from_labels(self, page, eq_number_labels: List[Dict[str, Any]], debug_out_dir: Any = None) -> Dict[Any, Dict[str, Any]]:
        results: Dict[Any, Dict[str, Any]] = {}
        lines = self._collect_lines(page)
        page_rect = page.rect
        opt = self.opt
        # debug setup
        debug_enabled = bool(debug_out_dir)
        debug_payload: Dict[str, Any] = {"items": []} if debug_enabled else {}
        t0 = time.time()
        for entry in eq_number_labels:
            try:
                num = int(entry['number'])
                nb = entry['bbox']
            except Exception:
                continue
            candidates, coarse, x0N, cyN, left_width, eps = self._build_candidates(page, lines, nb)
            if not candidates:
                # fallback narrow box (column-aware) with light vertical grow and raster left snap (right col)
                gutter = float(page_rect.width) / 2.0
                in_left_col = (x0N < gutter)
                x0 = max(0.0, x0N - 300.0); x1 = max(0.0, x0N - eps)
                # keep box entirely within the number's column
                if in_left_col:
                    x1 = min(x1, gutter - 8.0)
                    x0 = min(x0, gutter - 8.0)
                else:
                    x0 = max(x0, gutter + 8.0)
                    x1 = max(x1, gutter + 8.0)
                y0 = max(0.0, cyN - 20.0); y1 = min(page_rect.height, cyN + 20.0)
                # Full band-fill envelope growth using the corridor as a seed band
                env_y0, env_y1 = y0, y1
                seed_x0 = float(x0); seed_x1 = float(min(x1, x0N - eps))
                seed_w = max(1.0, seed_x1 - seed_x0)
                v_gap = max(14.0, 1.8 * (y1 - y0))
                for ln in lines:
                    lx0, ly0, lx1, ly1 = ln['bbox']
                    # column gate
                    if in_left_col:
                        if lx1 > (gutter - 6.0):
                            continue
                    else:
                        if lx0 < (gutter + 6.0):
                            continue
                    # horizontal overlap with seed band
                    overlap_seed = max(0.0, min(lx1, seed_x1) - max(lx0, seed_x0))
                    if overlap_seed < 0.5 * seed_w:
                        continue
                    # vertical adjacency
                    if (ly1 < env_y0 - v_gap) or (ly0 > env_y1 + v_gap):
                        continue
                    txt = ln.get('text') or ''
                    if not self._is_mathy(txt) and '=' not in txt:
                        continue
                    env_y0 = min(env_y0, ly0); env_y1 = max(env_y1, ly1)
                # Include thin wide lines (fractions)
                for ln2 in lines:
                    ax0, ay0, ax1, ay1 = ln2['bbox']
                    # column gate
                    if in_left_col:
                        if ax1 > (gutter - 6.0):
                            continue
                    else:
                        if ax0 < (gutter + 6.0):
                            continue
                    # near band horizontally
                    if ax1 < (seed_x0 - 14.0) or ax0 > (seed_x1 + 14.0):
                        continue
                    lh = (ay1 - ay0); lw = (ax1 - ax0)
                    if lh <= 8.0 and lw >= 0.4 * (seed_x1 - seed_x0):
                        env_y0 = min(env_y0, ay0); env_y1 = max(env_y1, ay1)
                # Vector fraction bars via drawings
                try:
                    drawings = page.get_drawings()
                    band_w = max(1.0, (seed_x1 - seed_x0))
                    min_bar_w = max(80.0, 0.3 * band_w)
                    for d in drawings or []:
                        rect = None
                        if isinstance(d, dict):
                            rect = d.get('rect')
                        if rect and isinstance(rect, (list, tuple)) and len(rect) == 4:
                            dx0, dy0, dx1, dy1 = map(float, rect)
                            # column gate
                            if in_left_col and dx1 > (gutter - 6.0):
                                continue
                            if (not in_left_col) and dx0 < (gutter + 6.0):
                                continue
                            # overlaps seed band sufficiently and wide enough
                            overlap_seed = max(0.0, min(dx1, seed_x1) - max(dx0, seed_x0))
                            if overlap_seed >= 0.5 * seed_w and (dx1 - dx0) >= min_bar_w:
                                env_y0 = min(env_y0, dy0); env_y1 = max(env_y1, dy1)
                except Exception:
                    pass
                y0, y1 = env_y0, env_y1
                # Raster vertical expansion first to set correct band (fixes half-band alignment)
                expanded = self._raster_expand_vert(page, x0, x1, y0, y1)
                if isinstance(expanded, tuple):
                    y0, y1 = expanded
                # Right column: snap left edge to first ink from gutter using expanded band
                if not in_left_col:
                    snapped = self._snap_left_edge(page, y0, y1, gutter, x1, in_left_col)
                    if isinstance(snapped, float) and snapped < x1 - self.opt.min_width:
                        x0 = max(gutter + 2.0, snapped)
                # Small vertical margin for safety
                y0 = max(0.0, y0 - 10.0)
                y1 = min(page_rect.height, y1 + 10.0)
                tight = (x0, y0, x1, y1)
                results[num] = {'tight_bbox': [tight[0], tight[1], tight[2], tight[3]], 'method': 'text-union', 'confidence': 0.35}
                if debug_enabled:
                    debug_payload["items"].append({
                        "number": num,
                        "number_bbox": list(map(float, nb)),
                        "coarse": list(coarse),
                        "candidates": [],
                        "seed": None,
                        "union_pre_envelope": [],
                        "merged_after_envelope": list(tight),
                        "final_bbox": list(tight),
                        "note": "fallback-narrow+env+raster"
                    })
                continue
            seed = self._choose_seed(candidates)
            union = self._grow_union(candidates, x0N, eps, seed, lines, left_width, cyN)
            merged = self._merge(union)
            if debug_enabled:
                dbg_item = {
                    "number": num,
                    "number_bbox": list(map(float, nb)),
                    "coarse": list(coarse),
                    "candidates": [c['bbox'] for c in candidates],
                    "seed": list(seed['bbox']) if seed else None,
                    "union_pre_envelope": [list(u) for u in union],
                }
            # Band-fill envelope grow
            if merged:
                ux0, uy0, ux1, uy1 = merged
                env_y0, env_y1 = uy0, uy1
                env_count = 0
                for ln in lines:
                    lx0, ly0, lx1, ly1 = ln['bbox']
                    if lx1 > (x0N - eps) or lx0 < (x0N - left_width - 50.0):
                        continue
                    txt = ln.get('text') or ''
                    if not self._is_mathy(txt) and '=' not in txt:
                        continue
                    if lx1 < (ux0 - 14.0) or lx0 > (x0N - eps + 14.0):
                        continue
                    # also require ≥50% overlap with the seed x-band
                    seed_x0 = float(seed['bbox'][0]); seed_x1 = min(float(seed['bbox'][2]), float(x0N - eps))
                    seed_w = max(1.0, seed_x1 - seed_x0)
                    overlap_seed = max(0.0, min(lx1, seed_x1) - max(lx0, seed_x0))
                    if overlap_seed < 0.35 * seed_w:
                        continue
                    env_y0 = min(env_y0, ly0); env_y1 = max(env_y1, ly1); env_count += 1
                if env_count >= 1:
                    cur_h = max(1.0, uy1 - uy0); env_h = max(1.0, env_y1 - env_y0)
                    if cur_h < (opt.env_height_ratio * env_h):
                        merged = (ux0, env_y0, ux1, env_y1)
                # Thin-line inclusion: include very thin but wide lines (fraction-like) near the union
                try:
                    v_gap2 = max(14.0, 1.6 * (seed['h']))
                    for ln2 in lines:
                        ax0, ay0, ax1, ay1 = ln2['bbox']
                        if ax1 > (x0N - eps):
                            continue
                        if ax1 < (ux0 - 14.0) or ax0 > (x0N - eps + 14.0):
                            continue
                        if (ay1 < env_y0 - v_gap2) or (ay0 > env_y1 + v_gap2):
                            continue
                        lh = (ay1 - ay0); lw = (ax1 - ax0)
                        if lh <= max(6.0, 0.5 * seed['h']) and lw >= 0.4 * (ux1 - ux0):
                            env_y0 = min(env_y0, ay0); env_y1 = max(env_y1, ay1)
                    if (env_y1 - env_y0) > (uy1 - uy0):
                        merged = (ux0, env_y0, ux1, env_y1)
                    # Vector fraction bars via page.get_drawings()
                    try:
                        drawings = page.get_drawings()
                        band_w = max(1.0, (ux1 - ux0))
                        min_bar_w = max(80.0, 0.3 * band_w)
                        for d in drawings or []:
                            rect = None
                            if isinstance(d, dict):
                                rect = d.get('rect')
                            if rect and isinstance(rect, (list, tuple)) and len(rect) == 4:
                                rx0, ry0, rx1, ry1 = map(float, rect)
                                rw = abs(rx1 - rx0); rh = abs(ry1 - ry0)
                                # wide and thin; overlapping horizontally with corridor band
                                if rh <= max(6.0, 0.5 * seed['h']) and rw >= min_bar_w:
                                    if not (rx1 < (ux0 - 14.0) or rx0 > (x0N - eps + 14.0)):
                                        env_y0 = min(env_y0, min(ry0, ry1))
                                        env_y1 = max(env_y1, max(ry0, ry1))
                            # Also parse path items for horizontal segments
                            try:
                                items = d.get('items') if isinstance(d, dict) else None
                            except Exception:
                                items = None
                            if items:
                                for it in items:
                                    try:
                                        # it is a tuple like (op, p1, p2, ...). We detect line segments.
                                        if not isinstance(it, (list, tuple)) or len(it) < 3:
                                            continue
                                        op = it[0]
                                        if op not in ('l', 're', 'c', 'qu', 'Q'):
                                            # 'l' line; ignore curves for now
                                            pass
                                        # For line ops, subsequent entries are point tuples
                                        pts = [p for p in it[1:] if isinstance(p, (list, tuple)) and len(p) >= 2]
                                        for j in range(len(pts)-1):
                                            xA, yA = float(pts[j][0]), float(pts[j][1])
                                            xB, yB = float(pts[j+1][0]), float(pts[j+1][1])
                                            rw = abs(xB - xA); rh = abs(yB - yA)
                                            if rw >= min_bar_w and rh <= max(6.0, 0.5 * seed['h']):
                                                seg_x0, seg_x1 = min(xA, xB), max(xA, xB)
                                                seg_y0, seg_y1 = min(yA, yB), max(yA, yB)
                                                if not (seg_x1 < (ux0 - 14.0) or seg_x0 > (x0N - eps + 14.0)):
                                                    env_y0 = min(env_y0, seg_y0)
                                                    env_y1 = max(env_y1, seg_y1)
                                    except Exception:
                                        continue
                        if (env_y1 - env_y0) > (uy1 - uy0):
                            merged = (ux0, env_y0, ux1, env_y1)
                    except Exception:
                        pass
                except Exception:
                    pass
                # Apply a small vertical snap-to-envelope margin when we detected envelope growth
                if merged and (env_y1 - env_y0) > (uy1 - uy0):
                    snap = max(6.0, 0.2 * seed['h'])
                    merged = (ux0, max(0.0, env_y0 - snap), ux1, min(page_rect.height, env_y1 + snap))
                else:
                    # If no explicit envelope growth, check for stacked math lines near top/bottom and snap slightly
                    try:
                        top_hits = 0; bottom_hits = 0
                        near_top_y = uy0; near_bot_y = uy1
                        for ln3 in lines:
                            lx0, ly0, lx1, ly1 = ln3['bbox']
                            txt = ln3.get('text') or ''
                            if not self._is_mathy(txt) and '=' not in txt:
                                continue
                            # overlap horizontally with current band
                            if lx1 < (ux0 - 14.0) or lx0 > (x0N - eps + 14.0):
                                continue
                            cy = (ly0 + ly1) / 2.0
                            if (uy0 - 16.0) <= cy <= (uy0 + 10.0):
                                top_hits += 1
                                near_top_y = min(near_top_y, ly0)
                            if (uy1 - 10.0) <= cy <= (uy1 + 16.0):
                                bottom_hits += 1
                                near_bot_y = max(near_bot_y, ly1)
                        if top_hits >= 2 or bottom_hits >= 2:
                            merged = (ux0, max(0.0, min(uy0, near_top_y - 4.0)), ux1, min(page_rect.height, max(uy1, near_bot_y + 4.0)))
                    except Exception:
                        pass
            # Robust left bound: avoid drifting far left due to wide lines; use seed-overlap-aware percentile (tighter)
            if merged:
                seed_x0 = float(seed['bbox'][0]); seed_x1 = min(float(seed['bbox'][2]), float(x0N - eps))
                seed_w = max(1.0, seed_x1 - seed_x0)
                def _overlaps_seed(r):
                    ox = max(0.0, min(r[2], seed_x1) - max(r[0], seed_x0))
                    return ox >= 0.5 * seed_w
                lefts = sorted([r[0] for r in union if _overlaps_seed(r)])
                seed_left = float(seed['bbox'][0])
                if lefts:
                    idx = int(round(0.85 * (len(lefts) - 1)))
                    p_left = lefts[max(0, min(len(lefts)-1, idx))]
                else:
                    p_left = merged[0]
                robust_left = max(seed_left - 30.0, p_left)
                merged = (max(merged[0], robust_left), merged[1], merged[2], merged[3])
            # Column-aware clamp: do not cross the gutter into the opposite column
            try:
                gutter = float(page_rect.width) / 2.0
                # x0N here represents the number's right edge (num_right)
                in_left_col = (x0N < gutter)
                if merged:
                    mx0, my0, mx1, my1 = merged
                    if in_left_col:
                        mx1 = min(mx1, gutter - 8.0)
                    else:
                        mx0 = max(mx0, gutter + 8.0)
                    merged = (mx0, my0, mx1, my1)
            except Exception:
                pass
            if debug_enabled:
                dbg_item["merged_after_envelope"] = list(merged) if merged else None
            # Normalize any inverted rectangle from the merge/envelope phase
            if merged:
                mx0, my0, mx1, my1 = merged
                nx0, nx1 = (mx0, mx1) if mx0 <= mx1 else (mx1, mx0)
                ny0, ny1 = (my0, my1) if my0 <= my1 else (my1, my0)
                merged = (nx0, ny0, nx1, ny1)
            # Post-merge left widen using aligned-left 15th percentile within seed band (improves narrow cases like 79b)
            try:
                if merged:
                    seed_x0 = float(seed['bbox'][0]); seed_x1 = min(float(seed['bbox'][2]), float(x0N - eps))
                    seed_w = max(1.0, seed_x1 - seed_x0)
                    def _overlaps_seed(r):
                        return max(0.0, min(r[2], seed_x1) - max(r[0], seed_x0)) >= 0.5 * seed_w
                    lefts = sorted([r[0] for r in union if _overlaps_seed(r)])
                    if lefts:
                        idx = int(round(0.10 * (len(lefts) - 1)))
                        widen_left = lefts[max(0, min(len(lefts)-1, idx))]
                        gutter = float(page_rect.width) / 2.0
                        in_left_col = (x0N < gutter)
                        if in_left_col:
                            widen_left = min(widen_left, gutter - 8.0)
                        else:
                            widen_left = max(widen_left, gutter + 8.0)
                        merged = (min(merged[0], widen_left), merged[1], merged[2], merged[3])
            except Exception:
                pass
            clip = (max(coarse[0], merged[0]), max(coarse[1], merged[1]), min(coarse[2], merged[2]), min(coarse[3], merged[3])) if merged else coarse
            x0, y0, x1, y1 = clip
            # Enforce a minimal width to avoid sliver boxes when merges invert or over-clip
            min_w = float(opt.min_width)
            if (x1 - x0) < min_w:
                # Expand left, keeping the right edge anchored to the number corridor
                desired_x0 = x1 - min_w
                x0 = max(coarse[0], desired_x0)
            x0 = max(0.0, x0 - opt.pad)
            y0 = max(0.0, y0 - opt.pad)
            # Unconditional final clamp: right edge must land a few pixels to the LEFT of the number label
            snap_eps = 1.5  # points; ~2 px at 150dpi
            x1 = max(x0 + 1.0, min(page_rect.width, x0N - snap_eps))
            y1 = min(page_rect.height, y1 + opt.pad)
            # Final column clamp and min-width enforce, with raster snap-to-ink on right column
            gutter = float(page_rect.width) / 2.0
            in_left_col = (x0N < gutter)
            if in_left_col:
                x1 = min(x1, gutter - 8.0)
                if (x1 - x0) < opt.min_width:
                    x0 = max(0.0, x1 - opt.min_width)
            else:
                x0 = max(x0, gutter + 8.0)
                if (x1 - x0) < opt.min_width:
                    x0 = max(gutter + 8.0, x1 - opt.min_width)
                # Snap left edge using robust percentile to include upper-line ink too
                snapped = self._snap_left_edge(page, y0, y1, gutter, x1, in_left_col, thr=245, percentile=0.10, margin=14.0)
                if isinstance(snapped, float) and snapped < x1 - 4.0:
                    x0 = max(gutter + 2.0, min(snapped, x1 - opt.min_width))
                # Try a more aggressive snap (min percentile) to capture earliest ink across rows
                snapped2 = self._snap_left_edge(page, y0, y1, gutter, x1, in_left_col, thr=248, percentile=0.00, margin=16.0)
                if isinstance(snapped2, float) and snapped2 < x1 - 4.0:
                    x0 = max(gutter + 2.0, min(min(x0, snapped2), x1 - opt.min_width))
                # Gentle fixed widen to improve perceived width on multi-line unions
                x0 = max(gutter + 2.0, x0 - 12.0)
            results[num] = {'tight_bbox': [x0, y0, x1, y1], 'method': 'multiline-union', 'confidence': 0.6}
            if debug_enabled:
                dbg_item["merged_after_envelope"] = [merged[0], merged[1], merged[2], merged[3]] if merged else dbg_item.get("merged_after_envelope")
                dbg_item["final_bbox"] = [x0, y0, x1, y1]
                debug_payload["items"].append(dbg_item)
        # Merge lettered tokens into results
        try:
            seen = set(results.keys())
            tokens = []
            tokens += self._lettered_from_raw(page)
            tokens += self._lettered_from_words(page)
            for token, bb in tokens:
                if token in seen:
                    continue
                # Treat token bbox as number bbox and refine
                cands, coarse, x0N, cyN, left_width, eps = self._build_candidates(page, lines, bb)
                if not cands:
                    # Lettered token fallback: column-aware narrow + full envelope + raster left snap
                    gutter = float(page.rect.width) / 2.0
                    in_left_col = (x0N < gutter)
                    x0 = max(0.0, x0N - 300.0); x1 = max(0.0, x0N - self.opt.right_eps)
                    if in_left_col:
                        x1 = min(x1, gutter - 8.0); x0 = min(x0, gutter - 8.0)
                    else:
                        x0 = max(x0, gutter + 8.0); x1 = max(x1, gutter + 8.0)
                    cyN = float((bb[1] + bb[3]) / 2.0)
                    y0 = max(0.0, cyN - 20.0); y1 = min(page.rect.height, cyN + 20.0)
                    env_y0, env_y1 = y0, y1
                    seed_x0 = float(x0); seed_x1 = float(min(x1, x0N - self.opt.right_eps))
                    seed_w = max(1.0, seed_x1 - seed_x0)
                    v_gap = max(14.0, 1.8 * (y1 - y0))
                    for ln in lines:
                        lx0, ly0, lx1, ly1 = ln['bbox']
                        if in_left_col:
                            if lx1 > (gutter - 6.0):
                                continue
                        else:
                            if lx0 < (gutter + 6.0):
                                continue
                        overlap_seed = max(0.0, min(lx1, seed_x1) - max(lx0, seed_x0))
                        if overlap_seed < 0.5 * seed_w:
                            continue
                        if (ly1 < env_y0 - v_gap) or (ly0 > env_y1 + v_gap):
                            continue
                        txt = ln.get('text') or ''
                        if not self._is_mathy(txt) and '=' not in txt:
                            continue
                        env_y0 = min(env_y0, ly0); env_y1 = max(env_y1, ly1)
                    # thin lines
                    for ln2 in lines:
                        ax0, ay0, ax1, ay1 = ln2['bbox']
                        if in_left_col:
                            if ax1 > (gutter - 6.0):
                                continue
                        else:
                            if ax0 < (gutter + 6.0):
                                continue
                        if ax1 < (seed_x0 - 14.0) or ax0 > (seed_x1 + 14.0):
                            continue
                        lh = (ay1 - ay0); lw = (ax1 - ax0)
                        if lh <= 8.0 and lw >= 0.4 * (seed_x1 - seed_x0):
                            env_y0 = min(env_y0, ay0); env_y1 = max(env_y1, ay1)
                    # drawings
                    try:
                        drawings = page.get_drawings()
                        band_w = max(1.0, (seed_x1 - seed_x0))
                        min_bar_w = max(80.0, 0.3 * band_w)
                        for d in drawings or []:
                            rect = None
                            if isinstance(d, dict):
                                rect = d.get('rect')
                            if rect and isinstance(rect, (list, tuple)) and len(rect) == 4:
                                dx0, dy0, dx1, dy1 = map(float, rect)
                                if in_left_col and dx1 > (gutter - 6.0):
                                    continue
                                if (not in_left_col) and dx0 < (gutter + 6.0):
                                    continue
                                overlap_seed = max(0.0, min(dx1, seed_x1) - max(dx0, seed_x0))
                                if overlap_seed >= 0.5 * seed_w and (dx1 - dx0) >= min_bar_w:
                                    env_y0 = min(env_y0, dy0); env_y1 = max(env_y1, dy1)
                    except Exception:
                        pass
                    y0, y1 = env_y0, env_y1
                    # Expand vertically first, then snap left edge (right column)
                    expanded = self._raster_expand_vert(page, x0, x1, y0, y1)
                    if isinstance(expanded, tuple):
                        y0, y1 = expanded
                    if not in_left_col:
                        snapped = self._snap_left_edge(page, y0, y1, gutter, x1, in_left_col)
                        if isinstance(snapped, float) and snapped < x1 - self.opt.min_width:
                            x0 = max(gutter + 2.0, snapped)
                    y0 = max(0.0, y0 - 10.0)
                    y1 = min(page.rect.height, y1 + 10.0)
                    results[token] = {'tight_bbox': [x0,y0,x1,y1], 'method': 'text-union', 'confidence': 0.35}
                    continue
                seed = self._choose_seed(cands)
                union = self._grow_union(cands, x0N, eps, seed, lines, left_width, cyN)
                merged = self._merge(union)
                if merged:
                    # Normalize any inverted rectangle
                    mx0, my0, mx1, my1 = merged
                    nx0, nx1 = (mx0, mx1) if mx0 <= mx1 else (mx1, mx0)
                    ny0, ny1 = (my0, my1) if my0 <= my1 else (my1, my0)
                    merged = (nx0, ny0, nx1, ny1)
                    # Apply robust left
                    seed_x0 = float(seed['bbox'][0]); seed_x1 = min(float(seed['bbox'][2]), float(x0N - eps))
                    seed_w = max(1.0, seed_x1 - seed_x0)
                    def _overlaps_seed(r):
                        ox = max(0.0, min(r[2], seed_x1) - max(r[0], seed_x0))
                        return ox >= 0.5 * seed_w
                    lefts = sorted([r[0] for r in union if _overlaps_seed(r)])
                    seed_left = float(seed['bbox'][0])
                    if lefts:
                        idx = int(round(0.85 * (len(lefts) - 1)))
                        p_left = lefts[max(0, min(len(lefts)-1, idx))]
                    else:
                        p_left = merged[0]
                    robust_left = max(seed_left - 30.0, p_left)
                    merged = (max(merged[0], robust_left), merged[1], merged[2], merged[3])
                    clip = (max(coarse[0], merged[0]), max(coarse[1], merged[1]), min(coarse[2], merged[2]), min(coarse[3], merged[3]))
                    x0,y0,x1,y1 = clip
                    # Enforce minimal width
                    min_w = float(self.opt.min_width)
                    if (x1 - x0) < min_w:
                        desired_x0 = x1 - min_w
                        x0 = max(coarse[0], desired_x0)
                    x0 = max(0.0, x0 - self.opt.pad)
                    y0 = max(0.0, y0 - self.opt.pad)
                    x1 = min(page.rect.width, min(x1 + self.opt.pad, x0N - self.opt.right_eps))
                    y1 = min(page.rect.height, y1 + self.opt.pad)
                    # Final column clamp and min-width enforce for lettered tokens, with raster snap on right column
                    gutter = float(page.rect.width) / 2.0
                    in_left_col = (x0N < gutter)
                    if in_left_col:
                        x1 = min(x1, gutter - 8.0)
                        if (x1 - x0) < self.opt.min_width:
                            x0 = max(0.0, x1 - self.opt.min_width)
                    else:
                        x0 = max(x0, gutter + 8.0)
                        if (x1 - x0) < self.opt.min_width:
                            x0 = max(gutter + 8.0, x1 - self.opt.min_width)
                        snapped = self._snap_left_edge(page, y0, y1, gutter, x1, in_left_col, thr=245, percentile=0.10, margin=14.0)
                        if isinstance(snapped, float) and snapped < x1 - 4.0:
                            x0 = max(gutter + 2.0, min(snapped, x1 - self.opt.min_width))
                        snapped2 = self._snap_left_edge(page, y0, y1, gutter, x1, in_left_col, thr=248, percentile=0.00, margin=16.0)
                        if isinstance(snapped2, float) and snapped2 < x1 - 4.0:
                            x0 = max(gutter + 2.0, min(x0, snapped2))
                    # Gentle fixed widen for lettered multi-line unions
                    x0 = max(gutter + 2.0, x0 - 12.0)
                    results[token] = {'tight_bbox': [x0,y0,x1,y1], 'method': 'multiline-union', 'confidence': 0.6}
        except Exception:
            pass
        # Emit debug sidecar if requested
        try:
            if debug_enabled and debug_out_dir is not None:
                import json
                from pathlib import Path
                out_dir = Path(debug_out_dir)
                out_dir.mkdir(parents=True, exist_ok=True)
                with (out_dir / 'equations_debug.json').open('w', encoding='utf-8') as f:
                    json.dump(debug_payload, f, indent=2)
        except Exception:
            pass
        # Agent run logging (lightweight metrics)
        try:
            logger = AgentLogger("equation_refinement_agent")
            pagestr = []
            try:
                # PyMuPDF page.number is 0-based; store as 1-based string with 4 digits
                pno = getattr(page, "number", None)
                if isinstance(pno, int):
                    pagestr = [f"{pno+1:04d}"]
            except Exception:
                pass
            metrics = {
                "inputs": len(eq_number_labels or []),
                "outputs": len(results),
                "duration_sec": max(0.0, time.time() - t0),
                "env_height_ratio": float(opt.env_height_ratio),
                "left_width": float(opt.left_width),
                "right_eps": float(opt.right_eps),
                "pad": float(opt.pad),
            }
            record = AgentRunRecord(
                timestamp=AgentLogger.now_ts(),
                agent="equation_refinement_agent",
                change_id=AgentLogger.short_change_id("multiline-union + robust-left + corridor-right-edge"),
                rationale="Stabilize tight boxes: use number right edge corridor; seed-overlap constraints; stronger envelope.",
                params={"options": {
                    "env_height_ratio": opt.env_height_ratio,
                    "left_width": opt.left_width,
                    "right_eps": opt.right_eps,
                    "pad": opt.pad,
                }},
                pages=pagestr,
                metrics=metrics,
                status="ok",
                artifacts={"debug": bool(debug_enabled)},
                tags=["equations", "refine", "multiline", "robust-left"],
            )
            logger.append(record)
        except Exception:
            pass
        return results








