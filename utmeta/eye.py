"""The eye's cut-out from real pixels: SAM instead of the simulator's per-pixel ground truth.

ultimateTruth's recognizer crops each thing by the renderer's root-body id per pixel — something a real camera never gives. Here SAM
segments the same picture from one point on the thing (SAM 2.1 now; SAM 3.1, which also takes a word such as "person", once the
access request is approved). ``iou`` compares the two, which is the honest number for the demo.
Needs torch + transformers (the comfy24 env on this machine); the render itself is tools/render_eye.py in the core's env.
"""
from __future__ import annotations

import time
from typing import Any, Tuple


def iou(a: Any, b: Any) -> float:
    import numpy as np
    a, b = np.asarray(a, bool), np.asarray(b, bool)
    union = int((a | b).sum())
    return float((a & b).sum()) / union if union else 0.0


class Sam:
    def __init__(self, name: str) -> None:
        if "sam3" in name:
            raise NotImplementedError("SAM 3.x is not wired yet: needs approved access to %s on Hugging Face (docs/plan.md, day 2)" % name)
        from transformers import Sam2Model, Sam2Processor
        self.name = name
        self.proc = Sam2Processor.from_pretrained(name)
        self.model = Sam2Model.from_pretrained(name).eval()

    def segment_point(self, rgb: Any, x: int, y: int) -> Tuple[Any, float]:
        """The mask of the thing under pixel (x, y), and the milliseconds the model took."""
        import torch
        from PIL import Image
        img = Image.fromarray(rgb)
        inp = self.proc(images=img, input_points=[[[[int(x), int(y)]]]], input_labels=[[[1]]], return_tensors="pt")
        with torch.no_grad():
            t = time.perf_counter()
            out = self.model(**inp, multimask_output=False)
            ms = (time.perf_counter() - t) * 1000.0
        masks = self.proc.post_process_masks(out.pred_masks, inp["original_sizes"])[0]
        return masks[0, 0].numpy() > 0, ms
