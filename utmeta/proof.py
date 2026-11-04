"""The proof register as data: how everything the mind holds from outside was proven, and every model proposal with the gate's
verdict. The teach server serves it live (`/proofdata`); `tools/proof_snapshot.py` freezes it to a file for the public page.
"""
from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, Iterable, List

from .core_client import Core, CoreError


FULL_NAMES = {"vhum": "the virtual human (vhum)", "mehum": "the meta human (mehum)", "vcat": "the virtual cat (vcat)"}   # a body's full name, then its key


def label(cell: Dict[str, Any]):
    """The best name a kind has: the word read from a book, else the name given, else the model's name, else its look."""
    for th, en in ((cell.get("word_th"), cell.get("word_en")), (cell.get("given_th"), cell.get("given_en")), (cell.get("name_th"), cell.get("name_en"))):
        if th and en:
            return th, en
    return cell.get("look", ""), cell.get("look", "")


def build(core: Core, cfg: Dict[str, Any], agents: Iterable[str] = ("vhum", "mehum"), root: str = "", log_rows: int = 40) -> Dict[str, Any]:
    """{"agents": {key: {kinds, proposals, edits} | {error}}, "log": [...newest first], "for_a_person": [...]}"""
    out: Dict[str, Any] = {"agents": {}, "log": [], "for_a_person": []}
    for ag in agents:
        try:
            cells = core.things(ag)
            kinds = []
            for key, c in cells.items():
                if not c.get("known"):
                    continue
                th, en = label(c)
                kinds.append({"key": key, "label_th": th, "label_en": en, "given": {"th": c.get("given_th"), "en": c.get("given_en"), "from": c.get("given_from")},
                              "asking": [{"what": w, "th": q.get("th"), "en": q.get("en"), "status": q.get("status"), "by": q.get("by", ""),
                                          "answer_th": q.get("answer_th", ""), "answer_en": q.get("answer_en", "")} for w, q in (c.get("asking") or {}).items()],
                              "met": c.get("met", 0)})
            props = core.proposals(ag)
            edits = [e for e in core.edits(ag) if e.get("store") in ("things", "proposed")][:20]
            wonder = core.asking(ag)
        except CoreError as exc:
            out["agents"][ag] = {"error": str(exc)}
            continue
        out["agents"][ag] = {"kinds": kinds, "proposals": props, "edits": edits}
        for w in wonder:                                          # needs a person: a name nobody has given yet, a thing in view
            if w["in_view"] and any(q["what"] == "name" for q in w["open"]):
                out["for_a_person"].append({"agent": ag, "sid": w["sid"], "cell": w["cell"], "label_th": w["label_th"], "label_en": w["label_en"], "why": "name"})
    path = os.path.join(root, cfg.get("proposals", "data/proposals.jsonl"))
    refused: Dict[str, int] = {}
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            rows = [json.loads(l) for l in f if l.strip()]
        out["log"] = rows[-log_rows:][::-1]
        for r in rows:                                            # a kind a model failed to name three times goes to a person (escalation)
            cell = (r.get("input") or {}).get("cell") if isinstance(r.get("input"), dict) else None
            if r.get("kind") in ("name", "teach") and cell and not r.get("accepted"):
                refused[cell] = refused.get(cell, 0) + 1
    for cell, n in refused.items():
        if n >= int((cfg.get("proof") or {}).get("escalate_after", 3)):
            out["for_a_person"].append({"agent": "", "sid": None, "cell": cell, "label_th": "", "label_en": "", "why": "refused %d times" % n})
    return out


def _what(r: Dict[str, Any]) -> str:
    o, i = r.get("output") or {}, r.get("input") or {}
    if not isinstance(o, dict):
        return ""
    if r.get("kind") == "teach":
        return "“%s” → %s" % (i.get("said", ""), o.get("name_en", ""))
    if r.get("kind") in ("name", "look_name"):
        return "%s" % (o.get("name_en", ""),)
    if r.get("kind") == "compose":
        return " → ".join(str(s.get("primitive")) for s in (o.get("steps") or []) if isinstance(s, dict))
    if r.get("kind") == "read":
        return "%d lines" % len(o.get("lines") or [])
    return ""


def markdown(data: Dict[str, Any], taken_at: str) -> str:
    """The register as Markdown (GitHub shows it): the log, then what each body knows and how it was proven."""
    L: List[str] = ["# Proof register (snapshot)", "",
                    "Taken %s from the live platform and `data/proposals.jsonl`. Meta's models propose; the mind decides. "
                    "Every model proposal below says which checks it passed or failed; every kind the mind knows says how its name was proven." % taken_at, "",
                    "## Every model proposal and the gate's verdict", "",
                    "| when | task | model | proposed | gate |", "|---|---|---|---|---|"]
    for r in data.get("log") or []:
        verdict = "✅ passed" if r.get("accepted") else "❌ " + "; ".join(r.get("problems") or [])
        L.append("| %s | %s | %s (%s s) | %s | %s |" % (str(r.get("at", "")).replace("T", " ")[:16], r.get("kind"), r.get("model"), r.get("seconds"),
                                                     _what(r).replace("|", "/"), verdict.replace("|", "/")))
    for ag, A in (data.get("agents") or {}).items():
        L += ["", "## %s: what the mind knows, and how it was proven" % FULL_NAMES.get(ag, ag), ""]
        if A.get("error"):
            L.append("_%s_" % A["error"])
            continue
        L += ["| kind (keyed by what it does) | called | question → answer (by) | met |", "|---|---|---|---|"]
        for k in A.get("kinds") or []:
            qs = "<br>".join(("❓ " if q.get("status") == "open" else "✅ ") + str(q.get("en") or q.get("th")) +
                             ("" if q.get("status") == "open" else " → %s (%s)" % (q.get("answer_en") or q.get("answer_th"), q.get("by"))) for q in k.get("asking") or [])
            L.append("| `%s` | %s | %s | %s |" % (k["key"].replace("kind|", ""), k.get("label_en") or k.get("label_th"), qs, k.get("met")))
        if A.get("proposals"):
            L += ["", "Processes a model proposed (H4): " + "; ".join("%s (%s, tries %s, answered %s, learnt %s)" % (p.get("en"), p.get("from"), p.get("tries"), p.get("answered"), p.get("learnt"))
                                                                  for p in A["proposals"])]
    if data.get("for_a_person"):
        L += ["", "## Needs a person", ""] + ["- %s %s: %s" % (p.get("agent") or "—", p.get("label_en") or p.get("cell"), p.get("why")) for p in data["for_a_person"]]
    return "\n".join(L) + "\n"


def snapshot(core: Core, cfg: Dict[str, Any], agents: Iterable[str], root: str = "") -> Dict[str, Any]:
    data = build(core, cfg, agents, root)
    data["snapshot_at"] = time.strftime("%Y-%m-%d %H:%M %z")
    return data
