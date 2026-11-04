"""Hook H4, end to end: a procedure a model composed (and the gate accepted) is handed to the mind as a candidate and rehearsed at
once against the mind's own ways; how it ranked is printed and kept in the proposals log.

    python tools/h4_rehearse.py [--agent vhum] [--problem unstuck] [--from-log | --backend glimmer] [--withdraw]

--from-log (default) takes the latest accepted compose from data/proposals.jsonl; --backend composes a fresh one with that model.
The steps are translated from names to the chip's enum numbers (samples/protocol.json, the chip's order). The mind keeps the
candidate unless --withdraw; what the rehearsal said is appended to data/proposals.jsonl as kind "rehearse".
"""
import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from utmeta import composer, config, proposals
from utmeta.core_client import Core, CoreError
from utmeta.llm import Llm

ap = argparse.ArgumentParser()
ap.add_argument("--agent", default="vhum")
ap.add_argument("--problem", default="unstuck", help="the solver's problem the procedure is for")
ap.add_argument("--backend", default=None, help="compose a fresh procedure with this model instead of taking the latest accepted one from the log")
ap.add_argument("--withdraw", action="store_true", help="take the candidate back afterwards (the rehearsal result stays in the log)")
a = ap.parse_args()
cfg = config.load()
core = Core(cfg)
prims, exits = composer.protocol_keys(cfg)

if a.backend:
    cfg["llm"]["backend"] = a.backend
    llm = Llm(cfg["llm"])
    from utmeta.__main__ import CORNER
    ans, s, probs = composer.propose(llm, CORNER, prims, exits, cfg["composer"])
    entry = proposals.record(cfg, "compose", llm.name, s, CORNER, ans, probs)
    if probs:
        print("the gate refused the fresh procedure:", probs); sys.exit(1)
    model, steps = llm.name, ans["steps"]
else:
    rows = [json.loads(l) for l in open(os.path.join(config.ROOT, cfg.get("proposals", "data/proposals.jsonl")), encoding="utf-8") if l.strip()]
    ok = [r for r in rows if r["kind"] == "compose" and r["accepted"]]
    if not ok:
        print("no accepted compose in the log"); sys.exit(1)
    model, steps = ok[-1]["model"], (ok[-1]["output"] or {}).get("steps") or []

proc = [{"primitive": prims.index(st["primitive"]), "target": 0, "p1": int(st.get("p1") or 0), "p2": 0,
         "exit_kind": exits.index(st["exit"]["kind"]), "exit_value": int(st["exit"].get("value") or 0)} for st in steps]
body = {"problem": a.problem, "steps": proc, "th": "ทางออกที่โมเดลเสนอ", "en": "the way a model proposed", "from": model[:40]}
t = time.perf_counter()
try:
    res = core._req("POST", "/api/orin/proposals", query={"agent": a.agent, "rehearse": "1"}, body=body)
except CoreError as exc:
    print("the mind refused the proposal:", exc)
    proposals.record(cfg, "rehearse", model, time.perf_counter() - t, {"agent": a.agent, "problem": a.problem, "steps": [st["primitive"] for st in steps]}, None, [str(exc)])
    sys.exit(1)
seconds = time.perf_counter() - t
reh = res.get("rehearsed") or {}
print("proposal %s kept as candidate %r for %s; rehearsed: done=%s row=%s rank=%s of %s (%.1f s, the world waited)"
      % (model, res.get("key"), a.agent, reh.get("done"), reh.get("row"), reh.get("rank"), reh.get("ways"), seconds))
for r in reh.get("ranked") or []:
    print("  %-28s score %6.2f  moved %5.2f m  bumps %s" % (r.get("key"), float(r.get("score") or 0), float(r.get("moved_m") or 0), r.get("bumps")))
proposals.record(cfg, "rehearse", model, seconds, {"agent": a.agent, "problem": a.problem, "steps": [st["primitive"] for st in steps], "key": res.get("key")},
                 {"done": reh.get("done"), "row": reh.get("row"), "rank": reh.get("rank"), "ways": reh.get("ways"), "ranked": reh.get("ranked"), "why": reh.get("why") or reh.get("why_en")},
                 [] if reh.get("done") else [str(reh.get("why_en") or reh.get("why") or "not rehearsed")])
if a.withdraw and res.get("key"):
    core._req("DELETE", "/api/orin/proposals/%s" % res["key"], query={"agent": a.agent})
    print("withdrawn")
