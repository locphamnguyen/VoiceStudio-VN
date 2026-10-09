# ─────────────────────────────────────────────────────────────────────────────
# VoiceStudio-VN — CÀI ĐẶT TỰ ĐỘNG cho Windows
#
# Người dùng chỉ cần bấm đúp "CaiDat-Windows.cmd" ở thư mục gốc. Script này:
#   1. Cài uv (quản lý Python) và bun (build giao diện) nếu máy chưa có.
#   2. Cài Python 3.11 + toàn bộ thư viện; tự chọn PyTorch GPU (card NVIDIA)
#      hoặc CPU.
#   3. Build giao diện web vào frontend/dist.
#   4. Tạo lối tắt "VoiceStudio" ngoài Desktop.
# Chạy lại bao nhiêu lần cũng được (bước nào xong rồi sẽ nhanh).
# ─────────────────────────────────────────────────────────────────────────────
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$Root = Resolve-Path (Join-Path $PSScriptRoot '..\..')
Set-Location $Root

function Buoc($n, $text) { Write-Host ""; Write-Host "[$n/5] $text" -ForegroundColor Cyan }
function Loi($text) {
  Write-Host ""
  Write-Host "LỖI: $text" -ForegroundColor Red
  Write-Host "Chụp màn hình cửa sổ này và gửi cho người hỗ trợ. Xem thêm mục 'Xử lý sự cố' trong README." -ForegroundColor Yellow
  exit 1
}
function Them-Path($dir) {
  if ((Test-Path $dir) -and -not (($env:Path -split ';') -contains $dir)) { $env:Path = "$dir;$env:Path" }
}

Write-Host "==============================================" -ForegroundColor Magenta
Write-Host "   CÀI ĐẶT VOICESTUDIO (bản tiếng Việt)" -ForegroundColor Magenta
Write-Host "==============================================" -ForegroundColor Magenta
Write-Host "Thư mục: $Root"
if ("$Root" -match '[^\x00-\x7F]') {
  Write-Host "CẢNH BÁO: đường dẫn thư mục có dấu tiếng Việt / ký tự đặc biệt. Nên chuyển thư mục về dạng C:\VoiceStudio rồi chạy lại." -ForegroundColor Yellow
}

# ── 1. uv ────────────────────────────────────────────────────────────────────
Buoc 1 "Kiểm tra uv (trình quản lý Python)"
Them-Path "$env:USERPROFILE\.local\bin"
Them-Path "$env:USERPROFILE\.cargo\bin"
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
  Write-Host "Chưa có uv — đang tải về..."
  try { Invoke-RestMethod https://astral.sh/uv/install.ps1 | Invoke-Expression } catch { Loi "Không tải được uv. Kiểm tra kết nối Internet." }
  Them-Path "$env:USERPROFILE\.local\bin"
}
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) { Loi "Cài uv xong nhưng không tìm thấy lệnh uv. Hãy đóng cửa sổ và chạy lại." }
Write-Host ("uv: " + (uv --version))

# ── 2. bun ───────────────────────────────────────────────────────────────────
Buoc 2 "Kiểm tra bun (dùng để build giao diện)"
Them-Path "$env:USERPROFILE\.bun\bin"
if (-not (Get-Command bun -ErrorAction SilentlyContinue)) {
  Write-Host "Chưa có bun — đang tải về..."
  try { Invoke-RestMethod https://bun.sh/install.ps1 | Invoke-Expression } catch { Loi "Không tải được bun. Kiểm tra kết nối Internet." }
  Them-Path "$env:USERPROFILE\.bun\bin"
}
if (-not (Get-Command bun -ErrorAction SilentlyContinue)) { Loi "Cài bun xong nhưng không tìm thấy lệnh bun. Hãy đóng cửa sổ và chạy lại." }
Write-Host ("bun: " + (bun --version))

# ── 3. Thư viện JavaScript + Python ──────────────────────────────────────────
Buoc 3 "Cài thư viện (lần đầu mất 10–30 phút tuỳ mạng — cứ để máy chạy)"
bun install
if ($LASTEXITCODE -ne 0) { Loi "bun install thất bại." }
# setup-api.mjs tự nhận card NVIDIA để chọn PyTorch CUDA, không có thì dùng CPU.
bun scripts/setup-api.mjs
if ($LASTEXITCODE -ne 0) { Loi "Cài thư viện Python thất bại." }

# ── 4. Build giao diện ───────────────────────────────────────────────────────
Buoc 4 "Build giao diện web"
bun run build:web
if ($LASTEXITCODE -ne 0) { Loi "Build giao diện thất bại." }
if (-not (Test-Path (Join-Path $Root 'frontend\dist\index.html'))) { Loi "Không thấy frontend\dist\index.html sau khi build." }

# ── 5. Lối tắt Desktop ───────────────────────────────────────────────────────
Buoc 5 "Tạo lối tắt ngoài Desktop"
try {
  $desktop = [Environment]::GetFolderPath('Desktop')
  $shell = New-Object -ComObject WScript.Shell
  $lnk = $shell.CreateShortcut((Join-Path $desktop 'VoiceStudio.lnk'))
  $lnk.TargetPath = Join-Path $Root 'ChayVoiceStudio-Windows.cmd'
  $lnk.WorkingDirectory = "$Root"
  $icon = Join-Path $Root 'electron\build\icons\icon.ico'
  if (Test-Path $icon) { $lnk.IconLocation = $icon }
  $lnk.Save()
  Write-Host "Đã tạo lối tắt 'VoiceStudio' ngoài Desktop."
} catch {
  Write-Host "Không tạo được lối tắt (không sao) — mở bằng ChayVoiceStudio-Windows.cmd." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "==============================================" -ForegroundColor Green
Write-Host " CÀI ĐẶT XONG!" -ForegroundColor Green
Write-Host " Bấm đúp 'VoiceStudio' ngoài Desktop (hoặc ChayVoiceStudio-Windows.cmd)" -ForegroundColor Green
Write-Host " để mở ứng dụng. Lần mở đầu tiên hãy bấm 'Đăng ký' — tài khoản đầu tiên" -ForegroundColor Green
Write-Host " sẽ là Quản trị viên." -ForegroundColor Green
Write-Host "==============================================" -ForegroundColor Green
