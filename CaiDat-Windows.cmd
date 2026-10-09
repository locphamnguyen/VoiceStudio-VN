@echo off
rem VoiceStudio-VN: bam dup tep nay de CAI DAT (chi can lam 1 lan).
chcp 65001 >nul
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\vn\cai-dat.ps1"
echo.
pause
