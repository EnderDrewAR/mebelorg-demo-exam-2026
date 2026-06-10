param(
    [string]$DbName = "furniture_demo",
    [string]$DbUser = "postgres",
    [string]$DbHost = "localhost",
    [int]$DbPort = 5432,
    [string]$DbPassword,
    [switch]$ResetConfig,
    [switch]$CheckOnly
)

$ErrorActionPreference = "Stop"
$env:PYTHONUTF8 = "1"
[void](chcp 65001)
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$OutputEncoding = [Console]::OutputEncoding
Set-Location $PSScriptRoot

function Find-PostgresTool {
    param([string]$ToolName)

    $candidates = @(
        "C:\Program Files\PostgreSQL\16\bin\$ToolName.exe",
        "C:\Program Files (x86)\PostgreSQL\16\bin\$ToolName.exe"
    )
    $fallbackCandidates = @()

    $registryRoots = @(
        "HKLM:\SOFTWARE\PostgreSQL\Installations",
        "HKLM:\SOFTWARE\WOW6432Node\PostgreSQL\Installations"
    )
    foreach ($registryRoot in $registryRoots) {
        $installations = Get-ChildItem $registryRoot -ErrorAction SilentlyContinue
        foreach ($installation in $installations) {
            $properties = Get-ItemProperty $installation.PSPath
            if ($properties."Base Directory") {
                $toolPath = Join-Path $properties."Base Directory" "bin\$ToolName.exe"
                if ([string]$properties.Version -like "16.*") {
                    $candidates += $toolPath
                }
                else {
                    $fallbackCandidates += $toolPath
                }
            }
        }
    }

    $command = Get-Command $ToolName -ErrorAction SilentlyContinue
    if ($command) {
        $fallbackCandidates += $command.Source
    }

    foreach ($candidate in @($candidates + $fallbackCandidates) | Select-Object -Unique) {
        if (Test-Path -LiteralPath $candidate) {
            return $candidate
        }
    }

    return $null
}

function Find-Uv {
    $command = Get-Command uv -ErrorAction SilentlyContinue
    if ($command) {
        return $command.Source
    }

    $candidates = @(
        (Join-Path $env:USERPROFILE ".local\bin\uv.exe"),
        (Join-Path $env:USERPROFILE ".cargo\bin\uv.exe")
    )
    foreach ($candidate in $candidates) {
        if (Test-Path -LiteralPath $candidate) {
            return $candidate
        }
    }

    return $null
}

function Read-DotEnv {
    param([string]$Path)

    $values = @{}
    if (-not (Test-Path -LiteralPath $Path)) {
        return $values
    }

    foreach ($line in Get-Content -LiteralPath $Path -Encoding UTF8) {
        if ($line -match "^\s*#" -or $line -notmatch "=") {
            continue
        }
        $parts = $line.Split("=", 2)
        $key = $parts[0].Trim()
        $value = $parts[1].Trim().Trim('"')
        $values[$key] = $value
    }
    return $values
}

function ConvertTo-DotEnvValue {
    param([string]$Value)

    $escaped = $Value.Replace("\", "\\").Replace('"', '\"')
    return '"' + $escaped + '"'
}

function ConvertFrom-SecureStringPlain {
    param([Security.SecureString]$SecureValue)

    $pointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($SecureValue)
    try {
        return [Runtime.InteropServices.Marshal]::PtrToStringBSTR($pointer)
    }
    finally {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer)
    }
}

function Assert-LastExitCode {
    param([string]$Message)

    if ($LASTEXITCODE -ne 0) {
        throw $Message
    }
}

function Stop-ExistingDjangoServer {
    param([int]$Port)

    $listeners = @(Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)
    foreach ($listener in $listeners) {
        $serverProcess = Get-CimInstance Win32_Process `
            -Filter "ProcessId = $($listener.OwningProcess)" `
            -ErrorAction SilentlyContinue

        if (-not $serverProcess -or $serverProcess.CommandLine -notmatch "manage\.py.+runserver") {
            $processName = if ($serverProcess) { $serverProcess.Name } else { "unknown process" }
            throw "Port $Port is already used by $processName (PID $($listener.OwningProcess))."
        }
    }

    $portPattern = [regex]::Escape([string]$Port)
    $oldServers = @(
        Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
            Where-Object {
                $_.CommandLine -match "manage\.py.+runserver.+:$portPattern(?:\s|$)"
            }
    )
    if ($oldServers.Count -gt 0) {
        Write-Host "Stopping the previous Django development server on port $Port..." -ForegroundColor Yellow
        foreach ($oldServer in $oldServers) {
            Stop-Process -Id $oldServer.ProcessId -Force -ErrorAction SilentlyContinue
        }
        Start-Sleep -Milliseconds 500
    }

    if (Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue) {
        throw "Failed to release port $Port."
    }
}

$psql = Find-PostgresTool "psql"
if (-not $psql) {
    Write-Host "PostgreSQL 16 client psql.exe was not found." -ForegroundColor Red
    Write-Host "Expected location: C:\Program Files\PostgreSQL\16\bin\psql.exe"
    exit 1
}

$uv = Find-Uv
if (-not $uv) {
    Write-Host "uv was not found. Install it from:" -ForegroundColor Red
    Write-Host "https://docs.astral.sh/uv/getting-started/installation/"
    exit 1
}

$envPath = Join-Path $PSScriptRoot ".env"
$savedConfig = Read-DotEnv $envPath
if (-not $ResetConfig -and $savedConfig.Count -gt 0) {
    if (-not $PSBoundParameters.ContainsKey("DbName") -and $savedConfig.POSTGRES_DB) {
        $DbName = $savedConfig.POSTGRES_DB
    }
    if (-not $PSBoundParameters.ContainsKey("DbUser") -and $savedConfig.POSTGRES_USER) {
        $DbUser = $savedConfig.POSTGRES_USER
    }
    if (-not $PSBoundParameters.ContainsKey("DbHost") -and $savedConfig.POSTGRES_HOST) {
        $DbHost = $savedConfig.POSTGRES_HOST
    }
    if (-not $PSBoundParameters.ContainsKey("DbPort") -and $savedConfig.POSTGRES_PORT) {
        $DbPort = [int]$savedConfig.POSTGRES_PORT
    }
    if (-not $PSBoundParameters.ContainsKey("DbPassword") -and $savedConfig.POSTGRES_PASSWORD) {
        $DbPassword = $savedConfig.POSTGRES_PASSWORD
    }
}

if ($DbName -notmatch "^[A-Za-z_][A-Za-z0-9_]*$") {
    throw "Database name may contain only Latin letters, digits, and underscores."
}
if ($DbUser -notmatch "^[A-Za-z_][A-Za-z0-9_]*$") {
    throw "Database user may contain only Latin letters, digits, and underscores."
}

if (-not $PSBoundParameters.ContainsKey("DbPassword") -and -not $DbPassword) {
    $securePassword = Read-Host "Enter the PostgreSQL password for user '$DbUser'" -AsSecureString
    $DbPassword = ConvertFrom-SecureStringPlain $securePassword
}

$env:PGPASSWORD = $DbPassword
$env:PGCLIENTENCODING = "UTF8"

Write-Host "Checking PostgreSQL at ${DbHost}:${DbPort}..." -ForegroundColor Cyan
& $psql -h $DbHost -p $DbPort -U $DbUser -d postgres -v ON_ERROR_STOP=1 -tAc "SELECT 1;" *> $null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Cannot connect to PostgreSQL." -ForegroundColor Red
    Write-Host "Check that the PostgreSQL service is running and the password is correct."
    exit 1
}

$serverVersion = & $psql `
    -h $DbHost `
    -p $DbPort `
    -U $DbUser `
    -d postgres `
    -v ON_ERROR_STOP=1 `
    -tAc "SHOW server_version;"
Assert-LastExitCode "Failed to read the PostgreSQL server version."
$serverVersion = ($serverVersion | Out-String).Trim()
Write-Host "Connected to PostgreSQL $serverVersion." -ForegroundColor Green
if ($serverVersion -notmatch "^16(?:\.|$)") {
    Write-Warning "The exam target is PostgreSQL 16, but server version $serverVersion is running."
}

$databaseExists = & $psql `
    -h $DbHost `
    -p $DbPort `
    -U $DbUser `
    -d postgres `
    -v ON_ERROR_STOP=1 `
    -tAc "SELECT 1 FROM pg_database WHERE datname = '$DbName';"
Assert-LastExitCode "Failed to check whether the database exists."

if (($databaseExists | Out-String).Trim() -ne "1") {
    Write-Host "Creating database '$DbName'..." -ForegroundColor Yellow
    & $psql `
        -h $DbHost `
        -p $DbPort `
        -U $DbUser `
        -d postgres `
        -v ON_ERROR_STOP=1 `
        -c "CREATE DATABASE `"$DbName`" ENCODING 'UTF8' TEMPLATE template0;"
    Assert-LastExitCode "Failed to create database '$DbName'."
}
else {
    Write-Host "Database '$DbName' already exists." -ForegroundColor Green
}

$secretKey = "mebelorg-local-exam-secret-key-2026-change-before-public-deployment"
$envLines = @(
    "DJANGO_SECRET_KEY=$(ConvertTo-DotEnvValue $secretKey)",
    "DJANGO_DEBUG=1",
    "DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1",
    "POSTGRES_DB=$(ConvertTo-DotEnvValue $DbName)",
    "POSTGRES_USER=$(ConvertTo-DotEnvValue $DbUser)",
    "POSTGRES_PASSWORD=$(ConvertTo-DotEnvValue $DbPassword)",
    "POSTGRES_HOST=$(ConvertTo-DotEnvValue $DbHost)",
    "POSTGRES_PORT=$DbPort"
)
[System.IO.File]::WriteAllLines(
    $envPath,
    $envLines,
    [System.Text.UTF8Encoding]::new($false)
)

$env:POSTGRES_DB = $DbName
$env:POSTGRES_USER = $DbUser
$env:POSTGRES_PASSWORD = $DbPassword
$env:POSTGRES_HOST = $DbHost
$env:POSTGRES_PORT = [string]$DbPort

Write-Host "Installing Python dependencies..." -ForegroundColor Cyan
& $uv sync --frozen
Assert-LastExitCode "uv sync failed."

Write-Host "Applying migrations and importing demo data..." -ForegroundColor Cyan
& $uv run python src/manage.py migrate --noinput
Assert-LastExitCode "Django migrations failed."
& $uv run python src/manage.py import_demo_data
Assert-LastExitCode "Demo data import failed."
& $uv run python src/manage.py findstatic css/app.css --verbosity 0 *> $null
Assert-LastExitCode "Static file src/static/css/app.css was not found."
& $uv run python src/manage.py check
Assert-LastExitCode "Django system check failed."

if ($CheckOnly) {
    Write-Host "PostgreSQL startup check completed successfully." -ForegroundColor Green
    exit 0
}

Stop-ExistingDjangoServer -Port 8000
Write-Host "Connected to PostgreSQL database '$DbName'." -ForegroundColor Green
Write-Host "Open http://127.0.0.1:8000" -ForegroundColor Green
& $uv run python src/manage.py runserver 127.0.0.1:8000 --noreload
