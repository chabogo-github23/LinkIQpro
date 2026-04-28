param(
    [int]$Port = 8000,
    [switch]$SkipMigrate,
    [switch]$UseRemoteDatabase
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root ".venv\Scripts\python.exe"

if (-not (Test-Path $python)) {
    Write-Error "Virtual environment Python was not found at $python. Create or restore the .venv first."
}

Set-Location $root

if (-not $env:DJANGO_SETTINGS_MODULE) {
    $env:DJANGO_SETTINGS_MODULE = "shadowiq.settings"
}

if (-not $env:DEBUG) {
    $env:DEBUG = "True"
}

if (-not $env:ALLOWED_HOSTS) {
    $env:ALLOWED_HOSTS = "localhost,127.0.0.1"
}

if (-not $env:CSRF_TRUSTED_ORIGINS) {
    $env:CSRF_TRUSTED_ORIGINS = "http://localhost:$Port,http://127.0.0.1:$Port"
}

if (-not $UseRemoteDatabase) {
    $env:USE_SQLITE_LOCAL = "True"
}
else {
    $env:USE_SQLITE_LOCAL = "False"
}

if (-not $SkipMigrate) {
    & $python manage.py migrate
}

Write-Host ""
Write-Host "ShadowIQ local server is starting at http://127.0.0.1:$Port/"
Write-Host "Stop it with Ctrl+C."
Write-Host ""

& $python manage.py runserver "127.0.0.1:$Port"
