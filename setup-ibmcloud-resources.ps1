# Helios IBM Cloud Resource Setup Script
# This script creates and configures all required IBM Cloud resources for the Helios MCP servers

$ErrorActionPreference = "Stop"
$ibmcloud = "C:\Program Files\IBM\Cloud\bin\ibmcloud.exe"

Write-Host "=== Helios IBM Cloud Setup ===" -ForegroundColor Cyan
Write-Host ""

# Check if logged in
Write-Host "Checking IBM Cloud login status..." -ForegroundColor Yellow
$target = & $ibmcloud target 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Not logged in to IBM Cloud. Please run: ibmcloud login" -ForegroundColor Red
    exit 1
}
Write-Host "✓ Logged in to IBM Cloud" -ForegroundColor Green
Write-Host ""

# Target Default resource group
Write-Host "Targeting Default resource group..." -ForegroundColor Yellow
& $ibmcloud target -g Default | Out-Null
Write-Host "✓ Resource group set to Default" -ForegroundColor Green
Write-Host ""

# 1. Check/Create Cloudant Instance
Write-Host "=== Cloudant Setup ===" -ForegroundColor Cyan
$cloudantInstances = & $ibmcloud resource service-instances --service-name cloudantnosqldb --output json | ConvertFrom-Json
$cloudantInstance = $cloudantInstances | Where-Object { $_.name -eq "watsonx-Hackathon Cloudant" }

if ($cloudantInstance) {
    Write-Host "✓ Cloudant instance 'watsonx-Hackathon Cloudant' already exists" -ForegroundColor Green
} else {
    Write-Host "Creating Cloudant Lite instance..." -ForegroundColor Yellow
    & $ibmcloud resource service-instance-create "helios-cloudant" cloudantnosqldb lite us-south
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ Cloudant instance created" -ForegroundColor Green
        $cloudantInstance = @{ name = "helios-cloudant" }
    } else {
        Write-Host "ERROR: Failed to create Cloudant instance" -ForegroundColor Red
        exit 1
    }
}

# Create Cloudant service key
Write-Host "Creating Cloudant service key..." -ForegroundColor Yellow
$cloudantKeyName = "helios-cloudant-key"
$existingKeys = & $ibmcloud resource service-keys --instance-name $cloudantInstance.name --output json 2>$null | ConvertFrom-Json
$keyExists = $existingKeys | Where-Object { $_.name -eq $cloudantKeyName }

if (-not $keyExists) {
    & $ibmcloud resource service-key-create $cloudantKeyName Manager --instance-name $cloudantInstance.name --output json | Out-Null
    Start-Sleep -Seconds 3
}

# Get Cloudant credentials
$cloudantKey = & $ibmcloud resource service-key $cloudantKeyName --instance-name $cloudantInstance.name --output json | ConvertFrom-Json
$cloudantUrl = $cloudantKey.credentials.url
$cloudantApiKey = $cloudantKey.credentials.apikey

Write-Host "✓ Cloudant URL: $cloudantUrl" -ForegroundColor Green
Write-Host "✓ Cloudant API Key: $($cloudantApiKey.Substring(0,10))..." -ForegroundColor Green
Write-Host ""

# 2. Check/Create watsonx.ai project
Write-Host "=== watsonx.ai Setup ===" -ForegroundColor Cyan
Write-Host "Note: watsonx.ai projects must be created via the web console" -ForegroundColor Yellow
Write-Host "Please ensure you have:" -ForegroundColor Yellow
Write-Host "  1. Created a watsonx.ai project at https://dataplatform.cloud.ibm.com/wx/home" -ForegroundColor Yellow
Write-Host "  2. Obtained the Project ID from project settings" -ForegroundColor Yellow
Write-Host "  3. Created an API key with watsonx access" -ForegroundColor Yellow
Write-Host ""

# Prompt for watsonx credentials
$watsonxProjectId = Read-Host "Enter your watsonx.ai Project ID (or press Enter to skip)"
if ([string]::IsNullOrWhiteSpace($watsonxProjectId)) {
    Write-Host "⚠ Skipping watsonx.ai configuration" -ForegroundColor Yellow
    $watsonxProjectId = ""
    $watsonxApiKey = ""
} else {
    $watsonxApiKey = Read-Host "Enter your watsonx.ai API Key"
    Write-Host "✓ watsonx.ai credentials provided" -ForegroundColor Green
}
Write-Host ""

# 3. Check/Create Code Engine project
Write-Host "=== Code Engine Setup ===" -ForegroundColor Cyan
Write-Host "Checking for Code Engine projects..." -ForegroundColor Yellow

# Install Code Engine plugin if not present
$plugins = & $ibmcloud plugin list
if ($plugins -notmatch "code-engine") {
    Write-Host "Installing Code Engine plugin..." -ForegroundColor Yellow
    & $ibmcloud plugin install code-engine -f
}

# List Code Engine projects
$ceProjects = & $ibmcloud ce project list --output json 2>$null | ConvertFrom-Json
$ceProject = $ceProjects | Where-Object { $_.name -eq "helios-ce" }

if ($ceProject) {
    Write-Host "✓ Code Engine project 'helios-ce' already exists" -ForegroundColor Green
    $ceProjectId = $ceProject.id
} else {
    Write-Host "Creating Code Engine project..." -ForegroundColor Yellow
    $createResult = & $ibmcloud ce project create --name helios-ce --output json 2>&1
    if ($LASTEXITCODE -eq 0) {
        $ceProject = $createResult | ConvertFrom-Json
        $ceProjectId = $ceProject.id
        Write-Host "✓ Code Engine project created: $ceProjectId" -ForegroundColor Green
    } else {
        Write-Host "⚠ Could not create Code Engine project (may require upgrade)" -ForegroundColor Yellow
        $ceProjectId = ""
    }
}
Write-Host ""

# 4. Update .env file
Write-Host "=== Updating .env file ===" -ForegroundColor Cyan
$envPath = Join-Path $PSScriptRoot ".env"

if (Test-Path $envPath) {
    $envContent = Get-Content $envPath -Raw
    
    # Update Cloudant credentials
    $envContent = $envContent -replace "CLOUDANT_URL=.*", "CLOUDANT_URL=$cloudantUrl"
    $envContent = $envContent -replace "CLOUDANT_APIKEY=.*", "CLOUDANT_APIKEY=$cloudantApiKey"
    
    # Update watsonx credentials if provided
    if (-not [string]::IsNullOrWhiteSpace($watsonxProjectId)) {
        $envContent = $envContent -replace "WATSONX_PROJECT_ID=.*", "WATSONX_PROJECT_ID=$watsonxProjectId"
        $envContent = $envContent -replace "WATSONX_APIKEY=.*", "WATSONX_APIKEY=$watsonxApiKey"
    }
    
    # Update Code Engine project ID if created
    if (-not [string]::IsNullOrWhiteSpace($ceProjectId)) {
        $envContent = $envContent -replace "CODE_ENGINE_PROJECT_ID=.*", "CODE_ENGINE_PROJECT_ID=$ceProjectId"
    }
    
    Set-Content -Path $envPath -Value $envContent -NoNewline
    Write-Host "✓ .env file updated" -ForegroundColor Green
} else {
    Write-Host "⚠ .env file not found at $envPath" -ForegroundColor Yellow
}
Write-Host ""

# 5. Create helios_* databases in Cloudant
Write-Host "=== Creating Cloudant Databases ===" -ForegroundColor Cyan
$databases = @("helios_regions", "helios_audit", "helios_findings", "helios_queue")

foreach ($db in $databases) {
    Write-Host "Creating database: $db..." -ForegroundColor Yellow
    $createDb = Invoke-RestMethod -Uri "$cloudantUrl/$db" -Method Put -Headers @{
        "Authorization" = "Basic " + [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes("apikey:$cloudantApiKey"))
    } -ErrorAction SilentlyContinue
    
    if ($createDb.ok -eq $true) {
        Write-Host "✓ Database $db created" -ForegroundColor Green
    } else {
        Write-Host "⚠ Database $db may already exist" -ForegroundColor Yellow
    }
}
Write-Host ""

# Summary
Write-Host "=== Setup Complete ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "Cloudant:" -ForegroundColor Green
Write-Host "  URL: $cloudantUrl"
Write-Host "  API Key: $($cloudantApiKey.Substring(0,10))..."
Write-Host ""

if (-not [string]::IsNullOrWhiteSpace($watsonxProjectId)) {
    Write-Host "watsonx.ai:" -ForegroundColor Green
    Write-Host "  Project ID: $watsonxProjectId"
    Write-Host "  API Key: $($watsonxApiKey.Substring(0,10))..."
    Write-Host ""
}

if (-not [string]::IsNullOrWhiteSpace($ceProjectId)) {
    Write-Host "Code Engine:" -ForegroundColor Green
    Write-Host "  Project ID: $ceProjectId"
    Write-Host ""
}

Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Restart Bob IDE to load updated .env variables"
Write-Host "  2. Test MCP servers with: python -m [server].server --list-tools"
Write-Host "  3. Verify MCP servers appear in Bob MCP panel"
Write-Host ""

# Made with Bob
