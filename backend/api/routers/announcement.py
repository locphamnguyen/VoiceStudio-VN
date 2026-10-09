"""``GET /announcement`` — thông báo từ trang trung tâm đang cache trong bộ nhớ.

Chỉ ĐỌC cache (``services/phone_home.py``), không gọi ra ngoài theo request. Khi
bật tài khoản, cổng đăng nhập đã chặn route này với người chưa đăng nhập.

Response: ``{ "announcement": null | { id, text, level, link, linkLabel, dismissible } }``
"""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from services.phone_home import current_announcement

router = APIRouter(tags=["announcement"])


@router.get("/announcement")
def get_announcement():
    a = current_announcement()
    return JSONResponse({"announcement": a.to_json() if a else None},
                        headers={"Cache-Control": "no-store"})
