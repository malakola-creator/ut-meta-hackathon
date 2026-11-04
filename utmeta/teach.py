"""Point and say: a person picks a thing in the house and says what it is called; the mind takes the name for the thing's kind.

1. The person's words: Thai speech goes to salika (the owner's own Thai speech-to-text, pre-existing, called over its HTTP API —
   not a Meta model), or typed text is used as it is.
2. The language model (Glimmer / Muse Spark) pulls out the name the person gave, in Thai and English — or says no name was given.
3. A gate checks it (a name in each language, Thai in Thai script, short).
4. Which kind the body grasped that thing as: the platform's hook H5 (the world's id → the thing memory).
5. The name goes in through hook H2. On the platform it answers the kind's standing question "what is it called"
   (``given:voice:<model>``). The body still learns what the thing *does* only by watching it; a kind still asked about takes no name
   (409): the body has to meet and watch it first.
"""
from __future__ import annotations

import json
import re
import subprocess
import urllib.request
import uuid
from typing import Any, Dict, Optional, Tuple

from .core_client import Core, CoreError
from .llm import Llm

SYSTEM = ("A person points at a thing in a house and says something about it (Thai speech, transcribed; it may have small errors). "
          "Pull out the name they give the thing. Answer JSON: {\"named\": bool, \"name_th\": str (Thai script), \"name_en\": str "
          "(the English for the same name), \"heard\": str}. Saying what it is counts as naming it: \"นี่คือ X\", \"อันนี้ X\", "
          "\"X นะ\", \"this is X\" all name it X (name_th is X exactly as said). If they did not say what it is, named is false and the "
          "names are empty. Use only what was said; do not guess a name from anything else.")
THAI = re.compile(r"[฀-๿]")
MAX_CHARS = 40


def to_wav16k(audio: bytes) -> bytes:
    """Whatever the browser recorded (webm / ogg / wav) → 16 kHz mono WAV, with ffmpeg."""
    p = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", "pipe:0", "-ac", "1", "-ar", "16000", "-f", "wav", "pipe:1"],
                       input=audio, capture_output=True, timeout=60)
    if p.returncode != 0 or not p.stdout:
        raise ValueError("the audio could not be read: %s" % p.stderr.decode("utf-8", "replace")[:200])
    return p.stdout


def transcribe(wav: bytes, url: str) -> Dict[str, Any]:
    """Thai speech → text with salika (POST /v1/transcribe, a multipart file)."""
    boundary = uuid.uuid4().hex
    body = (("--%s\r\nContent-Disposition: form-data; name=\"file\"; filename=\"speech.wav\"\r\nContent-Type: audio/wav\r\n\r\n" % boundary).encode()
            + wav + ("\r\n--%s--\r\n" % boundary).encode())
    req = urllib.request.Request(url.rstrip("/") + "/v1/transcribe", body, {"Content-Type": "multipart/form-data; boundary=" + boundary})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def check(answer: Dict[str, Any], said: Optional[str] = None) -> list:
    """A name in each language, Thai in Thai script, short — and the Thai name is words the person said (the model may only pick them
    out: measured 27 Oct, Glimmer Q5 wrote "หุ่ยนยนต์ดูดฝุ่" for "หุ่นยนต์ดูดฝุ่น")."""
    if not answer.get("named"):
        return ["no name was given"]
    problems = []
    for k in ("name_th", "name_en"):
        v = answer.get(k)
        if not isinstance(v, str) or not v.strip():
            problems.append("%s is missing" % k)
        elif len(v) > MAX_CHARS:
            problems.append("%s is longer than %d characters" % (k, MAX_CHARS))
    th = answer.get("name_th")
    if isinstance(th, str) and th.strip() and not THAI.search(th):
        problems.append("name_th is not Thai")
    elif said is not None and isinstance(th, str) and th.strip() and "".join(th.split()) not in "".join(said.split()):
        problems.append("name_th %r is not what was said" % th.strip())
    return problems


def name_from_words(llm: Llm, said: str) -> Tuple[Dict[str, Any], float, list]:
    answer, seconds = llm.ask(SYSTEM, json.dumps({"said": said}, ensure_ascii=False))
    return answer, seconds, check(answer, said)


def teach(core: Core, llm: Llm, sid: int, said: str, agent: Optional[str] = None) -> Dict[str, Any]:
    """The whole step for one pointed thing and what was said about it. Returns what happened at each stage (shown on the page)."""
    out: Dict[str, Any] = {"said": said, "sid": int(sid), "agent": agent, "model": llm.name}
    try:
        thing = core.thing_of(int(sid), agent)                      # H5
    except CoreError as exc:
        out.update(ok=False, stage="thing", why="the body has not met this thing in this life" if "404" in str(exc) else str(exc))
        return out
    out["thing"] = thing
    answer, seconds, problems = name_from_words(llm, said)
    out.update(answer=answer, seconds=round(seconds, 1), problems=problems)
    if problems:
        out.update(ok=False, stage="name")
        return out
    if not thing.get("known"):
        out.update(ok=False, stage="known", why="the body is still asking what this is: it must watch it first (the name is not taken yet)")
        return out
    try:
        core.name_thing(thing["cell"], answer["name_th"].strip(), answer["name_en"].strip(), ("voice:" + llm.name)[:40], agent)   # H2
    except CoreError as exc:
        out.update(ok=False, stage="give", why=str(exc))
        return out
    out.update(ok=True, stage="given", thing=core.thing_of(int(sid), agent))
    return out
