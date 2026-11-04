"""The client against the mock platform: what a judge can run from this repo alone."""
import os
import runpy
import sys
import threading
from http.server import ThreadingHTTPServer

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from utmeta.core_client import Core, CoreError

MOCK = runpy.run_path(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools", "mock_core.py"), run_name="mock")


def _core():
    srv = ThreadingHTTPServer(("127.0.0.1", 0), MOCK["Handler"])
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return Core({"core": {"url": "http://127.0.0.1:%d" % srv.server_address[1], "token_env": "UT_TOKEN_UNSET"}}), srv


def test_reads_the_things_and_the_eye():
    core, srv = _core()
    try:
        assert core.health()["ok"] is True
        things = core.things()
        assert things and all("meaning" in c for c in things.values())
        assert core.eye_png()[:8] == b"\x89PNG\r\n\x1a\n"
    finally:
        srv.shutdown()


def test_gives_a_name_only_to_a_known_kind():
    core, srv = _core()
    try:
        things = core.things()
        known = next(k for k, c in things.items() if c.get("known"))
        unknown = next(k for k, c in things.items() if not c.get("known"))
        assert core.name_thing(known, "หุ่นทำความสะอาด", "cleaning robot", "test")["ok"] is True
        assert core.things()[known]["given_en"] == "cleaning robot"
        try:
            core.name_thing(unknown, "หุ่น", "robot", "test")
        except CoreError as exc:
            assert "409" in str(exc)
        else:
            raise AssertionError("an unknown kind was named")
    finally:
        srv.shutdown()
