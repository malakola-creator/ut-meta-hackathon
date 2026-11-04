"""Look at a thing, cut it out with SAM 3.1, and name it from the picture — a proposal the mind may take.

1. What to look at: the nearest thing in view the body still wonders about (hook H6), or a given world id.
2. A picture as the body would see it: the platform's realistic Blender house is rendered on the GPU machine from the body's eye,
   turned toward the thing (tools/blender_shoot.py over SSH), so the thing is at the picture's centre.
3. Cut out by words the body has read: SAM 3.1 is prompted with short noun phrases taken from the words in the body's bookshelf
   knowledge (the reading store) and a few general ones; the smallest mask over the picture's centre is the thing.
4. Named from the cut-out and what watching showed (namer.py, a picture and observations), checked by the namer's gate.
5. Kept as a proposal (data/proposals.jsonl, the proof register); given to the mind (hook H2) only when asked to.
"""
from __future__ import annotations

import asyncio
import io
import json
import math
import os
import re
import subprocess
import tempfile
import time
from typing import Any, Dict, List, Optional, Tuple

from . import namer, proposals
from .core_client import Core
from .llm import Llm

BLENDER = {"host": "user@gpu-machine", "dir": "C:/Users/<you>/AppData/Local/ultimatetruth/shoot",                      # the GPU machine with Blender (ours in config.local.json: "blender")
           "exe": "C:/Users/<you>/AppData/Local/ultimatetruth/blender-4.2.23-windows-x64/blender.exe",
           "server": "http://127.0.0.1:5000", "size": 384, "hour": 10}
AIM_Z = {"tree": 1.3, "shelf": 0.9, "cleaner": 0.1, "charger": 0.35, "threat": 0.35, "agent": 0.9, "fruit": 1.6}
GENERAL = ("object", "robot", "plant", "furniture", "person")


def concepts(words: List[Dict[str, Any]], extra: Tuple[str, ...] = GENERAL, limit: int = 10) -> List[str]:
    """Short noun phrases from the words the body read ("a being (a person or a walking body)" → being, person, walking body)."""
    out: List[str] = []

    def add(p: str) -> None:
        p = re.sub(r"^(a|an|the)\s+", "", p.strip().lower()).strip(" .")
        if p and len(p) <= 30 and p not in out:
            out.append(p)
    for w in words:
        en = str(w.get("en", ""))
        add(en.split("(")[0])
        for inner in re.findall(r"\(([^)]*)\)", en):
            for part in re.split(r",|\bor\b|\band\b", inner):
                add(part)
    for e in extra:
        add(e)
    return out[:limit]


def render_look(cfg: Dict[str, Any], thing: Dict[str, Any], body: Dict[str, Any], near: bool = False) -> bytes:
    """The realistic house from the body's eye toward the thing, rendered headless on the GPU machine. ``near``: from 1.4 m off the
    thing on the body's side instead (a test of the cutting and naming when the body does not see the thing; not the body's eye)."""
    b = dict(BLENDER, **(cfg.get("blender") or {}))
    dx, dy = float(body["x"]) - float(thing["x"]), float(body["y"]) - float(thing["y"])
    dist = 1.4 if near else max(0.6, math.hypot(dx, dy) - 0.35)  # just in front of the body's face
    target = [{"name": "look", "id": int(thing["id"]), "kind": thing["kind"], "state": thing.get("state") or "", "th": "", "en": "",
               "bearing": math.atan2(dy, dx), "dist": dist, "cam_z": 1.6, "aim_z": AIM_Z.get(thing["kind"], 0.5)}]
    with tempfile.TemporaryDirectory() as d:
        tj = os.path.join(d, "look.json")
        json.dump(target, open(tj, "w"))
        here = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools", "blender_shoot.py")
        subprocess.run(["scp", "-q", tj, here, "%s:%s/" % (b["host"], b["dir"])], check=True, timeout=60)
        ps = ("cd '%s'; Remove-Item -Recurse -Force lookout -ErrorAction SilentlyContinue; & '%s' -b -P blender_shoot.py -- --live ultimatetruth_live.py "
              "--targets look.json --out lookout --size %d --hour %s --server %s 2>&1 | Out-Null" % (b["dir"], b["exe"], int(b["size"]), b["hour"], b["server"]))
        subprocess.run(["ssh", "-o", "BatchMode=yes", b["host"], ps], check=False, timeout=300)   # PowerShell reports 1 on stderr noise; the file decides
        out = os.path.join(d, "look.png")
        subprocess.run(["scp", "-q", "%s:%s/lookout/look.png" % (b["host"], b["dir"]), out], check=True, timeout=60)
        return open(out, "rb").read()


def sam2_point(cfg: Dict[str, Any], png: bytes, x: int, y: int):
    """The mask under one point from SAM 2.1, run in the env that has torch (config.sam2.python, default the comfy24 env)."""
    import numpy as np
    py = os.path.expanduser(str((cfg.get("sam2") or {}).get("python", "~/miniforge3/envs/comfy24/bin/python")))
    tool = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools", "sam2_point.py")
    with tempfile.TemporaryDirectory() as d:
        src, dst = os.path.join(d, "in.png"), os.path.join(d, "mask.npy")
        open(src, "wb").write(png)
        p = subprocess.run([py, tool, src, str(x), str(y), dst], capture_output=True, timeout=300)
        return np.load(dst) if p.returncode == 0 and os.path.exists(dst) else None


def cut_out(cfg: Dict[str, Any], png: bytes, phrases: List[str]) -> Dict[str, Any]:
    """SAM 3.1 with every phrase at once; the smallest mask over the picture's centre is the thing looked at, else the found thing
    nearest the centre within config look.centre_radius of the width (2026-11-05: the eye aims at a thing, not always dead on it)."""
    import numpy as np
    from PIL import Image
    from .sam3 import segment
    img = np.asarray(Image.open(io.BytesIO(png)).convert("RGB"))
    h, w = img.shape[:2]
    cy, cx = h // 2, w // 2
    t = time.perf_counter()

    async def all_phrases():
        return await asyncio.gather(*(segment(cfg, png, p) for p in phrases), return_exceptions=True)
    results = asyncio.run(all_phrases())
    seconds = time.perf_counter() - t
    best = None
    for phrase, res in zip(phrases, results):
        if isinstance(res, Exception):
            continue
        for obj in res:
            m = obj["mask"]
            if m[max(0, cy - 3):cy + 4, max(0, cx - 3):cx + 4].any() and (best is None or m.sum() < best[2].sum()):
                best = (phrase, obj["box"], m)
    found = {p: (len(r) if not isinstance(r, Exception) else str(r)[:80]) for p, r in zip(phrases, results)}
    if best is None:                                             # nothing under the very centre: the thing nearest the centre, if it is near (2026-11-05)
        near = float((cfg.get("look") or {}).get("centre_radius", 0.25)) * w
        for phrase, res in zip(phrases, results):
            if isinstance(res, Exception):
                continue
            for obj in res:
                l, tp, r, bt = obj["box"]
                d = ((l + r) / 2 - cx) ** 2 + ((tp + bt) / 2 - cy) ** 2
                if d <= near * near and (best is None or d < best[3]):
                    best = (phrase, obj["box"], obj["mask"], d)
        if best is not None:
            best = best[:3]
    if best is None:                                             # no word it knows finds it: SAM 2.1 from the centre point (class-agnostic)
        m = sam2_point(cfg, png, cx, cy)
        if m is None or not m.any():
            return {"phrase": None, "box": None, "crop": png, "found": found, "seconds": round(seconds, 1)}
        ys, xs = np.nonzero(m)
        best = ("(SAM 2.1, point)", (int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())), m)
    phrase, (l, tp, r, bt), m = best
    pad = int(0.15 * max(r - l, bt - tp)) + 4
    l, tp, r, bt = max(0, l - pad), max(0, tp - pad), min(w, r + pad), min(h, bt + pad)
    out = img.copy()
    out[~m] = (out[~m] * 0.3).astype(np.uint8)                   # the thing in full, the rest dimmed
    crop = Image.fromarray(out[tp:bt, l:r])
    k = 384 / max(crop.size)
    if k < 1:
        crop = crop.resize((int(crop.size[0] * k), int(crop.size[1] * k)))
    buf = io.BytesIO()
    crop.save(buf, "PNG")
    return {"phrase": phrase, "box": [int(l), int(tp), int(r), int(bt)], "pixels": int(m.sum()), "crop": buf.getvalue(), "found": found, "seconds": round(seconds, 1)}


def look_and_name(cfg: Dict[str, Any], core: Core, llm: Llm, agent: str = "vhum", sid: Optional[int] = None, give: bool = False,
                  keep: Optional[str] = None, force: bool = False, near: bool = False) -> Dict[str, Any]:
    scene = core.scene()
    body = next(b for b in scene.get("agents") or [] if b.get("key") == agent)
    wonder = core.asking(agent)
    if sid is None:
        seen = [a for a in wonder if a["in_view"] and any(q["what"] in ("name", "what") for q in a["open"])]   # a picture can answer these only
        if not seen:
            return {"ok": False, "why": "nothing in view whose name the body wonders about"}
        sid = int(seen[0]["sid"])
    elif not any(int(a["sid"]) == int(sid) and a["in_view"] for a in wonder) and not (force or near):
        return {"ok": False, "why": "the body does not see that thing now (it would be a picture of whatever is in between)"}
    thing = next(t for t in scene.get("stimuli") or [] if int(t["id"]) == int(sid))
    known = core.thing_of(sid, agent)
    cell = core.things(agent).get(known["cell"]) or {}
    words = ((core.store("reading", agent) or {}).get("words")) or []
    out: Dict[str, Any] = {"sid": sid, "kind_seen": thing["kind"], "cell": known["cell"], "model": llm.name}
    t = time.perf_counter()
    png = render_look(cfg, thing, body, near)
    out["view"] = "near the thing (a test, not the body's eye)" if near else "the body's eye"
    out["render_s"] = round(time.perf_counter() - t, 1)
    phrases = concepts(words)
    cut = cut_out(cfg, png, phrases)
    out.update(phrases=phrases, phrase=cut["phrase"], box=cut["box"], sam_found=cut["found"], sam_s=cut["seconds"])
    if keep:
        os.makedirs(keep, exist_ok=True)
        open(os.path.join(keep, "look_%d.png" % sid), "wb").write(png)
        open(os.path.join(keep, "look_%d_cut.png" % sid), "wb").write(cut["crop"])
    answer, seconds, problems, obs = namer.propose(llm, cell if cell.get("meaning") else {"meaning": {}}, 40, cut["crop"])
    out.update(answer=answer, name_s=round(seconds, 1), problems=problems)
    proposals.record(cfg, "look_name", llm.name, seconds, {"sid": sid, "cell": known["cell"], "phrase": cut["phrase"], "box": cut["box"], "view": out["view"]},
                     answer, problems)
    if give and not problems and known.get("known"):
        core.name_thing(known["cell"], answer["name_th"].strip(), answer["name_en"].strip(), ("sam3.1+" + llm.name)[:40], agent)
        out["given"] = True
    out["ok"] = not problems
    return out
