@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
set "PS1_PATH=%SCRIPT_DIR%ddnet_deploy.ps1"

if not exist "%PS1_PATH%" (
    echo Missing script: "%PS1_PATH%"
    pause
    exit /b 1
)

if /i "%~1"=="build" goto run_build
if /i "%~1"=="release" goto run_release
if /i "%~1"=="quit" goto quit

:menu
cls
echo ==========================================
echo           DDNet Cloud Deploy
echo ==========================================
echo 1. Build on cloud only
echo 2. Build, install, and restart server
echo Q. Quit
echo.
choice /c 12Q /n /m "Choose mode [1/2/Q]: "

if errorlevel 3 goto quit
if errorlevel 2 goto run_release
if errorlevel 1 goto run_build
goto menu

:run_build
echo.
echo Running mode 1: build on cloud only...
powershell -NoProfile -ExecutionPolicy Bypass -File "%PS1_PATH%" -Mode build
set "EXIT_CODE=%ERRORLEVEL%"
goto finish

:run_release
echo.
echo Running mode 2: build, install, and restart...
powershell -NoProfile -ExecutionPolicy Bypass -File "%PS1_PATH%" -Mode release
set "EXIT_CODE=%ERRORLEVEL%"
goto finish

:quit
echo Deploy cancelled.
pause
exit /b 0

:finish
echo.
if "%EXIT_CODE%"=="0" (
    echo Deploy script finished successfully.
) else (
    echo Deploy script failed. Exit code: %EXIT_CODE%
)
pause
exit /b %EXIT_CODE%
