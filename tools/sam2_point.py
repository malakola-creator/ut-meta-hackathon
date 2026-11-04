"""SAM 2.1 from one point (class-agnostic): the fallback when no word the body knows lets SAM 3.1 find the thing.

    ~/miniforge3/envs/comfy24/bin/python tools/sam2_point.py IN.png X Y OUT.npy [--model facebook/sam2.1-hiera-tiny]
Writes the mask (bool, h x w). Runs where torch + transformers are (comfy24 here); utmeta/look.py calls it as a subprocess.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import numpy as np
from PIL import Image

from utmeta.eye import Sam

ap = argparse.ArgumentParser()
ap.add_argument("png")
ap.add_argument("x", type=int)
ap.add_argument("y", type=int)
ap.add_argument("out")
ap.add_argument("--model", default="facebook/sam2.1-hiera-tiny")
a = ap.parse_args()
mask, ms = Sam(a.model).segment_point(np.asarray(Image.open(a.png).convert("RGB")), a.x, a.y)
np.save(a.out, mask)
print("%d px, %.0f ms" % (int(mask.sum()), ms))
