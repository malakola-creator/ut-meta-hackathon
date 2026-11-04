# Hooks H3 (a book written outside) and H4 (a process proposed from outside)

Written on 27 Oct 2026 for this project, in the platform repo (ultimateTruth, commits `95c2155` and `8ddf398`, 2026-10-27), and checked live on the same day.

**Only the new code is shown here,** as with H1, H2 and H5:
- the blocks that are entirely new, with no surrounding platform code;
- small edits to existing platform lines, described in words;
- the new tests.

## H3: a book written outside

A language model's page becomes a book **on the bookshelf in the house**. A body learns from it only by walking to the shelf and reading it there, line by line, like the house's own books. Nothing goes into the mind directly.

| Call | Behaviour |
|---|---|
| `GET /api/shelf/books` | Every shelf and its books, each with `outside` and `from`. |
| `POST /api/shelf/books` | Puts a checked book on a shelf (the first one unless `shelf` is given). The body is `{"id", "th", "en", "from", "entries": [...], "shelf"?}`. |
| `DELETE /api/shelf/books/<id>` | Takes an outside book off its shelf. The house's own books stay (400). |

**The checks** (each failure gives 400 with the reason):
- Only `word` and `note` lines are accepted.
- Every line has Thai (in Thai script) and English.
- A word's `desc` may say, true or false, only what the body can observe: `moves_self`, `came_closer`, `touched`, `food`.
- `for` (optional) names the bodies the line is for.
- At most `max_entries` lines per book.

**Other answers:**

| Answer | When |
|---|---|
| 409 | The id is already on a shelf, or the shelf already holds `max_books` outside books. |
| 404 | There is no such shelf or book. |

**What it looks like in the mind:**
- The book's id gets the prefix `outside-`.
- A word read from it is kept with `from: book:outside-<id>`.
- Like every book line, real experience replaces it.

**Lifetime:** outside books live only in the dashboard's memory. A restart or a world reset removes them, while what a body already read stays in its deep brain.

## H4: a process proposed from outside

A language model may propose steps for one of the solver's problems (so far `unstuck`). **A proposal is only one more candidate**:
- It joins the repertoire and is estimated from remembered tries. It has none at first, so it starts at the prior.
- It is rehearsed on copies of the world beside the mind's own processes.
- It is tried for real only when it comes out best.
- It is learnt only when a real try answered.
- It is never a base for composing, and it is never written to the chip just because it was proposed.

| Call | Behaviour |
|---|---|
| `POST /api/orin/proposals?agent=vhum` | The body is `{"problem", "steps", "loop"?, "th", "en", "from"}`. `steps` is in the PROC form (`primitive`, `target`, `p1`, `p2`, `exit_kind`, `exit_value` as the chip's enum numbers). A primitive or exit kind the chip does not have gives 400. Returns `{"key": "proposed:N", "rehearsed": null}`. |
| `POST …?rehearse=1` | Also rehearses it at once against the mind's own best few for the row running now. Returns `rehearsed: {"done", "row", "ways", "rank", "ranked": [{"key", "score", "moved_m", "bumps"}]}`. The world waits meanwhile (up to `rehearse_timeout_s`). Nothing is written or learnt from this. |
| `GET /api/orin/proposals` | Each proposal with `tries`, `answered`, `learnt`. |
| `DELETE /api/orin/proposals/<key>` | Takes it back. What real tries taught stays. |

**Kept:** proposals go into the DNA file with the solver's memory, so they survive a restart.

### Checked live (27 Oct)

A proposal "turn 120°, walk 80 cm" was sent for vhum with `?rehearse=1`. It ranked **2nd of 3**:

| Process | Score | Moved |
|---|---|---|
| vhum's own `wander` | 3.77 | 3.77 m |
| **the proposal** | 1.10 | 1.11 m |
| vhum's own `step_away` | 0.98 | 0.98 m |

The world waited 7.7 s. The test proposal was then withdrawn and the DNA file saved.

### Checked live again (5 Nov, `tools/h4_rehearse.py`)

The procedure Muse Glimmer 30B composed for "stuck in a corner" (turn_toward → drive_forward → turn_clear; the gate had accepted it on 26 Oct) was handed to vhum as `proposed:1` with `?rehearse=1`, against the mind's own ways for the row running then (row 20). It ranked **3rd of 3**: the mind's own `wander` moved 0.50 m, the mind's composed `wander+gentler` 0.18 m, the model's plan **0.00 m**: its exits (`bearing_below 0`, `dist_below 300`) were already met, so every step ended at once. The gate checks form; the rehearsal catches what form hides. The world waited 19 s. The candidate is kept (tries 0, learnt false).

## Small edits to existing platform lines (described, not copied)

- **`solver.py`:**
  - the module docstring gains a paragraph on proposals;
  - `DEFAULTS` gains `keep_proposed`;
  - `self.memory` gains `"proposed": {}`;
  - `think()` does not compose from a `proposed` base;
  - `record()` also learns a `proposed` way that answered, keeping its `from`.
- **`dna.py`:** loading and resetting the solver's memory keep `"proposed"`.
- **`runner.py`:** `SimProvider.call()` takes a `timeout` (2 s by default, longer for a rehearsal asked from outside).
- **`orin_api.py`:** `DEFAULTS` gains `rehearse_timeout_s`.

## New code

### `src/ultimatetruth/world/books.py` (a new block at the end)

```python
# ----------------------------------------------------------------- books written outside (hook H3, 2026-10-27)
#: what a book written outside may hold: a name with what such a thing does (matched later to a kind the body has watched), or a note
OUTSIDE_KINDS = ("word", "note")
#: what a word may say such a thing does: only what the body itself can observe (things.py meanings)
DESC_KEYS = ("moves_self", "came_closer", "touched", "food")
OUTSIDE_DEFAULTS: Dict[str, Any] = {"enabled": True, "id_prefix": "outside-", "max_books": 8, "max_entries": 40, "rgba": [0.25, 0.45, 0.75, 1.0]}
LABEL_MAX = 200


class ShelfConflict(Exception):
    """The book cannot go on: its id is already on a shelf, or the shelf holds as many outside books as it may."""


def _text(d: Dict[str, Any], key: str, where: str, top: int = LABEL_MAX) -> str:
    v = d.get(key)
    if not isinstance(v, str) or not v.strip() or len(v) > top:
        raise ValueError("%s: '%s' must be a non-empty string of at most %d characters" % (where, key, top))
    return v.strip()


def outside_book(body: Any, cfg: Dict[str, Any]) -> Dict[str, Any]:
    """A book written outside (a language model's page), checked line by line: {"id", "th", "en", "from", "entries": [...]}. Every
    entry is a word (th, en, desc of observable keys, true / false) or a note (th, en); "for" may name the bodies it is for. Raises
    ValueError saying what is wrong. The id gets ``id_prefix`` so the shelf and the reading log show where the book came from."""
    if not isinstance(body, dict):
        raise ValueError("the book must be a JSON object")
    raw_id = body.get("id")
    if not isinstance(raw_id, str) or not raw_id or len(raw_id) > 40 or not all(ch.isalnum() or ch in "-_" for ch in raw_id):
        raise ValueError("'id' must be 1-40 letters, digits, '-' or '_'")
    entries = body.get("entries")
    if not isinstance(entries, list) or not 1 <= len(entries) <= int(cfg["max_entries"]):
        raise ValueError("'entries' must be a list of 1 to %d lines" % int(cfg["max_entries"]))
    lines = []
    for i, e in enumerate(entries):
        where = "entries[%d]" % i
        if not isinstance(e, dict) or e.get("kind") not in OUTSIDE_KINDS:
            raise ValueError("%s: 'kind' must be one of %s" % (where, ", ".join(OUTSIDE_KINDS)))
        line: Dict[str, Any] = {"kind": e["kind"], "th": _text(e, "th", where), "en": _text(e, "en", where)}
        if not any("฀" <= ch <= "๿" for ch in line["th"]):
            raise ValueError("%s: 'th' must be Thai" % where)
        if e["kind"] == "word":
            desc = e.get("desc")
            if not isinstance(desc, dict) or not desc or any(k not in DESC_KEYS or not isinstance(v, bool) for k, v in desc.items()):
                raise ValueError("%s: a word's 'desc' must say, true or false, only what the body can observe (%s)" % (where, ", ".join(DESC_KEYS)))
            line["desc"] = dict(desc)
        who = e.get("for")
        if who is not None:
            if not isinstance(who, list) or not all(isinstance(w, str) and w for w in who):
                raise ValueError("%s: 'for' must be a list of body kinds" % where)
            line["for"] = list(who)
        lines.append(line)
    src = body.get("from", "")
    if not isinstance(src, str) or len(src) > 40:
        raise ValueError("'from' must be a string of at most 40 characters")
    return {"id": str(cfg["id_prefix"]) + raw_id, "th": _text(body, "th", "book"), "en": _text(body, "en", "book"), "from": src,
            "outside": True, "rgba": list(cfg["rgba"]), "entries": lines, "words_th": {}}


def shelf_list(world: Any, books: Dict[str, Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """Every shelf and its books: id, titles, where each came from, how many lines (the house book's are written when read)."""
    out = {}
    for sid, ids in sorted((getattr(world, "shelf_books", None) or {}).items()):
        out[str(sid)] = [{"id": b, "th": books.get(b, {}).get("th", b), "en": books.get(b, {}).get("en", b),
                          "outside": bool(books.get(b, {}).get("outside")), "from": str(books.get(b, {}).get("from", "")),
                          "entries": len(books.get(b, {}).get("entries", []))} for b in ids]
    return out


def put_on_shelf(world: Any, book_sets: List[Dict[str, Dict[str, Any]]], book: Dict[str, Any], cfg: Dict[str, Any], shelf: Optional[int] = None) -> int:
    """Put a checked outside book on a shelf (the first one unless ``shelf``); every body's book set learns it. Returns the shelf id.
    LookupError: no such shelf; ShelfConflict: the id is taken or the shelf already holds max_books outside books."""
    shelves = getattr(world, "shelf_books", None) or {}
    if not shelves:
        raise LookupError("there is no shelf in this world")
    sid = int(shelf) if shelf is not None else sorted(shelves)[0]
    if sid not in shelves:
        raise LookupError("there is no shelf %d" % sid)
    if any(book["id"] in ids for ids in shelves.values()):
        raise ShelfConflict("a book '%s' is already on a shelf" % book["id"])
    if sum(1 for b in shelves[sid] if b.startswith(str(cfg["id_prefix"]))) >= int(cfg["max_books"]):
        raise ShelfConflict("shelf %d already holds %d outside books" % (sid, int(cfg["max_books"])))
    for books in book_sets:
        books[book["id"]] = book
    shelves[sid].append(book["id"])
    return sid


def take_off_shelf(world: Any, book_sets: List[Dict[str, Dict[str, Any]]], book_id: str, cfg: Dict[str, Any]) -> None:
    """Take an outside book off its shelf (the house's own books stay). LookupError: not on a shelf; ValueError: not an outside book."""
    if not str(book_id).startswith(str(cfg["id_prefix"])):
        raise ValueError("only a book written outside ('%s…') can be taken off" % cfg["id_prefix"])
    shelves = getattr(world, "shelf_books", None) or {}
    holder = next((ids for ids in shelves.values() if book_id in ids), None)
    if holder is None:
        raise LookupError("no book '%s' on a shelf" % book_id)
    holder.remove(book_id)
    for books in book_sets:
        books.pop(book_id, None)
```

### `src/ultimatetruth/orin_api.py` (new methods of `OrinKnowledge`)

```python
    def propose_procedure(self, body: Any, by: str = "api", rehearse_now: bool = False) -> Dict[str, Any]:
        """A process proposed from outside for one of the solver's problems (hook H4, 2026-10-27): {"problem", "steps" (PROC form,
        STEP_FIELDS), "loop"?, "th", "en", "from"}. Every step must use a primitive and an exit kind the chip has. It becomes one more
        candidate of the solver (solver.propose): estimated, rehearsed beside the mind's own, tried only if it comes out best, learnt
        only if a real try answered. ``rehearse_now``: also rehearse it at once against the processes the mind has here (the current row,
        a copy of the world; the world waits meanwhile) and say how it ranked — nothing is written or learnt from that."""
        sv = getattr(self.orin, "solver", None)
        if sv is None:
            raise OrinApiError(404, "Orin นี้ไม่มีตัวแก้โจทย์", "this Orin has no solver")
        if not isinstance(body, dict):
            raise OrinApiError(400, "ต้องส่ง {\"problem\", \"steps\", \"th\", \"en\", \"from\"}", "send {\"problem\", \"steps\", \"th\", \"en\", \"from\"}")
        problem = body.get("problem", "unstuck")
        if problem not in (sv.cfg.get("problems") or {}):
            raise OrinApiError(400, "ไม่มีโจทย์ '%s' (มี: %s)" % (problem, ", ".join(sv.cfg.get("problems") or {})),
                               "no problem '%s' (there are: %s)" % (problem, ", ".join(sv.cfg.get("problems") or {})))
        steps = self._check("proposal.steps", ("steps", 1, U8_MAX, True), body.get("steps"))
        prims = {int(k) for k in self.sim.proto.enums["primitive"]}
        exits = {int(k) for k in self.sim.proto.enums["exit_kind"]}
        for i, st in enumerate(steps):
            if int(st["primitive"]) not in prims or int(st["exit_kind"]) not in exits:
                raise OrinApiError(400, "ขั้นที่ %d ใช้ primitive หรือ exit ที่ชิปไม่มี" % i, "step %d uses a primitive or exit kind the chip does not have" % i)
        th, en, src = (self._check("proposal." + f, (("str", 0, LABEL_MAX, True) if f != "from" else ("str", 0, KEY_STR_MAX, True)), body.get(f, ""))
                       for f in ("th", "en", "from"))
        loop = self._check("proposal.loop", ("bool", None, None, True), bool(body.get("loop", False)))
        key = sv.propose(problem, steps, loop, th, en, src or str(by)[:KEY_STR_MAX], int(self.sim.tick))
        self._audit("put", "proposed", key, by, None, copy.deepcopy(sv.memory["proposed"][key]))
        out: Dict[str, Any] = {"key": key, "problem": problem, "steps": len(steps), "rehearsed": None}
        if rehearse_now:
            out["rehearsed"] = self._rehearse_proposal(sv, problem, key)
        return out

    def _rehearse_proposal(self, sv: Any, problem: str, key: str) -> Dict[str, Any]:
        sim, o = self.sim, self.orin
        reh = getattr(sim, "rehearsal", None)
        row = int((getattr(o, "cur_row", None) or {}).get("row", 0) or 0)
        if reh is None or not reh.enabled or getattr(sim, "mind_kind", "python") != "python" or not hasattr(sim.world, "fork"):
            return {"done": False, "why_th": "ซ้อมไม่ได้ (ไม่มีสำเนาโลก หรือจิตไม่ใช่ Python)", "why_en": "no rehearsal here (no world copy, or not the Python mind)"}
        if not row:
            return {"done": False, "why_th": "ตอนนี้ไม่มีแถวที่กำลังทำ จึงไม่มีอะไรให้เทียบ", "why_en": "no row is running now, so there is nothing to rehearse against"}
        ring, _cur = sv.ring_from_place()
        procedures = getattr(sim.mind.table, "procedures", {}) or {}
        cands = sv.repertoire(problem, ring, procedures, int(sim.tick))
        mine = next((c for c in cands if c["key"] == key), None)
        if mine is None:
            return {"done": False, "why_th": "ข้อเสนอไม่ได้อยู่ในตัวเลือกตอนนี้", "why_en": "the proposal is not among the candidates now"}
        vec = sv.vec(ring)
        others = sorted((c for c in cands if c["key"] != key), key=lambda c: -sv.estimate(problem, c["key"], vec)[0])
        short = [mine] + others[:max(0, int(sv.p("think_ways")) - 1)]                  # the proposal, beside the mind's own best few
        trial = [dict(c, kind="variant", recipe=c["key"]) for c in short]
        ranked = reh.evaluate(sim, row, trial, score="escape") or []
        order = [r["candidate"].get("recipe") for r in ranked]
        return {"done": bool(ranked), "row": row, "ways": len(ranked), "rank": (order.index(key) + 1) if key in order else None,
                "ranked": [{"key": r["candidate"].get("recipe"), "score": r["score"], "moved_m": round(float(r["outcome"]["moved_m"]), 2),
                            "bumps": int(r["outcome"]["bumps"])} for r in ranked]}

    def withdraw_proposal(self, key: str, by: str = "api") -> Dict[str, Any]:
        """Take a proposal back (hook H4): it leaves the candidates; what real tries taught (stats, episodes, a learnt way) stays."""
        sv = getattr(self.orin, "solver", None)
        props = sv.memory.setdefault("proposed", {}) if sv is not None else {}
        if key not in props:
            raise OrinApiError(404, "ไม่มีข้อเสนอ '%s'" % key, "no proposal '%s'" % key)
        before = props.pop(key)
        self._audit("delete", "proposed", key, by, before, None)
        return {"key": key}

    def proposals(self) -> Dict[str, Any]:
        """The proposals the solver holds, with how they fared for real (tries, answered) and whether one was learnt."""
        sv = getattr(self.orin, "solver", None)
        if sv is None:
            raise OrinApiError(404, "Orin นี้ไม่มีตัวแก้โจทย์", "this Orin has no solver")
        props = sv.memory.setdefault("proposed", {})
        out = []
        for key, ent in sorted(props.items()):
            st = (sv.memory["stats"].get(ent.get("problem"), {}) or {}).get(key) or {}
            out.append({"key": key, "problem": ent.get("problem"), "th": ent.get("th", ""), "en": ent.get("en", ""), "from": ent.get("from", ""),
                        "steps": len(ent.get("steps") or []), "life": ent.get("life"), "tries": int(st.get("tries", 0)),
                        "answered": int(st.get("successes", 0)), "learnt": key in sv.memory["learned"]})
        return {"proposals": out}
```

### `src/ultimatetruth/solver.py` (new: the 4th source of the repertoire, and `propose`)

```python
        # 4. what was proposed from outside (hook H4): candidates like the rest, nothing more
        for key, ent in sorted(self.memory.setdefault("proposed", {}).items()):
            if ent.get("problem") != problem or key in failed or key in seen_keys or key in self.memory["learned"]:
                continue
            seen_keys.add(key)
            out.append({"key": key, "source": "proposed", "proc": None, "steps": [dict(s) for s in ent["steps"]], "loop": bool(ent.get("loop")),
                        "th": ent.get("th") or key, "en": ent.get("en") or key, "from": ent.get("from", ""), "life": ent.get("life")})
        return out

    def propose(self, problem: str, steps: List[Dict[str, Any]], loop: bool, th: str, en: str, source: str, tick: int) -> str:
        """Take a process proposed from outside as a candidate for ``problem`` (hook H4); returns its key. The oldest proposal goes
        first beyond ``keep_proposed``; one already learnt (it answered for real) stays where it is."""
        if problem not in (self.cfg.get("problems") or {}):
            raise KeyError(problem)
        props = self.memory.setdefault("proposed", {})
        n = 1 + max([int(k.rsplit(":", 1)[-1]) for k in props if k.rsplit(":", 1)[-1].isdigit()] or [0])
        key = "proposed:%d" % n
        props[key] = {"problem": problem, "steps": [dict(s) for s in steps], "loop": bool(loop), "th": th, "en": en, "from": source,
                      "life": int(getattr(self.orin, "life", 1)), "tick": int(tick)}
        while len(props) > int(self.p("keep_proposed")):
            del props[min(props, key=lambda k: int(props[k].get("tick", 0)))]
        return key
```

### `src/ultimatetruth/dashboard/app.py` (new routes inside `create_app`)

```python
    # ---------------------------------------------------------------- books written outside (hook H3, 2026-10-27): a language model's page
    # goes onto the shelf in the house; a body learns from it only by walking there and reading it (reading.py), like the house's own books
    from ..world import books as book_mod

    def shelf_ctx():
        sim = getattr(provider, "sim", None)
        if sim is None or not hasattr(sim, "books"):
            return None
        cfg = dict(book_mod.OUTSIDE_DEFAULTS, **{k: v for k, v in (((sim.spec.config.get("concepts") or {}).get("reading") or {}).get("outside") or {}).items()
                                                  if not k.startswith("_")})
        sims = list((getattr(provider, "sims", None) or {}).values()) or [sim]
        return sim, cfg, [s.books for s in sims]

    def shelf_call(fn):
        ctx = shelf_ctx()
        if ctx is None:
            return bilingual_failure(404, "โลกนี้ไม่มีชั้นหนังสือ", "this provider has no bookshelf")
        call = getattr(provider, "call", None)
        res = call(lambda: fn(*ctx)) if callable(call) else {"ok": True, "result": fn(*ctx)}
        if res.get("ok"):
            return no_store(jsonify(_json_safe(dict({"ok": True}, **res["result"]))))
        exc = res.get("exc")
        if isinstance(exc, LookupError):
            return bilingual_failure(404, "ไม่พบ: %s" % exc, str(exc))
        if isinstance(exc, book_mod.ShelfConflict):
            return bilingual_failure(409, "วางไม่ได้: %s" % exc, str(exc))
        if isinstance(exc, ValueError):
            return bilingual_failure(400, "หนังสือไม่ผ่านการตรวจ: %s" % exc, str(exc))
        return bilingual_failure(409, "การจำลองไม่ตอบ", str(res.get("error") or "simulation did not respond"))

    @app.get("/api/shelf/books")
    def shelf_books():
        """The shelves and their books, with where each came from (hook H3)."""
        return shelf_call(lambda sim, cfg, sets: {"shelves": book_mod.shelf_list(sim.world, sim.books)})

    @app.post("/api/shelf/books")
    def shelf_add():
        """Put a book written outside on a shelf: {"id", "th", "en", "from", "entries": [word / note lines], "shelf"?} (hook H3)."""
        body = request.get_json(force=True, silent=True)

        def add(sim, cfg, sets):
            if not bool(cfg.get("enabled", True)):
                raise ValueError("books from outside are switched off (config.concepts.reading.outside.enabled)")
            book = book_mod.outside_book(body, cfg)
            shelf = body.get("shelf") if isinstance(body, dict) else None
            if shelf is not None and (not isinstance(shelf, int) or isinstance(shelf, bool)):
                raise ValueError("'shelf' must be a shelf's stimulus id")
            sid = book_mod.put_on_shelf(sim.world, sets, book, cfg, shelf)
            return {"book": book["id"], "shelf": sid, "lines": len(book["entries"])}
        return shelf_call(add)

    @app.delete("/api/shelf/books/<book_id>")
    def shelf_remove(book_id: str):
        """Take a book written outside off its shelf (hook H3); the house's own books stay."""
        def remove(sim, cfg, sets):
            book_mod.take_off_shelf(sim.world, sets, book_id, cfg)
            return {"book": book_id}
        return shelf_call(remove)

    # ---------------------------------------------------------------- processes proposed from outside (hook H4, 2026-10-27)
    @app.get("/api/orin/proposals")
    def orin_proposals():
        """The processes proposed from outside that the solver holds, and how they fared for real."""
        return orin_call(lambda api: api.proposals())

    @app.post("/api/orin/proposals")
    def orin_propose():
        """Propose a process for one of the solver's problems: {"problem", "steps", "loop"?, "th", "en", "from"}; ?rehearse=1 also
        rehearses it at once against the mind's own (the world waits meanwhile, up to config.orin_api.rehearse_timeout_s)."""
        def write():
            body, by = orin_body(), orin_by()
            now = request.args.get("rehearse") in ("1", "true", "yes")
            api = orin_api()
            if api is None:
                return bilingual_failure(404, NO_ORIN["th"], NO_ORIN["en"])
            call = getattr(provider, "call", None)
            fn = lambda: api.propose_procedure(body, by, now)
            if callable(call):
                res = call(fn, timeout=float(api.cfg.get("rehearse_timeout_s", 120.0)) if now else 2.0)
            else:
                try:
                    res = {"ok": True, "result": fn()}
                except Exception as exc:
                    res = {"ok": False, "error": str(exc), "exc": exc}
            if res.get("ok"):
                return no_store(jsonify(_json_safe(dict({"ok": True}, **res["result"]))))
            exc = res.get("exc")
            if isinstance(exc, OrinApiError):
                return bilingual_failure(exc.status, exc.th, exc.en)
            if exc is not None:
                app.logger.error("a proposal failed: %r", exc)
                return bilingual_failure(500, "ข้อเสนอล้มเหลว: %s" % res.get("error"), "the proposal failed: %s" % res.get("error"))
            return bilingual_failure(409, "การจำลองไม่ตอบ", str(res.get("error") or "simulation did not respond"))
        return guarded(write)

    @app.delete("/api/orin/proposals/<key>")
    def orin_withdraw(key: str):
        """Take a proposal back (hook H4); what real tries taught stays."""
        by = orin_by()
        return orin_call(lambda api: api.withdraw_proposal(key, by))
```

### `spec/config.json` (new settings)

```json
   "outside": {
    "_note": "หนังสือจากภายนอก (hook H3, 2026-10-27: โมเดลภาษาเขียนหน้าหนังสือ): วางบนชั้นในบ้าน แล้วกายต้องเดินไปยืนอ่านเองเหมือนเล่มอื่น — ไม่มีสิ่งใดเข้าจิตตรงๆ รับเฉพาะบรรทัด word / note มีทั้งไทยและอังกฤษ ความหมายของคำใช้ได้แค่สิ่งที่กายสังเกตได้; อยู่ในหน่วยความจำของ dashboard เท่านั้น (เริ่มใหม่แล้วหาย) / books written outside: put on the shelf, read only by walking there; word and note lines, Thai and English; in memory only",
    "enabled": true,
    "id_prefix": "outside-",
    "max_books": 8,
    "max_entries": 40,
    "rgba": [0.25, 0.45, 0.75, 1.0]
   }
  "keep_proposed": 8,
  "_keep_proposed": "กระบวนการที่เสนอมาจากภายนอก (hook H4) เก็บไว้เป็นตัวเลือกได้กี่อัน เก่าสุดออกก่อน — เป็นแค่ตัวเลือก ต้องผ่านการคิด/ซ้อม/ลองจริงเหมือนอันอื่น / how many processes proposed from outside stay as candidates; the oldest goes first",
  "rehearse_timeout_s": 120,
  "_rehearse_timeout_s": "ข้อเสนอจากภายนอกที่ขอให้ซ้อมทันที (hook H4) รอผลได้นานเท่านี้ (วินาที); ระหว่างซ้อมโลกรอ / how long a rehearsal asked from outside may take; the world waits meanwhile"
```

### `tests/test_outside_hooks.py` (new tests)

```python
BOOK = {"id": "cats", "th": "สัตว์ในบ้าน", "en": "Animals at home", "from": "muse-glimmer-30b",
        "entries": [{"kind": "word", "th": "แมว", "en": "a cat", "desc": {"moves_self": True, "food": False}},
                    {"kind": "note", "th": "แมวชอบนอนบนโซฟา", "en": "A cat likes to sleep on the sofa"}]}


def test_a_book_written_outside_goes_on_the_shelf_checked_line_by_line():
    """H3 (2026-10-27): a language model's page becomes a book on the shelf in the house; only word / note lines, Thai and English,
    and a word may say only what the body can observe."""
    sim, c = _client()
    r = c.post("/api/shelf/books", json=BOOK)
    assert r.status_code == 200, r.get_json()
    assert r.get_json()["book"] == "outside-cats" and r.get_json()["lines"] == 2
    listed = [b for ids in c.get("/api/shelf/books").get_json()["shelves"].values() for b in ids]
    mine = [b for b in listed if b["id"] == "outside-cats"][0]
    assert mine["outside"] and mine["from"] == "muse-glimmer-30b" and any(not b["outside"] for b in listed)
    assert c.post("/api/shelf/books", json=BOOK).status_code == 409                             # the same id twice
    bad = dict(BOOK, id="dogs", entries=[{"kind": "word", "th": "สุนัข", "en": "a dog", "desc": {"barks": True}}])
    assert c.post("/api/shelf/books", json=bad).status_code == 400                               # not something the body observes
    assert c.post("/api/shelf/books", json=dict(BOOK, id="x", entries=[{"kind": "note", "th": "no thai", "en": "x"}])).status_code == 400
    assert c.post("/api/shelf/books", json=dict(BOOK, id="y", entries=[{"kind": "place", "th": "ครัว", "en": "kitchen"}])).status_code == 400
    assert c.delete("/api/shelf/books/food").status_code == 400                                  # the house's own books stay
    assert c.delete("/api/shelf/books/outside-cats").status_code == 200
    assert c.delete("/api/shelf/books/outside-cats").status_code == 404


def test_the_body_learns_an_outside_book_only_by_reading_it_at_the_shelf():
    """The book is on the shelf, not in the mind: the word comes into the deep brain when vhum has stood there and read that line."""
    from ultimatetruth.dashboard.app import create_app
    from ultimatetruth.runner import SimProvider
    sim = Simulation(spec=Spec(use_overrides=False), seed=0, world=make_world(500, body="vhum", room="house"))
    sim.world.day_cfg["enabled"] = False
    sim.reset(seed=0, pose=(5.0, -4.5, math.pi), battery=0.95)                                   # in the study, facing the shelf
    app = create_app(SimProvider(sim))
    app.config["TESTING"] = True
    assert app.test_client().post("/api/shelf/books", json=BOOK).status_code == 200
    rd = sim.orin.reading
    assert not any(w["en"] == "a cat" for w in rd.words)                                         # not known before it is read
    for _ in range(1500):
        sim.run(0.1)
        if any(w["en"] == "a cat" for w in rd.words):
            break
    cat = [w for w in rd.words if w["en"] == "a cat"]
    assert cat and cat[0]["from"] == "book:outside-cats" and cat[0]["desc"] == {"moves_self": True, "food": False}
    assert any(e["book"] == "outside-cats" for e in rd.log)


TURN_WALK = [{"primitive": 9, "target": 0, "p1": 120, "p2": 0, "exit_kind": 10, "exit_value": 0},          # turn_by 120°, until done
             {"primitive": 10, "target": 0, "p1": 80, "p2": 0, "exit_kind": 10, "exit_value": 0}]          # drive_dist 80 cm, until done
PROPOSAL = {"problem": "unstuck", "steps": TURN_WALK, "th": "หันแล้วเดินออก", "en": "turn and walk out", "from": "muse-glimmer-30b"}


def test_a_process_proposed_from_outside_is_only_a_candidate_until_it_answers():
    """H4 (2026-10-27): a proposal joins the solver's repertoire; it is learnt only when a real try answered; it is never a base to
    compose from; the chip's own primitives and exit kinds only."""
    sim, c = _client()
    r = c.post("/api/orin/proposals", json=PROPOSAL)
    assert r.status_code == 200, r.get_json()
    key = r.get_json()["key"]
    assert key == "proposed:1" and r.get_json()["rehearsed"] is None
    sv = sim.orin.solver
    ring, _ = sv.ring_from_place()
    cands = sv.repertoire("unstuck", ring, {}, sim.tick)
    mine = [x for x in cands if x["key"] == key]
    assert mine and mine[0]["source"] == "proposed" and mine[0]["from"] == "muse-glimmer-30b"
    assert sv.compose("unstuck", mine[0], 0) is not None and key not in sv.memory["learned"]          # composing is the caller's choice ...
    sv.record("unstuck", mine[0], ring, success=False)
    assert key not in sv.memory["learned"]                                                               # ... a failed try teaches no way
    sv.record("unstuck", mine[0], ring, success=True)
    assert sv.memory["learned"][key]["from"] == "muse-glimmer-30b"                                      # it answered for real: learnt
    listed = c.get("/api/orin/proposals").get_json()["proposals"]
    assert listed[0]["tries"] == 2 and listed[0]["answered"] == 1 and listed[0]["learnt"] is True
    bad = dict(PROPOSAL, steps=[dict(TURN_WALK[0], primitive=99)])
    assert c.post("/api/orin/proposals", json=bad).status_code == 400                                   # not a primitive of the chip
    assert c.post("/api/orin/proposals", json=dict(PROPOSAL, problem="fly")).status_code == 400
    assert c.post("/api/orin/proposals", json=dict(PROPOSAL, steps=[])).status_code == 400
    assert c.delete("/api/orin/proposals/%s" % key).status_code == 200                                # taken back: no longer a candidate,
    assert not [x for x in sv.repertoire("unstuck", ring, {}, sim.tick) if x["source"] == "proposed"]
    assert key in sv.memory["learned"] and c.delete("/api/orin/proposals/%s" % key).status_code == 404  # what it taught stays


def test_a_proposal_survives_in_the_dna_file(tmp_path, monkeypatch):
    import json
    from ultimatetruth.dna import DnaMemory
    monkeypatch.delenv("ULTIMATETRUTH_DNA", raising=False)
    sim, c = _client()
    c.post("/api/orin/proposals", json=PROPOSAL)
    dna = DnaMemory(dict(sim.spec.config.get("dna") or {}, enabled=True), path=tmp_path / "dna.json")
    (tmp_path / "dna.json").write_text(json.dumps(dna.gather(sim.orin)), encoding="utf-8")
    sim.orin.solver.memory = {"stats": {}, "episodes": [], "learned": {}, "proposed": {}}
    assert dna.apply(sim.orin)
    assert sim.orin.solver.memory["proposed"]["proposed:1"]["from"] == "muse-glimmer-30b"


def test_a_proposal_is_rehearsed_at_once_against_the_minds_own_ways():
    """?rehearse=1: the proposal and the mind's own best few run on copies of the world from here; the ranking is reported, nothing learnt."""
    sim, c = _client()
    for _ in range(int(4 * sim.world_hz)):
        sim.step()
        if (sim.orin.cur_row or {}).get("row"):
            break
    assert (sim.orin.cur_row or {}).get("row"), "no row ran within 4 s"
    r = c.post("/api/orin/proposals?rehearse=1", json=PROPOSAL)
    assert r.status_code == 200, r.get_json()
    reh = r.get_json()["rehearsed"]
    assert reh["done"] is True and reh["ways"] >= 2 and reh["rank"] is not None
    assert any(x["key"] == "proposed:1" for x in reh["ranked"]) and not sim.orin.solver.memory["learned"]
```

**The platform's tests** for the solver, the instinct, the deliberation, rehearsal, the DNA file, reading, the dashboard and the deep brain API all still pass.
