@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0one_click_setup.ps1"
if errorlevel 1 (
  echo.
  echo Setup failed. See errors above.
  pause
  exit /b 1
)
echo.
echo Setup finished.
pause
