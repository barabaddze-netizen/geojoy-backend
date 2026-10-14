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
python launch_geojoy.py --site
if errorlevel 1 pause
