"""Freeze the proof register: the live platform's stores and data/proposals.jsonl → data/proof_snapshot.json (what the public page
serves, tools/proof_site.py) and docs/proof.md (GitHub shows it without any server).

    python tools/proof_snapshot.py [--agents vhum,mehum,vcat] [--json data/proof_snapshot.json] [--md docs/proof.md]

Nothing private goes in: the stores hold kinds, names, questions and the proposals log, no addresses or keys; the script still
refuses to write a snapshot that contains a LAN address or a home path.
"""
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from utmeta import config, proof
from utmeta.core_client import Core

PRIVATE = re.compile(r"10\.0\.8\.\d+|/home/[a-z0-9]+|[A-Za-z]:\\\\Users|[a-z0-9]+@10\.|Bearer |ak-[A-Za-z0-9]{10,}")

ap = argparse.ArgumentParser()
ap.add_argument("--agents", default="vhum,mehum,vcat")
ap.add_argument("--json", default="data/proof_snapshot.json")
ap.add_argument("--md", default="docs/proof.md")
a = ap.parse_args()
cfg = config.load()
data = proof.snapshot(Core(cfg), cfg, [s.strip() for s in a.agents.split(",") if s.strip()], str(config.ROOT))
text = json.dumps(data, ensure_ascii=False, indent=1)
hit = PRIVATE.search(text)
if hit:
    print("refusing: the snapshot holds something private: %r" % hit.group(0), file=sys.stderr)
    sys.exit(1)
os.makedirs(os.path.dirname(os.path.join(config.ROOT, a.json)), exist_ok=True)
open(os.path.join(config.ROOT, a.json), "w", encoding="utf-8").write(text)
open(os.path.join(config.ROOT, a.md), "w", encoding="utf-8").write(proof.markdown(data, data["snapshot_at"]))
print("snapshot %s: %d log rows, agents %s, needs a person %d → %s, %s" % (data["snapshot_at"], len(data["log"]),
      {k: ("error" if v.get("error") else len(v.get("kinds") or [])) for k, v in data["agents"].items()}, len(data["for_a_person"]), a.json, a.md))
