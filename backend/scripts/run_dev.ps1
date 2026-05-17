$root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $root

$hostAddress = if ($env:UVICORN_HOST) { $env:UVICORN_HOST } else { "0.0.0.0" }
$port = if ($env:UVICORN_PORT) { $env:UVICORN_PORT } else { "8000" }

& "$root\.venv\Scripts\python.exe" -m uvicorn backend.app.main:app --host $hostAddress --port $port --reload
