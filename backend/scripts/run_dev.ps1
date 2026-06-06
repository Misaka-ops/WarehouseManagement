$root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $root

$hostAddress = if ($env:UVICORN_HOST) { $env:UVICORN_HOST } else { "0.0.0.0" }
$port = if ($env:UVICORN_PORT) { $env:UVICORN_PORT } else { "8000" }
$pythonPath = Join-Path $root "backend\.venv\Scripts\python.exe"

if (-not (Test-Path $pythonPath)) {
  $pythonPath = Join-Path $root ".venv\Scripts\python.exe"
}

if (-not (Test-Path $pythonPath)) {
  throw "Python virtual environment not found. Checked backend/.venv and repo-root .venv."
}

& $pythonPath -m uvicorn backend.app.main:app --host $hostAddress --port $port --reload
