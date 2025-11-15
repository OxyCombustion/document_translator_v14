#!/usr/bin/env python3
from __future__ import annotations

"""
GridOverlayAgent

Draws a light, thin grid on an image for pixel reference.
Usage: GridOverlayAgent().draw(img, spacing=100, major_every=5, color=(200,200,200), thickness=1, label=False)
"""

from dataclasses import dataclass
from typing import Tuple

import cv2


@dataclass
class GridConfig:
    spacing: int = 100
    major_every: int = 5
    color: Tuple[int, int, int] = (200, 200, 200)
    thickness: int = 1
    label: bool = False


class GridOverlayAgent:
    def __init__(self, config: GridConfig | None = None) -> None:
        self.cfg = config or GridConfig()

    def draw(self, img, spacing: int | None = None, major_every: int | None = None, color=None, thickness: int | None = None, label: bool | None = None):
        cfg = self.cfg
        spacing = int(spacing if spacing is not None else cfg.spacing)
        major_every = int(major_every if major_every is not None else cfg.major_every)
        color = tuple(color if color is not None else cfg.color)
        thickness = int(thickness if thickness is not None else cfg.thickness)
        label = bool(cfg.label if label is None else label)

        h, w = img.shape[:2]
        # Minor grid
        for x in range(0, w, spacing):
            cv2.line(img, (x, 0), (x, h - 1), color, thickness)
        for y in range(0, h, spacing):
            cv2.line(img, (0, y), (w - 1, y), color, thickness)

        # Major grid (every N minors)
        if major_every > 1:
            major_color = (max(0, color[0]-30), max(0, color[1]-30), max(0, color[2]-30))
            step = spacing * major_every
            for x in range(0, w, step):
                cv2.line(img, (x, 0), (x, h - 1), major_color, thickness)
            for y in range(0, h, step):
                cv2.line(img, (0, y), (w - 1, y), major_color, thickness)

        # Optional labels along top and left at major intervals
        if label:
            try:
                font = cv2.FONT_HERSHEY_SIMPLEX
                fscale = 0.4
                thick = 1
                step = spacing * max(1, major_every)
                for x in range(0, w, step):
                    cv2.putText(img, str(x), (x+2, 14), font, fscale, color, thick, cv2.LINE_AA)
                for y in range(0, h, step):
                    cv2.putText(img, str(y), (2, y+14), font, fscale, color, thick, cv2.LINE_AA)
            except Exception:
                pass

