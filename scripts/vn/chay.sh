#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# VoiceStudio-VN — MỞ ỨNG DỤNG trên macOS / Linux
#   ./chay.sh          chỉ máy này dùng (http://localhost:3900)
#   ./chay.sh --lan    cho máy khác cùng mạng Wi-Fi/LAN truy cập
#   PORT=4000 ./chay.sh  đổi cổng
# Đóng cửa sổ Terminal (hoặc Ctrl+C) = tắt VoiceStudio.
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$HOME/.bun/bin:$PATH"

if ! command -v uv >/dev/null || [ ! -d .venv ] || [ ! -f frontend/dist/index.html ]; then
  printf '\033[31mVoiceStudio chưa được cài đặt đầy đủ. Hãy chạy cài đặt trước (CaiDat-Mac.command hoặc ./cai-dat.sh).\033[0m\n'
  exit 1
fi

# Tệp cấu hình tuỳ chọn .env (KHOÁ=GIÁ_TRỊ mỗi dòng) — xem README.
if [ -f .env ]; then set -a; . ./.env; set +a; fi

PORT="${PORT:-3900}"
HOST=127.0.0.1
[ "${1:-}" = "--lan" ] && HOST=0.0.0.0
export OMNIVOICE_PORT="$PORT" PYTHONUTF8=1
URL="http://localhost:$PORT"

printf '\033[35m==============================================\n   VOICESTUDIO đang khởi động...\n   Địa chỉ: %s\n' "$URL"
if [ "$HOST" = "0.0.0.0" ]; then
  for ip in $( (hostname -I 2>/dev/null || ipconfig getifaddr en0 2>/dev/null || true) ); do
    printf '   Máy khác trong mạng: http://%s:%s\n' "$ip" "$PORT"
  done
fi
printf '   ĐỪNG đóng cửa sổ này khi đang dùng.\n==============================================\033[0m\n'

# Mở trình duyệt khi máy chủ sẵn sàng.
(
  for _ in $(seq 1 180); do
    if curl -fsS "$URL/health" >/dev/null 2>&1; then
      if command -v open >/dev/null; then open "$URL"; elif command -v xdg-open >/dev/null; then xdg-open "$URL" >/dev/null 2>&1; fi
      exit 0
    fi
    sleep 1
  done
) &

exec uv run --no-sync uvicorn main:app --app-dir backend --host "$HOST" --port "$PORT"
