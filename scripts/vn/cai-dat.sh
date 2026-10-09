#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# VoiceStudio-VN — CÀI ĐẶT TỰ ĐỘNG cho macOS và Linux
#   macOS : bấm đúp CaiDat-Mac.command
#   Linux : chạy  ./cai-dat.sh  trong Terminal
# Cài uv + bun nếu thiếu, cài thư viện Python (tự chọn GPU/CPU), build giao
# diện. Chạy lại bao nhiêu lần cũng được.
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

buoc() { printf '\n\033[36m[%s/4] %s\033[0m\n' "$1" "$2"; }
loi() {
  printf '\n\033[31mLỖI: %s\033[0m\n' "$1"
  printf '\033[33mChụp màn hình cửa sổ này và gửi cho người hỗ trợ. Xem mục "Xử lý sự cố" trong README.\033[0m\n'
  exit 1
}
export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$HOME/.bun/bin:$PATH"

printf '\033[35m==============================================\n   CÀI ĐẶT VOICESTUDIO (bản tiếng Việt)\n==============================================\033[0m\n'
echo "Thư mục: $ROOT"
command -v curl >/dev/null || loi "Máy chưa có curl. Linux: sudo apt install curl"
if [ "$(uname)" = "Darwin" ] && ! xcode-select -p >/dev/null 2>&1; then
  echo "macOS cần 'Command Line Tools'. Một cửa sổ cài đặt sẽ hiện ra — bấm Cài đặt, chờ xong rồi chạy lại tệp này."
  xcode-select --install || true
  exit 1
fi

buoc 1 "Kiểm tra uv (trình quản lý Python)"
if ! command -v uv >/dev/null; then
  echo "Chưa có uv — đang tải về..."
  curl -LsSf https://astral.sh/uv/install.sh | sh || loi "Không tải được uv. Kiểm tra kết nối Internet."
fi
command -v uv >/dev/null || loi "Không tìm thấy lệnh uv sau khi cài."
uv --version

buoc 2 "Kiểm tra bun (dùng để build giao diện)"
if ! command -v bun >/dev/null; then
  command -v unzip >/dev/null || loi "Máy chưa có unzip. Linux: sudo apt install unzip"
  echo "Chưa có bun — đang tải về..."
  curl -fsSL https://bun.sh/install | bash || loi "Không tải được bun. Kiểm tra kết nối Internet."
fi
command -v bun >/dev/null || loi "Không tìm thấy lệnh bun sau khi cài."
bun --version

buoc 3 "Cài thư viện (lần đầu mất 10–30 phút tuỳ mạng — cứ để máy chạy)"
bun install || loi "bun install thất bại."
# setup-api.mjs tự nhận card NVIDIA để chọn PyTorch CUDA; Mac chip M dùng GPU qua MPS.
bun scripts/setup-api.mjs || loi "Cài thư viện Python thất bại."

buoc 4 "Build giao diện web"
bun run build:web || loi "Build giao diện thất bại."
[ -f frontend/dist/index.html ] || loi "Không thấy frontend/dist/index.html sau khi build."

printf '\n\033[32m==============================================\n CÀI ĐẶT XONG!\n'
if [ "$(uname)" = "Darwin" ]; then
  printf ' Bấm đúp Chay-Mac.command để mở VoiceStudio.\n'
else
  printf ' Chạy ./chay.sh để mở VoiceStudio.\n'
fi
printf ' Lần đầu hãy bấm "Đăng ký" — tài khoản đầu tiên là Quản trị viên.\n==============================================\033[0m\n'
