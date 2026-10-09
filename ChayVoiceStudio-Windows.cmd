@echo off
rem VoiceStudio-VN: bam dup tep nay de MO VoiceStudio.
rem Them --lan de may khac trong mang noi bo cung dung: ChayVoiceStudio-Windows.cmd --lan
chcp 65001 >nul
set "VS_ARGS="
if /I "%~1"=="--lan" set "VS_ARGS=-Lan"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\vn\chay.ps1" %VS_ARGS%
