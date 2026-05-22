# Vercel Deployment Guide for ShadowIQ

This guide explains how to deploy ShadowIQ to Vercel while maintaining your Neon database connection.

## Prerequisites

1. **Vercel Account**: Sign up at [vercel.com](https://vercel.com)
2. **Vercel CLI**: Install globally with `npm install -g vercel`
3. **Neon Database**: Already configured (keep your `DATABASE_URL`)
4. **Git Repository**: Your code should be in a Git repository

## Project Structure Updates

The following files have been added/modified for Vercel deployment:

### New Files:
- `vercel.json` - Vercel configuration
- `shadowiq/vercel_wsgi.py` - Vercel-specific WSGI handler

### Modified Files:
- `shadowiq/settings.py` - Added Vercel-specific configurations

## Deployment Steps

### 1. Prepare Your Environment Variables

In Vercel, you need to set these environment variables:

**Required Variables:**
```bash
DATABASE_URL=postgresql://USER:PASSWORD@HOST/DBNAME?sslmode=require
SECRET_KEY=your-django-secret-key
DEBUG=False
ALLOWED_HOSTS=your-domain.com,*.vercel.app
CSRF_TRUSTED_ORIGINS=https://your-domain.com,https://*.vercel.app
CLOUDINARY_CLOUD_NAME=your-cloudinary-cloud-name
CLOUDINARY_API_KEY=your-cloudinary-api-key
CLOUDINARY_API_SECRET=your-cloudinary-api-secret
```

Vercel has a read-only application filesystem, so uploaded media cannot be saved under
`MEDIA_ROOT`. Production uploads use Cloudinary; without the Cloudinary variables above,
the app will fail configuration instead of falling back to `/var/task/media`.

**Optional Variables (for payment processing):**
```bash
PAYPAL_CLIENT_ID=your-paypal-client-id
PAYPAL_CLIENT_SECRET=your-paypal-client-secret
PAYSTACK_PUBLIC_KEY=your-paystack-public-key
PAYSTACK_SECRET_KEY=your-paystack-secret-key
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
```

### 2. Set Environment Variables in Vercel

#### Option A: Using Vercel Dashboard
1. Go to your project in Vercel Dashboard
2. Navigate to **Settings** → **Environment Variables**
3. Add each variable for **Production**, **Preview**, and **Development** environments

#### Option B: Using Vercel CLI
```bash
# Login to Vercel
vercel login

# Link your project
vercel link

# Set environment variables
vercel env add DATABASE_URL production
vercel env add SECRET_KEY production
vercel env add DEBUG production
vercel env add ALLOWED_HOSTS production
vercel env add CSRF_TRUSTED_ORIGINS production
```

### 3. Deploy to Vercel

#### Initial Deployment:
```bash
# Navigate to your project directory
cd c:\Users\HomePC\shadow\shadowIQr

# Deploy to production
vercel --prod

# Or deploy to preview
vercel
```

#### Automated Deployments:
If your GitHub repository is connected to Vercel, every push to the main branch will automatically deploy.

### 4. Run Migrations

After the first deployment, you need to run Django migrations:

```bash
# Option 1: Using Vercel CLI (recommended)
vercel env pull  # Pull environment variables locally
python manage.py migrate

# Option 2: Using Vercel's deployment hooks (advanced)
# Create a file `.vercelignore` to exclude unnecessary files
# Set up a post-deploy script in vercel.json
```

### 5. Collect Static Files

Vercel will automatically collect static files during the build process. However, you can verify locally:

```bash
python manage.py collectstatic --noinput
```

## Configuration Details

### How Vercel Works with Django

1. **Serverless Functions**: Vercel runs your Django app in serverless functions
2. **Static Files**: WhiteNoise serves static files efficiently
3. **Database Connections**: Neon connection pooling handles serverless connections
4. **Environment Variables**: Automatically injected by Vercel

### Key Settings in `settings.py`

The settings have been updated to:
- Detect Vercel environment via `IS_VERCEL` flag
- Automatically add Vercel domains to `ALLOWED_HOSTS`
- Configure CSRF for Vercel URLs
- Enable SSL/HTTPS in production
- Disable persistent database connections (incompatible with serverless)

### vercel.json Configuration

```json
{
  "builds": [
    {
      "src": "shadowiq/vercel_wsgi.py",
      "use": "@vercel/python"
    }
  ],
  "routes": [
    {
      "src": "/static/(.*)",
      "dest": "/static/$1"
    },
    {
      "src": "/(.*)",
      "dest": "shadowiq/vercel_wsgi.py"
    }
  ]
}
```

## Testing Your Deployment

### 1. Check Deployment Status
```bash
vercel ls
```

### 2. View Logs
```bash
vercel logs <deployment-url>
```

### 3. Test Locally with Vercel Environment
```bash
vercel env pull  # Creates .env.local with Vercel variables
python manage.py runserver
```

### 4. Verify Functionality
- Visit your Vercel URL (e.g., `https://your-project.vercel.app`)
- Test user registration/login
- Create a project
- Test file uploads
- Verify payment integrations

## Troubleshooting

### Common Issues

#### 1. Database Connection Errors
**Problem**: "connection refused" or "SSL connection required"
**Solution**: Ensure your `DATABASE_URL` includes `?sslmode=require`

#### 2. Static Files Not Loading
**Problem**: 404 errors for static files
**Solution**: 
- Verify `collectstatic` ran successfully
- Check that WhiteNoise middleware is in `MIDDLEWARE` list

#### 3. CSRF Token Errors
**Problem**: "CSRF token missing or incorrect"
**Solution**: 
- Add your Vercel domain to `CSRF_TRUSTED_ORIGINS`
- Ensure `SECURE_PROXY_SSL_HEADER` is set correctly

#### 4. Allowed Hosts Error
**Problem**: "Invalid HTTP_HOST header"
**Solution**: 
- Add your Vercel domain to `ALLOWED_HOSTS`
- Include both `.vercel.app` and your custom domain if using one

#### 5. Serverless Timeout
**Problem**: Function execution timeout
**Solution**: 
- Optimize database queries
- Consider using Vercel's Premium plan for longer timeouts
- Implement background tasks with Celery for long-running operations

### Debug Mode

To debug issues, temporarily enable DEBUG:

```bash
vercel env add DEBUG True production
```

**⚠️ Important**: Disable DEBUG after troubleshooting!

## Custom Domain Setup

If you want to use a custom domain:

1. **In Vercel Dashboard**:
   - Go to **Project Settings** → **Domains**
   - Add your domain (e.g., `shadowiq.com`)

2. **Update Environment Variables**:
   ```bash
   vercel env add ALLOWED_HOSTS "shadowiq.com,www.shadowiq.com,*.vercel.app" production
   vercel env add CSRF_TRUSTED_ORIGINS "https://shadowiq.com,https://www.shadowiq.com" production
   ```

3. **Configure DNS**:
   - Follow Vercel's DNS configuration instructions
   - Typically involves adding CNAME or A records

## CI/CD with GitHub

For automatic deployments on every push:

1. **Connect GitHub Repository**:
   - In Vercel Dashboard, import your GitHub repository
   - Configure automatic deployments for main branch

2. **Set Environment Variables**:
   - Add all required environment variables in Vercel
   - They'll be available in all deployments

3. **Preview Deployments**:
   - Every pull request gets a preview URL
   - Test changes before merging to main

## Migration from Render

### Key Differences

| Aspect | Render | Vercel |
|--------|--------|--------|
| **Runtime** | Persistent server | Serverless functions |
| **Database Connections** | Persistent connections OK | Must close after each request |
| **Static Files** | Served by gunicorn/whitenoise | Served by CDN + whitenoise |
| **Environment** | Set in Render dashboard | Set in Vercel dashboard |
| **Deployment** | Git push or manual | Git push or Vercel CLI |

### What Changed

1. **Removed**: `Procfile`, `render.yaml` (no longer needed)
2. **Added**: `vercel.json`, `shadowiq/vercel_wsgi.py`
3. **Modified**: `settings.py` for serverless compatibility

### Rollback Plan

If you need to revert to Render:
1. Keep your `render.yaml` file in git (but commented out)
2. Your Neon database remains unchanged
3. Simply redeploy to Render using the original configuration

## Performance Optimization

### 1. Database Connection Pooling
Neon automatically handles connection pooling for serverless functions.

### 2. Static File Optimization
- WhiteNoise compresses and caches static files
- Vercel's CDN serves static assets globally

### 3. Caching Strategies
Consider adding caching headers in your views:
```python
from django.utils.cache import patch_cache_control

def my_view(request):
    response = render(request, 'template.html')
    patch_cache_control(response, max_age=3600)
    return response
```

## Monitoring and Logs

### Vercel Dashboard
- **Deployments**: View deployment history and status
- **Logs**: Real-time function logs
- **Analytics**: Traffic and performance metrics

### Vercel CLI
```bash
# View recent deployments
vercel ls

# View logs for specific deployment
vercel logs <deployment-url>

# Inspect deployment
vercel inspect <deployment-url>
```

## Next Steps

1. ✅ Deploy to Vercel
2. ✅ Set up custom domain (optional)
3. ✅ Configure CI/CD with GitHub
4. ✅ Set up monitoring and alerts
5. ✅ Optimize performance
6. ✅ Implement proper error tracking (e.g., Sentry)

## Support Resources

- [Vercel Documentation](https://vercel.com/docs)
- [Django on Vercel Guide](https://vercel.com/guides/deploying-django-on-vercel)
- [Neon Serverless Driver](https://neon.tech/docs/serverless/serverless-driver)
- [WhiteNoise Documentation](https://whitenoise.readthedocs.io/)

## Checklist

Before going live, verify:

- [ ] All environment variables are set in Vercel
- [ ] Database migrations have been run
- [ ] Static files are collecting properly
- [ ] Custom domain is configured (if using)
- [ ] HTTPS is enforced
- [ ] DEBUG is set to False
- [ ] Payment integrations are tested
- [ ] Email functionality works
- [ ] File uploads work correctly
- [ ] All critical user flows are tested

---

**Note**: Keep this documentation updated as your deployment evolves.
