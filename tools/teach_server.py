"""Point and say, in a browser: a map of the house, click a thing, say (or type) what it is called.

    ~/miniforge3/envs/ut-meta/bin/python tools/teach_server.py [--port 8443] [--agent vhum]

Serves web/teach.html over HTTPS with a self-signed certificate (made once in data/certs; the browser asks to accept it) because a
browser lets a page use the microphone only on a secure origin. Talks to the platform over its HTTP API (config core.url), to salika
for Thai speech (config salika.url, default http://127.0.0.1:8790) and to the language model of config.llm.

There is no login: it is a demo on the owner's own network, and anyone who can reach it can teach the body a name. Keep it on
127.0.0.1 (--host) unless a phone needs it, and for the phone set TEACH_TOKEN (environment): a teaching is then taken only with
that word in the form field ``token``, which the pages take from the address (https://host:8443/?token=WORD).
"""
import argparse
import os
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from flask import Flask, Response, jsonify, request, send_from_directory

from utmeta import config, proof, proposals
from utmeta.core_client import Core, CoreError
from utmeta.llm import Llm, LlmError
from utmeta.teach import teach, to_wav16k, transcribe

ap = argparse.ArgumentParser()
ap.add_argument("--port", type=int, default=8443)
ap.add_argument("--agent", default="vhum")
ap.add_argument("--host", default="0.0.0.0")
ap.add_argument("--backend", default=None, help="a config.llm backend (glimmer, baseten, meta, ...); default: config.llm.backend")
a = ap.parse_args()
cfg = config.load()
if a.backend:
    cfg["llm"]["backend"] = a.backend
core, llm = Core(cfg), Llm(cfg["llm"])
SALIKA = str((cfg.get("salika") or {}).get("url", "http://127.0.0.1:8790"))
TOKEN = os.environ.get("TEACH_TOKEN", "")                                   # never printed, never written
# the CC0 models and textures the platform's Blender view already downloaded (Poly Haven), served read-only to the VR page
ASSETS = os.path.expanduser(str((cfg.get("xr") or {}).get("assets_dir", "~/.config/blender/4.2/datafiles/ultimatetruth_assets")))
WEB = os.path.join(config.ROOT, "web")
app = Flask(__name__)


label = proof.label


@app.get("/")
def page():
    return send_from_directory(WEB, "teach.html")


@app.get("/xr")
def page_xr():
    """The same, standing in the house in VR (WebXR: open it in the Meta Quest Browser)."""
    return send_from_directory(WEB, "teach_xr.html")


@app.get("/assets/<path:path>")
def assets(path):
    return send_from_directory(ASSETS, path, max_age=86400)


@app.get("/static")
def static_scene():
    """What does not change: the rooms, the renderer's asset list (the platform's /api/scene/static)."""
    return jsonify(core._req("GET", "/api/scene/static"))


@app.get("/scene")
def scene():
    s = core.scene()
    return jsonify({"walls": [o.get("corners") for o in s.get("obstacles") or [] if o.get("corners")],
                    "boxes": [{k: o.get(k) for k in ("name", "x", "y", "yaw", "size", "corners", "rgba")} for o in s.get("obstacles") or []],
                    "arena_half": s.get("arena_half"),
                    "things": [{k: t.get(k) for k in ("id", "kind", "x", "y", "state", "hidden", "yaw", "parent", "radius")} for t in s.get("stimuli") or []
                               if not t.get("hidden") and t.get("kind") not in ("soil",)],
                    "bodies": [{k: b.get(k) for k in ("key", "x", "y", "yaw")} for b in s.get("agents") or []]})


@app.get("/thing/<int(signed=True):sid>")
def thing(sid):
    agent = request.args.get("agent") or a.agent
    try:
        t = core.thing_of(sid, agent)
    except CoreError as exc:
        return jsonify({"ok": False, "why": "met" if "404" in str(exc) else str(exc)})
    cell = core.things(agent).get(t["cell"]) or {}
    th, en = label(cell)
    asking = [{"what": w, "th": q.get("th"), "en": q.get("en"), "status": q.get("status"), "by": q.get("by", "")} for w, q in (cell.get("asking") or {}).items()]
    return jsonify({"ok": True, "thing": t, "label_th": th, "label_en": en, "asking": asking, "looks": cell.get("looks") or []})


@app.get("/thumb")
def thumb():
    try:
        png = core._req("GET", "/api/things/thumb", query={"id": request.args.get("look", ""), "agent": request.args.get("agent") or a.agent}, raw=True)
    except CoreError:
        return Response(status=404)
    return Response(png, mimetype="image/png")


@app.post("/teach")
def teach_route():
    if TOKEN and request.form.get("token", "") != TOKEN:
        return jsonify({"ok": False, "stage": "token", "why": "this server takes a teaching only with its token (TEACH_TOKEN; add ?token=... to the address)"}), 403
    agent = request.form.get("agent") or a.agent
    sid = int(request.form.get("sid", "0"))
    said, heard = (request.form.get("text") or "").strip(), None
    audio = request.files.get("audio")
    try:
        if audio is not None:
            heard = transcribe(to_wav16k(audio.read()), SALIKA)
            said = str(heard.get("text", "")).strip()
        if not said:
            return jsonify({"ok": False, "stage": "words", "why": "nothing was heard"})
        out = teach(core, llm, sid, said, agent)
    except (ValueError, CoreError, LlmError, OSError) as exc:
        return jsonify({"ok": False, "stage": "error", "why": str(exc)})
    out["heard"] = heard
    problems = list(out.get("problems") or []) + ([out["why"]] if out.get("why") else [])
    proposals.record(cfg, "teach", llm.name, float(out.get("seconds") or 0.0),                 # every teaching, kept with how it went
                     {"said": said, "by_voice": heard is not None, "sid": sid, "agent": agent, "cell": (out.get("thing") or {}).get("cell")},
                     out.get("answer"), [] if out.get("ok") else (problems or ["not taken"]))
    return jsonify(out)


@app.get("/asking")
def asking():
    """What the body wonders about now (H6): the VR page marks those things with a question."""
    try:
        return jsonify({"ok": True, "asking": core.asking(request.args.get("agent") or a.agent)})
    except CoreError as exc:
        return jsonify({"ok": False, "why": str(exc), "asking": []})


@app.get("/proof")
def proof_page():
    return send_from_directory(WEB, "proof.html")


@app.get("/proofdata")
def proof_data():
    """The proof register: how everything the mind holds from outside was proven, and every model proposal with its verdicts."""
    return jsonify(proof.build(core, cfg, ("vhum", "mehum", "vcat"), str(config.ROOT)))


def certificate():
    d = os.path.join(config.ROOT, "data", "certs")
    crt, key = os.path.join(d, "teach.crt"), os.path.join(d, "teach.key")
    if not (os.path.exists(crt) and os.path.exists(key)):
        os.makedirs(d, exist_ok=True)
        subprocess.run(["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-days", "30", "-subj", "/CN=ut-meta-teach",
                        "-keyout", key, "-out", crt], check=True, capture_output=True)
        os.chmod(key, 0o600)
    return crt, key


if __name__ == "__main__":
    print("point and say: https://<this machine>:%d  (model %s, agent %s)" % (a.port, llm.name, a.agent))
    app.run(host=a.host, port=a.port, ssl_context=certificate(), threaded=True)
