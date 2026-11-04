"""Inside Blender on the GPU machine: photograph each target in the realistic house, in one Blender run.

    blender -b -P blender_shoot.py -- --live ultimatetruth_live.py --targets targets.json --out DIR [--size 384] [--server URL]
                                     [--hour 10]

Loads the platform's live script as a module (not its own entry point), then for each target reads where it is now (/api/scene),
places a camera on the chosen side and renders with ut_render_once. Thought balloons are off (they would tell the model the answer);
``--hour`` draws the moment at another hour of the day (a picture only: the world's clock is not touched). Writes DIR/<name>.png and DIR/labels.json.
"""
import json
import math
import os
import runpy
import sys

args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def opt(name, default=None):
    return args[args.index(name) + 1] if name in args else default


live = runpy.run_path(opt("--live"), run_name="ut_live")["ut_render_once"].__globals__   # the module's own globals (run_path hands back a copy)
live["SHOW_THOUGHTS"] = False
if opt("--server"):
    live["SERVER"] = opt("--server").rstrip("/")
targets = json.load(open(opt("--targets"), encoding="utf-8"))
out = opt("--out")
size = int(opt("--size", "384"))
hour = float(opt("--hour")) if opt("--hour") else None
os.makedirs(out, exist_ok=True)
labels = {}
for t in targets:
    live["_fetch_scene"]()
    now = {int(s["id"]): s for s in (live["_state"]["latest"] or {}).get("stimuli", [])}.get(t["id"])
    if now is None:
        print("gone: %s" % t["name"])
        continue
    tx, ty, tz, cz, bearing = float(now["x"]), float(now["y"]), t["aim_z"], t["cam_z"], t["bearing"]
    if t["kind"] == "fruit":                                   # a fruit is drawn on its tree's crown: aim where it is drawn, from outside
        live["apply"](live["_state"]["latest"])
        import bpy
        ob = bpy.data.objects.get("UT_Stim%d" % t["id"])           # the ball: always placed where the fruit is drawn
        tree = bpy.data.objects.get("UT_Stim%d" % int(now.get("parent") or 0))
        if ob is not None:
            tx, ty, tz = float(ob.location.x), float(ob.location.y), float(ob.location.z)
            cz = tz
            if tree is not None:
                bearing = math.atan2(ty - float(tree.get("ut_y", ty)), tx - float(tree.get("ut_x", tx)))
    cx, cy = tx + t["dist"] * math.cos(bearing), ty + t["dist"] * math.sin(bearing)
    view = "%.3f,%.3f,%.3f,%.3f,%.3f,%.3f" % (cx, cy, cz, tx, ty, tz)
    state, th, en, name = t["state"], t["th"], t["en"], t["name"]
    if t["kind"] in ("tree", "fruit") and str(now.get("state") or "") != state:     # it grew or ripened since it was picked: label what is drawn now
        state = str(now.get("state") or "")
        th, en = {"tree": ("ต้นไม้ (%s)", "a tree (%s)"), "fruit": ("ผลไม้ (%s)", "a fruit (%s)")}[t["kind"]]
        th, en, name = th % state, en % state, "%s_%s_%d" % (t["kind"], state, t["id"])
    path = os.path.join(out, name + ".png")
    live["ut_render_once"](path, view, (size, size), hour=hour)
    labels[name + ".png"] = {"kind": t["kind"], "state": state, "th": th, "en": en, "view": view}
json.dump(labels, open(os.path.join(out, "labels.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("done %d" % len(labels))
sys.stdout.flush()
os._exit(0)
