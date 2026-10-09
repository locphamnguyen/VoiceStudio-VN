# Worker gọi-về (phone-home) — trang trung tâm VoiceStudio-VN

Phía NHẬN của tính năng gọi-về, chạy trên Cloudflare của chủ dự án. Port từ Worker của
ZaloCRM (`ZCRM-EE/deploy/phone-home-worker`), chỉ đổi đường dẫn sang
`/voicestudio-phone-home/*` trên `updater.zopen.vn` và dùng D1 riêng — sản phẩm khác dùng
chung tên miền này bằng đường dẫn của nó, số liệu không lẫn nhau.

## Nó làm gì

Mỗi bản VoiceStudio-VN gọi `POST https://updater.zopen.vn/voicestudio-phone-home/v1/ping`
30 giây sau khi khởi động và mỗi 12 giờ, gửi **đúng hai trường** `{ instanceId, version }`.
Worker:

1. Ghi/cập nhật một dòng trong D1 `instances` theo `instance_id` (lần đầu thấy, lần cuối
   thấy, bản đang chạy). **Không ghi IP, không ghi header.**
2. Trả thông báo `enabled` mới nhất khớp điều kiện (`min_version`/`max_version`/
   `target_instance_id`), hoặc `{ announcement: null }` ⇒ dải trên giao diện ẩn.

## Dựng lần đầu

```bash
cd deploy/phone-home-worker
npm i -g wrangler && wrangler login
wrangler d1 create voicestudio-phone-home     # chép database_id vào wrangler.toml
wrangler d1 execute voicestudio-phone-home --remote --file=schema.sql
wrangler secret put ADMIN_TOKEN               # chuỗi dài ngẫu nhiên: openssl rand -hex 32
wrangler deploy
```

Zone `zopen.vn` phải nằm trên Cloudflare, và `updater.zopen.vn` cần một bản ghi DNS
**proxied** (đám mây cam) — ví dụ `AAAA updater 100::` — để route Worker bắt được request.

Đổi domain thì đổi hằng `PHONE_HOME_URL` ở `backend/services/phone_home.py` **trước khi
phát hành** — địa chỉ ghim cứng trong mã, không có biến env.

## Độ trễ

Bản cài gọi về mỗi 12h; giao diện hỏi backend mỗi 30 phút. Thông báo mới tới mọi người trong
tối đa ~12,5h. Muốn nhanh hơn thì giảm `PING_INTERVAL_S` ở `backend/services/phone_home.py`.

Dải thông báo mặc định **không có nút đóng** — người dùng luôn thấy thông báo chủ dự án gửi.
