@echo off
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 preview.py --open
) else (
  python preview.py --open
)
if errorlevel 1 (
  echo Preview could not start. Python 3 is required and port 8767 must be free.
  pause
)
