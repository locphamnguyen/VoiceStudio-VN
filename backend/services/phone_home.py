"""Gọi-về trang trung tâm VoiceStudio-VN + cache thông báo trong bộ nhớ.

Port từ ZaloCRM (``phone-home-service.ts``). Nhịp: một lần sau khi khởi động (trễ
30 giây), rồi mỗi 12 giờ. Mỗi lần gửi ĐÚNG ``{ instanceId, version }``, nhận
``{ announcement }`` rồi cất vào bộ nhớ. Route ``GET /announcement`` chỉ đọc
cache — không bao giờ gọi ra ngoài theo request của người dùng, nên trang trung
tâm chậm/sập KHÔNG làm giao diện chậm theo.

Luật hỏng-êm: timeout 5 giây, lỗi chỉ ghi log debug, thông báo đang cache giữ
nguyên (trang trung tâm chớp tắt không làm dải thông báo nhấp nháy).

Không có công tắc env (chủ dự án chốt): gọi-về và dải thông báo là một phần của
bản phát hành VoiceStudio-VN — cách dự án biết có bao nhiêu bản đang dùng và báo
cập nhật. Địa chỉ ghim cứng ở ``PHONE_HOME_URL``; đổi domain ⇒ đổi ở đây TRƯỚC khi
phát hành.

``instance_id``: uuid4 ngẫu nhiên sinh lần đầu, lưu ở tệp ``instance_id`` trong thư
mục dữ liệu. Không suy ra được gì về máy hay người dùng; chỉ để trang trung tâm đếm
"một máy = một bản cài".
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
import tempfile
import threading
import uuid
from typing import Optional

from core.announcement import Announcement, build_ping_payload, parse_announcement_response

log = logging.getLogger("omnivoice.phone_home")

PHONE_HOME_URL = "https://updater.zopen.vn/voicestudio-phone-home/v1/ping"
PING_INTERVAL_S = 12 * 60 * 60
BOOT_DELAY_S = 30
REQUEST_TIMEOUT_S = 5.0
INSTANCE_ID_FILE = "instance_id"

_current: Optional[Announcement] = None
_instance_id: Optional[str] = None
_id_lock = threading.Lock()
_in_flight = False


def current_announcement() -> Optional[Announcement]:
    """Thông báo đang cache — None khi chưa gọi lần nào hoặc trang trung tâm bảo "không có"."""
    return _current


def _data_dir() -> str:
    from core.config import get_app_data_dir

    return get_app_data_dir()


def _valid_uuid(value: str) -> bool:
    try:
        return str(uuid.UUID(value)) == value
    except ValueError:
        return False


def get_or_create_instance_id(data_dir: Optional[str] = None) -> str:
    """Đọc (hoặc sinh lần đầu) instance_id. Ghi atomic: tệp tạm rồi ``os.replace``."""
    global _instance_id
    with _id_lock:
        if _instance_id and data_dir is None:
            return _instance_id
        folder = data_dir or _data_dir()
        path = os.path.join(folder, INSTANCE_ID_FILE)
        try:
            with open(path, encoding="utf-8") as fh:
                existing = fh.read().strip()
            if _valid_uuid(existing):
                if data_dir is None:
                    _instance_id = existing
                return existing
        except OSError:
            pass
        new_id = str(uuid.uuid4())
        os.makedirs(folder, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=folder, prefix=".instance_id.")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(new_id + "\n")
            os.replace(tmp, path)
        except OSError:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise
        if data_dir is None:
            _instance_id = new_id
        return new_id


def _app_version() -> str:
    try:
        from core.version import APP_VERSION

        return str(APP_VERSION) or "unknown"
    except Exception:  # noqa: BLE001
        return "unknown"


async def ping_once(client=None) -> Optional[Announcement]:
    """Một lượt gọi-về. Trả thông báo đang cache sau lượt này. KHÔNG ném lỗi.

    ``client`` để test tiêm ``httpx.AsyncClient`` giả; mặc định tạo client mới.
    """
    global _current, _in_flight
    if _in_flight:
        return _current
    _in_flight = True
    try:
        import httpx

        instance_id = await asyncio.to_thread(get_or_create_instance_id)
        payload = build_ping_payload(instance_id, _app_version())
        own = client is None
        http = client or httpx.AsyncClient(timeout=REQUEST_TIMEOUT_S)
        try:
            res = await http.post(PHONE_HOME_URL, json=payload,
                                  headers={"accept": "application/json"},
                                  timeout=REQUEST_TIMEOUT_S)
        finally:
            if own:
                await http.aclose()
        if res.status_code < 200 or res.status_code >= 300:
            log.debug("[phone-home] trang trung tâm trả %s — giữ thông báo đang có", res.status_code)
            return _current
        _current = parse_announcement_response(res.json())
        return _current
    except asyncio.CancelledError:
        raise
    except Exception as exc:  # noqa: BLE001
        # Cố ý debug, không warning: máy không có mạng ra ngoài là bình thường.
        log.debug("[phone-home] gọi-về thất bại — giữ thông báo đang có: %s", exc)
        return _current
    finally:
        _in_flight = False


async def phone_home_loop() -> None:
    """Vòng chạy nền: trễ 30 giây sau khởi động, rồi mỗi 12 giờ."""
    log.info("[phone-home] Gửi {instanceId, version=%s} tới %s mỗi 12h",
             _app_version(), PHONE_HOME_URL)
    await asyncio.sleep(BOOT_DELAY_S)
    while True:
        await ping_once()
        await asyncio.sleep(PING_INTERVAL_S)


def should_start() -> bool:
    """Không chạy dưới pytest — bộ test không được gọi ra mạng."""
    return "pytest" not in sys.modules


def _reset_for_tests() -> None:
    global _current, _instance_id, _in_flight
    _current = None
    _instance_id = None
    _in_flight = False
