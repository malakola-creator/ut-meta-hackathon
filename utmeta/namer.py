"""Naming a kind of thing from what the body learnt by watching it (things.py cells in ultimateTruth).

The core already gives each known kind a mechanical description ("a thing that moves by itself, not food (a2)"). The model is asked
for a short everyday name in Thai and English, and must say which observations it used. A name that leans on an observation the
body does not have (an unknown, ``None``) is refused: the name may come from language, the meaning must come from watching.

With a picture (the thumbnail the eye kept of the look, /api/things/thumb), the model also sees it; ``picture`` is then one of the
observations it may say it used. The picture is from the simulator's eye: simple shapes, so it can mislead as well as help (measured
in docs/plan.md).
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional, Tuple

from .llm import Llm

SYSTEM = ("You are the deep brain of an embodied agent. Give a short everyday name for a kind of thing from what the body observed it do. "
          "Answer JSON: {\"name_en\": str, \"name_th\": str (Thai script), \"used\": [observation keys you relied on], \"why\": str}. "
          "Use only the observations given; an observation that is null is unknown and must not be used.")
THAI = re.compile(r"[฀-๿]")


PICTURE = (" You also get a small picture of it from the body's eye (a simulator, so things may be drawn as simple shapes);"
           " if you rely on it, list \"picture\" in used.")


def observations(cell: Dict[str, Any], picture: bool = False) -> Dict[str, Any]:
    """What watching showed, as the model sees it (no ids, no names the core made)."""
    m = cell.get("meaning") or {}
    ch = cell.get("changes") or {}
    obs = {"picture": True} if picture else {}
    obs.update({"moves_by_itself": m.get("moves_self"), "came_closer": m.get("came_closer"), "hurt_when_touched": m.get("touched"),
            "is_food": m.get("food"), "changes_look": bool(ch.get("looks", 0)) if ch else None, "size_m": cell.get("size_m"),
            "times_met": cell.get("met")})
    return obs


def check(answer: Dict[str, Any], obs: Dict[str, Any], max_chars: int) -> List[str]:
    problems = []
    for k in ("name_en", "name_th"):
        v = answer.get(k)
        if not isinstance(v, str) or not v.strip():
            problems.append("%s is missing" % k)
        elif len(v) > max_chars:
            problems.append("%s is longer than %d characters" % (k, max_chars))
    if isinstance(answer.get("name_th"), str) and answer["name_th"].strip() and not THAI.search(answer["name_th"]):
        problems.append("name_th is not Thai")
    used = answer.get("used")
    if not isinstance(used, list) or not used:
        problems.append("the answer does not say which observations it used")
    else:
        for k in used:
            if k not in obs:
                problems.append("used %r, which the body never observed" % k)
            elif obs[k] is None:
                problems.append("used %r, which is still unknown" % k)
    return problems


def propose(llm: Llm, cell: Dict[str, Any], max_chars: int = 40,
            picture: Optional[bytes] = None) -> Tuple[Dict[str, Any], float, List[str], Dict[str, Any]]:
    obs = observations(cell, picture is not None)
    shown = {k: v for k, v in obs.items() if k != "picture"}
    answer, seconds = llm.ask(SYSTEM + (PICTURE if picture is not None else ""), json.dumps({"observed": shown}),
                              [picture] if picture is not None else ())
    return answer, seconds, check(answer, obs, max_chars), obs
