# Starts XAMPP's MySQL only if it isn't already running (used by the VS Code auto-start task).
# If we start it, this terminal stays busy while MySQL runs - that's normal, don't close it.
$client = New-Object System.Net.Sockets.TcpClient
try { $running = $client.ConnectAsync('127.0.0.1', 3306).Wait(1000) } catch { $running = $false }
finally { $client.Dispose() }

if ($running) {
    Write-Host "MySQL is already running."
    exit 0
}

$xampp = @("$env:USERPROFILE\OneDrive - Strathmore University\Desktop\zamp", 'C:\xampp') |
    Where-Object { Test-Path (Join-Path $_ 'mysql_start.bat') } | Select-Object -First 1
if (-not $xampp) {
    Write-Host "XAMPP not found - start MySQL from the XAMPP Control Panel." -ForegroundColor Red
    exit 1
}
Write-Host "Starting MySQL from $xampp ..."
& (Join-Path $xampp 'mysql_start.bat')
