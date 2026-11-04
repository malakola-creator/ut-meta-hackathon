"""Inside Blender on the GPU machine: the recorded house (tools/video/record_scene.py) replayed frame by frame and rendered as clips.

    blender -b -P blender_footage.py -- --live ultimatetruth_live.py --scenes scene.json.gz --shots shots.json --out DIR
                                        [--size 1920x1080] [--fps 24] [--samples 16] [--model-dir DIR] [--only NAME] [--frames N] [--hide vhum] [--engine cycles]

shots.json is a list of shots: {"name", "start_s", "seconds", "camera", "hour"?, "thoughts"?, "lens"?} where camera is one of
  {"kind": "orbit", "centre": [x, y, z], "radius": R, "height": H, "deg": [from, to]}     a slow arc around a point
  {"kind": "path", "from": [x, y, z], "to": [x, y, z], "aim": [x, y, z]}                  a straight dolly looking at one point
  {"kind": "follow", "agent": "vcat", "back": 2.2, "up": 1.0, "aim_z": 0.3}              behind a body, smoothed like the live view
  {"kind": "eye", "agent": "vhum"}                                                       through the body's own eye camera
Writes DIR/<name>.mp4 (H.264 at the fps given) and DIR/<name>.json: for every frame, where each body and each thing of interest sits
on the picture (0..1 from the left and the bottom), so the overlays can be pinned to them later. The clip's clock drives the gait
smoothing (the live script's wall clock is replaced), so a body walks at the speed it walked.
"""
import gzip
import json
import math
import os
import runpy
import sys
import time as _real_time

import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector

args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def opt(name, default=None):
    return args[args.index(name) + 1] if name in args else default


class _Clock:
    """time.monotonic() for the live module = the clip's own clock; everything else is the real module."""
    now = 0.0

    def monotonic(self):
        return self.now

    def __getattr__(self, k):
        return getattr(_real_time, k)


live = runpy.run_path(opt("--live"), run_name="ut_live")["ut_render_once"].__globals__
clock = _Clock()
live["time"] = clock
if opt("--model-dir"):
    live["CAT_MODEL_DIRS"] = [opt("--model-dir")] + list(live.get("CAT_MODEL_DIRS") or [])
with gzip.open(opt("--scenes"), "rt", encoding="utf-8") as fh:
    if opt("--scenes").endswith(".jsonl.gz"):                       # record_scene.py: a header line, then one scene per line
        head = json.loads(fh.readline())
        rec = {"hz": head["hz"], "static": head.get("static"), "frames": [json.loads(l) for l in fh if l.strip()]}
    else:
        rec = json.load(fh)
HZ, FRAMES = float(rec["hz"]), rec["frames"]
live["_state"]["static"] = rec.get("static") or {}
print("scenes: %d frames at %g Hz (%.0f s)" % (len(FRAMES), HZ, len(FRAMES) / HZ), flush=True)
shots = json.load(open(opt("--shots"), encoding="utf-8"))
only = [args[i + 1] for i, x in enumerate(args) if x == "--only"] or None
out = opt("--out")
w, h = (int(v) for v in opt("--size", "1920x1080").lower().split("x"))
fps = int(opt("--fps", "24"))
samples = int(opt("--samples", "16"))
limit = int(opt("--frames", "0"))
HIDE = [k for k in (opt("--hide", "") or "").split(",") if k]
ENGINE = (opt("--engine", "eevee") or "eevee").lower()


def use_cycles(sc):
    """Path tracing on the GPU (OptiX, else CUDA), denoised, the scene kept between frames; samples from --samples."""
    sc.render.engine = "CYCLES"
    cy = sc.cycles
    cy.samples = samples
    cy.use_denoising = True
    cy.use_adaptive_sampling = True
    cy.adaptive_threshold = 0.05
    cy.max_bounces = 6
    for attr, val in (("denoiser", "OPTIX"), ("use_persistent_data", True)):
        try:
            setattr(cy if attr == "denoiser" else sc.render, attr, val)
        except Exception:
            pass
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        for kind in ("OPTIX", "CUDA"):
            try:
                prefs.compute_device_type = kind
                prefs.get_devices()
                devs = [d for d in prefs.devices if d.type == kind]
                if devs:
                    for d in prefs.devices:
                        d.use = d.type == kind
                    cy.device = "GPU"
                    print("cycles on", kind, [d.name for d in devs], flush=True)
                    break
            except Exception:
                continue
    except Exception as exc:
        print("cycles: no GPU preference (%s), CPU" % exc, flush=True)
if HIDE:
    live["SHOW_MEMORY"] = False                                    # the ghosts of a hidden body's memory would still float about
os.makedirs(out, exist_ok=True)
THINGS = ("cleaner", "shelf", "threat", "charger")


def with_hour(scene, hour):
    if hour is None:
        return scene
    scene = dict(scene)
    day = dict(scene.get("day") or {})
    rise, sets = float(day.get("sunrise", 6.0)), float(day.get("sunset", 18.0))
    day["hour"], day["light"] = float(hour), 1.0 if rise + 1 <= float(hour) <= sets - 1 else 0.12 if not rise <= float(hour) <= sets else 0.5
    scene["day"] = day
    return scene


def body_root(key):
    b = live["_built"]["bodies"].get(key)
    return b["root"] if b else None


def aim(cam, target):
    cam.rotation_euler = (Vector(target) - cam.location).to_track_quat("-Z", "Y").to_euler()


def ease(x):
    x = max(0.0, min(1.0, x))
    return 2 * x * x if x < 0.5 else 1 - (-2 * x + 2) ** 2 / 2


def _inside(px, py, corners):
    """Is the point inside the convex quad (corners in order)?"""
    sign = 0
    for k in range(len(corners)):
        x1, y1 = corners[k]; x2, y2 = corners[(k + 1) % len(corners)]
        cross = (x2 - x1) * (py - y1) - (y2 - y1) * (px - x1)
        if abs(cross) < 1e-9:
            continue
        if sign == 0:
            sign = 1 if cross > 0 else -1
        elif (cross > 0) != (sign > 0):
            return False
    return True


def clear_bearing(scene, tx, ty, d0, d1, first, margin=0.35, half=7.3):
    """A bearing (from the thing) along which a walk from d0 to d1 metres stays inside the house and off every wall and piece of
    furniture; candidates every 30 degrees from ``first``; the nearest clear one, else ``first``."""
    quads = [o["corners"] for o in (scene.get("obstacles") or []) if o.get("corners")]
    for m in (0.65, margin):                                           # a roomy path first (a corridor), a doorway only if nothing else is clear
        for step in (0, 30, -30, 60, -60, 90, -90, 120, -120, 150, -150, 180):
            b = first + math.radians(step)
            ok = True
            for j in range(25):
                d = d0 + (d1 - d0) * j / 24
                px, py = tx + d * math.cos(b), ty + d * math.sin(b)
                if abs(px) > half or abs(py) > half:
                    ok = False; break
                for dx, dy in ((0, 0), (m, 0), (-m, 0), (0, m), (0, -m), (m * .7, m * .7), (-m * .7, -m * .7), (m * .7, -m * .7), (-m * .7, m * .7)):
                    if any(_inside(px + dx, py + dy, q) for q in quads):
                        ok = False; break
                if not ok:
                    break
            if ok:
                print("approach: bearing %.0f deg is clear (margin %.2f m)" % (math.degrees(b), m), flush=True)
                return b
    print("approach: no clear bearing found, using the first", flush=True)
    return first


def clear_follow(scene, tx, ty, first, back, min_back, margin=0.3, half=7.3):
    """Where a follow camera can stand: behind the body at ``back`` metres if the way from the body to there crosses no wall or
    furniture; else nearer (down to min_back), else swung round by 30-degree steps. Returns (bearing, distance)."""
    quads = [o["corners"] for o in (scene.get("obstacles") or []) if o.get("corners")]

    def clear(b, d):
        for j in range(12):
            r = 0.3 + (d - 0.3) * j / 11
            px, py = tx + r * math.cos(b), ty + r * math.sin(b)
            if abs(px) > half or abs(py) > half:
                return False
            for dx, dy in ((0, 0), (margin, 0), (-margin, 0), (0, margin), (0, -margin)):
                if any(_inside(px + dx, py + dy, q) for q in quads):
                    return False
        return True
    for step in (0, 30, -30, 60, -60, 90, -90, 120, -120, 150, -150, 180):
        b = first + math.radians(step)
        d = back
        while d >= min_back - 1e-6:
            if clear(b, d):
                return b, d
            d -= 0.3
    return first, min_back


def place_camera(cam, spec, i, n, state):
    kind = spec["kind"]
    if kind == "orbit":
        c = Vector(spec["centre"])
        d0, d1 = spec["deg"]
        a = math.radians(d0 + (d1 - d0) * (i / max(1, n - 1)))
        cam.location = c + Vector((spec["radius"] * math.cos(a), spec["radius"] * math.sin(a), spec["height"]))
        aim(cam, c)
    elif kind == "path":
        f, t = Vector(spec["from"]), Vector(spec["to"])
        cam.location = f.lerp(t, i / max(1, n - 1))
        aim(cam, Vector(spec["aim"]))
    elif kind == "approach":                                       # a person's eye walking up to a thing (the WebXR view), from dist[0] to dist[1]
        tgt = next((st for st in state["frame"].get("stimuli") or [] if st.get("kind") == spec["target"]), None)
        if tgt is None:
            return
        tx, ty = float(tgt["x"]), float(tgt["y"])
        d0, d1 = spec.get("dist", [3.2, 1.3])
        if "bearing" not in state:                                     # the side we walk in from: the first bearing whose whole path crosses no wall
            state["bearing"] = clear_bearing(state["frame"], tx, ty, d0, d1, math.atan2(ty, tx) + math.pi)
        u = ease(i / max(1, n - 1))
        d = d0 + (d1 - d0) * u
        bob = float(spec.get("bob", 0.025)) * math.sin(2 * math.pi * 1.7 * (i / fps)) * (1.0 - u)   # the step rhythm fades as we stop
        cam.location = Vector((tx + d * math.cos(state["bearing"]), ty + d * math.sin(state["bearing"]), float(spec.get("height", 1.55)) + bob))
        aim(cam, Vector((tx, ty, float(spec.get("aim_z", 0.25)))))
    elif kind == "follow":
        root = body_root(spec["agent"])
        if root is None:
            return
        yaw = root.rotation_euler.z
        tx, ty = root.location.x, root.location.y
        target = Vector((tx, ty, float(spec.get("aim_z", 1.0))))
        b, back = clear_follow(state["frame"], tx, ty, yaw + math.pi, float(spec.get("back", 3.0)), float(spec.get("min_back", 0.9)))   # never behind a wall
        want = Vector((tx + back * math.cos(b), ty + back * math.sin(b), float(spec.get("up", 1.3))))
        cam.location = cam.location.lerp(want, 0.12) if state.get("init") else want
        state["init"] = True
        aim(cam, target)


def screen_places(sc, cam, scene):
    """Where the bodies and the things of interest sit on the picture: name -> [u, v] (0..1), only those inside the frame."""
    places = {}
    for key, b in live["_built"]["bodies"].items():
        o = b.get("head") or b["root"]
        p = o.matrix_world.translation if o.name.endswith("Head") or b.get("head") else o.matrix_world.translation + Vector((0, 0, 1.5))
        u, v, z = world_to_camera_view(sc, cam, p)
        if z > 0 and 0 <= u <= 1 and 0 <= v <= 1:
            places[key] = [round(u, 4), round(v, 4)]
    for s in scene.get("stimuli") or []:
        if s.get("kind") in THINGS:
            ob = bpy.data.objects.get("UT_Stim%d" % int(s["id"]))
            p = ob.matrix_world.translation if ob is not None else Vector((float(s["x"]), float(s["y"]), 0.3))
            u, v, z = world_to_camera_view(sc, cam, p)
            if z > 0 and 0 <= u <= 1 and 0 <= v <= 1:
                places["%s_%d" % (s["kind"], int(s["id"]))] = [round(u, 4), round(v, 4)]
    return places


def render_shot(shot):
    name, start_s, seconds = shot["name"], float(shot.get("start_s", 0)), float(shot["seconds"])
    n = int(seconds * fps)
    if limit:
        n = min(n, limit)
    hour, thoughts, spec = shot.get("hour"), bool(shot.get("thoughts", False)), shot["camera"]
    live["SHOW_THOUGHTS"] = thoughts
    sc = bpy.context.scene

    def frame_at(i):
        j = int(round((start_s + i / fps) * HZ))
        return with_hour(FRAMES[min(max(j, 0), len(FRAMES) - 1)], hour)

    # pre-roll: a second of frames before the shot so the walk smoothing is settled, and the assets are in
    for i in range(-fps, 0):
        f = frame_at(i)
        clock.now = start_s + i / fps
        live["apply"](f)
    end = _real_time.time() + 180.0
    while _real_time.time() < end and (len(live["_have"]["texture"]) + len(live["_have"]["model"]) < len(live["_want"]["texture"]) + len(live["_want"]["model"])):
        _real_time.sleep(0.5)
        live["_take_ready"]()
    cam = bpy.data.objects.get("UT_Clip") or bpy.data.objects.new("UT_Clip", bpy.data.cameras.new("UT_Clip"))
    live["_link"](cam, live["_coll"]("UT_Light"))
    cam.data.lens = float(shot.get("lens", 24))
    if spec["kind"] == "eye":
        eye = bpy.data.objects.get("UT_Eye_" + spec["agent"])
        if eye is not None:
            cam = eye
    state, places = {}, []

    def on_frame(scene_, depsgraph=None):
        i = scene_.frame_current - 1
        f = frame_at(i)
        clock.now = start_s + i / fps
        live["apply"](f)
        state["frame"] = f
        for o in bpy.data.objects:                                  # a body kept out of the picture (--hide): all of its parts and its balloon;
            if any(o.name.startswith("UT_%s_" % k) for k in HIDE) or o.name.startswith("UT_Status"):   # and the live view's status text
                o.hide_render = True
        if spec["kind"] != "eye":
            place_camera(cam, spec, i, n, state)
        scene_.camera = cam
        if thoughts:
            live["_aim_thoughts"](cam)
        bpy.context.view_layer.update()
        places.append({"t": round(i / fps, 3), "places": screen_places(scene_, cam, f),
                       "agents": {a["key"]: [round(float(a["x"]), 3), round(float(a["y"]), 3), round(float(a.get("yaw", 0)), 3)] for a in f.get("agents") or []}})

    bpy.app.handlers.frame_change_pre.clear()
    bpy.app.handlers.frame_change_pre.append(on_frame)
    for o in live["_thought_objects"]():
        o.hide_render = not thoughts
    sc.frame_start, sc.frame_end, sc.render.fps = 1, n, fps
    sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = w, h, 100
    if ENGINE == "cycles":
        use_cycles(sc)
    else:
        sc.eevee.taa_render_samples = samples
    st = sc.render.image_settings
    st.file_format, st.color_mode = "FFMPEG", "RGB"
    ff = sc.render.ffmpeg
    ff.format, ff.codec, ff.constant_rate_factor, ff.gopsize, ff.audio_codec = "MPEG4", "H264", "HIGH", 12, "NONE"
    sc.render.filepath = os.path.join(out, name + "_")
    t0 = _real_time.time()
    bpy.ops.render.render(animation=True)
    bpy.app.handlers.frame_change_pre.clear()
    made = [p for p in os.listdir(out) if p.startswith(name + "_") and p.endswith(".mp4")]
    for p in made:                                                  # Blender names the file <path><start>-<end>.mp4
        os.replace(os.path.join(out, p), os.path.join(out, name + ".mp4"))
    json.dump({"name": name, "fps": fps, "size": [w, h], "start_s": start_s, "hour": hour, "camera": spec, "frames": places},
              open(os.path.join(out, name + ".json"), "w", encoding="utf-8"))
    print("shot %s: %d frames in %.0f s (%.2f s/frame) → %s" % (name, n, _real_time.time() - t0, (_real_time.time() - t0) / max(1, n), os.path.join(out, name + ".mp4")), flush=True)


for shot in shots:
    if only and shot["name"] not in only:
        continue
    render_shot(shot)
print("done", flush=True)
