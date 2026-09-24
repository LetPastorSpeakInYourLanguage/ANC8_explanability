# Run the web app locally, with every tab working.
#
#   powershell -ExecutionPolicy Bypass -File dev.ps1
#
# Starts two things:
#   1. the Python prediction service (scripts/dev_api.py) on port 8000, in its
#      own window -- the Predict tab calls it; everything else is static;
#   2. the Next.js development server on http://localhost:3000, in this window.
# Close both windows (or press Ctrl+C) to stop.

$root = $PSScriptRoot
$python = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $python) { $python = (Get-Command py -ErrorAction SilentlyContinue).Source }
if (-not $python) { Write-Error "Python not found on PATH"; exit 1 }

if (-not (Test-Path "$root\app\node_modules")) {
    Write-Host "Installing web app dependencies (first run only)..."
    Push-Location "$root\app"; npm install; Pop-Location
}

Write-Host "Starting the prediction service on http://127.0.0.1:8000 ..."
Start-Process $python -ArgumentList "`"$root\scripts\dev_api.py`"" -WorkingDirectory $root

Write-Host "Starting the web app on http://localhost:3000 ..."
Push-Location "$root\app"
npm run dev
Pop-Location
