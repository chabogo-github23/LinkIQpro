# PowerShell script to deploy ShadowIQ to Vercel
# Usage: .\scripts\deploy-vercel.ps1 [-Environment "production"]

param(
    [string]$Environment = "production",
    [switch]$SkipChecks = $false
)

Write-Host "=== ShadowIQ Vercel Deployment Script ===" -ForegroundColor Green
Write-Host "Target Environment: $Environment" -ForegroundColor Yellow

# Function to check if command exists
function Test-Command($name) {
    return $null -ne (Get-Command $name -ErrorAction SilentlyContinue)
}

# Check prerequisites
if (-not $SkipChecks) {
    Write-Host "`n[1/5] Checking prerequisites..." -ForegroundColor Cyan

    if (-not (Test-Command "python")) {
        Write-Host "ERROR: Python is not installed or not in PATH" -ForegroundColor Red
        exit 1
    }
    Write-Host "✓ Python found: $(python --version)" -ForegroundColor Green

    if (-not (Test-Command "vercel")) {
        Write-Host "ERROR: Vercel CLI is not installed. Install with: npm install -g vercel" -ForegroundColor Red
        exit 1
    }
    Write-Host "✓ Vercel CLI found: $(vercel --version)" -ForegroundColor Green

    Write-Host "`n[2/5] Checking Vercel authentication..." -ForegroundColor Cyan
    $vercelUser = vercel whoami 2>$null
    if (-not $vercelUser) {
        Write-Host "You are not logged in to Vercel. Logging in..." -ForegroundColor Yellow
        vercel login
        if ($LASTEXITCODE -ne 0) {
            Write-Host "ERROR: Failed to login to Vercel" -ForegroundColor Red
            exit 1
        }
    } else {
        Write-Host "✓ Logged in as: $vercelUser" -ForegroundColor Green
    }
}

# Check if project is linked
Write-Host "`n[3/5] Checking Vercel project link..." -ForegroundColor Cyan
if (-not (Test-Path ".vercel")) {
    Write-Host "Project is not linked to Vercel. Linking now..." -ForegroundColor Yellow
    vercel link
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Failed to link project to Vercel" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "✓ Project is linked to Vercel" -ForegroundColor Green
}

# Run database migrations
Write-Host "`n[4/5] Running database migrations..." -ForegroundColor Cyan
python manage.py migrate --noinput
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Failed to run migrations" -ForegroundColor Red
    exit 1
} else {
    Write-Host "✓ Database migrations applied" -ForegroundColor Green
}

# Collect static files
Write-Host "`n[5/5] Collecting static files..." -ForegroundColor Cyan
python manage.py collectstatic --noinput
if ($LASTEXITCODE -ne 0) {
    Write-Host "WARNING: Failed to collect static files" -ForegroundColor Yellow
} else {
    Write-Host "✓ Static files collected" -ForegroundColor Green
}

# Deploy to Vercel
Write-Host "`n[6/5] Deploying to Vercel..." -ForegroundColor Cyan

if ($Environment -eq "production") {
    vercel --prod
} else {
    vercel
}

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n✓ Deployment successful!" -ForegroundColor Green
    Write-Host "Your application is now live on Vercel." -ForegroundColor Cyan
    Write-Host "`nNext steps:" -ForegroundColor Yellow
    Write-Host "1. Set environment variables in Vercel dashboard" -ForegroundColor White
    Write-Host "2. Verify the database migrations completed successfully" -ForegroundColor White
    Write-Host "3. Test your deployment" -ForegroundColor White
} else {
    Write-Host "`n✗ Deployment failed. Check the error messages above." -ForegroundColor Red
    exit 1
}
