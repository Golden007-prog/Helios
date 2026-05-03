# Helios IBM Cloud Resource Setup Script - Simplified
$ErrorActionPreference = "Stop"
$ibmcloud = "C:\Program Files\IBM\Cloud\bin\ibmcloud.exe"

Write-Host "=== Helios IBM Cloud Setup ===" -ForegroundColor Cyan

# Target Default resource group
& $ibmcloud target -g Default | Out-Null

# Get Cloudant credentials
Write-Host "Getting Cloudant credentials..." -ForegroundColor Yellow
$cloudantInstance = "watsonx-Hackathon Cloudant"

# Check if service key exists
$keys = & $ibmcloud resource service-keys --instance-name $cloudantInstance --output json 2>$null
if ($keys) {
    $keysJson = $keys | ConvertFrom-Json
    if ($keysJson.Count -eq 0) {
        Write-Host "Creating service key..." -ForegroundColor Yellow
        & $ibmcloud resource service-key-create helios-cloudant-key Manager --instance-name $cloudantInstance | Out-Null
        Start-Sleep -Seconds 5
    }
}

# Get the key details
$keyDetails = & $ibmcloud resource service-key helios-cloudant-key --instance-name $cloudantInstance --output json | ConvertFrom-Json
$cloudantUrl = $keyDetails.credentials.url
$cloudantApiKey = $keyDetails.credentials.apikey

Write-Host "Cloudant URL: $cloudantUrl" -ForegroundColor Green
Write-Host "Cloudant API Key: $($cloudantApiKey.Substring(0,10))..." -ForegroundColor Green

# Update .env file
Write-Host "`nUpdating .env file..." -ForegroundColor Yellow
$envPath = ".env"
$envContent = Get-Content $envPath -Raw

$envContent = $envContent -replace "CLOUDANT_URL=.*", "CLOUDANT_URL=$cloudantUrl"
$envContent = $envContent -replace "CLOUDANT_APIKEY=.*", "CLOUDANT_APIKEY=$cloudantApiKey"

Set-Content -Path $envPath -Value $envContent -NoNewline
Write-Host ".env file updated" -ForegroundColor Green

# Create Cloudant databases
Write-Host "`nCreating Cloudant databases..." -ForegroundColor Yellow
$databases = @("helios_regions", "helios_audit", "helios_findings", "helios_queue")
$auth = "Basic " + [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes("apikey:$cloudantApiKey"))

foreach ($db in $databases) {
    try {
        $result = Invoke-RestMethod -Uri "$cloudantUrl/$db" -Method Put -Headers @{ "Authorization" = $auth } -ErrorAction Stop
        Write-Host "Created database: $db" -ForegroundColor Green
    } catch {
        if ($_.Exception.Response.StatusCode -eq 412) {
            Write-Host "Database $db already exists" -ForegroundColor Yellow
        } else {
            Write-Host "Error creating $db : $_" -ForegroundColor Red
        }
    }
}

Write-Host "`n=== Setup Complete ===" -ForegroundColor Cyan
Write-Host "Cloudant is configured and ready to use" -ForegroundColor Green
Write-Host "`nNext: Configure watsonx.ai manually:" -ForegroundColor Yellow
Write-Host "1. Go to https://dataplatform.cloud.ibm.com/wx/home" -ForegroundColor Yellow
Write-Host "2. Create a project and get the Project ID" -ForegroundColor Yellow
Write-Host "3. Update WATSONX_PROJECT_ID and WATSONX_APIKEY in .env" -ForegroundColor Yellow

# Made with Bob
