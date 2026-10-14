@echo off
setlocal
cd /d "%~dp0"
set "PORT=8052"
if "%GEOJOY_ADMIN_PASSWORD%"=="" set "GEOJOY_ADMIN_PASSWORD=GeoJoy2026!"
where python >nul 2>nul
if errorlevel 1 (
  echo Python was not found. Install Python 3 from https://www.python.org/downloads/windows/
  pause
  exit /b 1
)
echo Checking GeoJoy and opening the admin panel...
python launch_geojoy.py --admin
if errorlevel 1 (
  echo.
  echo Admin could not be opened. Check geojoy_server.log in this folder.
  pause
  exit /b 1
)
echo Admin panel: http://127.0.0.1:8052/admin/
pause
