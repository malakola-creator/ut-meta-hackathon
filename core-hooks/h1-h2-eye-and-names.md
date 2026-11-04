# Hooks H1 (the eye as a picture) and H2 (a name given to a learnt kind)

Written on 26 Oct 2026 for this project, in the platform repo (ultimateTruth, commit `e38487e`, 2026-10-26 21:04 +0700), and checked live on the same day.

**Only the new code is shown here.** The organisers' FAQ says the submitted repo must be a standalone extract that keeps the existing codebase out. So this file holds:
- each hook's contract;
- the lines that were added, with no surrounding platform code;
- the new test file.

The full change stays in the private platform repo.

## H1: the eye as a picture

`GET /api/eye.png?agent=<name>&w=<px>&h=<px>` → `image/png`

| Part | Behaviour |
|---|---|
| `agent` | The body whose eye is rendered. When it is left out, the single body of the world is used. |
| `w`, `h` | Optional. They default to 320 × 240, and must be integers within the platform's camera limits (otherwise 400). |
| Rendering | Done on the simulation thread, with the eye's own field of view (`tpu.half_fov_deg`). |
| 404 | The world has no eye to render. |
| 503 | The render failed. The error is in the message. |
| Caching | The response is sent with `no-store`. |

Used by `utmeta/core_client.py` (`eye_png`) and by `python -m utmeta eye <out.png>`.

### Added: `dashboard/app.py`, inside `create_app`

```python
    @app.get("/api/eye.png")
    def eye_png():
        """What a body's eye sees (hook H1, 2026-10-26: for an outside eye such as SAM): ?agent=&w=&h= -> image/png, rendered on the
        simulation thread with the eye's own field of view. 404 when the world has no eye to render."""
        sims = getattr(provider, "sims", None)
        agent = request.args.get("agent")
        sim = sims.get(agent) if (sims and agent) else getattr(provider, "sim", None)
        render = getattr(getattr(sim, "world", None), "render_eye", None)
        if not callable(render):
            return failure(404, "this world has no eye to render")
        size = {"w": 320, "h": 240}
        for name in size:
            raw = request.args.get(name)
            if raw is None:
                continue
            try:
                size[name] = int(raw)
            except ValueError:
                return failure(400, "'%s' must be an integer" % name)
            if not CAMERA_MIN_PX <= size[name] <= CAMERA_MAX_PX:
                return failure(400, "'%s' must be between %d and %d" % (name, CAMERA_MIN_PX, CAMERA_MAX_PX))

        def shot():
            from ..world.imagecodec import encode_png
            import numpy as np
            rgb, _root = render(size["w"], size["h"], float(sim.tpu.half_fov_deg))
            return encode_png(np.ascontiguousarray(rgb))
        call = getattr(provider, "call", None)
        res = call(shot) if callable(call) else {"ok": True, "result": shot()}
        if not res.get("ok"):
            return failure(503, "the eye could not render: %s" % res.get("error"))
        return no_store(Response(bytes(res["result"]), mimetype="image/png"))
```

## H2: a name given to a learnt kind

`POST /api/orin/things/<key>/name`, with the body `{"th": "...", "en": "...", "from": "<model>"}`

**What the hook does:**
- The name is kept as `given_th` / `given_en` / `given_from`, beside the mind's own descriptive name, which does not change.
- The name comes from language, and the meaning from watching. The meaning the name was given for is stored with it.
- If later watching changes that meaning, the given name is dropped.
- Every change is audited like a hand edit (`/api/orin/edits`).
- `{"th": "", "en": ""}` removes the name.

| Answer | When |
|---|---|
| 200 | Saved (or removed). Returns `{"store", "key", "entry", "before"}`. |
| 400 | One of these: the body is not an object; only one of Thai / English is given; a field is not a string or is too long. |
| 404 | There is no such kind. |
| 409 | The kind is not known yet, because its question is still open. |

Used by `utmeta/core_client.py` (`name_thing`) and by `python -m utmeta name --give`. A name is given only when it passed the namer's gate.

### Added: `dashboard/app.py`, inside `create_app`

```python
    @app.post("/api/orin/things/<key>/name")
    def orin_thing_name(key: str):
        """A name given from outside to a kind the body has learnt (hook H2, 2026-10-26): {"th", "en", "from"}."""
        def write():
            body, by = orin_body(), orin_by()
            return orin_call(lambda api: api.name_thing(key, body, by))
        return guarded(write)
```

### Added: `orin_api.py`, a new method of `OrinKnowledge`

```python
    def name_thing(self, key: Any, body: Any, by: str = "api") -> Dict[str, Any]:
        """A name given from outside to a kind the body has learnt (2026-10-26, hook H2 of the hackathon sidecar: a language model
        names what watching showed). Kept beside the deep brain's own descriptive name as ``given_th`` / ``given_en`` with where it came
        from and the meaning it was given for: the name comes from language, the meaning from watching — when watching later changes
        the meaning, the given name is dropped (things._answer). ``{"th", "en", "from"}``; ``{"th": "", "en": ""}`` removes it."""
        th = getattr(self.orin, "things", None)
        cell = th.cells.get(str(key)) if th is not None else None
        if cell is None:
            raise OrinApiError(404, "ไม่มีสิ่งที่ชื่อ '%s'" % key, "no kind of thing '%s'" % key)
        if not cell.get("known"):
            raise OrinApiError(409, "ยังไม่รู้ว่าสิ่งนี้คืออะไร (คำถามยังเปิดอยู่) จึงตั้งชื่อไม่ได้", "the body does not know this kind yet (its question is open)")
        if not isinstance(body, dict):
            raise OrinApiError(400, "ต้องส่ง {\"th\", \"en\", \"from\"}", "send {\"th\", \"en\", \"from\"}")
        vals = {}
        for f, top in (("th", LABEL_MAX), ("en", LABEL_MAX), ("from", KEY_STR_MAX)):
            v = body.get(f, "")
            if not isinstance(v, str) or len(v) > top:
                raise OrinApiError(400, "'%s' ต้องเป็นข้อความไม่เกิน %d ตัวอักษร" % (f, top), "'%s' must be a string of at most %d characters" % (f, top))
            vals[f] = v.strip()
        if bool(vals["th"]) != bool(vals["en"]):
            raise OrinApiError(400, "ต้องมีทั้งชื่อไทยและอังกฤษ", "both the Thai and the English name are needed")
        fields = ("given_th", "given_en", "given_from", "given_meaning", "given_life", "edited")
        before = {f: copy.deepcopy(cell.get(f)) for f in fields}
        if vals["th"]:
            cell.update(given_th=vals["th"], given_en=vals["en"], given_from=vals["from"] or str(by)[:KEY_STR_MAX],
                        given_meaning=dict(cell.get("meaning") or {}), given_life=int(self.orin.life), edited=self._stamp(by))
        else:
            for f in fields[:-1]:
                cell.pop(f, None)
        after = {f: copy.deepcopy(cell.get(f)) for f in fields}
        self._audit("patch", "things", str(key), by, before, after)
        return {"store": "things", "key": str(key), "entry": after, "before": before}
```

### Added: `things.py`, in `ThingMemory`

When a kind is named again from what watching showed (after its meaning is worked out):

```python
        if cell.get("given_th") and cell.get("given_meaning") != m:          # a name given from outside no longer fits what watching showed
            for f in ("given_th", "given_en", "given_from", "given_meaning", "given_life"):
                cell.pop(f, None)
```

In the snapshot of each thing (after `word_th` / `word_en`):

```python
                    "given_th": str(c.get("given_th", "")), "given_en": str(c.get("given_en", "")),      # a name given from outside (orin_api.name_thing)
                    "given_from": str(c.get("given_from", "")),
```

### Small changes to existing lines (described, not copied)

- **`contracts.py`:** the example snapshot of a thing gains `"given_th": "", "given_en": "", "given_from": ""`.
- **`dashboard/static/index.html`:** the things card adds `given` to the end of each thing's line, where `given` is built like this:

```javascript
      var given = c.given_th ? T(' «' + str(c.given_th) + '» (ชื่อจาก ' + str(c.given_from) + ')', ' «' + str(c.given_en) + '» (name from ' + str(c.given_from) + ')') : '';   // hook H2
```

## New test file: `tests/test_outside_hooks.py` (platform repo)

It runs inside the platform's test suite, against the real simulation.

```python
"""Two ways in for an outside helper (2026-10-26, the hackathon sidecar ../ut-meta-hackathon, decision #37 keep the split):
H1 the body's eye as a picture, H2 a name given to a kind the body has learnt — the meaning stays what watching showed."""
from test_recognizer import needs_render

from ultimatetruth.dashboard.app import create_app
from ultimatetruth.runner import SimProvider, Simulation, make_world
from ultimatetruth.spec import Spec

CELL = {"cls": "neutral", "look": "m1", "looks": ["m1"], "known": True, "name_th": "สิ่งที่เคลื่อนที่เอง (m1)", "name_en": "a thing that moves by itself (m1)",
        "meaning": {"moves_self": True, "came_closer": True, "touched": None, "food": False}, "changes": {"moved": 5, "looks": 0},
        "size_m": 0.4, "met": 2, "recognized": 0, "seen_s": 2.0, "first_life": 1, "life": 1, "tick": 20, "quality": "", "place": None,
        "questions": 0, "edited": False}


def _client():
    sim = Simulation(spec=Spec(use_overrides=False), seed=0, world=make_world(500, body="vhum", room="house"))
    sim.reset(seed=0, pose=(0.0, 0.0, 0.0), battery=0.9)
    app = create_app(SimProvider(sim))
    app.config["TESTING"] = True
    return sim, app.test_client()


def test_a_given_name_is_kept_beside_the_orins_own_and_shows_in_the_things_view():
    sim, c = _client()
    sim.orin.things.cells["neutral|m1"] = dict(CELL)
    r = c.post("/api/orin/things/neutral|m1/name", json={"th": "หุ่นทำความสะอาด", "en": "cleaning robot", "from": "llama3.2:3b"})
    assert r.status_code == 200, r.get_json()
    cell = sim.orin.things.cells["neutral|m1"]
    assert cell["given_en"] == "cleaning robot" and cell["given_from"] == "llama3.2:3b" and cell["name_en"].startswith("a thing")   # the Orin's own name stays
    view = [t for t in sim.orin.things.snapshot()["things"] if t["key"] == "neutral|m1"][0]
    assert view["given_th"] == "หุ่นทำความสะอาด"
    assert c.get("/api/orin/edits").get_json()["edits"][0]["store"] == "things"                                   # audited like every hand edit
    assert c.post("/api/orin/things/neutral|m1/name", json={"th": "", "en": ""}).status_code == 200 and "given_th" not in cell


def test_a_name_is_refused_for_an_unknown_kind_a_missing_one_or_half_a_name():
    sim, c = _client()
    sim.orin.things.cells["neutral|m1"] = dict(CELL, known=False)
    assert c.post("/api/orin/things/neutral|m1/name", json={"th": "หุ่น", "en": "robot"}).status_code == 409
    assert c.post("/api/orin/things/neutral|zz/name", json={"th": "หุ่น", "en": "robot"}).status_code == 404
    sim.orin.things.cells["neutral|m1"]["known"] = True
    assert c.post("/api/orin/things/neutral|m1/name", json={"th": "หุ่น", "en": ""}).status_code == 400
    assert c.post("/api/orin/things/neutral|m1/name", json={"th": "x" * 300, "en": "robot"}).status_code == 400


def test_watching_that_changes_the_meaning_drops_the_given_name():
    sim, c = _client()
    th = sim.orin.things
    th.cells["neutral|m1"] = dict(CELL, meaning=dict(CELL["meaning"]), changes=dict(CELL["changes"]))
    c.post("/api/orin/things/neutral|m1/name", json={"th": "หุ่นทำความสะอาด", "en": "cleaning robot", "from": "test"})
    cell = th.cells["neutral|m1"]
    q = {"id": 1, "cell": "neutral|m1", "moved": True, "closer": True, "touched": False, "mind": {}, "explore": {}}
    th._answer(q, cell, 30)                                  # watched again, same meaning: the name stays
    assert cell["given_en"] == "cleaning robot"
    q["touched"] = True                                      # now it hurt when bumped: the meaning changed
    th._answer(q, cell, 40)
    assert "given_en" not in cell and cell["meaning"]["touched"] is True


@needs_render
def test_the_eye_is_a_png_of_the_size_asked():
    from ultimatetruth.world.imagecodec import decode_png
    _, c = _client()
    r = c.get("/api/eye.png?w=160&h=120")
    assert r.status_code == 200 and r.mimetype == "image/png"
    img = decode_png(r.data)
    assert img.shape[:2] == (120, 160) and img.std() > 0
    assert c.get("/api/eye.png?w=5").status_code == 400
```
