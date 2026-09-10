param(
    [ValidateSet('ActiveProduction', 'ActiveResearch', 'LegacyCompat')]
    [string]$Suite = 'ActiveProduction',
    [string]$ArtifactDirectory = 'artifacts/test_scope_reconciliation_01'
)

$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
New-Item -ItemType Directory -Force -Path $ArtifactDirectory | Out-Null

if ($Suite -eq 'ActiveResearch') {
    & python -m pytest -q -m active_research --junitxml="$ArtifactDirectory/ACTIVE_RESEARCH.xml"
    exit $LASTEXITCODE
}
if ($Suite -eq 'LegacyCompat') {
    & python -m pytest -q -m legacy_compat --junitxml="$ArtifactDirectory/LEGACY_COMPAT.xml"
    exit $LASTEXITCODE
}

$containerName = 'traders-test-scope-pg16'
$testPort = '55441'
$adminPassword = 'test-scope-admin-only'
$testRole = 'paper_test_active_scope'
$testPassword = 'test-scope-runtime-only'
$testDatabase = 'paper_test_active_scope_reconciliation'
$databaseUrl = "postgresql+psycopg://${testRole}:${testPassword}@127.0.0.1:${testPort}/${testDatabase}"

function Invoke-Checked {
    param([string[]]$Command)
    $executable = $Command[0]
    $arguments = $Command[1..($Command.Length - 1)]
    & $executable @arguments
    if ($LASTEXITCODE -ne 0) {
        throw "command failed with exit code ${LASTEXITCODE}: $($Command[0])"
    }
}

try {
    & docker rm -f $containerName 2>$null | Out-Null
    & docker run --rm -d --name $containerName `
        -e "POSTGRES_PASSWORD=$adminPassword" -p "${testPort}:5432" postgres:16 | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'failed to start isolated PostgreSQL 16' }
    $ready = $false
    foreach ($attempt in 1..60) {
        & docker exec $containerName pg_isready -U postgres 2>$null | Out-Null
        if ($LASTEXITCODE -eq 0) { $ready = $true; break }
        Start-Sleep -Seconds 1
    }
    if (-not $ready) { throw 'isolated PostgreSQL 16 did not become ready' }
    Invoke-Checked @('docker', 'exec', $containerName, 'psql', '-U', 'postgres', '-v', 'ON_ERROR_STOP=1', '-c', "CREATE ROLE $testRole LOGIN PASSWORD '$testPassword' NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS")
    Invoke-Checked @('docker', 'exec', $containerName, 'psql', '-U', 'postgres', '-v', 'ON_ERROR_STOP=1', '-c', "CREATE DATABASE $testDatabase OWNER $testRole")

    & python -m pytest -q -m active_production --junitxml="$ArtifactDirectory/ACTIVE_PRODUCTION_NO_DB.xml"
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    $previousNaturalUrl = $env:PAPER_NATURAL_E2E_DATABASE_URL
    $env:PAPER_NATURAL_E2E_DATABASE_URL = $databaseUrl
    try {
        & python -m pytest -q tests/integration/paper_natural_execution_e2e `
            --junitxml="$ArtifactDirectory/ACTIVE_PRODUCTION_POSTGRES16.xml"
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    }
    finally {
        $env:PAPER_NATURAL_E2E_DATABASE_URL = $previousNaturalUrl
    }
}
finally {
    & docker rm -f $containerName 2>$null | Out-Null
}
