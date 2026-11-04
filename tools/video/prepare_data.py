"""Everything the overlays show, gathered from the real files into one JSON (ut-meta-video/build/data.json), so no number in the
video is typed by hand: the proposals log, the nine pictures with each model's hits, the words the body read and the SAM prompts
made from them, the register's counts, and the voice-over word timings.

    python tools/video/prepare_data.py
"""
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, ROOT)
from utmeta import config
from utmeta.core_client import Core, CoreError
from utmeta.look import concepts

cfg = config.load()
video = os.path.join(ROOT, "ut-meta-video")
out = {}

# the proposals log: every row, oldest first
rows = [json.loads(l) for l in open(os.path.join(ROOT, "data", "proposals.jsonl"), encoding="utf-8") if l.strip()]
out["log"] = rows
out["counts"] = {"proposals": len(rows), "passed": sum(1 for r in rows if r["accepted"]), "refused": sum(1 for r in rows if not r["accepted"])}
names = [r for r in rows if r["kind"] in ("name", "look_name") and r["accepted"] and "cat" not in str((r.get("input") or {}).get("view", ""))]   # the vacuum's names; the cat's rows (5 Nov) are D.cat
out["wrong_names"] = [(r["output"] or {}).get("name_en") for r in names if (r["output"] or {}).get("name_en") not in ("robot vacuum", "robot vacuum cleaner")]
out["refusals"] = [{"kind": r["kind"], "model": r["model"], "why": (r.get("problems") or [""])[0]} for r in rows if not r["accepted"]]
reads = [r for r in rows if r["kind"] == "read"]
out["reads"] = [{"model": r["model"], "problems": r.get("problems") or [], "lines": ((r.get("output") or {}).get("lines") or [])[:8]} for r in reads]
out["composes"] = [{"model": r["model"], "accepted": r["accepted"], "problems": r.get("problems") or [],
                    "steps": [s.get("primitive") for s in ((r.get("output") or {}).get("steps") or []) if isinstance(s, dict)],
                    "whys": [str(s.get("why") or "") for s in ((r.get("output") or {}).get("steps") or []) if isinstance(s, dict)],
                    "situation": r.get("input") if isinstance(r.get("input"), dict) else {}} for r in rows if r["kind"] == "compose"]
look = [r for r in rows if r["kind"] == "look_name"]
out["look_names"] = [{"model": r["model"], "name_en": (r["output"] or {}).get("name_en"), "name_th": (r["output"] or {}).get("name_th"),
                      "used": (r["output"] or {}).get("used") or [], "why": (r["output"] or {}).get("why") or "",
                      "box": (r.get("input") or {}).get("box"), "phrase": (r.get("input") or {}).get("phrase"), "at": r["at"][:10]} for r in look]
out["rehearsals"] = [r for r in rows if r["kind"] == "rehearse"]
out["understandings"] = [{"model": r["model"], "name_en": (r["output"] or {}).get("name_en"), "used": (r["output"] or {}).get("used") or [], "why": (r["output"] or {}).get("why") or ""}
                         for r in rows if r["kind"] in ("name", "look_name") and r["accepted"]]

# the nine pictures and each model's answers (docs/results_picture_naming.md, the 27 Oct and 4 Nov runs)
crops = os.path.join(ROOT, "data", "blender", "crops2")
labels = json.load(open(os.path.join(crops, "labels.json"), encoding="utf-8"))
runs = {}
for tag, f in (("glimmer", "names_thumb_v2.json"), ("spark13", "names_thumb_spark13.json")):
    r = json.load(open(os.path.join(crops, f), encoding="utf-8"))
    runs[tag] = {"model": r["model"], "score": r["score"], "rows": {row["file"]: row for row in r["rows"]}}
out["pictures"] = []
for fname, lab in sorted(labels.items()):
    pic = {"file": os.path.join(crops, fname), "kind": lab["kind"], "en": lab["en"], "th": lab["th"]}
    for tag in runs:
        row = runs[tag]["rows"].get(fname, {})
        pic[tag] = {c: {"hit": bool(row.get(c, {}).get("hit")), "name": row.get(c, {}).get("name_en")} for c in "ABC"}
    out["pictures"].append(pic)
out["runs"] = {tag: {"model": runs[tag]["model"], "score": runs[tag]["score"]} for tag in runs}
out["thumbnail_48x64"] = {"B": "3/8", "C": "2/8"}                     # docs/results_picture_naming.md, the resized run

# the words a model read onto the shelf (the Glimmer read of 26 Oct, the lines that passed), and the SAM prompts the look chain
# makes from them (utmeta.look.concepts); the live store is empty in the body's current life, so the log is the source
glim = next((r for r in reads if r["model"].startswith("glimmer")), None)
words = [l for l in ((glim or {}).get("output") or {}).get("lines", []) if isinstance(l, dict) and l.get("kind") == "word"]
out["shelf_words"] = [{"en": w.get("en"), "th": w.get("th")} for w in words]
out["prompts"] = concepts(words)
out["sam3_by_words"] = json.load(open(os.path.join(ROOT, "data", "look", "look_5_sam3.json"), encoding="utf-8")) if os.path.exists(os.path.join(ROOT, "data", "look", "look_5_sam3.json")) else {}

# the pictures the look chain made (28 Oct): the eye's view and the SAM cut-out
out["look_full"] = os.path.join(ROOT, "data", "look", "look_5.png")
cat_names = os.path.join(ROOT, "data", "look", "look_cat_names.json")
out["cat"] = {"cut": os.path.join(ROOT, "data", "look", "look_cat_cut.png"), "frame": os.path.join(ROOT, "ut-meta-video", "build", "cat", "cat_frame_b.png"),
              "sam": json.load(open(os.path.join(ROOT, "data", "look", "look_cat_sam3.json"), encoding="utf-8")),
              "names": json.load(open(cat_names, encoding="utf-8"))} if os.path.exists(cat_names) else None   # the cat by the same chain (5 Nov)
out["look_cut"] = os.path.join(ROOT, "data", "look", "look_5_cut.png")
out["assets"] = {k: os.path.join(video, "storyboard", "assets", v) for k, v in
                 {"shelf": "shelf.png", "vacuum": "vacuum.png", "cactus": "cactus.png", "charger": "charger.png", "agent": "agent.png", "cat_sit": "cat_sit.png", "eye_scene": "eye_scene.png"}.items()}

# the voice-over: start of each line and when each word is spoken
nar = json.load(open(os.path.join(HERE, "narration.json"), encoding="utf-8"))
out["narration"] = []
for line in nar["lines"]:
    wj = os.path.join(video, "voice", line["id"] + ".words.json")
    words = json.load(open(wj, encoding="utf-8"))["words"] if os.path.exists(wj) else []
    out["narration"].append({"id": line["id"], "start": line["start"], "slot": line["slot"], "text": line["text"], "words": words})

# where things sit on each footage clip (blender_footage.py), per frame
out["footage"] = {}
for f in glob.glob(os.path.join(video, "footage", "*.json")):
    d = json.load(open(f, encoding="utf-8"))
    if "frames" in d:
        out["footage"][d["name"]] = {"fps": d["fps"], "frames": [{"places": fr["places"]} for fr in d["frames"]]}

os.makedirs(os.path.join(video, "build"), exist_ok=True)
json.dump(out, open(os.path.join(video, "build", "data.json"), "w", encoding="utf-8"), ensure_ascii=False)
print("data.json: %d log rows (%d passed, %d refused), %d wrong names, %d pictures, %d shelf words → %d prompts, footage clips %s, narration lines with words: %d/%d"
      % (len(rows), out["counts"]["passed"], out["counts"]["refused"], len(out["wrong_names"]), len(out["pictures"]), len(out["shelf_words"]), len(out["prompts"]),
         sorted(out["footage"]), sum(1 for n in out["narration"] if n["words"]), len(out["narration"])))
