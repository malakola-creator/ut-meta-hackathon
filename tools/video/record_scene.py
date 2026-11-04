"""Record the live house for the video: /api/scene at a fixed rate for N seconds, plus /api/scene/static once, streamed into one
gzip JSON-lines file that tools/video/blender_footage.py replays frame by frame inside Blender on the GPU machine.

    python tools/video/record_scene.py --seconds 900 --hz 24 --out ut-meta-video/footage/scene.jsonl.gz

Line 1 is the header {"hz", "seconds", "static"}; every other line is one /api/scene with "_t" (the clip's clock). Nothing is
staged: the bodies do whatever the mind does. At the end the recording says which 10-second windows held the most movement
(bodies and the cleaner), so the shots can be cut from the lively parts.
"""
import argparse
import gzip
import json
import math
import os
import sys
import time
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from utmeta import config

ap = argparse.ArgumentParser()
ap.add_argument("--seconds", type=float, default=900.0)
ap.add_argument("--hz", type=float, default=24.0)
ap.add_argument("--out", default="ut-meta-video/footage/scene.jsonl.gz")
ap.add_argument("--window", type=float, default=10.0, help="seconds per activity window in the summary")
a = ap.parse_args()
base = config.load()["core"]["url"].rstrip("/")


def get(path):
    with urllib.request.urlopen(base + path, timeout=3.0) as r:
        return json.loads(r.read().decode("utf-8"))


def spots(s):
    out = {ag["key"]: (float(ag["x"]), float(ag["y"])) for ag in s.get("agents") or []}
    for st in s.get("stimuli") or []:
        if st.get("kind") == "cleaner":
            out["cleaner"] = (float(st["x"]), float(st["y"]))
    return out


os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
static = get("/api/scene/static")
n = int(a.seconds * a.hz)
moved, last, t0, written = {}, None, time.monotonic(), 0
with gzip.open(a.out, "wt", encoding="utf-8") as f:
    f.write(json.dumps({"hz": a.hz, "seconds": a.seconds, "static": static}, ensure_ascii=False) + "\n")
    for i in range(n):
        due = t0 + i / a.hz
        while time.monotonic() < due:
            time.sleep(0.002)
        try:
            s = get("/api/scene")
        except Exception as exc:                                    # one missed frame: repeat the last
            if last is None:
                raise
            s = dict(last["scene"])
        s["_t"] = round(i / a.hz, 4)
        f.write(json.dumps(s, ensure_ascii=False) + "\n")
        written += 1
        now = spots(s)
        if last is not None:
            win = int(i / a.hz // a.window)
            for k, (x, y) in now.items():
                px, py = last["spots"].get(k, (x, y))
                moved.setdefault(win, {}).setdefault(k, 0.0)
                moved[win][k] += math.hypot(x - px, y - py)
        last = {"scene": s, "spots": now}
        if i % int(60 * a.hz) == 0 and i:
            print("  %d s recorded" % int(i / a.hz), flush=True)
print("recorded %d frames at %g Hz → %s (%.1f MB)" % (written, a.hz, a.out, os.path.getsize(a.out) / 1e6))
print("movement per %g-second window (metres): best first" % a.window)
for win, m in sorted(moved.items(), key=lambda kv: -sum(kv[1].values()))[:12]:
    print("  %4d–%4d s  total %5.1f  %s" % (win * a.window, (win + 1) * a.window, sum(m.values()), {k: round(v, 1) for k, v in m.items()}))
