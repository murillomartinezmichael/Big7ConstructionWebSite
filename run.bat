@echo off
REM Serve Big7Construction locally on port 8080.
setlocal
cd /d "%~dp0"

where python >nul 2>nul || (echo [ERROR] Python needed to serve static files. ^& pause ^& exit /b 1)

echo.
echo Serving Big7Construction at http://localhost:8080
echo Press Ctrl+C to stop.
echo.

start "" cmd /c "timeout /t 2 >nul & start http://localhost:8080"
python -m http.server 8080

endlocal
