-- D1 schema cho Worker gọi-về. Chạy: wrangler d1 execute voicestudio-phone-home --remote --file=schema.sql
--
-- instances: mỗi bản cài một dòng, khoá theo instance_id do bản cài tự sinh.
-- KHÔNG có cột IP — cố ý. Worker không ghi IP, không ghi header nào ngoài hai trường gửi lên.
CREATE TABLE IF NOT EXISTS instances (
  instance_id   TEXT PRIMARY KEY,
  version       TEXT NOT NULL,          -- bản gần nhất báo về
  first_seen_at TEXT NOT NULL,          -- ISO-8601 UTC: "đã cài" từ lúc này
  last_seen_at  TEXT NOT NULL,          -- ISO-8601 UTC: "đang dùng" nếu gần đây
  ping_count    INTEGER NOT NULL DEFAULT 1
);
CREATE INDEX IF NOT EXISTS instances_last_seen_idx ON instances(last_seen_at);

-- announcements: thông điệp hiện trên dải. Worker chọn thông điệp `enabled=1` MỚI NHẤT khớp
-- điều kiện version. Không có dòng nào khớp ⇒ trả { announcement: null } ⇒ dải ẩn.
--   min_version / max_version: so sánh semver với `version` bản cài gửi lên (NULL = không ràng).
--     ví dụ "đã có bản 3.5" chỉ hiện cho bản cũ: max_version = '3.4.99'
--   target_instance_id: NULL = mọi bản cài; đặt id = chỉ nhắm một máy chủ.
CREATE TABLE IF NOT EXISTS announcements (
  id                 TEXT PRIMARY KEY,   -- mã FE ghi nhớ khi đóng; đổi mã ⇒ hiện lại
  text               TEXT NOT NULL,      -- văn bản thuần ≤ 500 ký tự
  level              TEXT NOT NULL DEFAULT 'info',  -- info | warning | critical
  link               TEXT,               -- chỉ https
  link_label         TEXT,
  dismissible        INTEGER NOT NULL DEFAULT 1,
  enabled            INTEGER NOT NULL DEFAULT 1,
  min_version        TEXT,
  max_version        TEXT,
  target_instance_id TEXT,
  created_at         TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
);
