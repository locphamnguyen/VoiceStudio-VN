"""Đăng ký / đăng nhập kiểu Vonia (core.accounts + router /account + cổng).

Khoá các quyết định nghiệp vụ: người đầu tiên là Quản trị viên, người sau chờ
duyệt, chống dò email, khoá sau 5 lần sai, phiên bị thu hồi khi tài khoản bị
khoá, và cổng chặn mọi route khi chưa đăng nhập.
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from core import accounts as acc
from core.account_gate import AccountGateMiddleware

PW = "mat-khau-du-dai-1"
CSRF = {"X-VoiceStudio-CSRF": "1"}


class Clock:
    def __init__(self) -> None:
        self.t = 1_000_000.0

    def __call__(self) -> float:
        return self.t


@pytest.fixture(autouse=True)
def _fast_hash(monkeypatch):
    # 600k vòng PBKDF2 mỗi lần băm làm bộ test chậm vô ích; định dạng vẫn giữ.
    monkeypatch.setattr(acc, "PBKDF2_ITERATIONS", 1000)


@pytest.fixture
def clock():
    return Clock()


@pytest.fixture
def store(clock):
    s = acc.AccountStore(":memory:", clock=clock)
    yield s
    s.close()


@pytest.fixture
def accounts(store):
    return acc.Accounts(store)


# ── nghiệp vụ ────────────────────────────────────────────────────────────────

def test_first_user_is_active_admin_and_later_users_wait(accounts):
    first = accounts.register_password("Chu@Vi.vn", "Chủ hệ thống", PW)
    assert first.email == "chu@vi.vn"
    assert first.is_admin and first.active
    second = accounts.register_password("ban@vi.vn", "Bạn", PW)
    assert not second.is_admin and second.status == acc.STATUS_PENDING


def test_duplicate_registration_returns_none(accounts):
    accounts.register_password("a@vi.vn", "A", PW)
    assert accounts.register_password("A@vi.vn", "A lần hai", PW) is None


def test_admin_emails_restrict_bootstrap(store):
    store.admin_emails = {"boss@vi.vn"}
    accounts = acc.Accounts(store)
    stranger = accounts.register_password("la@vi.vn", "Lạ", PW)
    assert not stranger.is_admin and stranger.status == acc.STATUS_PENDING
    boss = accounts.register_password("boss@vi.vn", "Sếp", PW)
    assert boss.is_admin and boss.active


@pytest.mark.parametrize("email,name,password,field", [
    ("khong-phai-email", "A", PW, "email"),
    ("a@vi.vn", "   ", PW, "full_name"),
    ("a@vi.vn", "A", "ngan", "password"),
    ("abcdefghij@vi.vn", "A", "abcdefghij", "password"),
])
def test_register_validation(accounts, email, name, password, field):
    with pytest.raises(acc.AuthError) as exc:
        accounts.register_password(email, name, password)
    assert exc.value.status == 422 and field in exc.value.fields


def test_login_errors_do_not_reveal_which_emails_exist(accounts):
    accounts.register_password("co@vi.vn", "Có", PW)
    with pytest.raises(acc.AuthError) as missing:
        accounts.login_password("khong@vi.vn", PW)
    with pytest.raises(acc.AuthError) as wrong:
        accounts.login_password("co@vi.vn", "sai-mat-khau-roi")
    assert (missing.value.status, missing.value.message) == (wrong.value.status, wrong.value.message)


def test_pending_user_learns_status_only_with_right_password(accounts):
    accounts.register_password("admin@vi.vn", "QTV", PW)
    accounts.register_password("cho@vi.vn", "Chờ", PW)
    with pytest.raises(acc.AuthError) as wrong:
        accounts.login_password("cho@vi.vn", "sai-mat-khau-roi")
    assert wrong.value.code == acc.ERR_BAD_CREDENTIALS
    with pytest.raises(acc.AuthError) as right:
        accounts.login_password("cho@vi.vn", PW)
    assert right.value.code == acc.ERR_PENDING


def test_lockout_after_five_failures_then_expires(accounts, clock):
    accounts.register_password("a@vi.vn", "A", PW)
    for _ in range(acc.MAX_FAILED_LOGINS):
        with pytest.raises(acc.AuthError):
            accounts.login_password("a@vi.vn", "sai-mat-khau-roi")
    with pytest.raises(acc.AuthError) as locked:
        accounts.login_password("a@vi.vn", PW)
    assert locked.value.code == acc.ERR_TOO_MANY
    clock.t += acc.LOCKOUT_SECONDS + 1
    assert accounts.login_password("a@vi.vn", PW).email == "a@vi.vn"


def test_session_lifecycle(accounts, store, clock):
    user = accounts.register_password("a@vi.vn", "A", PW)
    token = store.create_session(user.email)
    assert store.resolve_session(token)[1] is True
    assert store.resolve_session("khac") is None
    clock.t += acc.SESSION_TTL + 1
    assert store.resolve_session(token) is None


def test_disabling_account_kills_its_session(accounts, store):
    admin = accounts.register_password("qtv@vi.vn", "QTV", PW)
    member = accounts.register_password("tv@vi.vn", "TV", PW)
    acc.admin_update(store, admin, member.email, "approve")
    token = store.create_session(member.email)
    assert store.resolve_session(token)[1] is True
    acc.admin_update(store, admin, member.email, "disable")
    user, ok = store.resolve_session(token)
    assert user.email == member.email and ok is False
    assert store.resolve_session(token) is None


def test_admin_guards(accounts, store):
    admin = accounts.register_password("qtv@vi.vn", "QTV", PW)
    with pytest.raises(acc.AuthError) as self_disable:
        acc.admin_update(store, admin, admin.email, "disable")
    assert self_disable.value.code == "SELF_ACTION"
    pending = accounts.register_password("tv@vi.vn", "TV", PW)
    with pytest.raises(acc.AuthError) as not_active:
        acc.admin_update(store, admin, pending.email, "make_admin")
    assert not_active.value.code == "NOT_ACTIVE"
    acc.admin_update(store, admin, pending.email, "delete")
    assert store.get(pending.email) is None


def test_google_login_takes_over_unverified_password(accounts, store):
    accounts.register_password("qtv@vi.vn", "QTV", PW)
    squatter = accounts.register_password("that@vi.vn", "Kẻ chiếm chỗ", PW)
    acc.admin_update(store, store.get("qtv@vi.vn"), squatter.email, "approve")
    user = accounts.login_google({"email": "that@vi.vn", "name": "Chủ thật", "email_verified": True})
    assert user.email_verified and user.password_hash == "" and user.providers == ["google"]
    with pytest.raises(acc.AuthError) as unverified:
        accounts.login_google({"email": "x@vi.vn", "email_verified": False})
    assert unverified.value.code == acc.ERR_EMAIL_UNVERIFIED


def test_state_cookie_roundtrip(accounts):
    url, cookie = accounts.build_google_redirect()
    state = dict(p.split("=", 1) for p in url.split("?", 1)[1].split("&"))["state"]
    assert accounts.verify_state_cookie(cookie, state)
    assert accounts.verify_state_cookie(cookie, "khac") is None
    assert accounts.verify_state_cookie(cookie[:-4] + "AAAA", state) is None


def test_password_hash_format_matches_vonia():
    stored = acc.hash_password("xin-chao-viet-nam")
    scheme, rounds, _salt, _digest = stored.split("$")
    assert scheme == "pbkdf2-sha256" and int(rounds) == acc.PBKDF2_ITERATIONS
    assert acc.verify_password(stored, "xin-chao-viet-nam")
    assert not acc.verify_password(stored, "sai")


# ── HTTP: router + cổng ──────────────────────────────────────────────────────

@pytest.fixture
def client(monkeypatch, accounts):
    from api.routers import accounts as router_mod

    monkeypatch.setenv(acc.ACCOUNTS_ENV, "on")
    acc.reset_accounts_for_tests(accounts)
    app = FastAPI()
    app.include_router(router_mod.router)

    @app.get("/engines")
    def engines():
        return {"ok": True}

    @app.get("/")
    def root():
        return {"spa": True}

    app.add_middleware(AccountGateMiddleware)
    with TestClient(app) as c:
        yield c
    acc.reset_accounts_for_tests(None)


def _register(client, email, name="Người dùng"):
    return client.post("/account/register", json={"email": email, "full_name": name, "password": PW},
                       headers=CSRF)


def test_gate_blocks_api_and_redirects_pages(client):
    r = client.get("/engines")
    assert r.status_code == 401 and r.json()["detail"] == acc.LOGIN_REQUIRED_DETAIL
    r = client.get("/", headers={"Accept": "text/html"}, follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/account/login"
    assert client.get("/account/login").status_code == 200
    assert "Đăng nhập" in client.get("/account/login").text


def test_register_first_admin_then_use_api(client):
    r = _register(client, "qtv@vi.vn", "QTV")
    assert r.status_code == 200 and r.json()["user"]["is_admin"]
    assert acc.COOKIE in r.cookies
    assert client.get("/engines").json() == {"ok": True}
    assert client.get("/account/me").json()["user"]["email"] == "qtv@vi.vn"


def test_second_registration_waits_and_duplicate_looks_identical(client):
    _register(client, "qtv@vi.vn")
    client.cookies.clear()
    new = _register(client, "moi@vi.vn")
    dup = _register(client, "moi@vi.vn")
    assert new.status_code == dup.status_code == 202
    assert new.json() == dup.json()
    r = client.post("/account/login", json={"email": "moi@vi.vn", "password": PW}, headers=CSRF)
    assert r.status_code == 403 and r.json()["redirect"] == "pending"


def test_posts_require_csrf_header(client):
    r = client.post("/account/register", json={"email": "a@vi.vn", "full_name": "A", "password": PW})
    assert r.status_code == 403


def test_admin_approves_member_via_api(client):
    _register(client, "qtv@vi.vn")
    admin_cookie = client.cookies.get(acc.COOKIE)
    client.cookies.clear()
    _register(client, "tv@vi.vn")
    client.cookies.set(acc.COOKIE, admin_cookie)
    users = client.get("/account/users").json()
    assert users["pending"] == 1
    r = client.post("/account/users/tv@vi.vn", json={"action": "approve"}, headers=CSRF)
    assert r.status_code == 200 and r.json()["user"]["status"] == "active"
    client.cookies.clear()
    r = client.post("/account/login", json={"email": "tv@vi.vn", "password": PW}, headers=CSRF)
    assert r.status_code == 200
    assert client.get("/account/users").status_code == 403  # thành viên thường


def test_logout_revokes_session(client):
    _register(client, "qtv@vi.vn")
    token = client.cookies.get(acc.COOKIE)
    client.post("/account/logout", json={}, headers=CSRF)
    client.cookies.set(acc.COOKIE, token)
    assert client.get("/engines").status_code == 401


def test_websocket_refused_without_session(client):
    from starlette.websockets import WebSocketDisconnect

    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect("/ws"):
            pass
    assert exc.value.code == 1008


def test_gate_off_lets_everything_through(client, monkeypatch):
    monkeypatch.setenv(acc.ACCOUNTS_ENV, "off")
    assert client.get("/engines").json() == {"ok": True}
    assert client.get("/account/me").json() == {"enabled": False, "user": None}


def test_voicestudio_api_key_bypasses_account_login(client, monkeypatch):
    # Công cụ tự động (MCP, n8n…) không có phiên trình duyệt: API key sẵn có
    # của VoiceStudio là danh tính đủ mạnh để qua cổng.
    monkeypatch.setenv("OMNIVOICE_API_KEY", "khoa-bi-mat-123")
    assert client.get("/engines").status_code == 401
    r = client.get("/engines", headers={"Authorization": "Bearer khoa-bi-mat-123"})
    assert r.json() == {"ok": True}


@pytest.mark.parametrize("email", ["a\n@vi.vn", "a@vi.vn\r\nX", "a\t@vi.vn", "a\x00@vi.vn"])
def test_email_rejects_control_and_whitespace(email):
    assert not acc.is_email(email)


def test_log_values_cannot_forge_lines():
    from api.routers.accounts import _clean

    assert "\n" not in _clean("x\nINFO giả mạo") and "\r" not in _clean("x\r")
