# Setup Cloudant databases for Helios
$ErrorActionPreference = "Stop"

# Load credentials from .env
$envContent = Get-Content .env -Raw
$cloudantUrl = ($envContent | Select-String -Pattern 'CLOUDANT_URL=(.+)').Matches.Groups[1].Value.Trim()
$cloudantApiKey = ($envContent | Select-String -Pattern 'CLOUDANT_APIKEY=(.+)').Matches.Groups[1].Value.Trim()

Write-Host "=== Creating Cloudant Databases ===" -ForegroundColor Cyan
Write-Host "Cloudant URL: $cloudantUrl" -ForegroundColor Yellow

# Get IAM token
Write-Host ""
Write-Host "Getting IAM token..." -ForegroundColor Yellow
$iamBody = @{
    grant_type = "urn:ibm:params:oauth:grant-type:apikey"
    apikey = $cloudantApiKey
}
$iamResponse = Invoke-RestMethod -Uri "https://iam.cloud.ibm.com/identity/token" -Method Post -Body $iamBody -ContentType "application/x-www-form-urlencoded"
$token = $iamResponse.access_token
Write-Host "IAM token obtained" -ForegroundColor Green

# Create databases
$databases = @("helios_regions", "helios_audit", "helios_findings", "helios_queue")
$headers = @{
    "Authorization" = "Bearer $token"
    "Content-Type" = "application/json"
}

foreach ($db in $databases) {
    Write-Host ""
    Write-Host "Creating database: $db..." -ForegroundColor Yellow
    try {
        $result = Invoke-RestMethod -Uri "https://$cloudantUrl/$db" -Method Put -Headers $headers -ErrorAction Stop
        Write-Host "Database $db created successfully" -ForegroundColor Green
    }
    catch {
        if ($_.Exception.Response.StatusCode -eq 412) {
            Write-Host "Database $db already exists" -ForegroundColor Yellow
        }
        else {
            Write-Host "Error creating $db : $($_.Exception.Message)" -ForegroundColor Red
        }
    }
}

Write-Host ""
Write-Host "=== Database Setup Complete ===" -ForegroundColor Cyan

# Made with Bob
