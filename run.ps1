# Starts the API (port 8000) and the frontend dev server (port 5173) together.
# Usage: right-click > Run with PowerShell, or `powershell -File run.ps1`

$root = $PSScriptRoot

Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$root'; venv\Scripts\Activate.ps1; uvicorn app.main:app --reload"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$root\frontend'; npm run dev"

Write-Host "API starting at http://127.0.0.1:8000 (docs at /docs)"
Write-Host "Frontend starting at http://localhost:5173"
