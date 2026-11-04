"""Reading a page of free text into the lines a book on ultimateTruth's shelf is made of (spec/books.json).

Today the core's books are written by hand as data. The model turns plain prose into the two kinds of line the core can take from
any page: a ``word`` (a name and what such a thing does, matched later to a kind the body has watched) and a ``note`` (kept as read).
Food facts and places in a page come back as ``note`` until the core has a gate for them (docs/plan.md, H3). Every line needs Thai
and English, and a word's meaning may only use the keys the body can observe.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Tuple

from .llm import Llm

SYSTEM = ("You turn a page of a book into lines for an embodied agent's bookshelf. Answer JSON: {\"lines\": [ "
          "{\"kind\": \"word\", \"en\": str, \"th\": str (Thai script), \"desc\": {\"moves_self\": bool, \"came_closer\": bool, "
          "\"touched\": bool, \"food\": bool} (only the keys the page says)} | {\"kind\": \"note\", \"en\": str, \"th\": str (Thai script)} ]}. "
          "One line per fact. Use only what the page says.")
DESC_KEYS = ("moves_self", "came_closer", "touched", "food")
THAI = re.compile(r"[฀-๿]")


def check_line(line: Any) -> List[str]:
    if not isinstance(line, dict):
        return ["a line is not an object"]
    problems = []
    kind = line.get("kind")
    if kind not in ("word", "note"):
        problems.append("kind %r is not word or note" % kind)
    for k in ("en", "th"):
        if not isinstance(line.get(k), str) or not line[k].strip():
            problems.append("%s is missing" % k)
    if isinstance(line.get("th"), str) and line["th"].strip() and not THAI.search(line["th"]):
        problems.append("th is not Thai")
    if kind == "word":
        desc = line.get("desc")
        if not isinstance(desc, dict) or not desc:
            problems.append("a word needs desc")
        else:
            for k, v in desc.items():
                if k not in DESC_KEYS:
                    problems.append("desc key %r is not something the body can observe" % k)
                elif not isinstance(v, bool):
                    problems.append("desc %r must be true or false" % k)
    return problems


def propose(llm: Llm, page: str) -> Tuple[List[Dict[str, Any]], float, List[str], Dict[str, Any]]:
    answer, seconds = llm.ask(SYSTEM, page)
    lines = answer.get("lines")
    if not isinstance(lines, list) or not lines:
        return [], seconds, ["no lines"], answer
    good, problems = [], []
    for i, line in enumerate(lines):
        p = check_line(line)
        if p:
            problems += ["line %d: %s" % (i, x) for x in p]
        else:
            good.append({k: line[k] for k in ("kind", "th", "en", "desc") if k in line})
    return good, seconds, problems, answer
