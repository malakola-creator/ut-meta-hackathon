# Hook H6: what the body still wonders about (the mind asks first)

Written on 27 Oct 2026 for this project, in the platform repo (ultimateTruth, commit `def9c67`). Only the new code is shown here, as with the other hooks.

## Why it exists

Meta's agent workshop on 27 Oct (`legal-agent-workshop`) showed an agent that stops and asks a person when it cannot prove something itself (`needs_input`), instead of guessing. Here the body does the same:
- It lists the things it tracks whose kind still has open standing questions (from #39, see `change-39-kinds-by-function.md`).
- Its thought balloon asks aloud "❓ what is this called?" when such a thing is in view and its kind has no name yet.

A person then answers in the Point-and-say page or in VR. That answer goes through H5 and H2, and its gates.

## Contract

`GET /api/orin/things/asking?agent=<name>` → `{"asking": [...]}`, nearest in view first. Each entry:

| Field | Meaning |
|---|---|
| `sid` | The thing's world id, as in `/api/scene`. |
| `cell` | Its kind (`kind|...`), or the look still asked about (`ask|...`). |
| `known` | Whether the body knows the kind yet. |
| `label_th`, `label_en` | What the kind is called (knowledge store, else general description). |
| `open` | The open questions, each `{what, th, en}`. `what` is one of: `name`, `touched`, `came_closer`, or `what` for a look still asked about. |
| `in_view` | Whether the thing is in view now. |
| `dist_m` | How far away it is. |

**The balloon:** `world.agents[i].thought.key == "wonder_name"`. It ranks after a weighing or a new way, and before wants. It can be switched off with `config.thought.ask_aloud`.

## New code

### `things.py` (a method of `ThingMemory`)

```python
    def asking(self, tick: int) -> List[Dict[str, Any]]:
        """What the body still wonders about the things it tracks in this life (hook H6, 2026-10-27, the user: the mind asks first, as an
        agent asks a person for what it cannot prove — "needs_input"): per tracked thing, its kind and the standing questions still open
        (or, for a look still asked about, "what is it"), whether it is in view now and how far. Nearest in view first."""
        lost = int(float(self.cfg["lost_s"]) * self.world_hz)
        out = []
        for tid, tr in self.tracks.items():
            cell = self.cells.get(tr.get("cell") or "")
            if cell is None:
                continue
            if cell.get("known"):
                open_q = [{"what": w, "th": str(q.get("th", "")), "en": str(q.get("en", ""))} for w, q in (cell.get("asking") or {}).items() if q.get("status") == "open"]
            else:
                open_q = [{"what": "what", "th": ASKED[0], "en": ASKED[1]}]
            if not open_q:
                continue
            th, en = self.label(cell) if cell.get("known") else (str(cell.get("look", "")), str(cell.get("look", "")))
            out.append({"sid": int(tid), "cell": str(tr["cell"]), "known": bool(cell.get("known")), "label_th": th, "label_en": en, "open": open_q,
                        "in_view": bool(tr.get("in_view")) and int(tick) - int(tr.get("last", 0)) <= lost, "dist_m": round(float(tr.get("dist", 0.0)), 2)})
        out.sort(key=lambda a: (not a["in_view"], a["dist_m"]))
        return out
```

### `orin_api.py`

```python
    def asking(self) -> Dict[str, Any]:
        """What the body still wonders about the things it tracks (hook H6): see things.ThingMemory.asking."""
        th = getattr(self.orin, "things", None)
        return {"asking": th.asking(int(self.sim.tick)) if th is not None else []}
```

### `dashboard/app.py`

```python
    @app.get("/api/orin/things/asking")
    def orin_things_asking():
        """What the body still wonders about the things it tracks: open standing questions, in view or not (hook H6, 2026-10-27)."""
        return orin_call(lambda api: api.asking())
```

### `thought.py`

```python
def _wonders_name(things: Any, tick: int) -> Optional[Dict[str, str]]:
    """The nearest thing in view whose kind no word names yet (its standing question "what is it called" is open): what it does."""
    try:
        for a in things.asking(int(tick)):
            if a["in_view"] and a["known"] and any(q["what"] == "name" for q in a["open"]):
                return {"th": a["label_th"], "en": a["label_en"]}
    except Exception:
        return None
    return None
```

**Edits to existing platform lines, described not copied:**
- the balloon's precedence list gains `wonder_name`;
- `compose()` gains one branch that uses `_wonders_name`;
- the defaults gain `ask_aloud` and the `wonder_name` phrase (Thai and English).

**Test:** `test_the_body_says_what_it_still_wonders_about_and_asks_aloud_for_a_name` in `tests/test_outside_hooks.py`. The full platform suite passes: 839 tests.
