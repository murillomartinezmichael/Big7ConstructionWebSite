@echo off
REM ====================================================================
REM  Big7Construction - Cloudflare Pages deploy (double-click wrapper)
REM
REM  One click deploys the static site (index.html + 404.html + images/)
REM  to Cloudflare Pages under project `m3-big7construction`.
REM
REM  Safe to re-click any time - every step is idempotent.
REM  First run pops a browser for `wrangler login`.
REM
REM  NOTE: this does NOT touch the Railway deploy. Big7 stays on Railway
REM  until you manually retire it. This just adds a CF Pages target as
REM  a viable free-tier alternative.
REM ====================================================================

setlocal
cd /d %~dp0

echo.
echo   Big7Construction ^| Cloudflare Pages deploy
echo   ============================================
echo.

REM ----- [1/4] wrangler login (skip if already logged in) -----
call npx --yes wrangler whoami >nul 2>&1
if errorlevel 1 (
    echo   [1/4] Not logged in. Opening browser for wrangler login...
    call npx --yes wrangler login
    if errorlevel 1 (
        echo   [X] wrangler login failed. Aborting.
        pause
        exit /b 1
    )
) else (
    echo   [1/4] wrangler already logged in.
)

REM ----- [2/4] ensure project exists (idempotent) -----
echo   [2/4] Ensuring project m3-big7construction exists...
call npx --yes wrangler pages project list 2>&1 | findstr /C:"m3-big7construction" >nul
if errorlevel 1 (
    echo         Creating project...
    call npx --yes wrangler pages project create m3-big7construction --production-branch main
    if errorlevel 1 (
        echo   [X] project create failed.
        pause
        exit /b 1
    )
) else (
    echo         Project already exists.
)

REM ----- [3/4] stage the static files into _cf-deploy/ -----
REM Keeps Dockerfile / nginx.conf / docs / .git out of the upload.
echo   [3/4] Staging index.html + 404.html + images/ into _cf-deploy/...
if exist _cf-deploy rmdir /S /Q _cf-deploy
mkdir _cf-deploy
copy /Y index.html _cf-deploy\ >nul
copy /Y 404.html _cf-deploy\ >nul
if exist images xcopy /Y /S /I /Q images _cf-deploy\images >nul

REM ----- [4/4] deploy -----
echo   [4/4] Deploying to Cloudflare Pages...
call npx --yes wrangler pages deploy _cf-deploy --project-name=m3-big7construction --branch=main
if errorlevel 1 (
    echo   [X] deploy failed.
    pause
    exit /b 1
)

echo.
echo   ============================================
echo   [OK] Deploy complete.
echo.
echo   The preview URL is printed above (looks like *.m3-big7construction.pages.dev).
echo.
echo   Next steps:
echo     - Attach the client's custom domain: Cloudflare dashboard
echo       -^> project m3-big7construction -^> Custom domains -^> Add
echo     - Smoke: curl -sI ^<preview-url^>/       ==^> 200
echo             curl -sI ^<preview-url^>/nope    ==^> 404 (proves 404.html works)
echo     - Log this chunk in COCKPIT.html (press l).
echo   ============================================
echo.
pause
endlocal
