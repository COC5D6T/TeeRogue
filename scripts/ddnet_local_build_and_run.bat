@echo off
setlocal

set "ROOT_DIR=D:\Desktop\AI\newfuwq\f"
set "BUILD_DIR=%ROOT_DIR%\build-ddnet-server-vs2026"
set "BUILD_OUTPUT_DIR=%BUILD_DIR%\Release"
set "RUNTIME_DIR=%ROOT_DIR%\ddnet-server\DDNet-19.7.1-win64"
set "SERVER_EXE=DDNet-Server.exe"

set "SOURCE_SERVER=%BUILD_OUTPUT_DIR%\%SERVER_EXE%"
set "SOURCE_CURL=%BUILD_OUTPUT_DIR%\libcurl.dll"
set "SOURCE_SQLITE=%BUILD_OUTPUT_DIR%\sqlite3.dll"
set "SOURCE_ZLIB=%BUILD_OUTPUT_DIR%\z.dll"

set "TARGET_SERVER=%RUNTIME_DIR%\%SERVER_EXE%"
set "TARGET_CURL=%RUNTIME_DIR%\libcurl.dll"
set "TARGET_SQLITE=%RUNTIME_DIR%\sqlite3.dll"
set "TARGET_ZLIB=%RUNTIME_DIR%\z.dll"

echo ==========================================
echo      DDNet Local Server Build And Run
echo ==========================================
echo.

if not exist "%BUILD_DIR%" (
    echo Build directory not found:
    echo %BUILD_DIR%
    pause
    exit /b 1
)

if not exist "%RUNTIME_DIR%" (
    echo Runtime directory not found:
    echo %RUNTIME_DIR%
    pause
    exit /b 1
)

if not exist "%RUNTIME_DIR%\data\autoexec_server.cfg" (
    echo Missing local server config:
    echo %RUNTIME_DIR%\data\autoexec_server.cfg
    pause
    exit /b 1
)

echo [1/5] Checking for an existing local server process...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$target = [System.IO.Path]::GetFullPath('%TARGET_SERVER%');" ^
  "$proc = Get-Process DDNet-Server -ErrorAction SilentlyContinue | Where-Object { $_.Path -and ([System.IO.Path]::GetFullPath($_.Path) -ieq $target) };" ^
  "if($proc){ $proc | Stop-Process -Force; Write-Host 'Stopped previous local server.' } else { Write-Host 'No previous local server is running.' }"
if errorlevel 1 (
    echo Failed while checking or stopping the previous local server.
    pause
    exit /b 1
)
echo.

echo [2/5] Building local server...
cmake --build "%BUILD_DIR%" --config Release --target game-server
if errorlevel 1 (
    echo.
    echo Build failed. Local server was not started.
    pause
    exit /b 1
)
echo.

echo [3/5] Verifying build output...
if not exist "%SOURCE_SERVER%" (
    echo Missing built server file:
    echo %SOURCE_SERVER%
    pause
    exit /b 1
)
if not exist "%SOURCE_CURL%" (
    echo Missing build dependency:
    echo %SOURCE_CURL%
    pause
    exit /b 1
)
if not exist "%SOURCE_SQLITE%" (
    echo Missing build dependency:
    echo %SOURCE_SQLITE%
    pause
    exit /b 1
)
if not exist "%SOURCE_ZLIB%" (
    echo Missing build dependency:
    echo %SOURCE_ZLIB%
    pause
    exit /b 1
)
echo.

echo [4/5] Syncing the new local server files...
copy /Y "%SOURCE_SERVER%" "%TARGET_SERVER%" >nul
if errorlevel 1 (
    echo Failed to copy:
    echo %SOURCE_SERVER%
    echo to
    echo %TARGET_SERVER%
    pause
    exit /b 1
)

copy /Y "%SOURCE_CURL%" "%TARGET_CURL%" >nul
if errorlevel 1 (
    echo Failed to copy:
    echo %SOURCE_CURL%
    pause
    exit /b 1
)

copy /Y "%SOURCE_SQLITE%" "%TARGET_SQLITE%" >nul
if errorlevel 1 (
    echo Failed to copy:
    echo %SOURCE_SQLITE%
    pause
    exit /b 1
)

copy /Y "%SOURCE_ZLIB%" "%TARGET_ZLIB%" >nul
if errorlevel 1 (
    echo Failed to copy:
    echo %SOURCE_ZLIB%
    pause
    exit /b 1
)
echo Files synced to:
echo %RUNTIME_DIR%
echo.

echo [5/5] Starting the local server...
start "DDNet Local Server" /D "%RUNTIME_DIR%" "%TARGET_SERVER%"
if errorlevel 1 (
    echo Failed to start the local server.
    pause
    exit /b 1
)
echo.
echo Local server build succeeded and the server window has been started.
echo Runtime directory:
echo %RUNTIME_DIR%
pause
exit /b 0
