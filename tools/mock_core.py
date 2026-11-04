"""A stand-in for the platform's HTTP API, from recorded answers (samples/), so this repo runs without ultimateTruth.

    python tools/mock_core.py [--port 5055]      # then set core.url to http://127.0.0.1:5055 in config.local.json

Serves /api/health, /api/agents, /api/orin/things, /api/eye.png, and takes POST /api/orin/things/<key>/name (kept in memory,
checked like the platform does: known kinds only, both Thai and English or neither).
"""
import argparse
import json
import os
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

SAMPLES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "samples")
THINGS = json.load(open(os.path.join(SAMPLES, "things.json"), encoding="utf-8"))
EYE = open(os.path.join(SAMPLES, "eye.png"), "rb").read()


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype="application/json"):
        data = body if isinstance(body, bytes) else json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        path = urllib.parse.urlparse(self.path).path
        if path == "/api/health":
            return self._send(200, {"ok": True, "provider": "mock", "tick": 0, "running": False, "error": None})
        if path == "/api/agents":
            return self._send(200, {"ok": True, "agents": [{"key": "vhum"}]})
        if path == "/api/orin/things":
            return self._send(200, {"ok": True, "store": "things", "value": THINGS})
        if path == "/api/eye.png":
            return self._send(200, EYE, "image/png")
        self._send(404, {"ok": False, "error": "the mock has no %s" % path})

    def do_POST(self):
        parts = urllib.parse.urlparse(self.path).path.split("/")
        if len(parts) == 6 and parts[1:4] == ["api", "orin", "things"] and parts[5] == "name":
            key = urllib.parse.unquote(parts[4])
            cell = THINGS["cells"].get(key)
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)) or b"{}")
            if cell is None:
                return self._send(404, {"ok": False, "error": "no kind of thing %r" % key})
            if not cell.get("known"):
                return self._send(409, {"ok": False, "error": "the body does not know this kind yet"})
            th, en = str(body.get("th", "")).strip(), str(body.get("en", "")).strip()
            if bool(th) != bool(en):
                return self._send(400, {"ok": False, "error": "both the Thai and the English name are needed"})
            cell.update(given_th=th, given_en=en, given_from=str(body.get("from", "")))
            return self._send(200, {"ok": True, "store": "things", "key": key})
        self._send(404, {"ok": False, "error": "the mock takes no POST to %s" % self.path})

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=5055)
    a = ap.parse_args()
    print("mock platform on http://127.0.0.1:%d" % a.port)
    ThreadingHTTPServer(("127.0.0.1", a.port), Handler).serve_forever()
