"""The deep brain's language: one ``ask(system, user) -> (dict, seconds)`` over three backends.

- ``ollama``  — a Meta open-weights Llama served locally (http://127.0.0.1:11434, ``ollama serve``); works offline, no key.
- ``openai``  — any OpenAI-compatible chat endpoint: the Llama API (https://api.llama.com/compat/v1) or the Meta Model API
                (Muse Spark) once the hackathon portal gives its URL. The key is read from the environment variable named in
                ``config.llm.openai.key_env`` and is never logged or printed.
- ``glimmer`` — Muse Glimmer 30B (open weights) on a llama.cpp server, here the Jetson AGX Orin on the robot's side. The chat
                template is applied by the server (/apply-template); the answer is forced onto the channel to the user (no long
                reasoning first, which costs ~100 s at ~6 tokens/s) and constrained to a JSON object by the server's grammar. A LoRA
                the server carries for other work is scaled to ``lora_scale`` (0 = the base model) for these requests only.
- ``fake``    — canned answers for tests.

Every answer must be a JSON object; a reply that is not one raises ``LlmError`` (the callers validate the content).
``images`` (PNG bytes) go with the user's message: llama.cpp's multimodal data, an OpenAI image_url part, Ollama's images list.
"""
from __future__ import annotations

import base64
import json
import os
import time
import urllib.request
from typing import Any, Callable, Dict, Optional, Sequence, Tuple


class LlmError(RuntimeError):
    pass


def _post(url: str, body: Dict[str, Any], headers: Dict[str, str], timeout: float) -> Dict[str, Any]:
    req = urllib.request.Request(url, json.dumps(body).encode("utf-8"), dict({"Content-Type": "application/json"}, **headers))
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def _object(text: str) -> Dict[str, Any]:
    try:
        out = json.loads(text)
    except (TypeError, ValueError) as exc:
        raise LlmError("the model did not answer JSON: %r" % str(text)[:200]) from exc
    if not isinstance(out, dict):
        raise LlmError("the model answered JSON that is not an object")
    return out


class Llm:
    def __init__(self, cfg: Dict[str, Any], fake: Optional[Callable[[str, str], Dict[str, Any]]] = None) -> None:
        self.cfg = cfg
        self.backend = "fake" if fake is not None else str(cfg.get("backend", "ollama"))
        self.fake = fake

    @property
    def name(self) -> str:
        if self.backend == "fake":
            return "fake"
        return "%s:%s" % (self.backend, (self.cfg.get(self.backend) or {}).get("model", "?"))

    def ask(self, system: str, user: str, images: Sequence[bytes] = ()) -> Tuple[Dict[str, Any], float]:
        t = time.perf_counter()
        if self.backend == "fake":
            return dict(self.fake(system, user) if not images else self.fake(system, user, images)), 0.0
        timeout = float(self.cfg.get("timeout_s", 300))
        temperature = float(self.cfg.get("temperature", 0.2))
        b64 = [base64.b64encode(bytes(i)).decode("ascii") for i in images]
        content: Any = user
        sect = self.cfg.get(self.backend) if isinstance(self.cfg.get(self.backend), dict) else {}
        if b64 and (self.backend in ("glimmer", "openai") or sect.get("kind") == "openai"):
            content = [{"type": "image_url", "image_url": {"url": "data:image/png;base64," + b}} for b in b64] + [{"type": "text", "text": user}]
        msgs = [{"role": "system", "content": system}, {"role": "user", "content": content}]
        if b64 and self.backend == "ollama":
            msgs[1]["images"] = b64
        if self.backend == "ollama":
            c = self.cfg["ollama"]
            r = _post(c["url"].rstrip("/") + "/api/chat", {"model": c["model"], "stream": False, "format": "json",
                                                          "options": {"temperature": temperature}, "messages": msgs}, {}, timeout)
            return _object((r.get("message") or {}).get("content")), time.perf_counter() - t
        if self.backend == "glimmer":
            c = self.cfg["glimmer"]
            base = c["url"].rstrip("/")
            prompt = _post(base + "/apply-template", {"messages": msgs, "chat_template_kwargs": {"reasoning_strength": c.get("reasoning_strength", "none")}},
                           {}, timeout)["prompt"] + c.get("answer_channel", " to=user<|message|>")
            body = {"prompt": {"prompt_string": prompt, "multimodal_data": b64} if b64 else prompt, "n_predict": int(c.get("max_tokens", 600)), "temperature": temperature, "json_schema": {"type": "object"}}
            if c.get("lora_scale") is not None:
                body["lora"] = [{"id": 0, "scale": float(c["lora_scale"])}]
            r = _post(base + "/completion", body, {}, timeout)
            return _object(r.get("content")), time.perf_counter() - t
        c = self.cfg.get(self.backend) if isinstance(self.cfg.get(self.backend), dict) else {}
        if self.backend == "openai" or c.get("kind") == "openai":         # any OpenAI-compatible endpoint (Meta Model API, Baseten, ...)
            c = c or self.cfg["openai"]
            if not c.get("url"):
                raise LlmError("config.llm.%s.url is empty: put the endpoint there" % self.backend)
            key = os.environ.get(str(c.get("key_env", "")), "")
            if not key and c.get("key_file"):                               # a key kept in a file only the user can read (never printed)
                try:
                    key = open(os.path.expanduser(str(c["key_file"])), encoding="utf-8").read().strip()
                except OSError:
                    key = ""
            if not key:
                raise LlmError("no API key: set %s or key_file for %s" % (c.get("key_env"), self.backend))
            body = {"model": c["model"], "temperature": temperature, "messages": msgs, "response_format": {"type": "json_object"}}
            if c.get("max_tokens"):
                body["max_tokens"] = int(c["max_tokens"])
            body.update(c.get("extra") or {})                              # e.g. reasoning_effort for a model that thinks first
            url, headers = c["url"].rstrip("/") + "/chat/completions", {"Authorization": "Bearer " + key}
            r = _post(url, body, headers, timeout)
            choice = (r.get("choices") or [{}])[0]
            content = (choice.get("message") or {}).get("content")
            if not content:                                                 # a model that thinks first (Muse Spark 1.3) may spend the whole
                room = int(body.get("max_tokens") or 4000)                  # budget on its reasoning and answer no content: once more, twice the room
                body["max_tokens"] = min(2 * room, 16000)
                r = _post(url, body, headers, timeout)
                choice = (r.get("choices") or [{}])[0]
                content = (choice.get("message") or {}).get("content")
            if not content:
                details = (r.get("usage") or {}).get("completion_tokens_details") or {}
                raise LlmError("the model answered no content (finish_reason %r, reasoning tokens %s, max_tokens %s)"
                               % (choice.get("finish_reason"), details.get("reasoning_tokens"), body.get("max_tokens")))
            return _object(content), time.perf_counter() - t
        raise LlmError("unknown backend %r (ollama, glimmer, openai, or a config.llm section with kind openai, fake)" % self.backend)
