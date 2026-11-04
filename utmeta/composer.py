"""Proposing a procedure for the mind chip from the primitives the chip actually has.

The chip's procedures are steps of (primitive, p1, exit condition). The model is told the exact primitives and exit kinds (read
from ultimateTruth's protocol) and the situation; anything outside them is refused here. An accepted proposal is still only a
candidate: on the core's side it must be rehearsed in the mental copy of the world before the chip may use it (docs/plan.md, H4).
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Sequence, Tuple

from .llm import Llm


def recorded_keys() -> Tuple[List[str], List[str]]:
    """(primitives, exit kinds) as recorded from the platform in ``samples/protocol.json``, for a machine without it."""
    from .config import ROOT
    rec = json.loads((ROOT / "samples" / "protocol.json").read_text(encoding="utf-8"))
    return list(rec["primitives"]), list(rec["exit_kinds"])


def protocol_keys(core_cfg: Dict[str, Any]) -> Tuple[List[str], List[str]]:
    """(primitives, exit kinds) from the core's protocol, in the chip's order; from the recorded sample when the platform is
    not on this machine (the sample is a copy of the same enums, so a judge's run composes against the same chip)."""
    try:
        from .config import import_core
        import_core(core_cfg)
        from ultimatetruth.protocol import Protocol
        P = Protocol()
    except Exception:
        return recorded_keys()

    def keys(enum: str) -> List[str]:
        return [v["key"] for _, v in sorted(P.enums[enum].items(), key=lambda kv: int(kv[0]))]
    return keys("primitive"), keys("exit_kind")


def system(prims: Sequence[str], exits: Sequence[str], lo: int, hi: int) -> str:
    return ("You compose a procedure for a robot's mind chip. It may ONLY use these primitives: %s and these exit kinds: %s. "
            "Answer JSON: {\"steps\": [{\"primitive\": str, \"p1\": int, \"exit\": {\"kind\": str, \"value\": int}, \"why\": str}]} "
            "with %d to %d steps." % (list(prims), list(exits), lo, hi))


def check(answer: Dict[str, Any], prims: Sequence[str], exits: Sequence[str], cfg: Dict[str, Any]) -> List[str]:
    steps = answer.get("steps")
    if not isinstance(steps, list):
        return ["no steps"]
    problems = []
    if not cfg["min_steps"] <= len(steps) <= cfg["max_steps"]:
        problems.append("%d steps (wanted %d to %d)" % (len(steps), cfg["min_steps"], cfg["max_steps"]))
    for i, s in enumerate(steps):
        if not isinstance(s, dict):
            problems.append("step %d is not an object" % i)
            continue
        if s.get("primitive") not in prims:
            problems.append("step %d: the chip has no primitive %r" % (i, s.get("primitive")))
        p1 = s.get("p1")
        if not isinstance(p1, int) or isinstance(p1, bool) or not 0 <= p1 <= cfg["p1_max"]:
            problems.append("step %d: p1 %r is not an integer 0..%d" % (i, p1, cfg["p1_max"]))
        ex = s.get("exit") if isinstance(s.get("exit"), dict) else {}
        if ex.get("kind") not in exits:
            problems.append("step %d: the chip has no exit kind %r" % (i, ex.get("kind")))
        v = ex.get("value")
        if not isinstance(v, int) or isinstance(v, bool) or not 0 <= v <= cfg["exit_value_max"]:
            problems.append("step %d: exit value %r is not an integer 0..%d" % (i, v, cfg["exit_value_max"]))
    return problems


def propose(llm: Llm, situation: Dict[str, Any], prims: Sequence[str], exits: Sequence[str],
            cfg: Dict[str, Any]) -> Tuple[Dict[str, Any], float, List[str]]:
    answer, seconds = llm.ask(system(prims, exits, cfg["min_steps"], cfg["max_steps"]), json.dumps(situation))
    return answer, seconds, check(answer, prims, exits, cfg)
