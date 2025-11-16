#!/usr/bin/env python3
"""
Table / Figure Zone Refiner (Agent)
    # Cap bottom by next caption/heading in same column and page margin; adjust top if too tall
    try:
        caps_all = find_captions(page)
    except Exception:
        caps_all = []
    next_cap_y = None
    for c in caps_all or []:
        try:
            x0c,y0c,x1c,y1c = map(float, (c.get('bbox') or []))
        except Exception:
            continue
        cx_cap = (x0c + x1c) / 2.0
        if cx_cap < band_left or cx_cap > band_right:
            continue
        if y0c <= (cy1 + 4.0):
            continue
        if next_cap_y is None or y0c < next_cap_y:
            next_cap_y = y0c
    max_bottom_cap = page_h - 36.0
    if next_cap_y is not None:
        max_bottom_cap = min(max_bottom_cap, next_cap_y - 10.0)
    my1 = min(my1, max_bottom_cap)
    # Limit maximum span by lowering top (keep bottom anchored)
    max_span = 480.0
    if (my1 - my0) > max_span:
        my0 = max(cy1 + 40.0, my1 - max_span)

Purpose
- Produce tight table / figure boxes using caption / GT hints and page content.
- Normalize GT coordinates to PDF points if provided in other units.

Outputs
- Dict with lists of tight boxes per page (PDF points), suitable for overlays and sidecars.
"""

from __future__ import annotations

from typing import List, Tuple, Dict, Any, Iterable, Optional
from pathlib import Path
import json
import re


def _collect_line_boxes(page) -> List[Tuple[float, float, float, float]]:
    lines: List[Tuple[float, float, float, float]] = []
    try:
        raw = page.get_text("rawdict")
    except Exception:
        raw = None
    if not isinstance(raw, dict):
        return lines
    for blk in raw.get("blocks", []) or []:
        if blk.get("type") != 0:
            continue
        for line in blk.get("lines", []) or []:
            x0 = y0 = float("inf")
            x1 = y1 = float("-inf")
            for sp in line.get("spans", []) or []:
                bb = sp.get("bbox")
                if not (isinstance(bb, (list, tuple)) and len(bb) == 4):
                    continue
                sx0, sy0, sx1, sy1 = map(float, bb)
                if sx1 - sx0 <= 0.5 or sy1 - sy0 <= 0.5:
                    continue
                x0 = min(x0, sx0)
                y0 = min(y0, sy0)
                x1 = max(x1, sx1)
                y1 = max(y1, sy1)
            if x1 > x0 and y1 > y0 and x0 != float("inf"):
                lines.append((x0, y0, x1, y1))
    return lines


def _merge_rects(rects: List[Tuple[float, float, float, float]]) -> Tuple[float, float, float, float] | None:
    if not rects:
        return None
    x0 = min(r[0] for r in rects)
    y0 = min(r[1] for r in rects)
    x1 = max(r[2] for r in rects)
    y1 = max(r[3] for r in rects)
    return (x0, y0, x1, y1)


def _rect_area(r) -> float:
    if not r:
        return 0.0
    x0, y0, x1, y1 = r
    return max(0.0, (x1 - x0)) * max(0.0, (y1 - y0))


def normalize_bbox_to_pdf_points(page, bbox: Tuple[float, float, float, float]) -> Tuple[float, float, float, float]:
    """Attempt to normalize bbox to PDF points based on page size.
    Accepts candidates in points, pixels (150/300dpi), or normalized [0..1].
    """
    W = float(page.rect.width)
    H = float(page.rect.height)
    x0, y0, x1, y1 = map(float, bbox)
    # already plausible points
    if 0 <= x0 < x1 <= (W * 1.2) and 0 <= y0 < y1 <= (H * 1.2):
        # If slightly over, clip later by intersection
        return (x0, y0, x1, y1)
    # normalized [0..1]
    if 0.0 <= max(x0, y0, x1, y1) <= 1.0:
        return (x0 * W, y0 * H, x1 * W, y1 * H)
    # pixel guesses
    for dpi in (300.0, 200.0, 150.0, 96.0):
        sx = 72.0 / dpi
        nx0, ny0, nx1, ny1 = x0 * sx, y0 * sx, x1 * sx, y1 * sx
        if 0 <= nx0 < nx1 <= (W * 1.2) and 0 <= ny0 < ny1 <= (H * 1.2):
            return (nx0, ny0, nx1, ny1)
    # fallback: clamp to page
    return (max(0.0, min(x0, W)), max(0.0, min(y0, H)), max(0.0, min(x1, W)), max(0.0, min(y1, H)))


def refine_tables(page, gt_tables_bboxes: Iterable[Tuple[float, float, float, float]] | None) -> List[Tuple[float, float, float, float]]:
    """Refine table boxes by shrinking to union of line boxes inside GT bbox (if provided).
    If no GT bbox, return empty and let caller fall back.
    """
    if not gt_tables_bboxes:
        return []
    lines = _collect_line_boxes(page)
    refined: List[Tuple[float, float, float, float]] = []
    for bb in gt_tables_bboxes:
        x0, y0, x1, y1 = normalize_bbox_to_pdf_points(page, bb)
        # expand slightly then collect line boxes whose centers fall inside
        pad = 6.0
        X0 = max(0.0, x0 - pad)
        Y0 = max(0.0, y0 - pad)
        X1 = min(page.rect.width, x1 + pad)
        Y1 = min(page.rect.height, y1 + pad)
        inside: List[Tuple[float, float, float, float]] = []
        for lx0, ly0, lx1, ly1 in lines:
            cx = (lx0 + lx1) / 2.0
            cy = (ly0 + ly1) / 2.0
            if X0 <= cx <= X1 and Y0 <= cy <= Y1:
                inside.append((lx0, ly0, lx1, ly1))
        m = _merge_rects(inside)
        # If we found lines, use their union; else keep normalized GT
        if m and _rect_area(m) > 0:
            refined.append(m)
        else:
            refined.append((x0, y0, x1, y1))
    return refined


def find_captions(page) -> List[Dict[str, Any]]:
    """Find caption spans like 'Table 1', 'Table. 1', 'Fig 1', 'Fig. 1', 'Figure 1'.

    Robustness improvements:
    - Allow matches anywhere in the line (not only line start).
    - Fallback to a word-level scan that can compose 'T a b l e' and roman numerals.
    """
    out: List[Dict[str, Any]] = []
    try:
        raw = page.get_text("rawdict")
    except Exception:
        raw = None

    # Regex allowing match anywhere; optional period, number can be digits or roman, optional letter suffix
    roman = r"[ivxlcdm]+"
    num_pat = rf"(?:\d+|{roman})[a-z]?"
    table_re = re.compile(rf"table\.?\s*({num_pat})\b", re.IGNORECASE)
    fig_re = re.compile(rf"fig(?:ure)?\.?\s*({num_pat})\b", re.IGNORECASE)

    if isinstance(raw, dict):
        for blk in raw.get("blocks", []) or []:
            if blk.get("type") != 0:
                continue
            for line in blk.get("lines", []) or []:
                text_fragments = []
                x0 = y0 = float("inf"); x1 = y1 = float("-inf")
                for sp in line.get("spans", []) or []:
                    t = sp.get("text") or ""
                    bb = sp.get("bbox")
                    if isinstance(bb, (list, tuple)) and len(bb) == 4:
                        sx0, sy0, sx1, sy1 = map(float, bb)
                        x0 = min(x0, sx0); y0 = min(y0, sy0)
                        x1 = max(x1, sx1); y1 = max(y1, sy1)
                    text_fragments.append(t)
                if x1 <= x0 or y1 <= y0:
                    continue
                line_text = "".join(text_fragments)
                mt = table_re.search(line_text)
                if mt:
                    out.append({'type': 'table', 'number': mt.group(1), 'bbox': [x0, y0, x1, y1], 'text': line_text})
                    continue
                mf = fig_re.search(line_text)
                if mf:
                    out.append({'type': 'figure', 'number': mf.group(1), 'bbox': [x0, y0, x1, y1], 'text': line_text})

    # If nothing found, fall back to word-level composition to handle spaced letters (e.g., 'T a b l e')
    if not out:
        try:
            words = page.get_text("words")  # (x0,y0,x1,y1,word, block, line, wordno)
        except Exception:
            words = []
        if words:
            from collections import defaultdict
            by_line: Dict[Tuple[int,int], List[Tuple[float,float,float,float,str]]] = defaultdict(list)
            for w in words:
                if not (isinstance(w, (list, tuple)) and len(w) >= 8):
                    continue
                x0,y0,x1,y1,word,blk,ln,wn = w[:8]
                if not isinstance(word, str):
                    continue
                by_line[(int(blk), int(ln))].append((float(x0), float(y0), float(x1), float(y1), word))
            def token_text(arr, i, j):
                return "".join(arr[k][4] for k in range(i, j+1))
            def token_bbox(arr, i, j):
                xs0 = [arr[k][0] for k in range(i, j+1)]; ys0 = [arr[k][1] for k in range(i, j+1)]
                xs1 = [arr[k][2] for k in range(i, j+1)]; ys1 = [arr[k][3] for k in range(i, j+1)]
                return [min(xs0), min(ys0), max(xs1), max(ys1)]
            table_pat = re.compile(r"^table\.?$", re.IGNORECASE)
            roman_pat = re.compile(rf"^{roman}$", re.IGNORECASE)
            digit_pat = re.compile(r"^\d+$")
            letter_pat = re.compile(r"^[a-z]$", re.IGNORECASE)
            for key, arr in by_line.items():
                arr.sort(key=lambda t: t[0])
                n = len(arr)
                i = 0
                while i < n:
                    # Compose up to 6 tokens to make 'table' (handles 'T a b l e' and punctuation)
                    matched_table = None
                    for j in range(i, min(i+6, n)):
                        text = token_text(arr, i, j)
                        norm = re.sub(r"[^A-Za-z]", "", text).lower()
                        if norm == "table":
                            matched_table = (i, j)
                            break
                    if not matched_table:
                        i += 1
                        continue
                    ti, tj = matched_table
                    # Now parse a number token from following 1-2 tokens: digits or roman, optional letter suffix
                    k = tj + 1
                    if k >= n:
                        i = tj + 1
                        continue
                    # Gather up to 2 tokens for the number
                    num_text = arr[k][4]
                    num_end = k
                    if (k+1) < n and letter_pat.match(arr[k+1][4] or ""):
                        num_text += arr[k+1][4]
                        num_end = k+1
                    norm_num = re.sub(r"[^A-Za-z0-9]", "", num_text)
                    if digit_pat.match(norm_num) or roman_pat.match(norm_num):
                        bbox = token_bbox(arr, ti, num_end)
                        out.append({'type': 'table', 'number': norm_num, 'bbox': bbox, 'text': token_text(arr, ti, num_end)})
                        i = num_end + 1
                        continue
                    # No valid number; advance past 'table'
                    i = tj + 1

    # Deduplicate captions by (type, number), keep topmost occurrence
    dedup: Dict[Tuple[str,str], Dict[str,Any]] = {}
    for c in out:
        key = (c['type'], str(c['number']))
        if key not in dedup or c['bbox'][1] < dedup[key]['bbox'][1]:
            dedup[key] = c
    return list(dedup.values())


def refine_tables_by_caption(page, target_number: Optional[str] = None, include_images: bool = False) -> List[Tuple[float, float, float, float]]:
    """Anchor on 'Table N' caption and tighten to rows beneath it.

    Strategy:
    - Find the first table caption on the page.
    - Define a vertical band below the caption and gather line boxes whose centers fall in it.
    - Filter lines by minimum width; merge into a tight union.
    """
    captions = find_captions(page)
    table_caps = [c for c in captions if c.get('type') == 'table']
    if target_number is not None:
        table_caps = [c for c in table_caps if str(c.get('number')) == str(target_number)]
    if not table_caps:
        return []
    # Choose nearest to top (first table on page)
    cap = sorted(table_caps, key=lambda c: c['bbox'][1])[0]
    cx0, cy0, cx1, cy1 = map(float, cap['bbox'])
    page_w = float(page.rect.width)
    page_h = float(page.rect.height)
    gutter = page_w / 2.0
    cap_cx = (cx0 + cx1) / 2.0
    in_left_col = cap_cx < gutter
    lines = _collect_line_boxes(page)
    # Determine column bounds first
    col_margin = 2.0
    if in_left_col:
        band_left = 0.0
        band_right = max(0.0, gutter - col_margin)
    else:
        band_left = min(page_w, gutter + col_margin)
        band_right = page_w
    # Find a better band top by scanning for table-like content just below the caption
    search_y0 = cy1 + 4.0
    search_y1 = min(page_h, search_y0 + 180.0)
    col_w = max(1.0, band_right - band_left)
    min_row_width = max(60.0, 0.35 * col_w)
    # Row-based candidate top (percentile of wide line tops below caption)
    row_tops: List[float] = []
    for lx0, ly0, lx1, ly1 in lines:
        cx = (lx0 + lx1) / 2.0
        cy = (ly0 + ly1) / 2.0
        if cx < band_left or cx > band_right:
            continue
        if cy <= search_y0 or cy >= search_y1:
            continue
        if (lx1 - lx0) >= min_row_width:
            row_tops.append(ly0)
    row_top = None
    if row_tops:
        row_tops.sort()
        # Use deeper percentile to anchor within table body
        idx = max(0, min(len(row_tops) - 1, int(0.70 * (len(row_tops) - 1))))
        row_top = row_tops[idx] + 2.0
    # Drawing-based candidate top (wide horizontal elements below caption)
    draw_top = None
    try:
        drawings = page.get_drawings()
        min_bar_w = max(80.0, 0.3 * col_w)
        for d in drawings or []:
            rect = None
            if isinstance(d, dict):
                rect = d.get('rect')
            if rect and isinstance(rect, (list, tuple)) and len(rect) == 4:
                dx0, dy0, dx1, dy1 = map(float, rect)
                if dx1 < band_left or dx0 > band_right:
                    continue
                if dy0 <= search_y0 or dy0 >= search_y1:
                    continue
                if (dx1 - dx0) >= min_bar_w:
                    if draw_top is None or dy0 < draw_top:
                        draw_top = dy0 + 2.0
    except Exception:
        pass
    # Choose final band top and set band bottom (initial estimate)
    band_top = min([t for t in [row_top, draw_top] if t is not None], default=search_y0)
    # Enforce a stronger offset from the caption baseline
    band_top = max(band_top, cy1 + 40.0)
    band_bottom = min(page_h, band_top + page_h * 0.60)

    # Cluster wide lines in the full column beneath the caption to find the dominant table block
    candidates: List[Tuple[float, float, float, float]] = []
    for lx0, ly0, lx1, ly1 in lines:
        cx = (lx0 + lx1) / 2.0
        cy = (ly0 + ly1) / 2.0
        if cx < band_left or cx > band_right:
            continue
        if cy <= (cy1 + 4.0):
            continue
        if (lx1 - lx0) >= min_row_width:
            candidates.append((lx0, ly0, lx1, ly1))
    clusters: List[Tuple[float, float, float, float, int]] = []  # x0,y0,x1,y1,count
    if candidates:
        candidates.sort(key=lambda r: (r[1] + r[3]) / 2.0)  # by line center y
        v_gap = 28.0
        cur: List[Tuple[float, float, float, float]] = []
        last_cy = None
        for r in candidates:
            cy_line = (r[1] + r[3]) / 2.0
            if last_cy is None or abs(cy_line - last_cy) <= v_gap:
                cur.append(r)
            else:
                if cur:
                    m = _merge_rects(cur)
                    clusters.append((m[0], m[1], m[2], m[3], len(cur)))
                cur = [r]
            last_cy = cy_line
        if cur:
            m = _merge_rects(cur)
            clusters.append((m[0], m[1], m[2], m[3], len(cur)))
    # Merge adjacent clusters that are close vertically to accumulate full table height
    if clusters:
        clusters.sort(key=lambda cl: cl[1])  # by y0
        merged_clusters: List[Tuple[float,float,float,float,int]] = []
        acc = list(clusters[0])
        for cl in clusters[1:]:
            # if this cluster starts within 40pt of the previous end, merge
            if cl[1] - acc[3] <= 40.0:
                acc = (min(acc[0], cl[0]), min(acc[1], cl[1]), max(acc[2], cl[2]), max(acc[3], cl[3]), acc[4]+cl[4])
            else:
                merged_clusters.append(tuple(acc))
                acc = list(cl)
        merged_clusters.append(tuple(acc))
        # Pick the merged cluster with maximum height (primary) then count (secondary)
        merged_clusters.sort(key=lambda cl: ((cl[3]-cl[1]), cl[4]), reverse=True)
        bx0, by0, bx1, by1, _ = merged_clusters[0]
        # Override band based on this merged cluster with margins; ensure start noticeably below caption
        band_top = max(cy1 + 8.0, by0 - 6.0)
        band_bottom = min(page_h, by1 + 16.0)

    # If images exist below the caption within the column, extend the band bottom to include them
    try:
        raw = page.get_text("rawdict")
        if isinstance(raw, dict):
            for blk in raw.get("blocks", []) or []:
                if blk.get("type") == 1:
                    bb = blk.get("bbox")
                    if isinstance(bb, (list, tuple)) and len(bb) == 4:
                        x0, y0, x1, y1 = map(float, bb)
                        cx = (x0 + x1) / 2.0
                        cyi = (y0 + y1) / 2.0
                        if cx >= band_left and cx <= band_right and cyi >= (cy1 + 4.0):
                            band_bottom = max(band_bottom, min(page_h, y1 + 12.0))
    except Exception:
        pass
    selected: List[Tuple[float, float, float, float]] = []
    for lx0, ly0, lx1, ly1 in lines:
        cx = (lx0 + lx1) / 2.0
        cy = (ly0 + ly1) / 2.0
        # require center inside the vertical band AND significant horizontal overlap with the band
        if band_top <= cy <= band_bottom and not (lx1 < band_left or lx0 > band_right):
            overlap = max(0.0, min(lx1, band_right) - max(lx0, band_left))
            bw = max(1.0, band_right - band_left)
            if overlap >= 0.30 * bw and (lx1 - lx0) >= 40.0:
                selected.append((lx0, ly0, lx1, ly1))
    # Optionally include image (raster) blocks within the band to cover hybrid text+figure tables
    if include_images:
        try:
            img_rects: List[Tuple[float, float, float, float]] = []
            raw = page.get_text("rawdict")
            if isinstance(raw, dict):
                for blk in raw.get("blocks", []) or []:
                    if blk.get("type") == 1:
                        bb = blk.get("bbox")
                        if isinstance(bb, (list, tuple)) and len(bb) == 4:
                            x0, y0, x1, y1 = map(float, bb)
                            cx = (x0 + x1) / 2.0
                            cy = (y0 + y1) / 2.0
                            if band_top <= cy <= band_bottom and not (x1 < band_left or x0 > band_right):
                                img_rects.append((x0, y0, x1, y1))
            selected.extend(img_rects)
        except Exception:
            pass
    # Include vector drawings (lines/rects), which often outline table borders
    try:
        drawings = page.get_drawings()
        for d in drawings or []:
            rect = None
            if isinstance(d, dict):
                rect = d.get('rect')
            if rect and isinstance(rect, (list, tuple)) and len(rect) == 4:
                dx0, dy0, dx1, dy1 = map(float, rect)
                dcx = (dx0 + dx1) / 2.0
                dcy = (dy0 + dy1) / 2.0
                if band_top <= dcy <= band_bottom and not (dx1 < band_left or dx0 > band_right):
                    selected.append((dx0, dy0, dx1, dy1))
    except Exception:
        pass
    merged = _merge_rects(selected)
    if not merged:
        # Fallback: try whole-page horizontal band but keep same-side-of-gutter gating
        selected = []
        fb_left, fb_right = 0.0, page_w
        for lx0, ly0, lx1, ly1 in lines:
            cx = (lx0 + lx1) / 2.0
            cy = (ly0 + ly1) / 2.0
            if band_top <= cy <= band_bottom and not (lx1 < fb_left or lx0 > fb_right):
                # same column as caption
                if in_left_col and cx > gutter:
                    continue
                if (not in_left_col) and cx < gutter:
                    continue
                if (lx1 - lx0) >= 40.0:
                    selected.append((lx0, ly0, lx1, ly1))
        if include_images:
            try:
                raw = page.get_text("rawdict")
                if isinstance(raw, dict):
                    for blk in raw.get("blocks", []) or []:
                        if blk.get("type") == 1:
                            bb = blk.get("bbox")
                            if isinstance(bb, (list, tuple)) and len(bb) == 4:
                                x0, y0, x1, y1 = map(float, bb)
                                cx = (x0 + x1) / 2.0
                                cy = (y0 + y1) / 2.0
                                if band_top <= cy <= band_bottom:
                                    if in_left_col and cx > gutter:
                                        continue
                                    if (not in_left_col) and cx < gutter:
                                        continue
                                    selected.append((x0, y0, x1, y1))
            except Exception:
                pass
        try:
            drawings = page.get_drawings()
            for d in drawings or []:
                rect = None
                if isinstance(d, dict):
                    rect = d.get('rect')
                if rect and isinstance(rect, (list, tuple)) and len(rect) == 4:
                    dx0, dy0, dx1, dy1 = map(float, rect)
                    dcx = (dx0 + dx1) / 2.0
                    dcy = (dy0 + dy1) / 2.0
                    if band_top <= dcy <= band_bottom:
                        if in_left_col and dcx > gutter:
                            continue
                        if (not in_left_col) and dcx < gutter:
                            continue
                        selected.append((dx0, dy0, dx1, dy1))
        except Exception:
            pass
        merged = _merge_rects(selected)
        if not merged:
            return []
    # Clip merged to column band and add small horizontal/vertical safety margins
    mx0, my0, mx1, my1 = merged
    mx0 = max(band_left, mx0 - 6.0)
    mx1 = min(band_right, mx1 + 6.0)
    # Anchor vertically to the cluster-informed band
    my0 = max(band_top, max(my0, band_top))
    my1 = min(band_bottom, max(my1, band_bottom - 2.0))

    # Raster-based envelope expansion to capture full table ink within column band
    try:
        import fitz
        import numpy as np
        # Clip area narrowly around current band to avoid vertical drift
        clip = fitz.Rect(band_left, max(band_top, my0 - 6.0), band_right, min(band_bottom, my1 + 10.0))
        dpi = 150
        scale = float(dpi) / 72.0
        pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), clip=clip, alpha=False)
        arr = np.frombuffer(pix.samples, dtype=np.uint8)
        if arr.size > 0:
            img = arr.reshape(pix.height, pix.width, pix.n)
            gray = (0.299 * img[:,:,0] + 0.587 * img[:,:,1] + 0.114 * img[:,:,2]).astype(np.uint8) if img.shape[2] > 1 else img[:,:,0]
            ink = gray < 242
            if ink.any():
                ys, xs = np.where(ink)
                x0p, x1p = xs.min(), xs.max()
                y0p, y1p = ys.min(), ys.max()
                # Map back to PDF points and intersect with column band (use clip origin)
                ex0 = max(band_left, clip.x0 + (x0p / scale))
                ex1 = min(band_right, clip.x0 + (x1p / scale))
                ey0 = max(band_top, clip.y0 + (y0p / scale))
                ey1 = min(band_bottom, clip.y0 + (y1p / scale))
                mx0, mx1 = ex0, ex1
                my0, my1 = ey0, ey1
    except Exception:
        pass
    # If the box still looks too shallow or too close to the caption, push it downward generically
    min_h = 220.0
    min_y1 = cy1 + 240.0
    if (my1 - my0) < min_h or my1 < min_y1:
        try:
            raw = page.get_text("rawdict")
        except Exception:
            raw = None
        img_sel: List[Tuple[float,float,float,float]] = []
        if isinstance(raw, dict):
            for blk in raw.get("blocks", []) or []:
                if blk.get("type") == 1:
                    bb = blk.get("bbox")
                    if isinstance(bb, (list, tuple)) and len(bb) == 4:
                        x0, y0, x1, y1 = map(float, bb)
                        cx = (x0 + x1) / 2.0
                        if cx >= band_left and cx <= band_right and y1 > (cy1 + 20.0):
                            img_sel.append((x0, y0, x1, y1))
        mimg = _merge_rects(img_sel)
        if mimg:
            mx0 = min(mx0, mimg[0]); mx1 = max(mx1, mimg[2])
            my0 = min(max(band_top, my0), max(band_top, mimg[1] - 8.0))
            my1 = max(my1, min(band_bottom, mimg[3] + 14.0))
        else:
            my0 = max(band_top, cy1 + 24.0)
            my1 = min(band_bottom, max(my1, my0 + min_h))
    # Ensure right edge reaches near the column boundary to avoid truncation
    mx1 = max(mx1, band_right - 4.0)
    # Small vertical safety expansion (horizontal already clipped to column)
    my1 = my1 + 6.0

    # Deep-bottom anchoring: scan the full column beneath caption to find deepest ink row
    try:
        import fitz
        import numpy as np
        clip2 = fitz.Rect(band_left, max(0.0, cy1 + 8.0), band_right, page_h)
        dpi2 = 150
        scale2 = float(dpi2) / 72.0
        pix2 = page.get_pixmap(matrix=fitz.Matrix(scale2, scale2), clip=clip2, alpha=False)
        arr2 = np.frombuffer(pix2.samples, dtype=np.uint8)
        if arr2.size > 0:
            img2 = arr2.reshape(pix2.height, pix2.width, pix2.n)
            gray2 = (0.299 * img2[:,:,0] + 0.587 * img2[:,:,1] + 0.114 * img2[:,:,2]).astype(np.uint8) if img2.shape[2] > 1 else img2[:,:,0]
            ink2 = gray2 < 245  # slightly looser threshold to catch faint gridlines/images
            rows_have = ink2.any(axis=1)
            if rows_have.any():
                deepest_row = int(np.max(np.where(rows_have)))
                deepest_y = clip2.y0 + (deepest_row / scale2)
                # Respect column band bottom but extend if deeper ink suggests table continues
                # Allow full column depth; do not clamp to band_bottom here
                proposed_bottom = min(page_h, deepest_y + 10.0)
                if proposed_bottom > my1:
                    my1 = proposed_bottom
    except Exception:
        pass

    # If still too shallow or too close to caption, enforce a minimum depth-based span
    min_span = 300.0
    min_y1 = cy1 + 360.0
    if (my1 - my0) < min_span or my1 < min_y1:
        # Try to extend using image blocks within the column under the caption
        try:
            raw = page.get_text("rawdict")
        except Exception:
            raw = None
        img_sel: List[Tuple[float,float,float,float]] = []
        if isinstance(raw, dict):
            for blk in raw.get("blocks", []) or []:
                if blk.get("type") == 1:
                    bb = blk.get("bbox")
                    if isinstance(bb, (list, tuple)) and len(bb) == 4:
                        x0, y0, x1, y1 = map(float, bb)
                        cx = (x0 + x1) / 2.0
                        if cx >= band_left and cx <= band_right and y1 > (cy1 + 20.0):
                            img_sel.append((x0, y0, x1, y1))
        mimg = _merge_rects(img_sel)
        if mimg:
            mx0 = min(mx0, mimg[0]); mx1 = max(mx1, mimg[2])
            my0 = max(cy1 + 24.0, min(my0, mimg[1] - 10.0))
            my1 = max(my1, min(page_h, mimg[3] + 16.0))
        # Enforce minimum span beneath caption
        my1 = max(my1, min(page_h, min_y1))
        if (my1 - my0) < min_span:
            my0 = max(cy1 + 24.0, my1 - min_span)

    return [(mx0, my0, mx1, my1)]


def match_docling_tables_to_captions(page, docling_boxes: List[Tuple[float, float, float, float]]) -> List[Dict[str, Any]]:
    """Assign Docling table boxes to detected 'Table N' captions on the page.

    Returns list of { 'table_number': str, 'bbox': [x0,y0,x1,y1] }.
    Selects at most one Docling box per caption by maximum overlap with a
    caption-anchored vertical band; if no overlap, uses nearest box below caption.
    """
    results: List[Dict[str, Any]] = []
    if not docling_boxes:
        return results

    caps = find_captions(page)
    table_caps = [c for c in caps if c.get('type') == 'table']
    if not table_caps:
        return results

    used = set()

    def area(r):
        return max(0.0, (r[2]-r[0])) * max(0.0, (r[3]-r[1]))

    def inter(a, b):
        x0 = max(a[0], b[0]); y0 = max(a[1], b[1])
        x1 = min(a[2], b[2]); y1 = min(a[3], b[3])
        if x1 <= x0 or y1 <= y0:
            return 0.0
        return (x1-x0)*(y1-y0)

    for cap in sorted(table_caps, key=lambda c: c['bbox'][1]):
        num = cap.get('number')
        cx0, cy0, cx1, cy1 = map(float, cap['bbox'])
        # Build a band below caption; expand horizontally to page width
        band_top = cy1 + 4.0
        band_bottom = min(float(page.rect.height), band_top + float(page.rect.height) * 0.6)
        band = (0.0, band_top, float(page.rect.width), band_bottom)

        # Score docling boxes by overlap with band; prefer unused boxes
        scored = []
        for idx, b in enumerate(docling_boxes):
            if idx in used:
                continue
            ov = inter(band, b)
            if ov > 0:
                scored.append((ov, idx, b))
        if scored:
            scored.sort(key=lambda t: (-t[0], t[1]))
            _, idx, b = scored[0]
            used.add(idx)
            results.append({'table_number': str(num), 'bbox': [b[0], b[1], b[2], b[3]]})
            continue
        # Fallback: choose the unused docling box whose top is nearest below caption
        nearest = None
        nearest_dy = None
        for idx, b in enumerate(docling_boxes):
            if idx in used:
                continue
            dy = (b[1] - cy1)  # distance from caption bottom to box top
            if dy >= -10.0:  # allow tiny overlap
                if nearest is None or dy < nearest_dy:
                    nearest = (idx, b)
                    nearest_dy = dy
        if nearest:
            idx, b = nearest
            used.add(idx)
            results.append({'table_number': str(num), 'bbox': [b[0], b[1], b[2], b[3]]})

    return results



def load_gt_tables_by_page(gt_path: Path) -> Dict[int, List[Tuple[float, float, float, float]]]:
    out: Dict[int, List[Tuple[float, float, float, float]]] = {}
    if not gt_path.exists():
        return out
    with gt_path.open('r', encoding='utf-8') as f:
        data = json.load(f)
    for t in data.get('tables', []) or []:
        page_no = t.get('page')
        bbox = t.get('bbox') or {}
        if isinstance(page_no, int) and all(k in bbox for k in ('x1', 'y1', 'x2', 'y2')):
            out.setdefault(page_no, []).append((bbox['x1'], bbox['y1'], bbox['x2'], bbox['y2']))
    return out
