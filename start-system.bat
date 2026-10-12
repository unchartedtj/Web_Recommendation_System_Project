@echo off
REM ==================================================================
REM  Double-click to START the WBL Placement Recommendation System.
REM  It starts MySQL (if needed), the backend and the frontend in the
REM  background, then opens http://localhost:5173 in your browser.
REM  There are no windows to keep open. To stop: stop-system.bat
REM ==================================================================
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\start.ps1"
echo.
echo   Press any key to close this window (the system keeps running).
pause >nul
