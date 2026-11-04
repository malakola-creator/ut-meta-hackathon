"""SAM's cut-out vs the renderer's ground truth on a scene from render_eye.py.

Runs in an env with torch + transformers (comfy24 here):
    ~/miniforge3/envs/comfy24/bin/python tools/eye_compare.py data/eye/scene.npz
One click at the middle of the true mask (the eye already knows roughly where the thing is), then IoU, the time, and an overlay PNG
(red = SAM, green = renderer, yellow = both).
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import numpy as np
from PIL import Image

from utmeta import config
from utmeta.eye import Sam, iou

ap = argparse.ArgumentParser()
ap.add_argument("scene")
ap.add_argument("--model", default=None)
a = ap.parse_args()
cfg = config.load()
d = np.load(a.scene)
rgb, truth = d["rgb"], d["mask"]
ys, xs = np.nonzero(truth)
if not len(xs):
    sys.exit("the thing is not in view")
px, py = int(np.median(xs)), int(np.median(ys))
sam = Sam(a.model or cfg["eye"]["model"])
pred, ms = sam.segment_point(rgb, px, py)
print("%s  click (%d,%d)  SAM %d px  renderer %d px  IoU %.2f  %.0f ms (CPU)" % (sam.name, px, py, int(pred.sum()), int(truth.sum()), iou(pred, truth), ms))
over = (rgb * 0.5).astype(np.uint8)
over[pred & ~truth] = (255, 0, 0)
over[truth & ~pred] = (0, 255, 0)
over[pred & truth] = (255, 255, 0)
Image.fromarray(over).save(os.path.splitext(a.scene)[0] + "_sam.png")
