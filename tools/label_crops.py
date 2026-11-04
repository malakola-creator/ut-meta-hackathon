"""A small labelled set of what the eye sees: crops of real things in the house with their true kind.

For each thing (one of every kind, a few trees and fruits in different stages, the other body), vhum is set down a short way off
and turned to face it, from whichever side shows the most of it. The crop is cut the way the platform's eye cuts it (the thing's box
from the renderer, a margin around it), kept at the eye's thumbnail size and at 4x that size.

Runs in the platform's env:
    MUJOCO_GL=egl ~/miniforge3/envs/ut/bin/python tools/label_crops.py data/crops
Writes <kind>_<id>.png / <kind>_<id>_big.png and labels.json (file -> true label, Thai and English).
"""
import argparse
import copy
import json
import math
import os
import sys

os.environ.setdefault("MUJOCO_GL", "egl")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import mujoco
import numpy as np

from utmeta import config

LABELS = {
    "tree": ("ต้นไม้ (%s)", "a tree (%s)"),
    "fruit": ("ผลไม้ (%s)", "a fruit (%s)"),
    "shelf": ("ชั้นหนังสือ", "a bookshelf"),
    "cleaner": ("หุ่นยนต์ทำความสะอาด", "a cleaning robot"),
    "charger": ("ที่ชาร์จไฟ", "a charging station"),
    "threat": ("สิ่งอันตราย", "a dangerous thing (the house's threat)"),
    "agent": ("หุ่นมนุษย์อีกตัว (mehum)", "another humanoid body (mehum)"),
}

ap = argparse.ArgumentParser()
ap.add_argument("out")
ap.add_argument("--dist", type=float, default=1.6)
ap.add_argument("--per-kind", type=int, default=3)
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
vhum = Simulation(world=world, spec=spec, seed=0, start_pose=(0.0, 0.0, 0.0), start_battery=0.9)
mehum = Simulation(world=AgentView(world, 1), spec=copy.deepcopy(spec), seed=0, agent_key="mehum", start_pose=(5.5, 3.4, math.pi),
                   start_battery=0.0005)
EXTRA = (("tree", 8.2, 2.5), ("tree", 8.9, 3.4), ("fruit", 8.6, 3.0), ("fruit", 2.0, 2.0), ("charger", 4.552, 3.394), ("threat", 6.947, 4.279))


def stand(pose):
    """vhum set down at pose; a reset restores the house's own things, so the extra trees and fruit are put back (same ids)."""
    vhum.world.reset(seed=0, pose=pose, battery=0.9)
    for kind, x, y in EXTRA:                                   # the house starts with soil; trees and fruit grow later
        world.add_stimulus(kind, x, y)


stand((0.0, 0.0, 0.0))
RENDER = None


def look(px, py, yaw, pitch=0.0):
    """A picture from eye height at (px, py) facing yaw, with the eye's field of view, and the root body per pixel (vhum hidden)."""
    global RENDER
    m, d = world.model, world.data
    if RENDER is None:
        m.vis.global_.fovy = math.degrees(2.0 * math.atan(math.tan(math.radians(FOV)) * H / W))
        RENDER = mujoco.Renderer(m, H, W)
    mujoco.mj_kinematics(m, d)
    m.vis.map.znear = 0.05 / max(float(m.stat.extent), 1e-9)   # MuJoCo's default near plane is 2 m in this house (see core-hooks)
    cam = mujoco.MjvCamera()
    cam.type = mujoco.mjtCamera.mjCAMERA_FREE
    z = float(world.eye_height)
    cam.lookat[:] = [px + math.cos(yaw) * math.cos(pitch), py + math.sin(yaw) * math.cos(pitch), z + math.sin(pitch)]
    cam.distance, cam.azimuth, cam.elevation = 1.0, math.degrees(yaw), math.degrees(pitch)
    opt = mujoco.MjvOption()
    for g in range(len(opt.geomgroup)):
        opt.geomgroup[g] = 1
    opt.geomgroup[BODY_GROUPS[0]] = 0                           # vhum's own figure (the camera is its eye)
    RENDER.update_scene(d, camera=cam, scene_option=opt)
    rgb = RENDER.render().copy()
    RENDER.enable_segmentation_rendering()
    RENDER.update_scene(d, camera=cam, scene_option=opt)
    seg = RENDER.render()
    RENDER.disable_segmentation_rendering()
    ids, types = seg[..., 0], seg[..., 1]
    geom = (types == int(mujoco.mjtObj.mjOBJ_GEOM)) & (ids >= 0)
    root = np.full(ids.shape, -1, dtype=np.int32)
    root[geom] = m.body_rootid[m.geom_bodyid[ids[geom]]]
    return rgb, root
e, m = cfg["eye"], world.model
W, H, FOV = 320, 240, float(e["half_fov_deg"])
thumb = (48, 64)                                               # the platform's eye keeps 48 x 64 (config things.recognizer.thumb)


def resize(img, w, h):
    ys = (np.arange(h) * img.shape[0] / h).astype(int)
    xs = (np.arange(w) * img.shape[1] / w).astype(int)
    return img[ys][:, xs]


targets = []
seen = {}
for s in world._stim_list:
    kind = str(s.kind)
    if kind not in LABELS or getattr(s, "hidden", False):
        continue
    if seen.get(kind, 0) >= (a.per_kind if kind in ("tree", "fruit") else 1):
        continue
    slot = world._slot_of.get(s.id)
    if slot is None:
        continue
    root = int(m.body_rootid[m.geom_bodyid[world._slot_geom[slot]]])
    seen[kind] = seen.get(kind, 0) + 1
    targets.append((kind, str(getattr(s, "state", "") or ""), int(s.id), float(s.x), float(s.y), {root}))
mroots = {int(m.body_rootid[m.geom_bodyid[g]]) for g in range(m.ngeom) if int(m.geom_group[g]) == BODY_GROUPS[1]}   # mehum's own geoms
mx, my = mehum.world.truth().x, mehum.world.truth().y
targets.append(("agent", "", -2, mx, my, mroots))

os.makedirs(a.out, exist_ok=True)
labels = {}
for kind, state, sid, x, y, roots in targets:
    best = None
    for k in range(8):                                          # 8 sides; level, or looking down for a low thing (the platform's eye
        ang = k * math.pi / 4                                   # is level only, so up close it sees nothing below ~0.8 m)
        px, py = x + a.dist * math.cos(ang), y + a.dist * math.sin(ang)
        for pitch in (0.0, -0.5):
            rgb, root = look(px, py, math.atan2(y - py, x - px), pitch)
            mask = np.isin(root, list(roots))
            if best is None or mask.sum() > best[0]:
                best = (int(mask.sum()), rgb, mask)
    n, rgb, mask = best
    if n < 60:
        st = world._stimuli.get(sid)
        print("skip %s %d: not in view (%d px; state %r, stored %r, hidden %r)" % (kind, sid, n, getattr(st, "state", None), getattr(st, "stored", None), getattr(st, "hidden", None)))
        continue
    ys, xs = np.nonzero(mask)
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    my_, mx_ = int((y1 - y0) * 0.12), int((x1 - x0) * 0.12)
    crop = rgb[max(0, y0 - my_):min(H, y1 + my_), max(0, x0 - mx_):min(W, x1 + mx_)]
    name = "%s_%s" % (kind, sid if sid >= 0 else "mehum")
    for suffix, (w, h) in (("", thumb), ("_big", (thumb[0] * 4, thumb[1] * 4))):
        with open(os.path.join(a.out, name + suffix + ".png"), "wb") as f:
            f.write(encode_png(np.ascontiguousarray(resize(crop, w, h))))
    th, en = LABELS[kind]
    labels[name + ".png"] = {"kind": kind, "state": state, "th": th % state if "%s" in th else th, "en": en % state if "%s" in en else en, "pixels": n}
    print("%-14s %5d px  %s" % (name, n, labels[name + ".png"]["en"]))
json.dump(labels, open(os.path.join(a.out, "labels.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
