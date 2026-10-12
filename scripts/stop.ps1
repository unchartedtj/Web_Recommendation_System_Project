# ==================================================================
#  Stops the WBL Placement system's backend and frontend.
#  (Run it by double-clicking stop-system.bat in the project folder.)
#  MySQL is left running; stop it in the XAMPP Control Panel if you want.
# ==================================================================
$root = Split-Path -Parent $PSScriptRoot

# Only this project's backend (flask) and frontend (vite / npm run dev) programs,
# found by their command line, so editors and other tools are never touched.
$targets = Get-CimInstance Win32_Process | Where-Object {
    $cmd = $_.CommandLine
    $cmd -and $cmd -like "*$root*" -and (
        ($_.Name -in @('flask.exe', 'python.exe') -and $cmd -like '*flask*') -or
        ($_.Name -eq 'node.exe' -and $cmd -like '*vite*') -or
        ($_.Name -eq 'cmd.exe' -and ($cmd -like '*npm*run*dev*' -or $cmd -like '*flask*'))
    )
}
# Also anything still listening on the two ports (e.g. started another way).
$portOwners = Get-NetTCPConnection -LocalPort 5000, 5173 -State Listen -ErrorAction SilentlyContinue |
    Select-Object -ExpandProperty OwningProcess -Unique

$ids = @($targets.ProcessId) + @($portOwners) | Where-Object { $_ } | Select-Object -Unique
foreach ($id in $ids) { Stop-Process -Id $id -Force -ErrorAction SilentlyContinue }

Write-Host ""
if ($ids.Count -gt 0) {
    Write-Host "  The backend and frontend have been stopped." -ForegroundColor Green
} else {
    Write-Host "  Nothing was running." -ForegroundColor Yellow
}
