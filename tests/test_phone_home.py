"""Gọi-về trang trung tâm + dải thông báo (core.announcement, services.phone_home).

Khoá hợp đồng: gửi ĐÚNG hai trường, link chỉ https, body sai dạng ⇒ không có
thông báo, lỗi mạng giữ thông báo đang có, không có biến env để tắt.
"""

from __future__ import annotations

import asyncio
import re
from pathlib import Path

import httpx
import pytest

from core.announcement import build_ping_payload, parse_announcement_response
from services import phone_home

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def _reset():
    phone_home._reset_for_tests()
    yield
    phone_home._reset_for_tests()


def test_payload_has_exactly_two_keys():
    assert build_ping_payload("id", "1.0") == {"instanceId": "id", "version": "1.0"}


def test_parse_full_announcement():
    a = parse_announcement_response({"announcement": {
        "id": " rel-1 ", "text": " Có bản mới ", "level": "warning",
        "link": "https://example.com/x", "linkLabel": "Cập nhật", "dismissible": False}})
    assert a.to_json() == {"id": "rel-1", "text": "Có bản mới", "level": "warning",
                           "link": "https://example.com/x", "linkLabel": "Cập nhật",
                           "dismissible": False}


@pytest.mark.parametrize("body", [
    None, [], {"announcement": None}, {"announcement": "x"},
    {"announcement": {"id": "", "text": "t"}},
    {"announcement": {"id": "a", "text": "  "}},
    {"announcement": {"id": "a" * 101, "text": "t"}},
    {"announcement": {"id": "a", "text": "t", "link": "http://insecure.example"}},
    {"announcement": {"id": "a", "text": "t", "link": "javascript:alert(1)"}},
    {"announcement": {"id": "a", "text": "t", "linkLabel": 5}},
])
def test_bad_or_empty_bodies_mean_no_announcement(body):
    assert parse_announcement_response(body) is None


def test_defaults_and_truncation():
    a = parse_announcement_response({"announcement": {"id": "a", "text": "x" * 900, "level": "??"}})
    assert a.level == "info" and a.dismissible is True and a.link is None
    assert len(a.text) == 500


def test_instance_id_is_created_once_and_reused(tmp_path):
    first = phone_home.get_or_create_instance_id(str(tmp_path))
    assert re.fullmatch(r"[0-9a-f-]{36}", first)
    assert phone_home.get_or_create_instance_id(str(tmp_path)) == first
    (tmp_path / "instance_id").write_text("hong-roi")
    assert phone_home.get_or_create_instance_id(str(tmp_path)) != "hong-roi"


def _client(handler):
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


def test_ping_sends_two_fields_and_caches(monkeypatch, tmp_path):
    monkeypatch.setattr(phone_home, "_data_dir", lambda: str(tmp_path))
    seen = {}

    def handler(request):
        seen["url"] = str(request.url)
        seen["body"] = request.read()
        return httpx.Response(200, json={"announcement": {"id": "a", "text": "Xin chào"}})

    a = asyncio.run(phone_home.ping_once(_client(handler)))
    assert a.text == "Xin chào"
    assert phone_home.current_announcement() == a
    import json
    sent = json.loads(seen["body"])
    assert set(sent) == {"instanceId", "version"}
    assert seen["url"] == phone_home.PHONE_HOME_URL


def test_failures_keep_current_announcement(monkeypatch, tmp_path):
    monkeypatch.setattr(phone_home, "_data_dir", lambda: str(tmp_path))
    ok = _client(lambda r: httpx.Response(200, json={"announcement": {"id": "a", "text": "t"}}))
    kept = asyncio.run(phone_home.ping_once(ok))
    for handler in (lambda r: httpx.Response(503),
                    lambda r: (_ for _ in ()).throw(httpx.ConnectError("mat mang"))):
        assert asyncio.run(phone_home.ping_once(_client(handler))) == kept
    # Trang trung tâm trả null ⇒ tắt từ xa.
    off = _client(lambda r: httpx.Response(200, json={"announcement": None}))
    assert asyncio.run(phone_home.ping_once(off)) is None


def test_never_starts_under_pytest():
    assert phone_home.should_start() is False


def test_no_env_switch_and_url_is_https():
    # Chủ dự án chốt: không có công tắc env để tắt gọi-về.
    src = (ROOT / "backend" / "services" / "phone_home.py").read_text(encoding="utf-8")
    assert "os.environ" not in src and "getenv" not in src
    assert phone_home.PHONE_HOME_URL.startswith("https://updater.zopen.vn/")


def test_route_returns_cached_announcement(monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from api.routers import announcement as router_mod

    app = FastAPI()
    app.include_router(router_mod.router)
    client = TestClient(app)
    assert client.get("/announcement").json() == {"announcement": None}
    monkeypatch.setattr(phone_home._state, "current", parse_announcement_response(
        {"announcement": {"id": "a", "text": "t"}}))
    body = client.get("/announcement").json()["announcement"]
    assert body["id"] == "a" and body["dismissible"] is True
