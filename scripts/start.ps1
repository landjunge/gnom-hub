# scripts/start.ps1 — Windows startup automation for Gnom-Hub and its agents
$repoDir = Split-Path -Parent $MyInvocation.MyCommand.Path
if ($repoDir -like "*scripts") {
    $repoDir = Split-Path -Parent $repoDir
}
Set-Location $repoDir

$venvPath = Join-Path $repoDir ".venv"
if (-not (Test-Path $venvPath)) {
    Write-Host "Virtuelle Umgebung .venv nicht gefunden. Bitte install.py ausführen." -ForegroundColor Red
    Exit 1
}

# Clean logs
New-Item -ItemType Directory -Force -Path (Join-Path $repoDir "logs") | Out-Null

# Stop running processes
$running = Get-CimInstance Win32_Process -Filter "Name = 'python.exe' AND (CommandLine LIKE '*gnom_hub*' OR CommandLine LIKE '*agents.run_agent*')"
if ($running) {
    Write-Host "🛑 Beende alte Gnom-Hub Prozesse..." -ForegroundColor Yellow
    $running | Invoke-CimMethod -MethodName Terminate | Out-Null
    Start-Sleep -Seconds 1
}

# Set env variables from .env
$envFile = Join-Path $repoDir "config\.env"
if (Test-Path $envFile) {
    Get-Content $envFile | Where-Object { $_ -match '=' -and $_ -notmatch '^\s*#' } | ForEach-Object {
        $name, $value = $_.Split('=', 2)
        [Environment]::SetEnvironmentVariable($name.Trim(), $value.Trim())
    }
}

Write-Host "🚀 Starte Gnom-Hub Server..." -ForegroundColor Green
$pythonExe = Join-Path $venvPath "Scripts\python.exe"
$hubLog = Join-Path $repoDir "logs\logs_hub.txt"
Start-Process -FilePath $pythonExe -ArgumentList "-m gnom_hub" -WorkingDirectory $repoDir -RedirectStandardOutput $hubLog -RedirectStandardError $hubLog -WindowStyle Hidden

Start-Sleep -Seconds 2

Write-Host "🤖 Starte 8 Hintergrund-Agenten..." -ForegroundColor Green
$agents = @("generalag", "soulag", "securityag", "watchdogag", "researcherag", "writerag", "editorag", "coderag")
foreach ($agent in $agents) {
    $agentLog = Join-Path $repoDir "logs\logs_$agent.txt"
    Start-Process -FilePath $pythonExe -ArgumentList "-u -m agents.run_agent --name $agent" -WorkingDirectory $repoDir -RedirectStandardOutput $agentLog -RedirectStandardError $agentLog -WindowStyle Hidden
}

Write-Host "✅ Gnom-Hub erfolgreich gestartet!" -ForegroundColor Green
Start-Process "http://127.0.0.1:3002"
