"""Look at a thing the body wonders about, cut it out with SAM 3.1 and name it (utmeta/look.py).

    ~/miniforge3/envs/ut-meta/bin/python tools/look_and_name.py [--agent vhum] [--sid ID] [--backend baseten] [--give] [--keep data/look]
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from utmeta import config
from utmeta.core_client import Core
from utmeta.llm import Llm
from utmeta.look import look_and_name

ap = argparse.ArgumentParser()
ap.add_argument("--agent", default="vhum")
ap.add_argument("--sid", type=int, default=None)
ap.add_argument("--backend", default=None)
ap.add_argument("--give", action="store_true", help="hand an accepted name to the mind (hook H2)")
ap.add_argument("--keep", default=None, help="save the picture and the cut-out here")
ap.add_argument("--force", action="store_true", help="look at --sid even when the body does not see it now")
ap.add_argument("--near", action="store_true", help="a test view from 1.4 m off the thing (not the body's eye)")
a = ap.parse_args()
cfg = config.load()
if a.backend:
    cfg["llm"]["backend"] = a.backend
out = look_and_name(cfg, Core(cfg), Llm(cfg["llm"]), a.agent, a.sid, a.give, a.keep, a.force, a.near)
print(json.dumps(out, ensure_ascii=False, indent=1))
