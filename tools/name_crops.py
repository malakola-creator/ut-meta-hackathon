"""Does a picture help the namer? The labelled crops (tools/label_crops.py) named three ways, scored against the true kind.

    python tools/name_crops.py data/crops [--size thumb|big] [--backend meta] [--tag spark13]

A: what watching would show of that kind (as the platform learns it), no picture · B: the picture alone · C: both.
The score is a word match against each kind's accepted words (KEYWORDS), printed beside every answer so it can be checked by eye.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from utmeta import config, namer
from utmeta.llm import Llm, LlmError

#: what watching shows of each kind in the house (the platform's meanings: moves by itself, came closer, hurt when bumped, food)
WATCHED = {
    "tree": {"moves_self": False, "came_closer": False, "touched": None, "food": False},
    "shelf": {"moves_self": False, "came_closer": False, "touched": None, "food": False},
    "cleaner": {"moves_self": True, "came_closer": True, "touched": None, "food": False},
    "threat": {"moves_self": False, "came_closer": False, "touched": True, "food": False},
    "agent": {"moves_self": True, "came_closer": True, "touched": None, "food": False},
    "charger": {"moves_self": False, "came_closer": False, "touched": None, "food": False},
    "fruit": {"moves_self": False, "came_closer": False, "touched": None, "food": True},
}
SIZE = {"tree": 0.15, "shelf": 0.5, "cleaner": 0.25, "threat": 0.2, "agent": 0.22, "charger": 0.35, "fruit": 0.045}
KEYWORDS = {
    "tree": ("tree", "plant", "bush", "shrub", "ต้น"),
    "shelf": ("shelf", "bookcase", "cabinet", "cupboard", "wardrobe", "ชั้น", "ตู้"),
    "cleaner": ("vacuum", "cleaner", "cleaning", "roomba", "robot", "ดูดฝุ่น", "หุ่น"),
    "threat": ("danger", "hazard", "harm", "hot", "spike", "trap", "fire", "อันตราย", "cactus", "กระบองเพชร"),   # drawn as a cactus since 27 Oct
    "agent": ("human", "person", "people", "man", "woman", "figure", "mannequin", "robot", "android", "humanoid", "doll", "คน", "หุ่น"),
    "charger": ("charg", "dock", "station", "pad", "ที่ชาร์จ", "แท่น"),
    "fruit": ("fruit", "apple", "berry", "cherry", "tomato", "orange", "plum", "peach", "ผล", "แอปเปิ"),
}


def hit(kind, ans):
    text = (str(ans.get("name_en", "")) + " " + str(ans.get("name_th", ""))).lower()
    return any(k in text for k in KEYWORDS[kind])


ap = argparse.ArgumentParser()
ap.add_argument("crops")
ap.add_argument("--size", default="thumb", choices=("thumb", "big"))
ap.add_argument("--tag", default="", help="a suffix for the result file (e.g. blender)")
ap.add_argument("--backend", default=None, help="a config.llm backend (glimmer, meta, baseten, ...); default: config.llm.backend")
ap.add_argument("--only", default=None, help="comma-separated picture files to name; the others are skipped (a partial result file)")
a = ap.parse_args()
cfg = config.load()
if a.backend:
    cfg["llm"]["backend"] = a.backend
llm = Llm(cfg["llm"])
labels = json.load(open(os.path.join(a.crops, "labels.json"), encoding="utf-8"))
rows, score = [], {"A": 0, "B": 0, "C": 0}
for fname, lab in sorted(labels.items()):
    if a.only and fname not in a.only.split(","):
        continue
    kind = lab["kind"]
    pic = open(os.path.join(a.crops, fname if a.size == "thumb" else fname.replace(".png", "_big.png")), "rb").read()
    watched = {"meaning": WATCHED[kind], "changes": {"moved": 0, "looks": 0}, "size_m": SIZE[kind], "met": 3}
    blind = {"meaning": {k: None for k in WATCHED[kind]}, "changes": {}, "size_m": None, "met": None}
    out = {"file": fname, "truth": lab["en"]}
    for cond, cell, picture in (("A", watched, None), ("B", blind, pic), ("C", watched, pic)):
        try:
            ans, s, probs, _ = namer.propose(llm, cell, cfg["namer"]["max_name_chars"], picture)
        except LlmError as exc:
            ans, s, probs = {"error": str(exc)}, 0.0, ["error"]
        ok = hit(kind, ans)
        score[cond] += ok
        out[cond] = {"name_en": ans.get("name_en"), "name_th": ans.get("name_th"), "hit": ok, "gate": not probs, "s": round(s, 1)}
        print("%-16s %s %-5s %-34s %s" % (fname, cond, "HIT" if ok else "miss", str(ans.get("name_en"))[:34], ans.get("name_th")), flush=True)
    rows.append(out)
n = len(rows)
print("\nmodel %s, %s pictures: A watched only %d/%d · B picture only %d/%d · C both %d/%d" % (llm.name, a.size, score["A"], n, score["B"], n, score["C"], n))
json.dump({"model": llm.name, "size": a.size, "score": score, "n": n, "rows": rows},
          open(os.path.join(a.crops, "names_%s%s.json" % (a.size, a.tag)), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
