# Hook H5: which kind in the thing memory a thing in the world is

Written on 27 Oct 2026 for this project, in the platform repo (ultimateTruth, commit `7d23626`, 2026-10-27 10:27 +0700), and checked live on the same day.

**Only the new code is shown here,** as with H1 and H2: the contract, the added lines with no surrounding platform code, and the new tests.

## Why it exists

A person in VR (Quest 2, WebXR) points at a thing in the house and says its name.
- The VR page knows the thing by its world id: the `id` of the stimulus in `/api/scene`.
- H2 names a kind in the mind's thing memory by its key, such as `neutral|a1`.

H5 is the bridge from one to the other.

## Contract

`GET /api/orin/things/by-stimulus/<id>?agent=<name>` → JSON

| Part | Behaviour |
|---|---|
| `id` | The stimulus id from `/api/scene` (an integer; the other body is `-2`). |
| `agent` | Whose memory to ask: `vhum` (the virtual human) or `mehum` (the meta human). |
| 200 | `{"id", "cell", "known", "look", "name_th", "name_en", "given_th", "given_en", "in_view", "seen_s_ago"}` |
| 404 | This life has not met that thing yet. The track memory starts over with every new life. |

**How it works:** the platform's eye tracker is a stand-in keyed by the world's own stimulus id, so the track of that id says which kind this life grasped the thing as. **A real eye has no such id.** It would have to match by place: the pointed-at spot against where each track was seen.

## Added: `orin_api.py`, a method of `OrinKnowledge`

```python
    def thing_of(self, sid: int) -> Dict[str, Any]:
        """Which kind in the thing memory a thing in the world is (2026-10-27, hook H5: a person points at a thing in VR and names it).
        The eye's tracker is a stand-in keyed by the world's own stimulus id (standins.py), so the track of that id says which cell this
        life grasped it as; a real eye would have to match by place instead. 404 when this life has not met the thing."""
        th = getattr(self.orin, "things", None)
        tr = th.tracks.get(int(sid)) if th is not None else None
        key = tr.get("cell") if tr else None
        if not key or key not in th.cells:
            raise OrinApiError(404, "ชีวิตนี้ยังไม่เคยพบสิ่งนี้ (id %d)" % int(sid), "this life has not met that thing (id %d)" % int(sid))
        cell = th.cells[key]
        hz = float(getattr(th, "world_hz", 500) or 500)
        return {"id": int(sid), "cell": str(key), "known": bool(cell.get("known")), "look": str(cell.get("look", "")),
                "name_th": str(cell.get("name_th", "")), "name_en": str(cell.get("name_en", "")),
                "given_th": str(cell.get("given_th", "")), "given_en": str(cell.get("given_en", "")),
                "in_view": bool(tr.get("in_view")), "seen_s_ago": round(max(0, int(self.sim.tick) - int(tr.get("last", 0))) / hz, 1)}
```

## Added: `dashboard/app.py`, inside `create_app`

```python
    @app.get("/api/orin/things/by-stimulus/<int(signed=True):sid>")
    def orin_thing_of(sid: int):
        """Which kind in the thing memory a thing in the world (its /api/scene stimulus id) is (hook H5, 2026-10-27)."""
        return orin_call(lambda api: api.thing_of(sid))
```

## Added tests: `tests/test_outside_hooks.py`

```python
def test_a_thing_in_the_world_is_found_in_the_thing_memory_by_its_stimulus_id():
    """H5 (2026-10-27): a person points at a thing in VR; its /api/scene id says which kind this life grasped it as."""
    sim, c = _client()
    sim.orin.things.cells["neutral|m1"] = dict(CELL)
    sim.orin.things.tracks[-2] = {"cell": "neutral|m1", "in_view": True, "last": 0}     # the other body (an agent) has id -2
    r = c.get("/api/orin/things/by-stimulus/-2")
    assert r.status_code == 200, r.get_json()
    body = r.get_json()
    assert body["cell"] == "neutral|m1" and body["known"] is True and body["in_view"] is True
    assert c.post("/api/orin/things/%s/name" % body["cell"], json={"th": "หุ่นทำความสะอาด", "en": "cleaning robot"}).status_code == 200
    assert c.get("/api/orin/things/by-stimulus/-2").get_json()["given_en"] == "cleaning robot"
    assert c.get("/api/orin/things/by-stimulus/99").status_code == 404                  # not met in this life


def test_the_eye_tracks_things_by_their_world_id():
    """What H5 rests on: the stand-in tracker numbers a track by the world's stimulus id."""
    sim, _ = _client()
    sid = sim.world.add_stimulus("neutral", 1.5, 0.0)
    for _ in range(int(3 * sim.world_hz)):
        sim.step()
    tr = sim.orin.things.tracks.get(sid)
    assert tr is not None and tr["cell"] in sim.orin.things.cells
```

The platform's own tests for the dashboard, the deep brain's API, the thing memory and the graph all still pass (6 hook tests plus those 4 files).

## Checked live (27 Oct)

vhum was looking at the cleaning robot (stimulus 5): `→ neutral|a1, known, in view, 0.0 s ago`.

## A limit found on 27 Oct, and fixed the same day

**What was found:** the platform's thing memory used to lump different things into one kind. A kind kept every look its tracked thing had ever shown, so `neutral|a1` held 8 looks, including the bookshelf's. Naming that kind would have named the bookshelf too.

**What was decided (decision #39):** a kind is now what a thing does, not how it looks. See `change-39-kinds-by-function.md`. H5 therefore returns a `kind|...` key, or an `ask|...` key while the thing is still being asked about.
