"""Point and say, without the platform or a model: the mock platform (tools/mock_core.py) and a fake language model."""
import os
import runpy
import sys
import threading
from http.server import ThreadingHTTPServer

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from utmeta.core_client import Core
from utmeta.llm import Llm
from utmeta.teach import check, teach

MOCK = runpy.run_path(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools", "mock_core.py"), run_name="mock")


def _core():
    srv = ThreadingHTTPServer(("127.0.0.1", 0), MOCK["Handler"])
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return Core({"core": {"url": "http://127.0.0.1:%d" % srv.server_address[1], "token_env": "UT_TOKEN_UNSET"}}), srv


def fake(answer):
    return Llm({}, fake=lambda system, user: answer)


def test_the_gate_takes_a_name_in_both_languages_only():
    assert check({"named": True, "name_th": "หุ่นยนต์ดูดฝุ่น", "name_en": "robot vacuum"}) == []
    assert check({"named": False}) == ["no name was given"]
    assert check({"named": True, "name_th": "robot", "name_en": "robot"}) == ["name_th is not Thai"]
    assert "name_en is missing" in check({"named": True, "name_th": "หุ่น", "name_en": ""})
    said = "นี่คือหุ่นยนต์ดูดฝุ่น"                                                  # the Thai name must be words that were said
    assert check({"named": True, "name_th": "หุ่นยนต์ ดูดฝุ่น", "name_en": "robot vacuum"}, said) == []
    assert check({"named": True, "name_th": "หุ่ยนยนต์ดูดฝุ่", "name_en": "robot vacuum"}, said)[0].endswith("is not what was said")


def test_a_known_thing_takes_the_name_said_and_an_unknown_one_does_not(monkeypatch):
    core, srv = _core()
    try:
        cells = core.things()
        known = next(k for k, c in cells.items() if c.get("known"))
        unknown = next(k for k, c in cells.items() if not c.get("known"))
        mapping = {5: {"id": 5, "cell": known, "known": True}, 6: {"id": 6, "cell": unknown, "known": False}}
        monkeypatch.setattr(core, "thing_of", lambda sid, agent=None: dict(mapping[sid]))
        out = teach(core, fake({"named": True, "name_th": "หุ่นยนต์ดูดฝุ่น", "name_en": "robot vacuum", "heard": "นี่คือหุ่นยนต์ดูดฝุ่น"}), 5, "นี่คือหุ่นยนต์ดูดฝุ่น")
        assert out["ok"] and out["stage"] == "given" and core.things()[known]["given_en"] == "robot vacuum"
        out = teach(core, fake({"named": True, "name_th": "แมว", "name_en": "cat"}), 6, "นี่คือแมว")
        assert not out["ok"] and out["stage"] == "known" and not core.things()[unknown].get("given_en")
        out = teach(core, fake({"named": False, "name_th": "", "name_en": ""}), 5, "อะไรนะ")
        assert not out["ok"] and out["stage"] == "name"
    finally:
        srv.shutdown()
