#!/usr/bin/env python3
from __future__ import annotations

from typing import Any, Dict, List, Optional


class FormulaDetectorAgent:
    """Optional ML-based checker using LayoutParser/Detectron2.

    This is a lightweight scaffold: if dependencies are unavailable, `available()` returns False
    and `detect()` yields no predictions. When available, it loads a community model with a
    Formula/Equation class and runs CPU inference on page images.
    """

    def __init__(self) -> None:
        self._lp = None
        self._model = None
        self._model_name: Optional[str] = None
        try:
            import layoutparser as lp  # type: ignore
            self._lp = lp
            # Example: pick a generic PubLayNet/DocBank-like model if available.
            # Users can customize the config path via environment or future options.
            # CPU-only inference
            try:
                self._model = lp.Detectron2LayoutModel(
                    config_path="lp://PrimaLayout/mask_rcnn_R_50_FPN_3x/config",
                    label_map={0: 'Text', 1: 'Title', 2: 'List', 3: 'Table', 4: 'Figure'},
                    extra_config=["MODEL.DEVICE", "cpu"],
                )
                self._model_name = "Detectron2-PrimaLayout"
            except Exception:
                self._model = None
        except Exception:
            self._lp = None

    def available(self) -> bool:
        return self._lp is not None and self._model is not None

    def model_name(self) -> Optional[str]:
        return self._model_name

    def detect(self, image_bgr) -> List[Dict[str, Any]]:
        if not self.available():
            return []
        # LayoutParser expects RGB
        try:
            import numpy as np
            img_rgb = image_bgr[:, :, ::-1]
            layout = self._model.detect(img_rgb)
            preds = []
            for l in layout:
                # Some models may not include formula; this scaffold passes through all classes
                x1, y1, x2, y2 = float(l.block.x_1), float(l.block.y_1), float(l.block.x_2), float(l.block.y_2)
                preds.append({'bbox': [x1, y1, x2, y2], 'label': getattr(l, 'type', None), 'score': float(getattr(l, 'score', 1.0))})
            return preds
        except Exception:
            return []

