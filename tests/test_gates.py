"""The checks every model answer passes before it may be offered to the mind (no network, no model: a fake backend)."""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from utmeta import composer, namer, reader
from utmeta.eye import iou
from utmeta.llm import Llm, LlmError

CELL = {"look": "a2", "known": True, "meaning": {"moves_self": True, "came_closer": False, "touched": None, "food": False},
        "changes": {"moved": 203, "looks": 53}, "size_m": 0.5, "met": 38}
PRIMS = ["hold", "turn_by", "drive_dist", "turn_clear"]
EXITS = ["never", "time_ms", "done", "front_clear"]
COMP = {"min_steps": 2, "max_steps": 4, "p1_max": 65535, "exit_value_max": 65535}


def fake(answer):
    return Llm({}, fake=lambda system, user: answer)


def test_a_name_from_what_was_watched_is_accepted():
    ans, _, probs, obs = namer.propose(fake({"name_en": "cleaning robot", "name_th": "หุ่นทำความสะอาด", "used": ["moves_by_itself", "is_food"]}), CELL)
    assert probs == [] and obs["hurt_when_touched"] is None


def test_a_name_that_leans_on_an_unknown_or_unseen_observation_is_refused():
    _, _, probs, _ = namer.propose(fake({"name_en": "dog", "name_th": "สุนัข", "used": ["hurt_when_touched", "barks"]}), CELL)
    assert any("still unknown" in p for p in probs) and any("never observed" in p for p in probs)


def test_a_name_needs_thai_script():
    _, _, probs, _ = namer.propose(fake({"name_en": "robot", "name_th": "robot", "used": ["moves_by_itself"]}), CELL)
    assert probs == ["name_th is not Thai"]


def test_reading_keeps_good_lines_and_says_why_others_were_dropped():
    lines = [{"kind": "word", "en": "a cat", "th": "แมว", "desc": {"moves_self": True, "food": False}},
             {"kind": "note", "en": "The kitchen is north-east", "th": "ครัวอยู่ทิศตะวันออกเฉียงเหนือ"},
             {"kind": "word", "en": "a dog", "th": "สุนัข", "desc": {"barks": True}},
             {"kind": "place", "en": "fridge", "th": "ตู้เย็น"}]
    good, _, probs, _ = reader.propose(fake({"lines": lines}), "a page")
    assert [g["en"] for g in good] == ["a cat", "The kitchen is north-east"]
    assert any("barks" in p for p in probs) and any("'place'" in p for p in probs)


def test_a_procedure_may_only_use_what_the_chip_has():
    ok = {"steps": [{"primitive": "turn_by", "p1": 90, "exit": {"kind": "done", "value": 0}},
                    {"primitive": "drive_dist", "p1": 50, "exit": {"kind": "done", "value": 0}}]}
    _, _, probs = composer.propose(fake(ok), {"problem": "corner"}, PRIMS, EXITS, COMP)
    assert probs == []
    bad = {"steps": [{"primitive": "jump", "p1": -1, "exit": {"kind": "when_free", "value": 1.5}}]}
    _, _, probs = composer.propose(fake(bad), {"problem": "corner"}, PRIMS, EXITS, COMP)
    assert len(probs) == 5 and "1 steps" in probs[0]


def test_without_the_platform_the_chip_primitives_come_from_the_recorded_sample(monkeypatch):
    monkeypatch.setitem(sys.modules, "ultimatetruth", None)                           # "import ultimatetruth" now fails, as on a judge's machine
    monkeypatch.setitem(sys.modules, "ultimatetruth.protocol", None)
    prims, exits = composer.protocol_keys({"core": {"path": "/nowhere"}})
    assert prims[:2] == ["hold", "turn_toward"] and "drive_dist" in prims and {"never", "done", "flag"} <= set(exits)
    assert (prims, exits) == composer.recorded_keys()


def test_the_composer_prompt_lists_the_chip_primitives():
    seen = {}

    def capture(system, user):
        seen["system"] = system
        return {"steps": []}
    composer.propose(Llm({}, fake=capture), {"p": 1}, PRIMS, EXITS, COMP)
    assert all(p in seen["system"] for p in PRIMS + EXITS)


def test_a_reply_that_is_not_a_json_object_is_an_error():
    from utmeta.llm import _object
    for text in ("not json", "[1, 2]"):
        try:
            _object(text)
        except LlmError:
            continue
        raise AssertionError(text)
    assert _object(json.dumps({"a": 1})) == {"a": 1}


def test_iou():
    a = [[1, 1, 0], [0, 0, 0]]
    b = [[1, 0, 0], [0, 0, 0]]
    assert iou(a, b) == 0.5 and iou(b, b) == 1.0 and iou([[0]], [[0]]) == 0.0


def test_a_picture_goes_to_the_model_and_may_be_named_as_used():
    seen = {}

    def capture(system, user, images=()):
        seen.update(system=system, images=list(images))
        return {"name_en": "cleaning robot", "name_th": "หุ่นทำความสะอาด", "used": ["picture", "moves_by_itself"]}
    ans, _, probs, obs = namer.propose(Llm({}, fake=capture), CELL, 40, b"PNGBYTES")
    assert probs == [] and seen["images"] == [b"PNGBYTES"] and "picture" in seen["system"] and obs["picture"] is True
    _, _, probs, _ = namer.propose(fake({"name_en": "robot", "name_th": "หุ่นยนต์", "used": ["picture"]}), CELL)
    assert probs == ["used 'picture', which the body never observed"]                 # no picture was shown


def test_a_thinking_model_that_answers_no_content_is_asked_once_more_with_twice_the_room(monkeypatch):
    from utmeta import llm as llm_mod
    calls = []

    def fake_post(url, body, headers, timeout):
        calls.append(dict(body))
        if len(calls) == 1:                                                   # the reasoning ate the whole budget: content null
            return {"choices": [{"message": {"content": None, "role": "assistant"}, "finish_reason": "length"}],
                    "usage": {"completion_tokens_details": {"reasoning_tokens": 1000}}}
        return {"choices": [{"message": {"content": json.dumps({"name_en": "robot vacuum"})}, "finish_reason": "stop"}]}
    monkeypatch.setattr(llm_mod, "_post", fake_post)
    monkeypatch.setenv("UT_TEST_MODEL_KEY", "x")
    model = Llm({"backend": "openai", "openai": {"url": "http://model.test", "model": "m", "key_env": "UT_TEST_MODEL_KEY", "max_tokens": 1000}})
    ans, _ = model.ask("s", "u")
    assert ans == {"name_en": "robot vacuum"} and [c["max_tokens"] for c in calls] == [1000, 2000]
    monkeypatch.setattr(llm_mod, "_post", lambda *a, **k: {"choices": [{"message": {"content": None}, "finish_reason": "length"}], "usage": {}})
    try:
        model.ask("s", "u")
    except LlmError as exc:
        assert "no content" in str(exc) and "length" in str(exc)
    else:
        raise AssertionError("no LlmError")
