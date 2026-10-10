@echo off
REM ==================================================================
REM  Starts the WBL Placement Recommendation System.
REM  1. Start MySQL first in the XAMPP Control Panel (zamp\xampp-control.exe).
REM  2. Double-click this file. It opens two windows (backend + frontend)
REM     and then the website in your browser.
REM  To stop the system: close the two windows (or press Ctrl+C in them).
REM ==================================================================
cd /d "%~dp0"

start "WBL Backend (Flask, port 5000)" cmd /k "cd /d backend && venv\Scripts\flask.exe run"
start "WBL Frontend (React, port 5173)" cmd /k "cd /d frontend && npm run dev"

REM Give the servers a few seconds to start, then open the site.
timeout /t 6 >nul
start "" http://localhost:5173
