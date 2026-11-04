"""Render what vhum's eye sees with mehum standing ahead, and the renderer's ground-truth mask of mehum.

Runs in the core's env (MuJoCo + ultimateTruth):
    MUJOCO_GL=egl ~/miniforge3/envs/ut/bin/python tools/render_eye.py data/eye/scene.npz [--dist 2.5]
Writes rgb (H, W, 3) uint8, mask (H, W) bool and the dist to the npz, plus a PNG beside it.
"""
import argparse
import copy
import math
import os
import sys

os.environ.setdefault("MUJOCO_GL", "egl")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import numpy as np

from utmeta import config

ap = argparse.ArgumentParser()
ap.add_argument("out")
ap.add_argument("--dist", type=float, default=2.5)
a = ap.parse_args()
cfg = config.load()
config.import_core(cfg)

from ultimatetruth.runner import Simulation
from ultimatetruth.spec import Spec
from ultimatetruth.world.imagecodec import encode_png
from ultimatetruth.world.multibody import BODY_GROUPS, AgentView, SharedWorld

spec = Spec(use_overrides=False)
world = SharedWorld(["vhum", "mehum"], names=["vhum", "mehum"], room="house")
world.day_cfg["enabled"] = False
mx = 2.5
vhum = Simulation(world=world, spec=spec, seed=0, start_pose=(mx - a.dist, 0.0, 0.0), start_battery=0.9)
Simulation(world=AgentView(world, 1), spec=copy.deepcopy(spec), seed=0, agent_key="mehum", start_pose=(mx, 0.0, math.pi), start_battery=0.0005)
e = cfg["eye"]
rgb, root = vhum.world.render_eye(int(e["width"]), int(e["height"]), float(e["half_fov_deg"]))
m = world.model
roots = {int(m.body_rootid[m.geom_bodyid[g]]) for g in range(m.ngeom) if int(m.geom_group[g]) == BODY_GROUPS[1]}
mask = np.isin(root, list(roots))
os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
np.savez_compressed(a.out, rgb=rgb, mask=mask, dist=a.dist)
with open(os.path.splitext(a.out)[0] + ".png", "wb") as f:
    f.write(encode_png(np.ascontiguousarray(rgb)))
print("rendered %dx%d, mehum covers %d pixels" % (rgb.shape[1], rgb.shape[0], int(mask.sum())))
