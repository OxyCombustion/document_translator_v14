#!/usr/bin/env python3
"""
Equation Zone Refiner (Agent)

Purpose
- Given equation number labels and a coarse region (left-of-number),
  derive a tight bounding box for the actual equation by intersecting
  page text blocks with the coarse region, merging, and padding.

Inputs
- PyMuPDF page (fitz.Page)
- eq_number_labels: list of { 'number': int, 'bbox': [x0,y0,x1,y1] } in PDF points
- coarse_region_func: callable(label_bbox, page_rect) -> (x0,y0,x1,y1) (PDF points)
- params: dict with keys { 'min_overlap': float, 'pad': float }

Outputs
- Dict[number] = { 'tight_bbox': [x0,y0,x1,y1], 'method': 'text-union', 'confidence': float }
"""

from __future__ import annotations

from typing import Dict, List, Tuple, Any
import re
from .equation_refinement_agent import EquationRefinementAgent, EquationRefineOptions


def _collect_line_boxes(page) -> List[Dict[str, Any]]:
    """Collect line-level boxes by unioning span boxes per line.
    Returns list of {'bbox':[x0,y0,x1,y1], 'text':str, 'cy':float, 'h':float}.
    """
    lines: List[Dict[str, Any]] = []
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
            texts = []
            for sp in line.get("spans", []) or []:
                tb = sp.get("bbox")
                t = sp.get("text")
                if not (isinstance(tb, (list, tuple)) and len(tb) == 4):
                    continue
                sx0, sy0, sx1, sy1 = map(float, tb)
                if sx1 - sx0 <= 0.5 or sy1 - sy0 <= 0.5:
                    continue
                x0 = min(x0, sx0)
                y0 = min(y0, sy0)
                x1 = max(x1, sx1)
                y1 = max(y1, sy1)
                if isinstance(t, str) and t:
                    texts.append(t)
            if x1 > x0 and y1 > y0:
                cy = (y0 + y1) / 2.0
                h = (y1 - y0)
                text = "".join(texts)
                lines.append({
                    'bbox': [x0, y0, x1, y1],
                    'text': text,
                    'cy': cy,
                    'h': h,
                })
    return lines


def _rect_intersection(a, b) -> float:
    ax0, ay0, ax1, ay1 = a
    bx0, by0, bx1, by1 = b
    ix0 = max(ax0, bx0)
    iy0 = max(ay0, by0)
    ix1 = min(ax1, bx1)
    iy1 = min(ay1, by1)
    if ix1 <= ix0 or iy1 <= iy0:
        return 0.0
    return (ix1 - ix0) * (iy1 - iy0)


def _rect_intersection_rect(a, b):
    ax0, ay0, ax1, ay1 = a
    bx0, by0, bx1, by1 = b
    ix0 = max(ax0, bx0)
    iy0 = max(ay0, by0)
    ix1 = min(ax1, bx1)
    iy1 = min(ay1, by1)
    if ix1 <= ix0 or iy1 <= iy0:
        return None
    return (ix0, iy0, ix1, iy1)


def _rect_area(r) -> float:
    x0, y0, x1, y1 = r
    return max(0.0, (x1 - x0)) * max(0.0, (y1 - y0))


def _merge_rects(rects: List[Tuple[float, float, float, float]]) -> Tuple[float, float, float, float] | None:
    if not rects:
        return None
    x0 = min(r[0] for r in rects)
    y0 = min(r[1] for r in rects)
    x1 = max(r[2] for r in rects)
    y1 = max(r[3] for r in rects)
    return (x0, y0, x1, y1)


def _is_mathy(text: str) -> bool:
    if not text:
        return False
    math_tokens = ['=', '/', '\\', '^', '_', '∑', '∫', '√', '·', '×', '−', '+', '÷']
    if any(tok in text for tok in math_tokens):
        return True
    return False


def default_coarse_region(label_bbox, page_rect, width: float = 400.0, pad: float = 50.0) -> Tuple[float, float, float, float]:
    x0, y0, x1, y1 = label_bbox
    cx = (x0 + x1) / 2.0
    cy = (y0 + y1) / 2.0
    rx0 = max(0.0, cx - width)
    ry0 = max(0.0, cy - (pad + 10.0))
    rx1 = min(page_rect.width, cx + 50.0)
    ry1 = min(page_rect.height, cy + (pad + 10.0))
    return (rx0, ry0, rx1, ry1)


def refine_equation_regions(page, eq_number_labels: List[Dict[str, Any]], params: Dict[str, Any] | None = None) -> Dict[Any, Dict[str, Any]]:
    # Delegate to the agent for main logic; keep legacy helpers available for future use
    opts = EquationRefineOptions()
    if params:
        if 'pad' in params:
            opts.pad = float(params['pad'])
        if 'left_width' in params:
            opts.left_width = float(params['left_width'])
        if 'env_height_ratio' in params:
            opts.env_height_ratio = float(params['env_height_ratio'])
    debug_out_dir = None
    if params and params.get('debug_out_dir'):
        debug_out_dir = params.get('debug_out_dir')
    agent = EquationRefinementAgent(opts)
    results = agent.refine_from_labels(page, eq_number_labels, debug_out_dir=debug_out_dir)
    return results


# === Lettered label detection utilities (unanchored to GT) ===
def _find_lettered_tokens_from_raw(page) -> List[Tuple[str, Tuple[float, float, float, float]]]:
        # Supports (79a) and (79 a) variants
        patt1 = re.compile(r"\((\d{1,3}[a-z])\)")
        patt2 = re.compile(r"\((\d{1,3})\s*([a-z])\)")
        out: List[Tuple[str, Tuple[float, float, float, float]]] = []
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
                # Gather spans and text
                span_boxes = []
                line_text = ""
                for sp in line.get("spans", []) or []:
                    t = sp.get("text") or ""
                    bb = sp.get("bbox")
                    if isinstance(bb, (list, tuple)) and len(bb) == 4:
                        span_boxes.append((t, tuple(map(float, bb))))
                    line_text += t
                # Quick check first
                if not (patt1.search(line_text) or patt2.search(line_text)):
                    continue
                # Try to match at span granularity; else fall back to line box
                for t, bb in span_boxes:
                    m1 = patt1.search(t)
                    if m1:
                        out.append((m1.group(1), (bb[0], bb[1], bb[2], bb[3])))
                        continue
                    m2 = patt2.search(t)
                    if m2:
                        token = f"{m2.group(1)}{m2.group(2)}"
                        out.append((token, (bb[0], bb[1], bb[2], bb[3])))
                # If none matched at span level, use the line bbox as approximate box
                if not (any(patt1.search(t) for t, _ in span_boxes) or any(patt2.search(t) for t, _ in span_boxes)):
                    # compute line bbox
                    lx0 = min(s[1][0] for s in span_boxes) if span_boxes else None
                    ly0 = min(s[1][1] for s in span_boxes) if span_boxes else None
                    lx1 = max(s[1][2] for s in span_boxes) if span_boxes else None
                    ly1 = max(s[1][3] for s in span_boxes) if span_boxes else None
                    if lx0 is not None:
                        for m1 in patt1.finditer(line_text):
                            out.append((m1.group(1), (lx0, ly0, lx1, ly1)))
                        for m2 in patt2.finditer(line_text):
                            token = f"{m2.group(1)}{m2.group(2)}"
                            out.append((token, (lx0, ly0, lx1, ly1)))
        return out


def _find_lettered_tokens_structural(page) -> List[Tuple[str, Tuple[float, float, float, float]]]:
        """Detect lettered tokens by walking spans structurally: '(', digits, optional space, letter, ')'.
        Returns list of (token, bbox) where token is like '79a'.
        """
        out: List[Tuple[str, Tuple[float, float, float, float]]] = []
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
                toks: List[Tuple[str, Tuple[float, float, float, float]]] = []
                for sp in spans:
                    t = sp.get("text") or ""
                    bb = sp.get("bbox")
                    if isinstance(bb, (list, tuple)) and len(bb) == 4:
                        toks.append((t, (float(bb[0]), float(bb[1]), float(bb[2]), float(bb[3]))))
                if not toks:
                    continue
                i = 0
                while i < len(toks):
                    t0 = toks[i][0]
                    if "(" not in t0:
                        i += 1; continue
                    j = i
                    seen_lparen = False
                    digits = ""
                    letter = ""
                    bbs: List[Tuple[float,float,float,float]] = []
                    broke = False
                    while j < len(toks) and (not broke):
                        tj, bbj = toks[j]
                        for ch in tj:
                            if not seen_lparen:
                                if ch == "(":
                                    seen_lparen = True
                                    bbs.append(bbj)
                                continue
                            else:
                                if ch.isdigit() and letter == "":
                                    digits += ch
                                    bbs.append(bbj)
                                elif ch.isspace() and digits and letter == "":
                                    bbs.append(bbj)
                                elif ch.isalpha() and digits and letter == "":
                                    letter = ch.lower()
                                    bbs.append(bbj)
                                elif ch == ")" and digits and letter:
                                    bbs.append(bbj)
                                    x0 = min(b[0] for b in bbs); y0 = min(b[1] for b in bbs)
                                    x1 = max(b[2] for b in bbs); y1 = max(b[3] for b in bbs)
                                    out.append((f"{digits}{letter}", (x0,y0,x1,y1)))
                                    broke = True
                                    break
                                else:
                                    # ignore other chars
                                    pass
                        j += 1
                    i = j if j > i else i + 1
        return out


def _find_lettered_tokens_words(page) -> List[Tuple[str, Tuple[float, float, float, float]]]:
        """Detect lettered tokens by scanning word tuples and composing nearby words.
        Looks for patterns: (79a), (79 a), with/without spaces split across words.
        """
        out: List[Tuple[str, Tuple[float, float, float, float]]] = []
        try:
            words = page.get_text("words")  # list of (x0,y0,x1,y1,word, block, line, wordno)
        except Exception:
            words = []
        if not words:
            return out
        # group by (block,line)
        from collections import defaultdict
        by_line: Dict[Tuple[int, int], List[Tuple[float,float,float,float,str]]] = defaultdict(list)
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
            arr.sort(key=lambda t: t[0])  # by x0
            n = len(arr)
            for i in range(n):
                x0,y0,x1,y1,w0 = arr[i]
                # Case 1: single word contains full token
                m1 = patt1.match(w0)
                if m1:
                    out.append((m1.group(1), (x0,y0,x1,y1)))
                    continue
                m2 = patt2.match(w0)
                if m2:
                    tok = f"{m2.group(1)}{m2.group(2)}"
                    out.append((tok, (x0,y0,x1,y1)))
                    continue
                # Case 2: compose up to 5 contiguous words (handles '( 79 a )', '(79 a )', etc.)
                max_run = min(i+5, n)
                comp2 = w0
                bx0,by0,bx1,by1 = x0,y0,x1,y1
                for k in range(i+1, max_run):
                    tx0,ty0,tx1,ty1,tw = arr[k]
                    comp2 += tw
                    bx0 = min(bx0, tx0); by0 = min(by0, ty0)
                    bx1 = max(bx1, tx1); by1 = max(by1, ty1)
                    m1c = patt1.match(comp2)
                    if m1c:
                        out.append((m1c.group(1), (bx0,by0,bx1,by1)))
                        break
                    m2c = patt2.match(comp2)
                    if m2c:
                        tok = f"{m2c.group(1)}{m2c.group(2)}"
                        out.append((tok, (bx0,by0,bx1,by1)))
                        break
        return out


def find_lettered_labels(page, targets: List[str] | None = None) -> List[Dict[str, Any]]:
    """Aggregate lettered label detectors and return list of {'id': '79a', 'bbox': [x0,y0,x1,y1]}.

    - targets: optional whitelist like ['79a','79b'] in lower-case without parentheses.
    """
    out: List[Dict[str, Any]] = []
    seen = set()
    def _add(tok: str, bb: Tuple[float,float,float,float]):
        tid = tok.lower().strip()
        if tid.startswith('(') and tid.endswith(')'):
            tid = tid[1:-1]
        if targets and tid not in targets:
            return
        key = (tid, tuple(round(v,2) for v in bb))
        if key in seen:
            return
        seen.add(key)
        out.append({'id': tid, 'bbox': [float(bb[0]), float(bb[1]), float(bb[2]), float(bb[3])]})

    # First, use textpage.search for exact token hits (most precise bbox)
    try:
        tp = page.get_textpage()
        lookups = []
        if targets:
            lookups = [f"({t})" for t in targets]
        else:
            lookups = []
        # Search common variants with optional spaces
        var_map: List[Tuple[str, str]] = []
        for tok in (lookups or []):
            # e.g., '(79b)' -> also '(79 b)'
            if len(tok) >= 5 and tok.startswith('(') and tok.endswith(')'):
                digits = tok[1:-2]
                letter = tok[-2]
                var_map.append((tok, tok))
                var_map.append((tok, f"({digits} {letter})"))
        for orig, patt in (var_map or []):
            try:
                for inst in tp.search(patt, quads=True):
                    rect = inst.rect if hasattr(inst, 'rect') else fitz.Rect(inst)
                    _add(orig.strip('()'), (rect.x0, rect.y0, rect.x1, rect.y1))
            except Exception:
                continue
    except Exception:
        pass

    # Then, use raw, structural, and words detectors
    try:
        for tok, bb in _find_lettered_tokens_from_raw(page):
            _add(tok, bb)
    except Exception:
        pass
    try:
        for tok, bb in _find_lettered_tokens_structural(page):
            _add(tok, bb)
    except Exception:
        pass
    try:
        for tok, bb in _find_lettered_tokens_words(page):
            _add(tok, bb)
    except Exception:
        pass
    # Consolidate duplicates by choosing the RIGHTMOST occurrence per id (closest to right margin)
    best: Dict[str, Dict[str, Any]] = {}
    for item in out:
        tid = item['id']
        bb = item['bbox']
        x0 = float(bb[0])
        if tid not in best or x0 > float(best[tid]['bbox'][0]):
            best[tid] = item
    return list(best.values())

    def _compute_tight_for_label(label_bbox: Tuple[float, float, float, float]) -> Tuple[Tuple[float, float, float, float], float, str]:
        # Core logic extracted to reuse for lettered labels
        bx0, by0, bx1, by1 = map(float, label_bbox)
        # Use the NUMBER'S LEFT EDGE as the clamp reference; equations must end just left of it
        x0N = min(bx0, bx1)
        y0N = min(by0, by1)
        x1N = max(bx0, bx1)
        y1N = max(by0, by1)
        left_width = 500.0
        eps = 5.0
        cyN = (y0N + y1N) / 2.0
        hN = (y1N - y0N)
        coarse = (max(0.0, x0N - left_width), max(0.0, cyN - (hN * 1.5)), max(0.0, x0N - eps), min(page_rect.height, cyN + (hN * 1.5)))
        coarse_area = _rect_area(coarse)

        # Candidate filter
        candidates: List[Dict[str, Any]] = []
        for ln in lines:
            bx0, by0, bx1, by1 = ln['bbox']
            if bx1 > (x0N - eps):
                continue
            cyB = ln['cy']
            hB = ln['h']
            tol = max(8.0, 0.6 * max(hN, hB))
            if not (abs(cyB - cyN) <= tol or (by0 <= cyN <= by1)):
                continue
            if bx0 < (x0N - left_width - 50.0):
                continue
            right_gap = (x0N - eps) - bx1
            area = max(0.0, (bx1 - bx0)) * max(0.0, (by1 - by0))
            width = (bx1 - bx0)
            text = ln.get('text') or ''
            if not _is_mathy(text):
                continue
            if width < 60.0:
                continue
            candidates.append({'bbox': [bx0, by0, bx1, by1], 'right_gap': right_gap, 'h': hB, 'area': area, 'text': text})

        if candidates:
            # Prefer lines with explicit '=' when available (often the main equation line)
            for c in candidates:
                txt = (c.get('text') or '')
                c['has_eq'] = ('=' in txt)
            candidates.sort(key=lambda d: (0 if d['has_eq'] else 1, abs(d['right_gap']), -d['area']))
            best = candidates[0]
            bx0, by0, bx1, by1 = best['bbox']
            union_rects = [(bx0, by0, bx1, by1)]
            # thresholds for inclusion
            max_vert_delta = max(12.0, 1.6 * best['h'])
            max_right_gap = max(14.0, abs(best['right_gap']) + 8.0)
            # First pass: pick lines near the number center alignment
            for cand in candidates[1:]:
                cx0, cy0, cx1, cy1 = cand['bbox']
                if abs(cand['right_gap']) <= max_right_gap and abs(((cy0 + cy1) / 2.0) - cyN) <= (max_vert_delta * 1.6):
                    union_rects.append((cx0, cy0, cx1, cy1))
            # Multiline expansion: include adjacent mathy lines vertically contiguous within band up to right boundary
            expanded_changed = True
            while expanded_changed:
                expanded_changed = False
                merged_tmp = _merge_rects(union_rects)
                if not merged_tmp:
                    break
                ux0, uy0, ux1, uy1 = merged_tmp
                # Limit right boundary by number
                ux1 = min(ux1, x0N - eps)
                v_gap = max(14.0, 1.8 * best['h'])
                for cand in candidates:
                    cx0, cy0, cx1, cy1 = cand['bbox']
                    # Horizontal overlap with current band
                    if cx1 < (ux0 - 14.0) or cx0 > (ux1 + 14.0):
                        continue
                    # Vertical contiguity to current merged box
                    if (cy1 < (uy0 - v_gap)) or (cy0 > (uy1 + v_gap)):
                        continue
                    # Reasonable right edge alignment
                    if abs(cand['right_gap']) > (max_right_gap * 2.0):
                        continue
                    # Prefer mathy or '=' lines when expanding
                    if not _is_mathy(cand.get('text') or '') and '=' not in (cand.get('text') or ''):
                        continue
                    rect = (cx0, cy0, cx1, cy1)
                    if rect not in union_rects:
                        union_rects.append(rect)
                        expanded_changed = True
            # If still small and we have a nearby wide fraction/continuation line above-left, include it
            # Heuristic: look for lines within 1.2*v_gap above with width > 0.6*band_width
            merged_now = _merge_rects(union_rects)
            if merged_now:
                bw = merged_now[2] - merged_now[0]
                for ln in lines:
                    (lx0, ly0, lx1, ly1) = ln['bbox']
                    if lx1 > (x0N - eps):
                        continue
                    if ly1 < (merged_now[1] - v_gap*1.2) or ly0 > (merged_now[3] + v_gap*1.2):
                        continue
                    if (lx1 - lx0) >= (0.6 * bw):
                        if ln not in union_rects:
                            union_rects.append((lx0, ly0, lx1, ly1))
            merged = _merge_rects(union_rects)
            # Band-fill safeguard: expand to envelope of math-like lines inside corridor if too short
            if merged:
                ux0, uy0, ux1, uy1 = merged
                # Compute relaxed math envelope within corridor [x0N-left_width, x0N-eps]
                env_y0 = uy0
                env_y1 = uy1
                count_env = 0
                for ln in lines:
                    lx0, ly0, lx1, ly1 = ln['bbox']
                    txt = ln.get('text') or ''
                    if lx1 > (x0N - eps):
                        continue
                    if lx0 < (x0N - left_width - 50.0):
                        continue
                    # Must be math-like or contain '='
                    if not _is_mathy(txt) and '=' not in txt:
                        continue
                    # Horizontal overlap with corridor band where current union resides
                    if lx1 < (ux0 - 14.0) or lx0 > (x0N - eps + 14.0):
                        continue
                    env_y0 = min(env_y0, ly0)
                    env_y1 = max(env_y1, ly1)
                    count_env += 1
                if count_env >= 2:
                    current_h = max(1.0, (uy1 - uy0))
                    env_h = max(1.0, (env_y1 - env_y0))
                    if current_h < (0.85 * env_h):
                        # Expand vertically to envelope (clip later)
                        merged = (ux0, env_y0, ux1, env_y1)
            clip = _rect_intersection_rect(merged, coarse) if merged else None
            tight_rect = clip or merged or coarse
            x0, y0, x1, y1 = tight_rect
            x0 = max(0.0, x0 - pad)
            y0 = max(0.0, y0 - pad)
            # Clamp right to just left of number; if the union's right edge is far from the number, snap it to the number
            cand_x1 = min(page_rect.width, min(x1 + pad, x0N - eps))
            snap_margin_pt = 80.0  # if more than ~80pt away (≈1.6 grid at 150dpi), snap
            snap_eps = 1.5
            if (x0N - cand_x1) > snap_margin_pt:
                x1 = max(x0 + 1.0, x0N - snap_eps)
            else:
                x1 = cand_x1
            y1 = min(page_rect.height, y1 + pad)
            conf = min(1.0, (_rect_area(_merge_rects(union_rects) or tight_rect) / max(1.0, coarse_area)))
            return (x0, y0, x1, y1), conf, 'multiline-union'
        else:
            x0 = max(0.0, x0N - 300.0)
            x1 = max(0.0, x0N - eps)
            y0 = max(0.0, cyN - (hN * 0.8))
            y1 = min(page_rect.height, cyN + (hN * 0.8))
            return (x0, y0, x1, y1), 0.2, 'text-union'

    # Legacy lettered detection helpers are retained above (unused now) to document prior implementations.
