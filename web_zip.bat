@echo off
chcp 65001 >nul
set PYTHONUTF8=1
cd /d %~dp0
python -m pygbag --archive .
echo.
echo  Done: build\web.zip  (upload this file to itch.io)
pause
