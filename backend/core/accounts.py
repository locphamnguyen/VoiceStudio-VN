"""Tài khoản người dùng: đăng ký / đăng nhập bằng email + mật khẩu hoặc Google.

Port từ module xác thực của Vonia (``omnivoice/server/auth.py``), giữ nguyên các
quyết định nghiệp vụ, nhưng đổi kho lưu từ Redis sang **SQLite** — người dùng
không rành kỹ thuật không phải cài thêm Redis/Docker:

* Hai đường vào: email + mật khẩu (PBKDF2-SHA256, cùng định dạng băm với
  Vonia/SSTC để chuyển dữ liệu được) và "Tiếp tục với Google" (OAuth 2.0 + PKCE,
  chỉ bật khi đặt ``GOOGLE_CLIENT_ID`` + ``GOOGLE_CLIENT_SECRET``).
* **Người đăng ký ĐẦU TIÊN là Quản trị viên, dùng được ngay.** Mọi người đăng ký
  sau ở trạng thái ``pending`` cho tới khi Quản trị viên duyệt.
* Tài khoản chưa duyệt HOẶC bị khoá nhận CÙNG một mã lỗi (``ACCOUNT_PENDING``) —
  phân biệt hai ca là tiết lộ email nào đã có tài khoản.
* Đăng ký trùng email trả CÙNG một câu như đăng ký mới (chống dò tài khoản).
* Sai mật khẩu 5 lần → khoá đăng nhập bằng mật khẩu 15 phút cho email đó.
* Phiên lưu dạng băm SHA-256 của token, hạn 30 ngày trượt. Mỗi yêu cầu đều đọc
  lại hồ sơ người dùng, nên khoá tài khoản là văng ra ngay.

Bật/tắt bằng biến môi trường ``VOICESTUDIO_ACCOUNTS`` (mặc định ``on``). Ứng
dụng desktop Electron tự đặt ``off`` khi khởi chạy backend: ở đó máy tính của
chính người dùng đã là lớp đăng nhập.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import sqlite3
import threading
import time
import unicodedata
import urllib.parse
from dataclasses import dataclass, field
from typing import Callable, Optional

# ── Cấu hình qua biến môi trường ─────────────────────────────────────────────
ACCOUNTS_ENV = "VOICESTUDIO_ACCOUNTS"
ADMIN_EMAILS_ENV = "VOICESTUDIO_ADMIN_EMAILS"
ALLOWED_DOMAIN_ENV = "VOICESTUDIO_ALLOWED_DOMAIN"
PUBLIC_URL_ENV = "VOICESTUDIO_PUBLIC_URL"
SECRET_ENV = "VOICESTUDIO_SESSION_SECRET"
DB_PATH_ENV = "VOICESTUDIO_ACCOUNTS_DB"

# ── Cookie ───────────────────────────────────────────────────────────────────
COOKIE = "vs_session"
STATE_COOKIE = "vs_oauth_state"

# ── Phiên ────────────────────────────────────────────────────────────────────
SESSION_TTL = 30 * 24 * 3600      # 30 ngày kể từ lần dùng cuối
SESSION_REFRESH = 3600            # chỉ ghi lại hạn khi phiên "cũ" quá 1 giờ

# ── Trạng thái tài khoản ─────────────────────────────────────────────────────
STATUS_ACTIVE = "active"
STATUS_PENDING = "pending"
STATUS_DISABLED = "disabled"
STATUSES = (STATUS_ACTIVE, STATUS_PENDING, STATUS_DISABLED)

# ── Mã lỗi — HỢP ĐỒNG với trang đăng nhập (tham số ?loi=) ────────────────────
ERR_PENDING = "ACCOUNT_PENDING"
ERR_EMAIL_UNVERIFIED = "EMAIL_UNVERIFIED"
ERR_EMAIL_MISSING = "EMAIL_MISSING"
ERR_DOMAIN = "DOMAIN_NOT_ALLOWED"
ERR_BAD_CREDENTIALS = "BAD_CREDENTIALS"
ERR_TOO_MANY = "TOO_MANY_ATTEMPTS"
ERR_GOOGLE_DENIED = "GOOGLE_DENIED"
ERR_LOGIN_INVALID = "LOGIN_REQUEST_INVALID"
ERR_INVALID = "INVALID"

# Mã lỗi → giá trị ``?loi=`` trên trang đăng nhập. Mã lạ → "he_thong".
REASONS = {
    ERR_PENDING: "cho_duyet",
    ERR_EMAIL_UNVERIFIED: "chua_xac_minh",
    ERR_EMAIL_MISSING: "thieu_email",
    ERR_DOMAIN: "sai_mien",
    ERR_GOOGLE_DENIED: "google_tu_choi",
    ERR_LOGIN_INVALID: "phien_dang_nhap_hong",
}

# Chi tiết 401 mà giao diện React nhận ra để chuyển sang trang đăng nhập.
LOGIN_REQUIRED_DETAIL = "account login required"

# ── Mật khẩu ─────────────────────────────────────────────────────────────────
PBKDF2_ITERATIONS = 600_000
SALT_LEN = 16
HASH_LEN = 32
HASH_SCHEME = "pbkdf2-sha256"
PASSWORD_MIN = 10
PASSWORD_MAX = 128

MAX_FAILED_LOGINS = 5
LOCKOUT_SECONDS = 15 * 60


def accounts_enabled() -> bool:
    raw = (os.environ.get(ACCOUNTS_ENV) or "on").strip().lower()
    return raw not in ("off", "0", "false", "no")


class AuthError(Exception):
    """Lỗi nghiệp vụ của luồng xác thực — tầng HTTP dịch sang status + mã."""

    def __init__(self, status: int, code: str, message: str,
                 fields: Optional[dict[str, str]] = None) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message
        self.fields = fields or {}


# ═════════════════════════════════════════════════════════════════════════════
# Mật khẩu — PBKDF2-SHA256, định dạng ``pbkdf2-sha256$<vòng>$<muối>$<băm>``
# (base64 chuẩn không đệm), trùng với Vonia để chuyển dữ liệu được.
# ═════════════════════════════════════════════════════════════════════════════

def _b64(b: bytes) -> str:
    return base64.b64encode(b).decode().rstrip("=")


def _unb64(s: str) -> bytes:
    return base64.b64decode(s + "=" * (-len(s) % 4))


def hash_password(password: str, iterations: Optional[int] = None) -> str:
    iterations = iterations or PBKDF2_ITERATIONS
    salt = secrets.token_bytes(SALT_LEN)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, iterations, HASH_LEN)
    return f"{HASH_SCHEME}${iterations}${_b64(salt)}${_b64(dk)}"


def verify_password(stored: str, password: str) -> bool:
    parts = (stored or "").split("$")
    if len(parts) != 4 or parts[0] != HASH_SCHEME:
        return False
    try:
        iterations = int(parts[1])
        salt = _unb64(parts[2])
        expected = _unb64(parts[3])
    except (ValueError, TypeError):
        return False
    if iterations < 1:
        return False
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, iterations, len(expected))
    return hmac.compare_digest(dk, expected)


def needs_rehash(stored: str) -> bool:
    parts = (stored or "").split("$")
    if len(parts) != 4 or parts[0] != HASH_SCHEME:
        return True
    try:
        return int(parts[1]) < PBKDF2_ITERATIONS
    except ValueError:
        return True


def check_new_password(password: str, email: str = "") -> str:
    """Trả câu lỗi nếu mật khẩu không đạt, chuỗi rỗng nếu đạt."""
    n = len(password or "")
    if n < PASSWORD_MIN:
        return f"Mật khẩu phải có ít nhất {PASSWORD_MIN} ký tự."
    if n > PASSWORD_MAX:
        return f"Mật khẩu không được quá {PASSWORD_MAX} ký tự."
    if not password.strip():
        return "Mật khẩu không được chỉ gồm khoảng trắng."
    e = (email or "").strip().lower()
    if e:
        low = password.lower()
        if low == e or low == e.split("@", 1)[0]:
            return "Mật khẩu không được trùng địa chỉ email."
    return ""


def normalize_email(email: str) -> str:
    return unicodedata.normalize("NFC", (email or "").strip().lower())


def is_email(e: str) -> bool:
    """Kiểm tra hình thức tối thiểu: đúng một @, hai phía không rỗng, không khoảng trắng."""
    if not e or e.count("@") != 1 or any(ch.isspace() or not ch.isprintable() for ch in e):
        return False
    local, _, domain = e.partition("@")
    return bool(local) and "." in domain and not domain.startswith(".") and not domain.endswith(".")


def in_domain(email: str, domain: str) -> bool:
    """So phần sau @ (đòi ĐÚNG MỘT @ — chặn ``ke@evil.example@mien.example``)."""
    if email.count("@") != 1:
        return False
    return email.partition("@")[2].lower() == domain.lower()


_DUMMY_HASH: Optional[str] = None


def _dummy_verify(password: str) -> None:
    """Đối chiếu với một bản băm mồi — để email không tồn tại tốn CÙNG thời gian
    như sai mật khẩu (không dò được email nào có tài khoản qua thời gian trả lời)."""
    global _DUMMY_HASH
    if _DUMMY_HASH is None:
        _DUMMY_HASH = hash_password(secrets.token_urlsafe(16))
    verify_password(_DUMMY_HASH, password)


# ═════════════════════════════════════════════════════════════════════════════
# Người dùng + phiên (SQLite)
# ═════════════════════════════════════════════════════════════════════════════

@dataclass
class User:
    email: str
    full_name: str
    status: str = STATUS_PENDING
    is_admin: bool = False
    password_hash: str = ""
    providers: list[str] = field(default_factory=list)   # "password" | "google"
    email_verified: bool = False
    created_at: float = 0.0
    approved_by: str = ""
    approved_at: float = 0.0

    @property
    def active(self) -> bool:
        return self.status == STATUS_ACTIVE

    def public(self) -> dict:
        """Dữ liệu an toàn để trả cho giao diện (không có băm mật khẩu)."""
        return {
            "email": self.email,
            "full_name": self.full_name,
            "status": self.status,
            "is_admin": self.is_admin,
            "providers": list(self.providers),
            "email_verified": self.email_verified,
            "has_password": bool(self.password_hash),
            "created_at": self.created_at,
            "approved_by": self.approved_by,
            "approved_at": self.approved_at,
        }


_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    email          TEXT PRIMARY KEY,
    full_name      TEXT NOT NULL,
    status         TEXT NOT NULL,
    is_admin       INTEGER NOT NULL DEFAULT 0,
    password_hash  TEXT NOT NULL DEFAULT '',
    providers      TEXT NOT NULL DEFAULT '[]',
    email_verified INTEGER NOT NULL DEFAULT 0,
    created_at     REAL NOT NULL,
    approved_by    TEXT NOT NULL DEFAULT '',
    approved_at    REAL NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS sessions (
    token_hash TEXT PRIMARY KEY,
    email      TEXT NOT NULL,
    seen       REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS sessions_email ON sessions(email);
CREATE TABLE IF NOT EXISTS login_failures (
    email      TEXT PRIMARY KEY,
    count      INTEGER NOT NULL,
    expires_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""

BOOTSTRAP_KEY = "bootstrap_admin"


def _token_hash(token: str) -> str:
    # Lưu BĂM của token, không lưu nguyên văn: lộ bản sao CSDL không đồng nghĩa
    # lộ phiên đăng nhập của mọi người.
    return hashlib.sha256(token.encode()).hexdigest()


def default_db_path() -> str:
    override = (os.environ.get(DB_PATH_ENV) or "").strip()
    if override:
        return override
    from core.config import get_app_data_dir

    return os.path.join(get_app_data_dir(), "accounts.db")


class AccountStore:
    """Kho người dùng + phiên trên một tệp SQLite riêng (``accounts.db``).

    Mọi phương thức là đồng bộ và an toàn đa luồng (một khoá cho cả kết nối);
    tầng HTTP gọi chúng trong threadpool.
    """

    def __init__(self, path: str, admin_emails: Optional[set[str]] = None,
                 clock: Callable[[], float] = time.time) -> None:
        if path != ":memory:":
            os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        self._db = sqlite3.connect(path, check_same_thread=False, isolation_level=None)
        self._db.row_factory = sqlite3.Row
        self._lock = threading.RLock()
        # Nếu đặt VOICESTUDIO_ADMIN_EMAILS: chỉ các email này mới có thể trở
        # thành Quản trị viên đầu tiên. Để trống = đúng nghĩa "ai đăng ký trước".
        self.admin_emails = admin_emails or set()
        self.now = clock
        with self._lock:
            if path != ":memory:":
                self._db.execute("PRAGMA journal_mode=WAL")
            self._db.executescript(_SCHEMA)

    def close(self) -> None:
        with self._lock:
            self._db.close()

    # ── đọc / ghi người dùng ────────────────────────────────────────────────

    @staticmethod
    def _row_to_user(row: sqlite3.Row) -> User:
        return User(
            email=row["email"], full_name=row["full_name"], status=row["status"],
            is_admin=bool(row["is_admin"]), password_hash=row["password_hash"],
            providers=list(json.loads(row["providers"] or "[]")),
            email_verified=bool(row["email_verified"]), created_at=row["created_at"],
            approved_by=row["approved_by"], approved_at=row["approved_at"],
        )

    def get(self, email: str) -> Optional[User]:
        with self._lock:
            row = self._db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        return self._row_to_user(row) if row else None

    def save(self, user: User) -> None:
        with self._lock:
            self._db.execute(
                "UPDATE users SET full_name=?, status=?, is_admin=?, password_hash=?, "
                "providers=?, email_verified=?, approved_by=?, approved_at=? WHERE email=?",
                (user.full_name, user.status, int(user.is_admin), user.password_hash,
                 json.dumps(user.providers), int(user.email_verified), user.approved_by,
                 user.approved_at, user.email),
            )

    def list(self, status: Optional[str] = None) -> list[User]:
        with self._lock:
            if status is None:
                rows = self._db.execute("SELECT * FROM users ORDER BY created_at").fetchall()
            else:
                rows = self._db.execute(
                    "SELECT * FROM users WHERE status = ? ORDER BY created_at", (status,)
                ).fetchall()
        return [self._row_to_user(r) for r in rows]

    def count_admins(self) -> int:
        with self._lock:
            row = self._db.execute(
                "SELECT COUNT(*) FROM users WHERE is_admin = 1 AND status = ?", (STATUS_ACTIVE,)
            ).fetchone()
        return int(row[0])

    def has_bootstrap_admin(self) -> bool:
        with self._lock:
            row = self._db.execute("SELECT 1 FROM meta WHERE key = ?", (BOOTSTRAP_KEY,)).fetchone()
        return row is not None

    # ── tạo ─────────────────────────────────────────────────────────────────

    def create(self, email: str, full_name: str, *, password_hash: str = "",
               provider: str, email_verified: bool) -> Optional[User]:
        """Tạo tài khoản mới. Trả None nếu email đã có tài khoản.

        Người tạo ĐẦU TIÊN (giành được dòng ``bootstrap_admin`` trong bảng meta)
        thành Quản trị viên, kích hoạt ngay. Cả việc tạo lẫn giành quyền chạy
        trong một transaction ``BEGIN IMMEDIATE`` nên hai người đăng ký cùng lúc
        trên hệ thống trống chỉ một người thắng.
        """
        now = self.now()
        user = User(
            email=email, full_name=full_name or email, status=STATUS_PENDING,
            password_hash=password_hash, providers=[provider],
            email_verified=email_verified, created_at=now,
        )
        eligible = not self.admin_emails or email in self.admin_emails
        with self._lock:
            self._db.execute("BEGIN IMMEDIATE")
            try:
                exists = self._db.execute("SELECT 1 FROM users WHERE email = ?", (email,)).fetchone()
                if exists:
                    self._db.execute("ROLLBACK")
                    return None
                if eligible:
                    won = self._db.execute(
                        "INSERT OR IGNORE INTO meta(key, value) VALUES (?, ?)", (BOOTSTRAP_KEY, email)
                    ).rowcount == 1
                    if won:
                        user.is_admin = True
                        user.status = STATUS_ACTIVE
                        user.approved_by = "bootstrap"
                        user.approved_at = now
                self._db.execute(
                    "INSERT INTO users(email, full_name, status, is_admin, password_hash, providers, "
                    "email_verified, created_at, approved_by, approved_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (user.email, user.full_name, user.status, int(user.is_admin), user.password_hash,
                     json.dumps(user.providers), int(user.email_verified), user.created_at,
                     user.approved_by, user.approved_at),
                )
                self._db.execute("COMMIT")
            except BaseException:
                self._db.execute("ROLLBACK")
                raise
        return user

    def delete(self, email: str) -> None:
        with self._lock:
            self._db.execute("DELETE FROM users WHERE email = ?", (email,))
            self._db.execute("DELETE FROM sessions WHERE email = ?", (email,))

    # ── khoá đăng nhập sau nhiều lần sai ────────────────────────────────────

    def _failures(self, email: str) -> int:
        row = self._db.execute(
            "SELECT count, expires_at FROM login_failures WHERE email = ?", (email,)
        ).fetchone()
        if not row:
            return 0
        if row["expires_at"] <= self.now():
            self._db.execute("DELETE FROM login_failures WHERE email = ?", (email,))
            return 0
        return int(row["count"])

    def is_locked(self, email: str) -> bool:
        with self._lock:
            return self._failures(email) >= MAX_FAILED_LOGINS

    def record_failure(self, email: str) -> int:
        with self._lock:
            n = self._failures(email) + 1
            row = self._db.execute(
                "SELECT expires_at FROM login_failures WHERE email = ?", (email,)
            ).fetchone()
            expires = row["expires_at"] if row else 0.0
            if n == 1 or n == MAX_FAILED_LOGINS:
                # Đặt hạn lúc lượt đầu (cửa sổ đếm), và đặt lại lúc chạm ngưỡng
                # (khoá đủ 15 phút tính từ lần sai cuối).
                expires = self.now() + LOCKOUT_SECONDS
            self._db.execute(
                "INSERT INTO login_failures(email, count, expires_at) VALUES (?, ?, ?) "
                "ON CONFLICT(email) DO UPDATE SET count = excluded.count, expires_at = excluded.expires_at",
                (email, n, expires),
            )
            return n

    def clear_failures(self, email: str) -> None:
        with self._lock:
            self._db.execute("DELETE FROM login_failures WHERE email = ?", (email,))

    # ── phiên ───────────────────────────────────────────────────────────────

    def create_session(self, email: str) -> str:
        # Token MỚI mỗi lần đăng nhập — chống cố định phiên (session fixation).
        token = secrets.token_urlsafe(32)
        with self._lock:
            self._db.execute(
                "INSERT INTO sessions(token_hash, email, seen) VALUES (?, ?, ?)",
                (_token_hash(token), email, self.now()),
            )
        return token

    def resolve_session(self, token: Optional[str]) -> Optional[tuple[User, bool]]:
        """Đổi token lấy (user, còn_hiệu_lực).

        None = không có phiên. (user, False) = phiên trỏ tới tài khoản không còn
        kích hoạt (phiên đã bị xoá luôn). Đây là CỬA DUY NHẤT sinh danh tính từ
        cookie — khoá tài khoản chặn ở đây, không phải ở từng handler.
        """
        if not token:
            return None
        key = _token_hash(token)
        now = self.now()
        with self._lock:
            row = self._db.execute(
                "SELECT email, seen FROM sessions WHERE token_hash = ?", (key,)
            ).fetchone()
            if not row:
                return None
            if now - float(row["seen"]) >= SESSION_TTL:
                self._db.execute("DELETE FROM sessions WHERE token_hash = ?", (key,))
                return None
            user = self.get(row["email"])
            if user is None:
                self._db.execute("DELETE FROM sessions WHERE token_hash = ?", (key,))
                return None
            if not user.active:
                self._db.execute("DELETE FROM sessions WHERE token_hash = ?", (key,))
                return user, False
            if now - float(row["seen"]) >= SESSION_REFRESH:
                self._db.execute("UPDATE sessions SET seen = ? WHERE token_hash = ?", (now, key))
        return user, True

    def revoke_session(self, token: Optional[str]) -> None:
        if token:
            with self._lock:
                self._db.execute("DELETE FROM sessions WHERE token_hash = ?", (_token_hash(token),))


# ═════════════════════════════════════════════════════════════════════════════
# Nghiệp vụ đăng ký / đăng nhập (không biết gì về FastAPI)
# ═════════════════════════════════════════════════════════════════════════════

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"


class Accounts:
    """Cấu hình + nghiệp vụ xác thực."""

    def __init__(self, store: AccountStore) -> None:
        env = os.environ.get
        self.store = store
        self.google_client_id = (env("GOOGLE_CLIENT_ID") or "").strip()
        self.google_client_secret = (env("GOOGLE_CLIENT_SECRET") or "").strip()
        public_url = (env(PUBLIC_URL_ENV) or "").strip().rstrip("/")
        self.redirect_uri = f"{public_url}/account/google/callback"
        # Rỗng = MỌI MIỀN (mặc định). Cửa chặn nằm ở bước duyệt, không ở miền.
        self.allowed_domain = (env(ALLOWED_DOMAIN_ENV) or "").strip().lower().lstrip("@")
        secret = env(SECRET_ENV) or secrets.token_hex(32)
        self._secret = secret.encode()
        self.auth_url = GOOGLE_AUTH_URL
        self.token_url = GOOGLE_TOKEN_URL
        self.userinfo_url = GOOGLE_USERINFO_URL

    @property
    def google_enabled(self) -> bool:
        return bool(self.google_client_id and self.google_client_secret)

    def _check_domain(self, email: str, verb: str) -> None:
        if self.allowed_domain and not in_domain(email, self.allowed_domain):
            raise AuthError(403, ERR_DOMAIN, f"Chỉ tài khoản @{self.allowed_domain} mới {verb} được.")

    # ── Email + mật khẩu ────────────────────────────────────────────────────

    def register_password(self, email: str, full_name: str, password: str) -> Optional[User]:
        """Trả User nếu tạo mới, None nếu email đã có tài khoản. Tầng HTTP trả
        CÙNG một câu cho hai ca (trừ ca người đầu tiên được kích hoạt ngay)."""
        email = normalize_email(email)
        full_name = " ".join((full_name or "").split())
        errors: dict[str, str] = {}
        if not is_email(email):
            errors["email"] = "Địa chỉ email không hợp lệ."
        if not full_name:
            errors["full_name"] = "Họ tên không được để trống."
        elif len(full_name) > 120:
            errors["full_name"] = "Họ tên quá dài."
        why = check_new_password(password, email)
        if why:
            errors["password"] = why
        if errors:
            raise AuthError(422, ERR_INVALID, next(iter(errors.values())), errors)
        self._check_domain(email, "đăng ký")
        return self.store.create(email, full_name, password_hash=hash_password(password),
                                 provider="password", email_verified=False)

    def login_password(self, email: str, password: str) -> User:
        email = normalize_email(email)
        store = self.store
        if store.is_locked(email):
            raise AuthError(429, ERR_TOO_MANY,
                            "Đã thử sai quá nhiều lần. Vui lòng chờ ít phút rồi thử lại.")
        user = store.get(email) if email else None
        if user is None or not user.password_hash:
            # Email không tồn tại / tài khoản chỉ vào bằng Google: CÙNG câu, CÙNG
            # thời gian với sai mật khẩu.
            _dummy_verify(password or "")
            store.record_failure(email)
            raise AuthError(401, ERR_BAD_CREDENTIALS, "Email hoặc mật khẩu không đúng.")
        if not verify_password(user.password_hash, password or ""):
            store.record_failure(email)
            raise AuthError(401, ERR_BAD_CREDENTIALS, "Email hoặc mật khẩu không đúng.")
        store.clear_failures(email)
        # Kiểm trạng thái SAU khi đúng mật khẩu: người không biết mật khẩu
        # không được biết tài khoản đang chờ duyệt hay bị khoá.
        if not user.active:
            raise AuthError(403, ERR_PENDING,
                            "Tài khoản chưa được kích hoạt. Vui lòng liên hệ Quản trị viên.")
        if needs_rehash(user.password_hash):
            user.password_hash = hash_password(password)
            store.save(user)
        return user

    def change_password(self, user: User, current: str, new: str) -> None:
        if user.password_hash and not verify_password(user.password_hash, current or ""):
            raise AuthError(401, ERR_BAD_CREDENTIALS, "Mật khẩu hiện tại không đúng.")
        why = check_new_password(new, user.email)
        if why:
            raise AuthError(422, ERR_INVALID, why, {"password": why})
        user.password_hash = hash_password(new)
        if "password" not in user.providers:
            user.providers.append("password")
        self.store.save(user)

    # ── Google ──────────────────────────────────────────────────────────────

    def build_google_redirect(self) -> tuple[str, str]:
        """Trả (URL sang Google, giá trị cookie state đã ký).

        Cookie gói cả ``state`` (chống CSRF) và ``code_verifier`` (PKCE), nên không
        cần lưu gì phía máy chủ giữa lượt chuyển hướng và lượt gọi về.
        """
        state = secrets.token_urlsafe(32)
        code_verifier = secrets.token_urlsafe(48)
        code_challenge = (
            base64.urlsafe_b64encode(hashlib.sha256(code_verifier.encode()).digest())
            .rstrip(b"=").decode()
        )
        params = {
            "client_id": self.google_client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
            # Buộc chọn tài khoản — máy dùng chung không âm thầm đăng nhập lại
            # bằng tài khoản của người trước.
            "prompt": "select_account",
        }
        url = self.auth_url + "?" + urllib.parse.urlencode(params)
        return url, self._sign(json.dumps({"state": state, "cv": code_verifier}))

    def verify_state_cookie(self, cookie_val: Optional[str], returned_state: str) -> Optional[str]:
        """Trả code_verifier nếu state khớp, ngược lại None."""
        if not cookie_val or not returned_state:
            return None
        payload = self._unsign(cookie_val)
        if payload is None:
            return None
        try:
            data = json.loads(payload)
        except ValueError:
            return None
        if not isinstance(data, dict):
            return None
        if not hmac.compare_digest(str(data.get("state", "")), returned_state):
            return None
        return data.get("cv")

    def fetch_google_profile(self, http, code: str, code_verifier: str) -> dict:
        """Đổi mã uỷ quyền lấy hồ sơ {email, name, email_verified}.

        ``http`` là một ``httpx.Client``; ném ``httpx.HTTPError`` khi hỏng."""
        import httpx

        resp = http.post(self.token_url, data={
            "code": code,
            "client_id": self.google_client_id,
            "client_secret": self.google_client_secret,
            "redirect_uri": self.redirect_uri,
            "grant_type": "authorization_code",
            "code_verifier": code_verifier,
        })
        resp.raise_for_status()
        access_token = resp.json().get("access_token")
        if not access_token:
            raise httpx.HTTPError("token endpoint không trả access_token")
        resp = http.get(self.userinfo_url, headers={"Authorization": f"Bearer {access_token}"})
        resp.raise_for_status()
        info = resp.json()
        verified = info.get("email_verified")
        return {
            "email": normalize_email(info.get("email") or ""),
            "name": (info.get("name") or "").strip(),
            "email_verified": verified is True or str(verified).lower() == "true",
        }

    def login_google(self, profile: dict) -> User:
        """Áp luật ai-được-vào cho hồ sơ Google, tạo tài khoản chờ duyệt nếu mới."""
        store = self.store
        email = profile.get("email") or ""
        if not profile.get("email_verified"):
            # Google có thể trả email CHƯA xác minh — nhận nó là nhận lời khai
            # chưa kiểm chứng về danh tính.
            raise AuthError(403, ERR_EMAIL_UNVERIFIED, "Địa chỉ email chưa được Google xác minh.")
        if not email:
            raise AuthError(403, ERR_EMAIL_MISSING, "Google không trả về địa chỉ email.")
        self._check_domain(email, "đăng nhập")

        user = store.get(email)
        if user is None:
            user = store.create(email, profile.get("name") or email,
                                provider="google", email_verified=True)
            if user is None:            # vừa bị tạo song song — đọc lại
                user = store.get(email)
        else:
            changed = False
            if not user.email_verified:
                # Google vừa chứng minh chủ sở hữu email. Mật khẩu (nếu có) được
                # đặt bởi một người CHƯA chứng minh sở hữu email này — có thể là
                # kẻ chiếm chỗ trước — nên huỷ nó đi.
                user.email_verified = True
                user.password_hash = ""
                if "password" in user.providers:
                    user.providers.remove("password")
                changed = True
            if "google" not in user.providers:
                user.providers.append("google")
                changed = True
            if changed:
                store.save(user)
        assert user is not None
        if not user.active:
            raise AuthError(403, ERR_PENDING,
                            "Tài khoản chưa được kích hoạt. Vui lòng liên hệ Quản trị viên.")
        return user

    # ── HMAC ký cookie state ────────────────────────────────────────────────

    def _sign(self, payload: str) -> str:
        sig = hmac.new(self._secret, payload.encode(), hashlib.sha256).hexdigest()
        return base64.urlsafe_b64encode(f"{payload}||{sig}".encode()).decode()

    def _unsign(self, value: str) -> Optional[str]:
        try:
            raw = base64.urlsafe_b64decode(value.encode()).decode()
            payload, _, sig = raw.rpartition("||")
            expected = hmac.new(self._secret, payload.encode(), hashlib.sha256).hexdigest()
            if not hmac.compare_digest(sig, expected):
                return None
            return payload
        except Exception:  # noqa: BLE001
            return None


# ═════════════════════════════════════════════════════════════════════════════
# Quản trị thành viên
# ═════════════════════════════════════════════════════════════════════════════

ADMIN_ACTIONS = ("approve", "disable", "make_admin", "revoke_admin", "delete")


def admin_update(store: AccountStore, actor: User, email: str, action: str) -> Optional[User]:
    """Thực hiện một thao tác quản trị lên tài khoản ``email``.

    Trả User sau khi đổi (None nếu đã xoá). Ném AuthError nếu không hợp lệ.
    """
    email = normalize_email(email)
    target = store.get(email)
    if target is None:
        raise AuthError(404, "USER_NOT_FOUND", "Không tìm thấy tài khoản.")
    self_action = target.email == actor.email

    if action in ("disable", "revoke_admin", "delete") and self_action:
        raise AuthError(409, "SELF_ACTION", "Không thể tự khoá, tự xoá hoặc tự gỡ quyền của chính mình.")
    if action in ("disable", "revoke_admin", "delete") and target.is_admin and target.active:
        if store.count_admins() <= 1:
            raise AuthError(409, "LAST_ADMIN", "Hệ thống phải còn ít nhất một Quản trị viên.")

    now = store.now()
    if action == "approve":
        target.status = STATUS_ACTIVE
        target.approved_by = actor.email
        target.approved_at = now
    elif action == "disable":
        target.status = STATUS_DISABLED
    elif action == "make_admin":
        if not target.active:
            raise AuthError(409, "NOT_ACTIVE", "Hãy duyệt tài khoản trước khi cấp quyền Quản trị viên.")
        target.is_admin = True
    elif action == "revoke_admin":
        target.is_admin = False
    elif action == "delete":
        store.delete(email)
        return None
    else:
        raise AuthError(400, "UNKNOWN_ACTION", "Thao tác không hợp lệ.")
    store.save(target)
    return target


# ═════════════════════════════════════════════════════════════════════════════
# Thể hiện dùng chung cho cả tiến trình
# ═════════════════════════════════════════════════════════════════════════════

_singleton: Optional[Accounts] = None
_singleton_lock = threading.Lock()


def get_accounts() -> Accounts:
    global _singleton
    with _singleton_lock:
        if _singleton is None:
            admins = {
                normalize_email(e)
                for e in (os.environ.get(ADMIN_EMAILS_ENV) or "").split(",")
                if e.strip()
            }
            _singleton = Accounts(AccountStore(default_db_path(), admins))
        return _singleton


def reset_accounts_for_tests(accounts: Optional[Accounts] = None) -> None:
    global _singleton
    with _singleton_lock:
        _singleton = accounts
