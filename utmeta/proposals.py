"""Every proposal the language model makes is kept, accepted or not, with why it was refused — the record the demo shows.

The mind never takes a proposal straight from here: a name, a book line or a procedure goes back into ultimateTruth only through
a gate on the core's side (see docs/plan.md, the hooks H2–H4), and experience still overrides it.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, List

from .config import ROOT


def record(cfg: Dict[str, Any], kind: str, model: str, seconds: float, inp: Any, out: Any, problems: List[str]) -> Dict[str, Any]:
    entry = {"at": time.strftime("%Y-%m-%dT%H:%M:%S"), "kind": kind, "model": model, "seconds": round(seconds, 2),
             "accepted": not problems, "problems": problems, "input": inp, "output": out}
    path = ROOT / cfg.get("proposals", "data/proposals.jsonl")
    path.parent.mkdir(parents=True, exist_ok=True)
    with Path(path).open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry
