@echo off
setlocal

set "PROJECT_ROOT=%~dp0"
set "WEB_DIR=%PROJECT_ROOT%web"
set "PYTHON_EXE=%PROJECT_ROOT%.runtime-python310\python.exe"
set "VITE_CLI=%WEB_DIR%\node_modules\vite\bin\vite.js"
set "SECRETS_FILE=%PROJECT_ROOT%.onyx-secrets.cmd"

if not exist "%PYTHON_EXE%" (
  echo [Onyx] Missing backend runtime: "%PYTHON_EXE%"
  echo Restore the workspace-local Python 3.10 runtime before starting Onyx.
  pause
  exit /b 1
)

if not exist "%VITE_CLI%" (
  echo [Onyx] Missing frontend dependencies: "%VITE_CLI%"
  echo Install the web dependencies before starting Onyx.
  pause
  exit /b 1
)

where node >nul 2>nul
if errorlevel 1 (
  echo [Onyx] Node.js is not available on PATH.
  pause
  exit /b 1
)

if not exist "%SECRETS_FILE%" (
  echo [Onyx] Generating local API credentials...
  powershell -NoProfile -Command "$ingest=[guid]::NewGuid().ToString('N')+[guid]::NewGuid().ToString('N'); $response=[guid]::NewGuid().ToString('N')+[guid]::NewGuid().ToString('N'); $lines=@(('set ONYX_TELEMETRY_INGEST_API_KEY='+$ingest),('set ONYX_RESPONSE_API_KEY='+$response)); Set-Content -LiteralPath '%SECRETS_FILE%' -Encoding Ascii -Value $lines"
  if errorlevel 1 (
    echo [Onyx] Could not generate local API credentials.
    pause
    exit /b 1
  )
)
call "%SECRETS_FILE%"

echo [Onyx] Starting backend at http://0.0.0.0:8020 ...
netstat -ano | findstr /R /C:":8020 .*LISTENING" >nul
if errorlevel 1 (
  start "Onyx Backend" /D "%WEB_DIR%" cmd /k ""%PYTHON_EXE%" -m uvicorn backend.server:app --host 0.0.0.0 --port 8020 --reload"
) else (
  echo [Onyx] Backend is already running on port 8020.
)

echo [Onyx] Starting frontend at http://127.0.0.1:5183 ...
netstat -ano | findstr /R /C:":5183 .*LISTENING" >nul
if errorlevel 1 (
  start "Onyx Frontend" /D "%WEB_DIR%" cmd /k "node node_modules\vite\bin\vite.js --host 127.0.0.1 --port 5183"
) else (
  echo [Onyx] Frontend is already running on port 5183.
)

echo.
echo Onyx is starting in two command windows.
echo Frontend: http://127.0.0.1:5183/
echo Backend:  http://127.0.0.1:8020/api/health
echo Response authorization key: %ONYX_RESPONSE_API_KEY%
echo Credentials are stored locally in: %SECRETS_FILE%
endlocal
