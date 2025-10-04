#!/usr/bin/env pwsh
# Quick setup script for Microsoft Agent Framework integration example
# Run this to get started quickly

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "Dakora + Microsoft Agent Framework Setup" -ForegroundColor Cyan
Write-Host "============================================`n" -ForegroundColor Cyan

# Check Python version
Write-Host "Checking Python version..." -ForegroundColor Yellow
$pythonVersion = python --version 2>&1
if ($pythonVersion -match "Python 3\.(\d+)") {
    $minorVersion = [int]$Matches[1]
    if ($minorVersion -lt 10) {
        Write-Host "❌ Python 3.10+ required. You have: $pythonVersion" -ForegroundColor Red
        exit 1
    }
    Write-Host "✓ Python version OK: $pythonVersion`n" -ForegroundColor Green
} else {
    Write-Host "❌ Python not found or version check failed" -ForegroundColor Red
    exit 1
}

# Create virtual environment
Write-Host "Setting up virtual environment..." -ForegroundColor Yellow
if (-not (Test-Path "venv")) {
    python -m venv venv
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ Virtual environment created`n" -ForegroundColor Green
    } else {
        Write-Host "❌ Failed to create virtual environment" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "✓ Virtual environment already exists`n" -ForegroundColor Green
}

# Activate virtual environment
Write-Host "Activating virtual environment..." -ForegroundColor Yellow
& .\venv\Scripts\Activate.ps1
if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Virtual environment activated`n" -ForegroundColor Green
} else {
    Write-Host "⚠️  Could not activate virtual environment automatically" -ForegroundColor Yellow
    Write-Host "   Please run: .\venv\Scripts\Activate.ps1`n" -ForegroundColor Yellow
}

# Install dependencies
Write-Host "Installing dependencies in virtual environment..." -ForegroundColor Yellow
Write-Host "   (Note: Microsoft Agent Framework is in beta - this may take a moment)`n" -ForegroundColor Gray
python -m pip install --upgrade pip
pip install -r requirements.txt

if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Dependencies installed`n" -ForegroundColor Green
} else {
    Write-Host "❌ Failed to install dependencies" -ForegroundColor Red
    Write-Host "`n⚠️  Troubleshooting tips:" -ForegroundColor Yellow
    Write-Host "   1. Microsoft Agent Framework is currently in beta" -ForegroundColor Gray
    Write-Host "   2. Try installing manually:" -ForegroundColor Gray
    Write-Host "      pip install agent-framework agent-framework-azure --pre" -ForegroundColor Cyan
    Write-Host "   3. Or install specific beta version:" -ForegroundColor Gray
    Write-Host "      pip install agent-framework==1.0.0b251001 agent-framework-azure==1.0.0b251001" -ForegroundColor Cyan
    Write-Host "`n   4. If packages aren't available, check:" -ForegroundColor Gray
    Write-Host "      https://pypi.org/project/agent-framework/#history`n" -ForegroundColor Cyan
    exit 1
}

# Check Azure CLI
Write-Host "Checking Azure CLI..." -ForegroundColor Yellow
$azVersion = az version 2>&1 | ConvertFrom-Json
if ($azVersion) {
    Write-Host "✓ Azure CLI found`n" -ForegroundColor Green
} else {
    Write-Host "⚠️  Azure CLI not found. Install from: https://aka.ms/azure-cli" -ForegroundColor Yellow
    Write-Host "   You can still use this example with API key authentication`n"
}

# Check Azure login status
Write-Host "Checking Azure login status..." -ForegroundColor Yellow
$azAccount = az account show 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Azure CLI authenticated`n" -ForegroundColor Green
} else {
    Write-Host "⚠️  Not logged in to Azure. Run: az login" -ForegroundColor Yellow
    Write-Host "   Or set AZURE_OPENAI_API_KEY environment variable`n"
}

# Initialize Dakora
Write-Host "Initializing Dakora..." -ForegroundColor Yellow
if (-not (Test-Path "dakora.yaml")) {
    dakora init
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ Dakora initialized`n" -ForegroundColor Green
    } else {
        Write-Host "⚠️  Could not initialize Dakora automatically" -ForegroundColor Yellow
        Write-Host "   The examples will still work (they auto-create templates)`n" -ForegroundColor Gray
    }
} else {
    Write-Host "✓ Dakora already initialized`n" -ForegroundColor Green
}

# Check environment variables
Write-Host "Checking environment configuration..." -ForegroundColor Yellow

# Check if .env.example exists and .env doesn't
if ((Test-Path ".env.example") -and (-not (Test-Path ".env"))) {
    Write-Host "📋 Found .env.example but no .env file" -ForegroundColor Yellow
    Write-Host "   Creating .env from template...`n" -ForegroundColor Yellow
    Copy-Item ".env.example" ".env"
    Write-Host "✓ Created .env file - please edit it with your Azure credentials!`n" -ForegroundColor Green
    Write-Host "⚠️  IMPORTANT: Edit .env and set your AZURE_OPENAI_ENDPOINT`n" -ForegroundColor Yellow
}

$hasAzureOpenAI = [bool]$env:AZURE_OPENAI_ENDPOINT
$hasAzureAI = [bool]$env:AZURE_AI_PROJECT_ENDPOINT

if ($hasAzureOpenAI -or $hasAzureAI) {
    Write-Host "✓ Azure endpoint configured`n" -ForegroundColor Green
    if ($hasAzureOpenAI) {
        Write-Host "   AZURE_OPENAI_ENDPOINT: $env:AZURE_OPENAI_ENDPOINT`n" -ForegroundColor Gray
    }
    if ($hasAzureAI) {
        Write-Host "   AZURE_AI_PROJECT_ENDPOINT: $env:AZURE_AI_PROJECT_ENDPOINT`n" -ForegroundColor Gray
    }
} else {
    Write-Host "⚠️  No Azure endpoints configured" -ForegroundColor Yellow
    Write-Host "   You have two options:`n" -ForegroundColor Yellow
    
    Write-Host "   Option 1: Edit .env file (recommended):" -ForegroundColor Cyan
    Write-Host "   - Open .env in your editor" -ForegroundColor Gray
    Write-Host "   - Set AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com`n" -ForegroundColor Gray
    
    Write-Host "   Option 2: Set environment variable directly:" -ForegroundColor Cyan
    Write-Host "   `$env:AZURE_OPENAI_ENDPOINT='https://your-resource.openai.azure.com'`n" -ForegroundColor Gray
}

# Summary
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "Setup Complete!" -ForegroundColor Green
Write-Host "============================================`n" -ForegroundColor Cyan

Write-Host "⚡ Your virtual environment is ready!" -ForegroundColor Green
Write-Host "   Location: .\venv`n" -ForegroundColor Gray

Write-Host "Next steps:" -ForegroundColor Yellow

Write-Host "1. Activate the virtual environment (if not already active):" -ForegroundColor White
Write-Host "   .\venv\Scripts\Activate.ps1`n" -ForegroundColor Gray

Write-Host "2. Configure Azure credentials:" -ForegroundColor White
Write-Host "   a) Edit .env file with your Azure OpenAI endpoint:" -ForegroundColor Gray
Write-Host "      AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com`n" -ForegroundColor Gray
Write-Host "   b) Login to Azure CLI (for authentication):" -ForegroundColor Gray
Write-Host "      az login`n" -ForegroundColor Gray

Write-Host "3. Run the simple example:" -ForegroundColor White
Write-Host "   python simple_agent_example.py`n" -ForegroundColor Gray

Write-Host "4. Or run the multi-agent example:" -ForegroundColor White
Write-Host "   python multi_agent_example.py`n" -ForegroundColor Gray

Write-Host "5. Explore and edit templates with Dakora Playground:" -ForegroundColor White
Write-Host "   dakora playground`n" -ForegroundColor Gray

Write-Host "6. When done, deactivate the virtual environment:" -ForegroundColor White
Write-Host "   deactivate`n" -ForegroundColor Gray

Write-Host "💡 Tip: The virtual environment keeps dependencies isolated from your system Python." -ForegroundColor Cyan
Write-Host "   This is best practice for Python projects!`n" -ForegroundColor Cyan

Write-Host "For help, see README.md or visit:" -ForegroundColor Yellow
Write-Host "https://github.com/bogdan-pistol/dakora`n" -ForegroundColor Cyan
