"""A draft of the demo's voice-over by Muse Wonder (Meta Model API), from the lines we have and the facts on screen: tighter words,
the same facts. Written to ut-meta-video/script_wonder.md for a person to compare; nothing in the video changes by itself.

    python tools/video/script_wonder.py [--model muse-wonder-1.0] [--apply]

--apply copies the draft's lines into tools/video/narration.json (then run tools/video/tts.py --force).
Every number and claim must come from the current lines; the prompt forbids new ones, and the draft is checked for digits that were
not in the originals before it is accepted.
"""
import argparse
import json
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, ROOT)
from utmeta import config
from utmeta.llm import Llm, LlmError

ap = argparse.ArgumentParser()
ap.add_argument("--model", default="muse-wonder-1.0")
ap.add_argument("--apply", action="store_true")
a = ap.parse_args()
cfg = config.load()
cfg["llm"]["backend"] = "meta"
cfg["llm"]["meta"]["model"] = a.model
cfg["llm"]["meta"]["max_tokens"] = 16000
cfg["llm"]["meta"]["extra"] = dict(cfg["llm"]["meta"].get("extra") or {}, reasoning_effort="low")   # it thinks long otherwise, and answers nothing
llm = Llm(cfg["llm"])
nar = json.load(open(os.path.join(HERE, "narration.json"), encoding="utf-8"))
shots = {"D1": "title card: ultimateTruth (a virtual environment and a thinking system) and the Meta layer (for the Meta Global AI Developer Hackathon); a thought balloon 'pet cat?' over a robot vacuum; stamps GATE: PASSED then MIND: NOT YET",
         "D2": "Push the Frontier: robotics; the log of wrong names that all passed the form gate; then an animated diagram: house → senses → mesh chip → body; deep brain writes rows; Mind Bridge with six hooks; the Meta layer proposes, never commands",
         "D3": "Glimmer reads a page and says what each thing does (cat moves by itself, not food; fruit is food; it also called rotten fruit food, the gate passed the form, the body's own meals decide); the shelf words are what SAM 3.1 looks for, none found; the eye's picture cut from the centre; the name 'robot vacuum' with the model's reasons; → Mind Bridge: a proposal until the body watches or a person confirms; taught the word, SAM 3.1 finds it",
         "D4": "nine pictures of the house: the robot's own eye (primitives) 1 of 7; realistic full size 8 of 9 for Glimmer on the robot and Spark 1.3 on the API; thumbnails 2 of 8; watching alone names nothing; the finding is about the eye",
         "D5": "point and say through the WebXR view: 'This is a robot vacuum' → extracted → gate: both languages → given to the mind, pinned to what the body saw it do; a thing not watched → 409 not yet",
         "D6": "a model proposes how to act: Llama's plan refused (a hole), Glimmer's passed; rehearsed live against the mind's own ways it ranked 3 of 3 and moved nothing, its exits were met at once",
         "D7": "four cards: 15 proposals, 12 passed, 3 refused; 3 refusal reasons; 9 wrong or vague names passed, 0 reached the mind; 15 tests, 1.6 s, 0 keys",
         "D8": "Meta Global AI Developer Hackathon; what was built; the register as credits; 'A model may propose. This mind decides.'"}
lines = [{"id": l["id"], "seconds": l["slot"], "max_words": int(l["slot"] * 2.3), "current": l["text"], "on_screen": shots.get(l["id"], "")} for l in nar["lines"]]
system = ("You write the voice-over of a 3-minute hackathon demo video, spoken slowly in plain English, one line per shot. "
          "Keep every fact and number exactly as given; add no claim, no number, no model name that is not in the input. "
          "Each line must fit its seconds: at most max_words words. Short sentences. No hype words. "
          "Answer JSON only: {\"lines\": [{\"id\": str, \"text\": str}], \"notes\": str}.")
user = json.dumps({"video": "ultimateTruth x Meta: a mind that must prove a model's guess before the body believes it; the Meta layer understands what a thing is and hands that to the Mind Bridge, another way to teach a robot",
                   "lines": lines}, ensure_ascii=False)
t = time.perf_counter()
try:
    ans, s = llm.ask(system, user)
except LlmError as exc:
    print("Muse Wonder did not answer:", exc); sys.exit(1)
draft = {l["id"]: l["text"] for l in ans.get("lines", []) if isinstance(l, dict) and l.get("id") and l.get("text")}
old_digits = set(re.findall(r"\d+", " ".join(l["current"] for l in lines)))
problems = []
for l in lines:
    txt = draft.get(l["id"], "")
    words = len(txt.split())
    new_digits = set(re.findall(r"\d+", txt)) - old_digits
    if not txt:
        problems.append("%s: no line" % l["id"])
    if words > l["max_words"]:
        problems.append("%s: %d words, at most %d" % (l["id"], words, l["max_words"]))
    if new_digits:
        problems.append("%s: numbers not in the original: %s" % (l["id"], sorted(new_digits)))
out = ["# A voice-over draft by %s (%.0f s)" % (llm.name, time.perf_counter() - t), "", "Notes from the model: %s" % ans.get("notes", ""), "",
       "| shot | seconds | current | draft |", "|---|---|---|---|"]
for l in lines:
    out.append("| %s | %d | %s | %s |" % (l["id"], l["seconds"], l["current"].replace("|", "/"), draft.get(l["id"], "").replace("|", "/")))
out += ["", "Checks: " + ("; ".join(problems) if problems else "every line fits its slot and adds no number")]
path = os.path.join(ROOT, "ut-meta-video", "script_wonder.md")
open(path, "w", encoding="utf-8").write("\n".join(out) + "\n")
print("\n".join(out))
print("→", path)
if a.apply and not problems:
    for l in nar["lines"]:
        l["text"] = draft[l["id"]]
    json.dump(nar, open(os.path.join(HERE, "narration.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("applied to narration.json (run tools/video/tts.py --force)")
