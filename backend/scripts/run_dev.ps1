$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

& "$root\.venv\Scripts\python.exe" -m uvicorn backend.app.main:app --reload

