#!/usr/bin/env pwsh
# Quick Start Script for Extractor Evaluation Suite
# Usage: ./quick_test.ps1

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "ALA Parameter Extractor - Evaluation Suite" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# Check if OPENAI_API_KEY is set, if not try to load from env.yaml
if (-not $env:OPENAI_API_KEY) {
    # Try to load from env.yaml in project root
    $envYamlPath = "../../env.yaml"
    if (Test-Path $envYamlPath) {
        Write-Host "Loading API key from env.yaml..." -ForegroundColor Yellow
        $envContent = Get-Content $envYamlPath -Raw
        # Match only lines that start with OPENAI_API_KEY (not commented with #)
        if ($envContent -match '(?m)^(?!#)\s*OPENAI_API_KEY:\s*[''"]?([^''"#\r\n]+)[''"]?') {
            $env:OPENAI_API_KEY = $matches[1].Trim()
            Write-Host "[OK] OpenAI API Key loaded from env.yaml" -ForegroundColor Green
        } else {
            Write-Host "ERROR: OPENAI_API_KEY not found in env.yaml" -ForegroundColor Red
            Write-Host ""
            Write-Host "Please add it to env.yaml or set it using:" -ForegroundColor Yellow
            Write-Host '  $env:OPENAI_API_KEY = "your-api-key"' -ForegroundColor Yellow
            Write-Host ""
            exit 1
        }
    } else {
        Write-Host "ERROR: OPENAI_API_KEY environment variable not set" -ForegroundColor Red
        Write-Host "       and env.yaml not found at $envYamlPath" -ForegroundColor Red
        Write-Host ""
        Write-Host "Please set it using:" -ForegroundColor Yellow
        Write-Host '  $env:OPENAI_API_KEY = "your-api-key"' -ForegroundColor Yellow
        Write-Host ""
        exit 1
    }
} else {
    Write-Host "[OK] OpenAI API Key found in environment" -ForegroundColor Green
}
Write-Host ""

# Check if OPENAI_BASE_URL is set, if not use default
if (-not $env:OPENAI_BASE_URL) {
    # Try to load from env.yaml in project root
    $envYamlPath = "../../env.yaml"
    if (Test-Path $envYamlPath) {
        $envContent = Get-Content $envYamlPath -Raw
        # Match only lines that start with OPENAI_BASE_URL (not commented with #)
        if ($envContent -match '(?m)^(?!#)\s*OPENAI_BASE_URL:\s*[''"]?([^''"#\r\n]+)[''"]?') {
            $env:OPENAI_BASE_URL = $matches[1].Trim()
            Write-Host "[OK] OpenAI base URL loaded from env.yaml: $env:OPENAI_BASE_URL" -ForegroundColor Green
        } else {
            # Use default if not in env.yaml
            $env:OPENAI_BASE_URL = "https://api.ai.it.ufl.edu"
            Write-Host "[OK] Using default OpenAI base URL: $env:OPENAI_BASE_URL" -ForegroundColor Green
        }
    } else {
        # Use default if env.yaml doesn't exist
        $env:OPENAI_BASE_URL = "https://api.ai.it.ufl.edu"
        Write-Host "[OK] Using default OpenAI base URL: $env:OPENAI_BASE_URL" -ForegroundColor Green
    }
} else {
    Write-Host "[OK] OpenAI base URL found in environment: $env:OPENAI_BASE_URL" -ForegroundColor Green
}
Write-Host ""

# Check if we're in the right directory
if (-not (Test-Path "run_extractor_tests.py")) {
    Write-Host "ERROR: run_extractor_tests.py not found" -ForegroundColor Red
    Write-Host "Please run this script from tests/extractor_tests directory" -ForegroundColor Yellow
    Write-Host ""
    exit 1
}

Write-Host "[OK] Test runner found" -ForegroundColor Green
Write-Host ""

# Ask user for verbose mode
$verbose = Read-Host "Run in verbose mode? (y/N)"
$verboseFlag = ""
if ($verbose -eq "y" -or $verbose -eq "Y") {
    $verboseFlag = "--verbose"
}

# Generate timestamped report filename
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$reportFile = "reports/extractor_test_${timestamp}.json"

# Create reports directory if it doesn't exist
if (-not (Test-Path "reports")) {
    New-Item -ItemType Directory -Path "reports" | Out-Null
    Write-Host "[OK] Created reports directory" -ForegroundColor Green
    Write-Host ""
}

# Run tests
Write-Host "Running tests..." -ForegroundColor Cyan
Write-Host ""

if ($verboseFlag) {
    python run_extractor_tests.py $verboseFlag --output $reportFile
} else {
    python run_extractor_tests.py --output $reportFile
}

$exitCode = $LASTEXITCODE

Write-Host ""
if ($exitCode -eq 0) {
    Write-Host "============================================================" -ForegroundColor Green
    Write-Host "ALL TESTS PASSED!" -ForegroundColor Green
    Write-Host "============================================================" -ForegroundColor Green
} else {
    Write-Host "============================================================" -ForegroundColor Red
    Write-Host "SOME TESTS FAILED" -ForegroundColor Red
    Write-Host "============================================================" -ForegroundColor Red
    Write-Host ""
    Write-Host "Check the detailed report at: $reportFile" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Report saved to: $reportFile" -ForegroundColor Cyan

exit $exitCode