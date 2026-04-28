#!/bin/bash
# Bash script to deploy ShadowIQ to Vercel
# Usage: ./scripts/deploy-vercel.sh [production|preview]

ENVIRONMENT=${1:-production}
SKIP_CHECKS=${2:-false}

echo "=== ShadowIQ Vercel Deployment Script ==="
echo "Target Environment: $ENVIRONMENT"

# Check prerequisites
if [ "$SKIP_CHECKS" != "true" ]; then
    echo ""
    echo "[1/5] Checking prerequisites..."
    
    # Check Python
    if ! command -v python &> /dev/null; then
        echo "ERROR: Python is not installed or not in PATH"
        exit 1
    fi
    echo "✓ Python found: $(python --version)"
    
    # Check Vercel CLI
    if ! command -v vercel &> /dev/null; then
        echo "ERROR: Vercel CLI is not installed. Install with: npm install -g vercel"
        exit 1
    fi
    echo "✓ Vercel CLI found: $(vercel --version)"
    
    # Check if logged in to Vercel
    echo ""
    echo "[2/5] Checking Vercel authentication..."
    VERCEL_USER=$(vercel whoami 2>/dev/null)
    if [ -z "$VERCEL_USER" ]; then
        echo "You are not logged in to Vercel. Logging in..."
        vercel login
        if [ $? -ne 0 ]; then
            echo "ERROR: Failed to login to Vercel"
            exit 1
        fi
    else
        echo "✓ Logged in as: $VERCEL_USER"
    fi
fi

# Check if project is linked
echo ""
echo "[3/5] Checking Vercel project link..."
if [ ! -d ".vercel" ]; then
    echo "Project is not linked to Vercel. Linking now..."
    vercel link
    if [ $? -ne 0 ]; then
        echo "ERROR: Failed to link project to Vercel"
        exit 1
    fi
else
    echo "✓ Project is linked to Vercel"
fi

# Collect static files
echo ""
echo "[4/5] Collecting static files..."
python manage.py collectstatic --noinput
if [ $? -ne 0 ]; then
    echo "WARNING: Failed to collect static files"
else
    echo "✓ Static files collected"
fi

# Deploy to Vercel
echo ""
echo "[5/5] Deploying to Vercel..."

if [ "$ENVIRONMENT" = "production" ]; then
    vercel --prod
else
    vercel
fi

if [ $? -eq 0 ]; then
    echo ""
    echo "✓ Deployment successful!"
    echo "Your application is now live on Vercel."
    echo ""
    echo "Next steps:"
    echo "1. Set environment variables in Vercel dashboard"
    echo "2. Run migrations: vercel env pull && python manage.py migrate"
    echo "3. Test your deployment"
else
    echo ""
    echo "✗ Deployment failed. Check the error messages above."
    exit 1
fi