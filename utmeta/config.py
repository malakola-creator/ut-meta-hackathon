"""Settings: ``config.json`` at the repo root, overridden by ``config.local.json`` (git-ignored) when present.

``core.path`` is where ultimateTruth lives on this machine. The hackathon repo never copies it: it talks to the running
dashboard over HTTP and imports the core only for local tools (rendering the eye, reading the chip's primitives).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parent.parent


def _merge(a: Dict[str, Any], b: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(a)
    for k, v in b.items():
        out[k] = _merge(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else v
    return out


def load() -> Dict[str, Any]:
    cfg = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
    local = ROOT / "config.local.json"
    if local.exists():
        cfg = _merge(cfg, json.loads(local.read_text(encoding="utf-8")))
    return cfg


def core_path(cfg: Dict[str, Any]) -> Path:
    return (ROOT / cfg["core"]["path"]).resolve()


def import_core(cfg: Dict[str, Any]) -> None:
    """Make ``import ultimatetruth`` work for the local tools (not needed by the sidecar's HTTP side)."""
    src = str(core_path(cfg) / "src")
    if src not in sys.path:
        sys.path.insert(0, src)
