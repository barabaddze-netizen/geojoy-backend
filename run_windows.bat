@echo off
setlocal
cd /d "%~dp0"
set "PORT=8052"
set "GEOJOY_ADMIN_PASSWORD=%GEOJOY_ADMIN_PASSWORD%"
if "%GEOJOY_ADMIN_PASSWORD%"=="" set "GEOJOY_ADMIN_PASSWORD=GeoJoy2026!"
where python >nul 2>nul
if errorlevel 1 (
  echo Python was not found. Install Python 3 from https://www.python.org/downloads/windows/
  echo During installation, enable "Add Python to PATH".
  pause
  exit /b 1
)
echo Starting GeoJoy 8.9.0 and checking that this exact version is ready...
python launch_geojoy.py
if errorlevel 1 (
  echo.
  echo GeoJoy did not start correctly. Check geojoy_server.log in this folder.
  pause
  exit /b 1
)
echo.
echo Website: http://127.0.0.1:8052/
echo Admin:   http://127.0.0.1:8052/admin/
echo To open the admin panel later, run open_admin.bat.
echo The server continues in the background. Stop it by closing its Python process or restarting Windows.
echo.
pause
