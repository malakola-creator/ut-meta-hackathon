"""Talking to a running ultimateTruth over its HTTP API — the only way the sidecar touches the mind.

Reads need nothing. Writes from another machine need the dashboard's write token (header ``X-UT-Token``); it comes from the
environment variable named in ``config.core.token_env`` and is never printed.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional


class CoreError(RuntimeError):
    pass


class Core:
    def __init__(self, cfg: Dict[str, Any]) -> None:
        self.url = str(cfg["core"]["url"]).rstrip("/")
        self.token = os.environ.get(str(cfg["core"].get("token_env", "")), "")

    def _req(self, method: str, path: str, body: Any = None, query: Optional[Dict[str, Any]] = None, raw: bool = False) -> Any:
        url = self.url + path + ("?" + urllib.parse.urlencode(query) if query else "")
        data = None if body is None else (body if isinstance(body, bytes) else json.dumps(body).encode("utf-8"))
        headers = {"Content-Type": "image/png" if isinstance(body, bytes) else "application/json"}
        if self.token and method != "GET":
            headers["X-UT-Token"] = self.token
        try:
            with urllib.request.urlopen(urllib.request.Request(url, data, headers, method=method), timeout=30) as r:
                return r.read() if raw else json.load(r)
        except urllib.error.HTTPError as exc:
            raise CoreError("%s %s -> HTTP %d: %s" % (method, path, exc.code, exc.read()[:300].decode("utf-8", "replace"))) from None
        except urllib.error.URLError as exc:
            raise CoreError("ultimateTruth is not reachable at %s (%s)" % (self.url, exc.reason)) from None

    def health(self) -> Dict[str, Any]:
        return self._req("GET", "/api/health")

    def agents(self) -> List[Dict[str, Any]]:
        return self._req("GET", "/api/agents").get("agents", [])

    def store(self, name: str, agent: Optional[str] = None) -> Any:
        """One of the deep brain's stores (/api/orin/<store>): its ``value``."""
        return self._req("GET", "/api/orin/" + name, query={"agent": agent} if agent else None).get("value")

    def things(self, agent: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
        return (self.store("things", agent) or {}).get("cells") or {}

    def camera_png(self) -> bytes:
        return self._req("GET", "/api/camera.png", raw=True)

    def thumb_png(self, look: str, agent: Optional[str] = None) -> bytes:
        """The picture the eye kept of a look (the platform's /api/things/thumb)."""
        q: Dict[str, Any] = {"id": look}
        if agent:
            q["agent"] = agent
        return self._req("GET", "/api/things/thumb", query=q, raw=True)

    def eye_png(self, agent: Optional[str] = None, w: int = 320, h: int = 240) -> bytes:
        """What a body's eye sees now (hook H1)."""
        q: Dict[str, Any] = {"w": w, "h": h}
        if agent:
            q["agent"] = agent
        return self._req("GET", "/api/eye.png", query=q, raw=True)

    def scene(self) -> Dict[str, Any]:
        """The house as it is now (walls, things, bodies): the platform's /api/scene."""
        return self._req("GET", "/api/scene")

    def thing_of(self, sid: int, agent: Optional[str] = None) -> Dict[str, Any]:
        """Which kind in the body's thing memory a thing in the world is (hook H5)."""
        return self._req("GET", "/api/orin/things/by-stimulus/%d" % int(sid), query={"agent": agent} if agent else None)

    def asking(self, agent: Optional[str] = None) -> List[Dict[str, Any]]:
        """What the body still wonders about the things it tracks, nearest in view first (hook H6)."""
        return self._req("GET", "/api/orin/things/asking", query={"agent": agent} if agent else None).get("asking", [])

    def proposals(self, agent: Optional[str] = None) -> List[Dict[str, Any]]:
        """The processes proposed from outside that the body's solver holds, and how they fared for real (hook H4)."""
        return self._req("GET", "/api/orin/proposals", query={"agent": agent} if agent else None).get("proposals", [])

    def edits(self, agent: Optional[str] = None) -> List[Dict[str, Any]]:
        """The audit of changes made to the deep brain from outside (who, when, what)."""
        return self._req("GET", "/api/orin/edits", query={"agent": agent} if agent else None).get("edits", [])

    def name_thing(self, key: str, th: str, en: str, source: str, agent: Optional[str] = None) -> Dict[str, Any]:
        """Give a name to a kind the body has learnt (hook H2): it answers the kind's standing question "what is it called" (#39 on the platform)."""
        return self._req("POST", "/api/orin/things/%s/name" % urllib.parse.quote(key, safe=""), {"th": th, "en": en, "from": source},
                         query={"agent": agent} if agent else None)
