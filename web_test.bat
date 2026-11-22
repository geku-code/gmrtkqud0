@echo off
chcp 65001 >nul
set PYTHONUTF8=1
cd /d %~dp0

rem pygbag puts the bind address into its download URLs, so 0.0.0.0 does not work
rem (the page stays on "Downloading..."). Bind to this PC's real Wi-Fi/LAN IP instead.
set IP=
for /f "usebackq delims=" %%i in (`powershell -NoProfile -Command "(Get-NetIPConfiguration | Where-Object { $_.IPv4DefaultGateway } | Select-Object -First 1).IPv4Address.IPAddress"`) do set IP=%%i
if "%IP%"=="" set IP=localhost

echo.
echo  [web test server]
echo  PC and phone (same Wi-Fi) : http://%IP%:8000
echo  First load can take 10-30 seconds.
echo  Stop: Ctrl+C
echo.
python -m pygbag --bind %IP% .
pause
