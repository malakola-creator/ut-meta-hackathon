"""SAM 3.1 over the Meta Model API: cut things out of a picture by a short noun phrase.

The API streams the result over the OpenAI SDK's Responses API; Meta's ``meta_sam_parser`` reads the stream into boxes and masks. A mask
covers its own bounds only, so it is placed back into the whole picture here. The key is read from ``config.llm.meta.key_file``
(or MODEL_API_KEY) and never printed. Needs the ``openai`` and ``meta_sam_parser`` packages (the ut-meta env).
"""
from __future__ import annotations

import base64
import os
from typing import Any, AsyncIterator, Dict, List

MODEL = "sam-3.1"


def _key(cfg: Dict[str, Any]) -> str:
    c = (cfg.get("llm") or {}).get("meta") or {}
    key = os.environ.get(str(c.get("key_env") or "MODEL_API_KEY"), "")
    if not key and c.get("key_file"):
        key = open(os.path.expanduser(str(c["key_file"])), encoding="utf-8").read().strip()
    if not key:
        raise RuntimeError("no Meta Model API key: set MODEL_API_KEY or config.llm.meta.key_file")
    return key


async def _events(stream: Any) -> AsyncIterator[Dict[str, Any]]:
    """The SDK's events as plain dicts; the API does not send ``response.output_text.done``, which the parser needs to close a lane,
    so it is made from ``response.content_part.done`` (as Meta's cookbook does)."""
    closed = set()
    async for ev in stream:
        d = ev.model_dump() if hasattr(ev, "model_dump") else dict(ev)
        lane = (d.get("item_id"), d.get("output_index"), d.get("content_index"))
        if d.get("type") == "response.output_text.done":
            if lane not in closed:
                closed.add(lane)
                yield d
            continue
        yield d
        part = d.get("part")
        if d.get("type") == "response.content_part.done" and lane not in closed and isinstance(part, dict) \
                and part.get("type") == "output_text" and isinstance(part.get("text"), str):
            closed.add(lane)
            yield {"type": "response.output_text.done", "item_id": d.get("item_id"), "output_index": d.get("output_index"),
                   "content_index": d.get("content_index"), "text": part["text"]}


async def segment(cfg: Dict[str, Any], png: bytes, concept: str) -> List[Dict[str, Any]]:
    """Every object SAM 3.1 finds for ``concept`` in the picture: [{"box": (l, t, r, b), "mask": bool array (h, w)}]."""
    import numpy as np
    from contextlib import aclosing
    from meta_sam_parser import decode_mask_to_raster, image_segmentation_format, parse_responses_stream
    from openai import AsyncOpenAI
    from PIL import Image
    import io
    w, h = Image.open(io.BytesIO(png)).size
    url = "data:image/png;base64," + base64.b64encode(png).decode("ascii")
    async with AsyncOpenAI(base_url="https://api.meta.ai/v1", api_key=_key(cfg)) as api:
        stream = await api.responses.create(model=MODEL, stream=True, input=[{"type": "message", "role": "user", "content": [
            {"type": "input_text", "text": concept.strip()}, {"type": "input_image", "image_url": url}]}])
        async with stream, aclosing(_events(stream)) as evs:
            res = await parse_responses_stream(evs, image_segmentation_format()).final_result()
    out = []
    for rec in res.records:
        if rec.kind != "mask":
            continue
        local = np.frombuffer(decode_mask_to_raster(rec.mask), dtype=np.uint8).reshape(rec.mask.height, rec.mask.width) > 0
        full = np.zeros((h, w), dtype=bool)
        b = rec.bounds
        full[b.top:b.top + local.shape[0], b.left:b.left + local.shape[1]] = local[:h - b.top, :w - b.left]
        out.append({"box": (b.left, b.top, b.right, b.bottom), "mask": full})
    return out
