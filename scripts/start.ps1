# ==================================================================
#  Starts the WBL Placement Recommendation System in the BACKGROUND.
#  (Run it by double-clicking start-system.bat in the project folder.)
#
#  1. Makes sure MySQL is running (starts XAMPP's MySQL if needed)
#  2. Starts the backend (Flask, port 5000) and frontend (React, port 5173)
#     as hidden background programs: there are NO windows to keep open
#  3. Waits until both answer, then opens the website
#  Running it again while the system is up just opens the website.
#  To stop everything: double-click stop-system.bat.
#  Problems? Look in the logs\ folder (backend.log, frontend.log).
# ==================================================================
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot          # the project folder
$logs = Join-Path $root 'logs'
New-Item -ItemType Directory -Force -Path $logs | Out-Null

# Is something answering on this port? Checks both kinds of "localhost":
# 127.0.0.1 (IPv4, used by Flask and MySQL) and ::1 (IPv6, used by Vite).
function Test-Port([int]$Port) {
    foreach ($address in @('127.0.0.1', '::1')) {
        $family = [System.Net.IPAddress]::Parse($address).AddressFamily
        $client = New-Object System.Net.Sockets.TcpClient($family)
        try { if ($client.ConnectAsync($address, $Port).Wait(500) -and $client.Connected) { return $true } }
        catch { }
        finally { $client.Dispose() }
    }
    return $false
}

# Wait up to $Seconds for a port to answer.
function Wait-Port([int]$Port, [int]$Seconds) {
    for ($i = 0; $i -lt $Seconds; $i++) {
        if (Test-Port $Port) { return $true }
        Start-Sleep -Seconds 1
    }
    return $false
}

# Show the last lines of a log file (used when something fails to start).
function Show-Log([string]$Name) {
    $path = Join-Path $logs $Name
    if (Test-Path $path) {
        Write-Host "  --- last lines of logs\$Name ---" -ForegroundColor DarkGray
        Get-Content $path -Tail 15 | ForEach-Object { Write-Host "  $_" -ForegroundColor DarkGray }
    }
}

Write-Host ""
Write-Host "  WBL Placement Recommendation System" -ForegroundColor Cyan
Write-Host "  -----------------------------------"

# ---- 1. MySQL -------------------------------------------------------------------
if (Test-Port 3306) {
    Write-Host "  [OK] MySQL is running"
} else {
    Write-Host "  [..] MySQL is off - starting XAMPP's MySQL"
    $xampp = @("$env:USERPROFILE\OneDrive - Strathmore University\Desktop\zamp", 'C:\xampp') |
        Where-Object { Test-Path (Join-Path $_ 'mysql_start.bat') } | Select-Object -First 1
    if ($xampp) {
        Start-Process -FilePath (Join-Path $xampp 'mysql_start.bat') -WorkingDirectory $xampp -WindowStyle Hidden
    }
    if (Wait-Port 3306 25) {
        Write-Host "  [OK] MySQL started"
    } else {
        Write-Host "  [!!] Could not start MySQL. Open the XAMPP Control Panel, click Start next to MySQL," -ForegroundColor Red
        Write-Host "       then run this again." -ForegroundColor Red
        exit 1
    }
}

# ---- 2. Backend (Flask) ---------------------------------------------------------
if (Test-Port 5000) {
    Write-Host "  [OK] Backend already running"
} else {
    Write-Host "  [..] Starting the backend"
    Start-Process -FilePath (Join-Path $root 'backend\venv\Scripts\flask.exe') -ArgumentList 'run', '--port', '5000' `
        -WorkingDirectory (Join-Path $root 'backend') -WindowStyle Hidden `
        -RedirectStandardOutput (Join-Path $logs 'backend.log') -RedirectStandardError (Join-Path $logs 'backend-errors.log')
}

# ---- 3. Frontend (React / Vite) -------------------------------------------------
if (Test-Port 5173) {
    Write-Host "  [OK] Frontend already running"
} else {
    Write-Host "  [..] Starting the frontend"
    Start-Process -FilePath 'npm.cmd' -ArgumentList 'run', 'dev' `
        -WorkingDirectory (Join-Path $root 'frontend') -WindowStyle Hidden `
        -RedirectStandardOutput (Join-Path $logs 'frontend.log') -RedirectStandardError (Join-Path $logs 'frontend-errors.log')
}

# ---- 4. Wait until both answer ---------------------------------------------------
$backendUp = Wait-Port 5000 40
$frontendUp = Wait-Port 5173 40
if ($backendUp) { Write-Host "  [OK] Backend is up   (http://localhost:5000)" } else { Write-Host "  [!!] Backend did not start" -ForegroundColor Red; Show-Log 'backend-errors.log' }
if ($frontendUp) { Write-Host "  [OK] Frontend is up  (http://localhost:5173)" } else { Write-Host "  [!!] Frontend did not start" -ForegroundColor Red; Show-Log 'frontend.log' }

if ($backendUp -and $frontendUp) {
    Start-Process 'http://localhost:5173'
    Write-Host ""
    Write-Host "  The system is running in the background - you can close this window." -ForegroundColor Green
    Write-Host "  To stop it later: double-click stop-system.bat"
} else {
    exit 1
}
