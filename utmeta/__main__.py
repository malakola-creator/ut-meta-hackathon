"""Command line: python -m utmeta {health, name, eye, read, compose}

  health                    is ultimateTruth running, and which language backend is set
  name [--agent vhum] [-n 3] [--give] [--picture]
                            propose names for the kinds of things the body has learnt (read from the live mind);
                            --give hands every accepted name to the mind (hook H2); --picture shows the model the
                            thumbnail the eye kept of each look
  eye OUT.png [--agent vhum] save what the body's eye sees now (hook H1)
  read FILE.txt             turn a page of prose into bookshelf lines
  compose [--situation J]   propose a procedure from the chip's primitives (default: stuck in a corner)

Every proposal goes to data/proposals.jsonl with the reasons it was refused, if it was.
"""
from __future__ import annotations

import argparse
import json
import sys

from . import composer, config, namer, proposals, reader
from .core_client import Core, CoreError
from .llm import Llm, LlmError

CORNER = {"problem": "stuck in a corner", "front_clear_cm": 45, "left_clear_cm": 40, "right_clear_cm": 300, "behind_seen": "unknown"}


def _show(entry) -> None:
    mark = "accepted" if entry["accepted"] else "refused: " + "; ".join(entry["problems"])
    print("[%s %s %.1f s] %s" % (entry["kind"], entry["model"], entry["seconds"], mark))
    print("  " + json.dumps(entry["output"], ensure_ascii=False)[:600])


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="utmeta")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("health")
    p = sub.add_parser("name")
    p.add_argument("--agent", default=None)
    p.add_argument("-n", type=int, default=3)
    p.add_argument("--give", action="store_true")
    p.add_argument("--picture", action="store_true")
    p = sub.add_parser("eye")
    p.add_argument("out")
    p.add_argument("--agent", default=None)
    p = sub.add_parser("read")
    p.add_argument("file")
    p = sub.add_parser("compose")
    p.add_argument("--situation", default=None, help="a JSON object; default: stuck in a corner")
    a = ap.parse_args(argv)
    cfg = config.load()
    llm = Llm(cfg["llm"])
    try:
        if a.cmd == "health":
            print(json.dumps({"core": Core(cfg).health(), "llm": llm.name}, ensure_ascii=False))
        elif a.cmd == "name":
            core = Core(cfg)
            for key, c in [(k, c) for k, c in core.things(a.agent).items() if c.get("known")][: a.n]:
                pic = None
                if a.picture:
                    try:
                        pic = core.thumb_png(str(c.get("look")), a.agent)
                    except CoreError:
                        print("  (no picture kept of %s)" % c.get("look"))
                ans, s, probs, obs = namer.propose(llm, c, cfg["namer"]["max_name_chars"], pic)
                print("%s (now: %s)" % (c.get("look"), c.get("name_en")))
                _show(proposals.record(cfg, "name", llm.name, s, dict(obs, key=key), ans, probs))
                if a.give and not probs:
                    core.name_thing(key, ans["name_th"].strip(), ans["name_en"].strip(), llm.name[:40], a.agent)
                    print("  given to the mind")
        elif a.cmd == "eye":
            png = Core(cfg).eye_png(a.agent, cfg["eye"]["width"], cfg["eye"]["height"])
            open(a.out, "wb").write(png)
            print("saved %s (%d bytes)" % (a.out, len(png)))
        elif a.cmd == "read":
            page = open(a.file, encoding="utf-8").read()
            lines, s, probs, raw = reader.propose(llm, page)
            _show(proposals.record(cfg, "read", llm.name, s, page, raw, probs))
            print("lines the shelf could take: %d" % len(lines))
        elif a.cmd == "compose":
            prims, exits = composer.protocol_keys(cfg)
            situation = json.loads(a.situation) if a.situation else CORNER
            ans, s, probs = composer.propose(llm, situation, prims, exits, cfg["composer"])
            _show(proposals.record(cfg, "compose", llm.name, s, situation, ans, probs))
    except (CoreError, LlmError) as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
