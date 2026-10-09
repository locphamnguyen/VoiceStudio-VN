# ─────────────────────────────────────────────────────────────────────────────
# VoiceStudio-VN — MỞ ỨNG DỤNG trên Windows
#
# Bấm đúp "ChayVoiceStudio-Windows.cmd" (hoặc lối tắt ngoài Desktop). Script
# chạy máy chủ VoiceStudio ở cổng 3900 rồi tự mở trình duyệt.
#   -Lan   : cho máy khác trong mạng nội bộ (cùng Wi-Fi/LAN) truy cập.
#   -Port N: đổi cổng (mặc định 3900).
# Đóng cửa sổ đen này = tắt VoiceStudio.
# ─────────────────────────────────────────────────────────────────────────────
param([switch]$Lan, [int]$Port = 3900)
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$Root = Resolve-Path (Join-Path $PSScriptRoot '..\..')
Set-Location $Root
foreach ($d in @("$env:USERPROFILE\.local\bin", "$env:USERPROFILE\.cargo\bin", "$env:USERPROFILE\.bun\bin")) {
  if ((Test-Path $d) -and -not (($env:Path -split ';') -contains $d)) { $env:Path = "$d;$env:Path" }
}

if (-not (Get-Command uv -ErrorAction SilentlyContinue) -or -not (Test-Path (Join-Path $Root '.venv')) -or
    -not (Test-Path (Join-Path $Root 'frontend\dist\index.html'))) {
  Write-Host "VoiceStudio chưa được cài đặt đầy đủ. Hãy bấm đúp CaiDat-Windows.cmd trước." -ForegroundColor Red
  Read-Host "Nhấn Enter để đóng"
  exit 1
}

# Đọc tệp cấu hình tuỳ chọn .env (KHOÁ=GIÁ_TRỊ mỗi dòng) — xem README.
$envFile = Join-Path $Root '.env'
if (Test-Path $envFile) {
  foreach ($line in Get-Content $envFile -Encoding UTF8) {
    if ($line -match '^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)\s*$' -and -not $line.TrimStart().StartsWith('#')) {
      [Environment]::SetEnvironmentVariable($Matches[1], $Matches[2].Trim('"'), 'Process')
    }
  }
}

$BindHost = if ($Lan) { '0.0.0.0' } else { '127.0.0.1' }
$env:OMNIVOICE_PORT = "$Port"
$env:PYTHONUTF8 = '1'
$Url = "http://localhost:$Port"

Write-Host "==============================================" -ForegroundColor Magenta
Write-Host "   VOICESTUDIO đang khởi động..." -ForegroundColor Magenta
Write-Host "   Địa chỉ: $Url" -ForegroundColor Magenta
if ($Lan) {
  $ips = (Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
    Where-Object { $_.IPAddress -notmatch '^(127|169\.254)\.' }).IPAddress
  foreach ($ip in $ips) { Write-Host "   Máy khác trong mạng: http://${ip}:$Port" -ForegroundColor Magenta }
}
Write-Host "   ĐỪNG đóng cửa sổ này khi đang dùng." -ForegroundColor Magenta
Write-Host "==============================================" -ForegroundColor Magenta

# Mở trình duyệt khi máy chủ trả lời /health (tối đa ~3 phút).
Start-Job -ArgumentList $Url -ScriptBlock {
  param($u)
  for ($i = 0; $i -lt 180; $i++) {
    try { Invoke-WebRequest "$u/health" -UseBasicParsing -TimeoutSec 2 | Out-Null; Start-Process $u; return } catch { Start-Sleep 1 }
  }
} | Out-Null

uv run --no-sync uvicorn main:app --app-dir backend --host $BindHost --port $Port
Write-Host ""
Write-Host "VoiceStudio đã dừng." -ForegroundColor Yellow
Read-Host "Nhấn Enter để đóng"
