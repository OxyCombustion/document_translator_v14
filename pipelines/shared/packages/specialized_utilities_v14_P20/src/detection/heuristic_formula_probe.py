#!/usr/bin/env python3
from __future__ import annotations

from typing import Any, Dict, List, Tuple


class HeuristicFormulaProbe:
    def __init__(self) -> None:
        pass

    @staticmethod
    def _is_mathy(text: str) -> bool:
        if not text:
            return False
        ascii_tokens = ['=', '/', '\\', '^', '_', '+', '-', '*']
        if any(tok in text for tok in ascii_tokens):
            return True
        unicode_tokens = ['×', '÷', '±', '≤', '≥', '≠', '≈', '≡', '∝', '√', '∞', '∫', '∮', '∬', '∂', '∇', '∑', '∏', '∧', '∨', '⊕', '⊗', '→', '←', '↔', '⋯', '…', '•', '·', '°']
        if any(tok in text for tok in unicode_tokens):
            return True
        greek = 'αβγδεζηθικλμνξοπρστυφχψω' + 'ΑΒΓΔΕΖΗΘΙΚΛΜΝΞΟΠΡΣΤΥΦΧΨΩ'
        if any(ch in text for ch in greek):
            return True
        return False

    def detect(self, page) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        try:
            raw = page.get_text("rawdict")
        except Exception:
            raw = None
        if not isinstance(raw, dict):
            return results
        lines: List[Tuple[float,float,float,float,str]] = []
        for blk in raw.get('blocks', []) or []:
            if blk.get('type') != 0:
                continue
            for line in blk.get('lines', []) or []:
                x0=y0=float('inf'); x1=y1=float('-inf'); text=""
                for sp in line.get('spans', []) or []:
                    bb=sp.get('bbox'); t=sp.get('text') or ''
                    if isinstance(bb,(list,tuple)) and len(bb)==4:
                        sx0,sy0,sx1,sy1 = map(float, bb)
                        x0=min(x0,sx0); y0=min(y0,sy0); x1=max(x1,sx1); y1=max(y1,sy1)
                        text += t
                if x1>x0 and y1>y0:
                    lines.append((x0,y0,x1,y1,text))
        # simple grouping: select mathy lines and merge vertically contiguous ones
        math_lines = [(x0,y0,x1,y1) for (x0,y0,x1,y1,t) in lines if self._is_mathy(t)]
        math_lines.sort(key=lambda r: (r[1], r[0]))
        def merge_rects(rects):
            if not rects:
                return []
            rects = sorted(rects, key=lambda r: (r[1], r[0]))
            merged=[rects[0]]
            for r in rects[1:]:
                x0,y0,x1,y1=r; X0,Y0,X1,Y1=merged[-1]
                # vertical overlap or close proximity
                if not (y0>Y1+6 or y1<Y0-6):
                    merged[-1]=(min(X0,x0), min(Y0,y0), max(X1,x1), max(Y1,y1))
                else:
                    merged.append(r)
            return merged
        boxes = merge_rects(math_lines)
        for b in boxes:
            results.append({'bbox':[b[0],b[1],b[2],b[3]], 'score':1.0})
        return results

