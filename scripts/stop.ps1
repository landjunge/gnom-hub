# scripts/stop.ps1 — Windows shutdown automation for Gnom-Hub and its agents
$processes = Get-CimInstance Win32_Process -Filter "Name = 'python.exe' AND (CommandLine LIKE '*gnom_hub*' OR CommandLine LIKE '*agents.run_agent*')"
if ($processes) {
    Write-Host "🛑 Beende $($processes.Count) Gnom-Hub Prozesse..." -ForegroundColor Red
    $processes | Invoke-CimMethod -MethodName Terminate | Out-Null
    Write-Host "✅ Alle Prozesse gestoppt." -ForegroundColor Green
} else {
    Write-Host "ℹ️ Keine laufenden Gnom-Hub Prozesse gefunden." -ForegroundColor Yellow
}
