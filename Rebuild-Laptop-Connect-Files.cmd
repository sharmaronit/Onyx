@echo off
title Rebuild Onyx Laptop Connect Files
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\endpoint_heartbeat\rebuild_direct_connect_bundles.ps1"
echo.
pause
