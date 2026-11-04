"""Pick the things to photograph in the realistic house and a side to shoot each from (no wall in between).

Reads the running platform's /api/scene; checks the line of sight against the house's walls and furniture with MuJoCo rays
(the realistic Blender house is drawn on the same boxes). Runs in the platform's env:
    ~/miniforge3/envs/ut/bin/python tools/blender_targets.py data/blender/targets.json
Each target: what it truly is (Thai and English), its id, the bearing to shoot from, distance, camera and aim heights.
"""
import argparse
import json
import math
import os
import sys
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import numpy as np

from utmeta import config

#: kind -> (label th, label en, distance m, camera height m, aim height m); trees and fruit get theirs from the stage
SHOTS = {
    "shelf": ("ชั้นหนังสือ", "a bookshelf", 2.2, 1.5, 0.9),
    "cleaner": ("หุ่นยนต์ทำความสะอาด", "a cleaning robot", 1.0, 0.9, 0.1),
    "charger": ("ที่ชาร์จไฟ", "a charging station", 1.0, 0.9, 0.05),
    "threat": ("สิ่งอันตราย", "a dangerous thing (the house's threat)", 1.1, 1.0, 0.25),
    "agent": ("หุ่นมนุษย์อีกตัว (mehum)", "another humanoid body (mehum)", 2.2, 1.4, 0.85),
}
TREE_H = {"seedling": 0.5, "grown": 2.4, "flowering": 2.8, "fruiting": 3.0, "old": 3.0, "dead": 1.8}   # the Blender assets' heights

ap = argparse.ArgumentParser()
ap.add_argument("out")
a = ap.parse_args()
cfg = config.load()
scene = json.load(urllib.request.urlopen(cfg["core"]["url"].rstrip("/") + "/api/scene", timeout=30))
config.import_core(cfg)
os.environ.setdefault("MUJOCO_GL", "egl")
import mujoco
from ultimatetruth.runner import Simulation
from ultimatetruth.spec import Spec
from ultimatetruth.world.multibody import SharedWorld

world = SharedWorld(["vhum", "mehum"], names=["vhum", "mehum"], room="house")
Simulation(world=world, spec=Spec(use_overrides=False), seed=0, start_pose=(0.0, 0.0, 0.0), start_battery=0.9)
m, d = world.model, world.data
mujoco.mj_kinematics(m, d)


def clear(p, q):
    """Nothing of the house itself (walls, furniture: body 0) between p and q."""
    p, q = np.asarray(p, float), np.asarray(q, float)
    v = q - p
    n = float(np.linalg.norm(v))
    gid = np.array([-1], dtype=np.int32)
    hit = mujoco.mj_ray(m, d, p, v / n, None, 1, -1, gid)
    return hit < 0 or hit >= n - 0.05 or int(m.geom_bodyid[gid[0]]) != 0


stims = {int(s["id"]): s for s in scene["stimuli"]}
bodies = [(float(b["x"]), float(b["y"])) for b in scene.get("agents") or []]


def free_of_bodies(cx, cy, tx, ty):
    """No body (vhum, mehum) at the camera or standing on the line to the thing (not counting the thing itself)."""
    for bx, by in bodies:
        if math.hypot(bx - tx, by - ty) < 0.3:
            continue
        vx, vy = tx - cx, ty - cy
        u = max(0.0, min(1.0, ((bx - cx) * vx + (by - cy) * vy) / max(vx * vx + vy * vy, 1e-9)))
        if math.hypot(cx + u * vx - bx, cy + u * vy - by) < 0.45:
            return False
    return True
picked, seen = [], {}
for s in scene["stimuli"]:
    kind, state = str(s["kind"]), str(s.get("state") or "")
    if s.get("hidden") or kind in ("soil",):
        continue
    if kind == "tree":
        h = TREE_H.get(state, 2.4)
        shot = ("ต้นไม้ (%s)" % state, "a tree (%s)" % state, max(1.2, h * 1.1), 1.5, h * 0.5)
    elif kind == "fruit":
        tree = stims.get(int(s.get("parent") or 0))
        z = TREE_H.get(str(tree.get("state")), 2.4) * (0.5 + 0.25 * ((int(s["id"]) * 0.618) % 1.0)) if tree else 0.045
        shot = ("ผลไม้ (%s)" % state, "a fruit (%s)" % state, 0.35, z, z)
    elif kind in SHOTS:
        shot = SHOTS[kind]
    else:
        continue
    key = (kind, state)
    if seen.get(key):
        continue
    th, en, dist, cz, az = shot
    tx, ty = float(s["x"]), float(s["y"])
    first = float(s.get("yaw") or 0.0) + math.pi if kind == "shelf" else 0.0          # a shelf from its front (its yaw faces the wall)
    for k in range(16):
        b = first + k * math.pi / 8
        cx, cy = tx + dist * math.cos(b), ty + dist * math.sin(b)
        if clear((cx, cy, cz), (tx, ty, az)) and clear((tx, ty, az), (cx, cy, cz)) and free_of_bodies(cx, cy, tx, ty):
            break
    else:
        print("no clear side for %s %s %d" % (kind, state, s["id"]))
        continue
    seen[key] = True
    name = "%s_%s%d" % (kind, (state + "_") if state and kind != "agent" else "", int(s["id"]) if int(s["id"]) >= 0 else 0)
    picked.append({"name": name, "id": int(s["id"]), "kind": kind, "state": state, "th": th, "en": en,
                   "bearing": round(b, 4), "dist": dist, "cam_z": cz, "aim_z": az})
    print("%-22s from %3d°, %.1f m  %s" % (name, round(math.degrees(b)), dist, en))
os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
json.dump(picked, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
