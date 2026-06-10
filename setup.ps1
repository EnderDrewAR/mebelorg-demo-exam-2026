param(
    [string]$DbPassword = "postgres"
)

$ErrorActionPreference = "Stop"
$env:PYTHONUTF8 = "1"
Set-Location $PSScriptRoot

# Настройки PostgreSQL на экзамене
$DbName = "furniture_demo"
$DbUser = "postgres"
$DbHost = "localhost"
$DbPort = 5432

function Check-Command {
    param([string]$Message)

    if ($LASTEXITCODE -ne 0) {
        Write-Host $Message -ForegroundColor Red
        exit 1
    }
}

# PostgreSQL 16 обычно устанавливается в эту папку
$psql = "C:\Program Files\PostgreSQL\16\bin\psql.exe"
if (-not (Test-Path $psql)) {
    $psqlCommand = Get-Command psql -ErrorAction SilentlyContinue
    if ($psqlCommand) {
        $psql = $psqlCommand.Source
    }
    else {
        $psql = Get-ChildItem "C:\Program Files\PostgreSQL\*\bin\psql.exe" `
            -ErrorAction SilentlyContinue |
            Select-Object -First 1 -ExpandProperty FullName
    }
}

if (-not $psql -or -not (Test-Path $psql)) {
    Write-Host "PostgreSQL 16 was not found." -ForegroundColor Red
    exit 1
}

$uv = Get-Command uv -ErrorAction SilentlyContinue
if (-not $uv) {
    Write-Host "uv was not found." -ForegroundColor Red
    exit 1
}

$env:PGPASSWORD = $DbPassword
$env:PGCLIENTENCODING = "UTF8"

Write-Host "Checking PostgreSQL..." -ForegroundColor Cyan
& $psql -h $DbHost -p $DbPort -U $DbUser -d postgres -v ON_ERROR_STOP=1 -tAc "SELECT 1;" *> $null
Check-Command "Cannot connect to PostgreSQL."

$databaseExists = & $psql `
    -h $DbHost `
    -p $DbPort `
    -U $DbUser `
    -d postgres `
    -v ON_ERROR_STOP=1 `
    -tAc "SELECT 1 FROM pg_database WHERE datname = '$DbName';"
Check-Command "Cannot check the database."

if (($databaseExists | Out-String).Trim() -ne "1") {
    Write-Host "Creating database $DbName..." -ForegroundColor Yellow
    & $psql `
        -h $DbHost `
        -p $DbPort `
        -U $DbUser `
        -d postgres `
        -v ON_ERROR_STOP=1 `
        -c "CREATE DATABASE $DbName ENCODING 'UTF8' TEMPLATE template0;"
    Check-Command "Cannot create the database."
}

# Django читает эти настройки из файла .env
$envText = @"
DJANGO_SECRET_KEY=local-exam-key
DJANGO_DEBUG=1
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
POSTGRES_DB=$DbName
POSTGRES_USER=$DbUser
POSTGRES_PASSWORD=$DbPassword
POSTGRES_HOST=$DbHost
POSTGRES_PORT=$DbPort
"@
[System.IO.File]::WriteAllText(
    (Join-Path $PSScriptRoot ".env"),
    $envText,
    [System.Text.UTF8Encoding]::new($false)
)

$env:POSTGRES_DB = $DbName
$env:POSTGRES_USER = $DbUser
$env:POSTGRES_PASSWORD = $DbPassword
$env:POSTGRES_HOST = $DbHost
$env:POSTGRES_PORT = [string]$DbPort

Write-Host "Installing dependencies..." -ForegroundColor Cyan
& $uv.Source sync --frozen
Check-Command "Dependency installation failed."

Write-Host "Applying migrations..." -ForegroundColor Cyan
& $uv.Source run python src/manage.py migrate --noinput
Check-Command "Migration failed."

Write-Host "Importing data..." -ForegroundColor Cyan
& $uv.Source run python src/manage.py import_demo_data
Check-Command "Data import failed."

& $uv.Source run python src/manage.py check
Check-Command "Django system check failed."

Write-Host ""
Write-Host "Setup completed successfully." -ForegroundColor Green
Write-Host "You can delete setup.ps1 now."
Write-Host "Run the project with:"
Write-Host "uv run python src/manage.py runserver" -ForegroundColor Cyan
