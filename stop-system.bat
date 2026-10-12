@echo off
REM ==================================================================
REM  Double-click to STOP the WBL Placement system's backend and frontend.
REM  (MySQL keeps running; stop it in the XAMPP Control Panel if you want.)
REM ==================================================================
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\stop.ps1"
echo.
echo   Press any key to close this window.
pause >nul
