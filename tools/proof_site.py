"""The proof register as a public page on Modal, so judges can open it without the platform: web/proof.html plus the frozen
register from tools/proof_snapshot.py (data/proof_snapshot.json). Nothing here talks to the platform or holds a key.

    python tools/proof_snapshot.py                      # freeze the register first (needs the live platform)
    modal deploy tools/proof_site.py                    # → https://<workspace>--ut-meta-proof-web.modal.run
    modal serve tools/proof_site.py                     # a temporary URL while editing
"""
import os

import modal

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
app = modal.App("ut-meta-proof")
image = (modal.Image.debian_slim(python_version="3.12")
         .pip_install("fastapi[standard]==0.115.12")
         .add_local_file(os.path.join(ROOT, "web", "proof.html"), "/root/site/proof.html")
         .add_local_file(os.path.join(ROOT, "data", "proof_snapshot.json"), "/root/site/proofdata.json"))


@app.function(image=image, min_containers=0)
@modal.asgi_app()
def web():
    from fastapi import FastAPI
    from fastapi.responses import HTMLResponse, Response

    html = open("/root/site/proof.html", encoding="utf-8").read()
    data = open("/root/site/proofdata.json", "rb").read()
    api = FastAPI()

    @api.get("/")
    def page():
        return HTMLResponse(html)

    @api.get("/proofdata")
    def proofdata():
        return Response(data, media_type="application/json")

    return api
