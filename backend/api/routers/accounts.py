"""Đăng ký / đăng nhập / quản trị thành viên — các route ``/account/*``.

Nghiệp vụ nằm ở ``core.accounts``; tệp này chỉ dịch HTTP ↔ nghiệp vụ. Route
đồng bộ (``def``) để FastAPI chạy chúng trong threadpool: băm PBKDF2 600k vòng
và SQLite không chặn event loop.
"""

from __future__ import annotations

import logging
import urllib.parse
from typing import Optional

from fastapi import APIRouter, Query, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel

from core.account_pages import (
    login_page,
    members_page,
    pending_page,
    profile_page,
    register_page,
)
from core.accounts import (
    ADMIN_ACTIONS,
    COOKIE,
    ERR_GOOGLE_DENIED,
    ERR_LOGIN_INVALID,
    ERR_PENDING,
    REASONS,
    SESSION_TTL,
    STATE_COOKIE,
    STATUS_PENDING,
    STATUSES,
    AuthError,
    User,
    accounts_enabled,
    admin_update,
    get_accounts,
)
from core.csrf import CSRF_HEADER, CSRF_VALUE, effective_scheme

log = logging.getLogger("omnivoice.accounts")

router = APIRouter(prefix="/account", tags=["account"])

_NO_STORE = {"Cache-Control": "no-store"}


class LoginBody(BaseModel):
    email: str = ""
    password: str = ""


class RegisterBody(BaseModel):
    email: str = ""
    full_name: str = ""
    password: str = ""


class PasswordBody(BaseModel):
    current_password: str = ""
    password: str = ""


class AdminAction(BaseModel):
    action: str


# ── tiện ích ─────────────────────────────────────────────────────────────────

def _err(status: int, message: str, code: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"error": {"message": message, "type": code}},
                        headers=_NO_STORE)


def _auth_err(exc: AuthError) -> JSONResponse:
    body: dict = {"message": exc.message, "type": exc.code}
    if exc.fields:
        body["fields"] = exc.fields
    return JSONResponse(status_code=exc.status, content={"error": body}, headers=_NO_STORE)


def _html(markup: str) -> HTMLResponse:
    return HTMLResponse(markup, headers=_NO_STORE)


def _secure(request: Request) -> bool:
    return effective_scheme(request) == "https"


def _set_session_cookie(request: Request, resp: Response, token: str) -> None:
    # HttpOnly: JS không đọc được. Lax (không Strict): lượt gọi về từ Google là
    # điều hướng cấp cao nhất từ tên miền khác, Strict sẽ chặn cookie.
    resp.set_cookie(COOKIE, token, httponly=True, samesite="lax",
                    secure=_secure(request), max_age=SESSION_TTL, path="/")


def _json_post_ok(request: Request) -> bool:
    """Chỉ nhận POST JSON kèm header chống CSRF — form giả mạo từ trang khác
    không đặt được hai thứ này nếu không qua CORS preflight."""
    ctype = request.headers.get("content-type", "").split(";")[0].strip().lower()
    return ctype == "application/json" and request.headers.get(CSRF_HEADER) == CSRF_VALUE


def _csrf_refused() -> JSONResponse:
    return _err(403, "Yêu cầu không hợp lệ (thiếu header chống CSRF).", "csrf")


def _current_user(request: Request) -> Optional[User]:
    resolved = get_accounts().store.resolve_session(request.cookies.get(COOKIE))
    return resolved[0] if resolved and resolved[1] else None


def _to_login(reason: str) -> RedirectResponse:
    # URL đích dựng từ hằng số, không từ yêu cầu → không có open redirect.
    resp = RedirectResponse(
        "pending" if reason == "cho_duyet" else "login?" + urllib.parse.urlencode({"loi": reason}),
        status_code=303)
    resp.delete_cookie(STATE_COOKIE, path="/")
    return resp


def _disabled() -> JSONResponse:
    return _err(404, "Chức năng tài khoản đang tắt (VOICESTUDIO_ACCOUNTS=off).", "accounts_disabled")


# ── trang HTML ───────────────────────────────────────────────────────────────

@router.get("/login", include_in_schema=False)
def account_login_page(request: Request, loi: Optional[str] = Query(None)):
    if not accounts_enabled():
        return RedirectResponse("/", status_code=303)
    if _current_user(request):
        return RedirectResponse("/", status_code=303)
    return _html(login_page(get_accounts().google_enabled, loi))


@router.get("/register", include_in_schema=False)
def account_register_page(request: Request):
    if not accounts_enabled():
        return RedirectResponse("/", status_code=303)
    if _current_user(request):
        return RedirectResponse("/", status_code=303)
    accounts = get_accounts()
    return _html(register_page(accounts.google_enabled,
                               first_user=not accounts.store.has_bootstrap_admin()))


@router.get("/pending", include_in_schema=False)
def account_pending_page():
    return _html(pending_page())


@router.get("/profile", include_in_schema=False)
def account_profile_page(request: Request):
    user = _current_user(request)
    if not user:
        return RedirectResponse("login", status_code=303)
    return _html(profile_page(user.public()))


@router.get("/members", include_in_schema=False)
def account_members_page(request: Request):
    user = _current_user(request)
    if not user:
        return RedirectResponse("login", status_code=303)
    if not user.is_admin:
        return RedirectResponse("profile", status_code=303)
    return _html(members_page(user.email))


# ── JSON: đăng nhập / đăng ký / phiên ────────────────────────────────────────

@router.get("/me")
def account_me(request: Request):
    """Người dùng hiện tại. ``enabled: false`` khi chức năng tài khoản đang tắt."""
    if not accounts_enabled():
        return JSONResponse({"enabled": False, "user": None}, headers=_NO_STORE)
    user = _current_user(request)
    if not user:
        return _err(401, "Chưa đăng nhập.", "unauthorized")
    return JSONResponse({"enabled": True, "user": user.public()}, headers=_NO_STORE)


@router.post("/login")
def account_login(request: Request, body: LoginBody):
    """Đăng nhập bằng email + mật khẩu → đặt cookie phiên."""
    if not accounts_enabled():
        return _disabled()
    if not _json_post_ok(request):
        return _csrf_refused()
    accounts = get_accounts()
    try:
        user = accounts.login_password(body.email, body.password)
    except AuthError as exc:
        if exc.code == ERR_PENDING:
            return JSONResponse(status_code=403, headers=_NO_STORE, content={
                "error": {"message": exc.message, "type": exc.code}, "redirect": "pending"})
        return _auth_err(exc)
    token = accounts.store.create_session(user.email)
    resp = JSONResponse({"user": user.public(), "redirect": "/"}, headers=_NO_STORE)
    _set_session_cookie(request, resp, token)
    log.info("Password login: %s", user.email)
    return resp


@router.post("/register")
def account_register(request: Request, body: RegisterBody):
    """Người đầu tiên → Quản trị viên, đăng nhập luôn. Người sau → chờ duyệt;
    email trùng nhận CÙNG câu trả lời (không dò được email đã đăng ký)."""
    if not accounts_enabled():
        return _disabled()
    if not _json_post_ok(request):
        return _csrf_refused()
    accounts = get_accounts()
    try:
        user = accounts.register_password(body.email, body.full_name, body.password)
    except AuthError as exc:
        return _auth_err(exc)
    if user is not None and user.active:
        token = accounts.store.create_session(user.email)
        resp = JSONResponse({"user": user.public(), "redirect": "/",
                             "message": "Đã tạo tài khoản Quản trị viên."}, headers=_NO_STORE)
        _set_session_cookie(request, resp, token)
        log.info("Bootstrap admin registered: %s", user.email)
        return resp
    if user is not None:
        log.info("New registration pending approval: %s", user.email)
    return JSONResponse(status_code=202, headers=_NO_STORE, content={
        "message": "Đã nhận yêu cầu đăng ký. Tài khoản sẽ dùng được sau khi Quản trị viên duyệt."})


@router.post("/password")
def account_password(request: Request, body: PasswordBody):
    if not _json_post_ok(request):
        return _csrf_refused()
    user = _current_user(request)
    if not user:
        return _err(401, "Chưa đăng nhập.", "unauthorized")
    try:
        get_accounts().change_password(user, body.current_password, body.password)
    except AuthError as exc:
        return _auth_err(exc)
    return JSONResponse({"message": "Đã đổi mật khẩu."}, headers=_NO_STORE)


@router.get("/logout", include_in_schema=False)
def account_logout(request: Request):
    get_accounts().store.revoke_session(request.cookies.get(COOKIE))
    resp = RedirectResponse("login", status_code=303)
    resp.delete_cookie(COOKIE, path="/")
    return resp


@router.post("/logout")
def account_logout_post(request: Request):
    if not _json_post_ok(request):
        return _csrf_refused()
    get_accounts().store.revoke_session(request.cookies.get(COOKIE))
    resp = JSONResponse({"redirect": "login"}, headers=_NO_STORE)
    resp.delete_cookie(COOKIE, path="/")
    return resp


# ── Google OAuth ─────────────────────────────────────────────────────────────

@router.get("/google", include_in_schema=False)
def account_google(request: Request):
    """Bắt đầu OAuth + PKCE, chuyển sang Google."""
    accounts = get_accounts()
    if not accounts_enabled() or not accounts.google_enabled:
        return _to_login("google_chua_bat")
    url, state_cookie_val = accounts.build_google_redirect()
    resp = RedirectResponse(url, status_code=303)
    resp.set_cookie(STATE_COOKIE, state_cookie_val, httponly=True, samesite="lax",
                    secure=_secure(request), max_age=600, path="/")
    return resp


@router.get("/google/callback", include_in_schema=False)
def account_google_callback(
    request: Request,
    code: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
):
    """Nhận lượt gọi về từ Google, áp luật duyệt, mở phiên."""
    import httpx

    accounts = get_accounts()
    if not accounts_enabled() or not accounts.google_enabled:
        return _to_login("google_chua_bat")
    # Trang đích của callback nằm ở /account/google/…, nên đường tương đối về
    # trang đăng nhập cần thêm "../".
    def back(reason: str) -> RedirectResponse:
        resp = _to_login(reason)
        resp.headers["location"] = "../" + resp.headers["location"]
        return resp

    if error:
        log.info("Google OAuth callback error: %s", error)
        return back(REASONS[ERR_GOOGLE_DENIED])
    code_verifier = accounts.verify_state_cookie(request.cookies.get(STATE_COOKIE), state or "")
    if not code or not code_verifier:
        log.warning("Google OAuth callback: missing code or state mismatch.")
        return back(REASONS[ERR_LOGIN_INVALID])
    try:
        with httpx.Client(timeout=15) as http:
            profile = accounts.fetch_google_profile(http, code, code_verifier)
    except (httpx.HTTPError, ValueError) as exc:
        log.error("Google OAuth exchange failed: %s", exc)
        return back("he_thong")
    try:
        user = accounts.login_google(profile)
    except AuthError as exc:
        log.info("Google login refused (%s): %s", exc.code, profile.get("email"))
        return back(REASONS.get(exc.code, "he_thong"))

    token = accounts.store.create_session(user.email)
    resp = RedirectResponse("/", status_code=303)
    _set_session_cookie(request, resp, token)
    resp.delete_cookie(STATE_COOKIE, path="/")
    log.info("Google login: %s", user.email)
    return resp


# ── Quản trị thành viên (chỉ Quản trị viên) ──────────────────────────────────

def _admin(request: Request) -> Optional[User]:
    user = _current_user(request)
    return user if user is not None and user.is_admin else None


@router.get("/users")
def account_list_users(request: Request, status: Optional[str] = Query(None)):
    if not _admin(request):
        return _err(403, "Chỉ Quản trị viên mới được thực hiện thao tác này.", "forbidden")
    if status is not None and status not in STATUSES:
        return _err(400, "Trạng thái không hợp lệ.", "invalid_request")
    users = get_accounts().store.list(status)
    users.sort(key=lambda u: (u.status != STATUS_PENDING, -u.created_at))
    return JSONResponse({"users": [u.public() for u in users],
                         "pending": sum(1 for u in users if u.status == STATUS_PENDING)},
                        headers=_NO_STORE)


@router.post("/users/{email:path}")
def account_user_action(request: Request, email: str, body: AdminAction):
    if not _json_post_ok(request):
        return _csrf_refused()
    actor = _admin(request)
    if not actor:
        return _err(403, "Chỉ Quản trị viên mới được thực hiện thao tác này.", "forbidden")
    if body.action not in ADMIN_ACTIONS:
        return _err(400, "Thao tác không hợp lệ.", "invalid_request")
    try:
        user = admin_update(get_accounts().store, actor, email, body.action)
    except AuthError as exc:
        return _auth_err(exc)
    log.info("Admin %s: %s → %s", actor.email, body.action, email)
    return JSONResponse({"user": user.public() if user else None}, headers=_NO_STORE)
