"""Phần THUẦN của gọi-về (phone-home): dựng gói gửi đi, kiểm định gói nhận về.

Port từ ZaloCRM (``backend/src/modules/phone-home/announcement.ts``). Không HTTP,
không I/O — để test khoá được hợp đồng mà không cần mock gì.

HỢP ĐỒNG VỚI TRANG TRUNG TÂM (``deploy/phone-home-worker/``):
  gửi:  ``{ instanceId, version }``                         — ĐÚNG HAI TRƯỜNG, không hơn.
  nhận: ``{ announcement: null | { id, text, level?, link?, linkLabel?, dismissible? } }``
      (``dismissible`` vắng mặt ⇒ False: dải không có nút đóng)

Mọi thứ nhận về là dữ liệu bên ngoài: kiểm từng trường, cắt độ dài, chỉ nhận link
https. Sai một trường ⇒ coi như KHÔNG có thông báo (an toàn hơn hiện bừa).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Optional
from urllib.parse import urlsplit

ANNOUNCEMENT_LEVELS = ("info", "warning", "critical")
TEXT_MAX_LEN = 500
ID_MAX_LEN = 100
LINK_LABEL_MAX_LEN = 60
LINK_MAX_LEN = 2048


@dataclass(frozen=True)
class Announcement:
    id: str              # FE ghi nhớ mã đã đóng; mã mới ⇒ hiện lại
    text: str            # văn bản thuần — giao diện KHÔNG render HTML
    level: str           # info | warning | critical
    link: Optional[str]  # chỉ https
    linkLabel: Optional[str]
    dismissible: bool    # mặc định False ⇒ không có nút đóng; True chỉ khi trang trung tâm gửi rõ

    def to_json(self) -> dict:
        return asdict(self)


def build_ping_payload(instance_id: str, version: str) -> dict:
    """Gói gửi đi — hàm riêng để test khoá "đúng hai khoá, không thêm"."""
    return {"instanceId": instance_id, "version": version}


_INVALID = object()


def _parse_https_link(v: Any):
    if v is None or v == "":
        return None
    if not isinstance(v, str) or len(v) > LINK_MAX_LEN:
        return _INVALID
    try:
        parts = urlsplit(v)
    except ValueError:
        return _INVALID
    if parts.scheme != "https" or not parts.netloc:
        return _INVALID
    return v


def parse_announcement_response(body: Any) -> Optional[Announcement]:
    """Trả None khi không có thông báo HOẶC body sai dạng — giao diện xử lý như nhau (ẩn dải)."""
    if not isinstance(body, dict):
        return None
    a = body.get("announcement")
    if not isinstance(a, dict):
        return None

    ident, text = a.get("id"), a.get("text")
    if not isinstance(ident, str) or not ident.strip() or len(ident) > ID_MAX_LEN:
        return None
    if not isinstance(text, str) or not text.strip():
        return None

    level = a.get("level") if a.get("level") in ANNOUNCEMENT_LEVELS else "info"

    link = _parse_https_link(a.get("link"))
    if link is _INVALID:
        return None

    label = a.get("linkLabel")
    link_label: Optional[str] = None
    if label not in (None, ""):
        if not isinstance(label, str):
            return None
        link_label = label.strip()[:LINK_LABEL_MAX_LEN] or None

    # Mặc định KHÔNG cho đóng (chủ dự án chốt 2026-10-08): đây là kênh chủ dự án gửi
    # thông báo tới người dùng. Chỉ hiện nút đóng khi trang trung tâm gửi rõ true.
    dismissible = a.get("dismissible") is True

    return Announcement(
        id=ident.strip(),
        text=text.strip()[:TEXT_MAX_LEN],
        level=level,
        link=link,
        linkLabel=link_label,
        dismissible=dismissible,
    )
