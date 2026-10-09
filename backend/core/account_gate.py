"""Cổng đăng nhập tài khoản: mọi yêu cầu HTTP / WebSocket phải mang phiên hợp lệ.

Chỉ hoạt động khi ``VOICESTUDIO_ACCOUNTS`` bật (mặc định bật; ứng dụng desktop
Electron tự tắt). Pure ASGI để không đệm body (upload/stream âm thanh lớn).

Không có phiên:
* điều hướng trình duyệt (GET + ``Accept: text/html``) → chuyển tới
  ``/account/login`` (hoặc ``/account/pending`` nếu tài khoản bị khoá/chưa duyệt);
* yêu cầu API → 401 ``{"detail": "account login required"}`` — giao diện React
  nhận ra chi tiết này và chuyển sang trang đăng nhập;
* WebSocket → đóng với mã 1008.

Không có ngoại lệ cho loopback: đứng sau nginx/Caddy trên cùng máy thì MỌI
yêu cầu từ Internet đều trông như đến từ 127.0.0.1. Công cụ tự động (MCP, CLI,
n8n…) đi qua bằng API key sẵn có của VoiceStudio (``OMNIVOICE_API_KEY``).
"""

from __future__ import annotations

from typing import Optional

import anyio
from starlette.datastructures import Headers
from starlette.responses import JSONResponse, RedirectResponse

from core.accounts import (
    COOKIE,
    LOGIN_REQUIRED_DETAIL,
    accounts_enabled,
    get_accounts,
)

# Đường không qua cổng: trang/route tài khoản, thăm dò sức khoẻ của launcher,
# và tài nguyên tĩnh của giao diện (không chứa dữ liệu người dùng).
_EXEMPT_EXACT = frozenset({
    "/account",
    "/health",
    "/startup/progress",
    "/system/shutdown-intent",
    "/early-error-capture.js",
    "/manifest.webmanifest",
})
_EXEMPT_PREFIXES = ("/account/", "/assets/", "/favicon")

# Danh tính đủ mạnh để bỏ qua đăng nhập tài khoản: API key (OMNIVOICE_API_KEY)
# và phiên quản trị đổi từ API key. PIN chia sẻ LAN thì KHÔNG — PIN dành cho
# khách xem tạm, không phải danh tính người dùng.
_STRONG_PRINCIPALS = frozenset({"api_key", "admin_session"})

ACCOUNT_USER_STATE = "account_user"


def is_exempt_path(path: str) -> bool:
    return path in _EXEMPT_EXACT or path.startswith(_EXEMPT_PREFIXES)


def _cookie_value(headers: Headers, name: str) -> Optional[str]:
    raw = headers.get("cookie")
    if not raw:
        return None
    for part in raw.split(";"):
        key, sep, value = part.strip().partition("=")
        if sep and key == name:
            return value
    return None


def _strong_principal(scope) -> bool:
    try:
        from starlette.requests import HTTPConnection

        from core.auth import principal_for

        principal = principal_for(HTTPConnection(scope))
    except Exception:  # noqa: BLE001 — cổng không được sập vì bộ phân giải danh tính
        return False
    kind = getattr(principal.kind, "value", principal.kind)
    return kind in _STRONG_PRINCIPALS


class AccountGateMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] not in ("http", "websocket") or not accounts_enabled():
            return await self.app(scope, receive, send)
        if scope["type"] == "http" and str(scope.get("method", "GET")).upper() == "OPTIONS":
            return await self.app(scope, receive, send)
        path = scope.get("path", "") or ""
        if is_exempt_path(path) or _strong_principal(scope):
            return await self.app(scope, receive, send)

        headers = Headers(scope=scope)
        token = _cookie_value(headers, COOKIE)
        resolved = None
        if token:
            store = get_accounts().store
            resolved = await anyio.to_thread.run_sync(store.resolve_session, token)
        if resolved and resolved[1]:
            scope.setdefault("state", {})[ACCOUNT_USER_STATE] = resolved[0]
            return await self.app(scope, receive, send)

        if scope["type"] == "websocket":
            await receive()  # websocket.connect
            await send({"type": "websocket.close", "code": 1008})
            return

        method = str(scope.get("method", "GET")).upper()
        wants_html = method in ("GET", "HEAD") and "text/html" in headers.get("accept", "")
        if wants_html:
            resp = RedirectResponse("/account/pending" if resolved else "/account/login",
                                    status_code=303)
        elif resolved:
            resp = JSONResponse({"detail": LOGIN_REQUIRED_DETAIL, "reason": "account_pending"},
                                status_code=403)
        else:
            resp = JSONResponse({"detail": LOGIN_REQUIRED_DETAIL}, status_code=401)
        resp.headers["Cache-Control"] = "no-store"
        if token:
            # Phiên hỏng / tài khoản vừa bị khoá → xoá cookie.
            resp.delete_cookie(COOKIE, path="/")
        return await resp(scope, receive, send)
