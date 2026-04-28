import os
from dotenv import load_dotenv
from pathlib import Path
from urllib.parse import urlparse, parse_qs

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent


def get_list_env(name, default=''):
    value = os.environ.get(name, default)
    return [item.strip() for item in value.split(',') if item.strip()]

SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-dev-key-change-in-production')

DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'

ALLOWED_HOSTS = get_list_env('ALLOWED_HOSTS', 'localhost,127.0.0.1')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Domain Apps (SDLC/SOLID structured)
    'apps.users',
    'apps.projects',
    'apps.payments',
    'apps.messaging',
    'apps.audit',
    'apps.negotiations',
    
    # Legacy core app (for backward compatibility during migration)
    'core',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'core.middleware.PseudonymousAuthMiddleware',
]

ROOT_URLCONF = 'shadowiq.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            os.path.join(BASE_DIR, 'templates'),
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'core.context_processors.chat_users',
            ],
        },
    },
]

WSGI_APPLICATION = 'shadowiq.wsgi.application'

database_url = os.environ.get('DATABASE_URL', '').strip()
use_sqlite_local = os.environ.get('USE_SQLITE_LOCAL', 'False').lower() == 'true'

if database_url and not use_sqlite_local:
    parsed_db = urlparse(database_url)
    query_params = parse_qs(parsed_db.query)

    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': parsed_db.path.lstrip('/'),
            'USER': parsed_db.username,
            'PASSWORD': parsed_db.password,
            'HOST': parsed_db.hostname,
            'PORT': parsed_db.port or 5432,
            'OPTIONS': {
                'sslmode': query_params.get('sslmode', ['require'])[0],
            },
            'CONN_MAX_AGE': int(os.environ.get('DB_CONN_MAX_AGE', 600)),
            'CONN_HEALTH_CHECKS': True,
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }


AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Session configuration
SESSION_ENGINE = 'django.contrib.sessions.backends.db'
SESSION_COOKIE_AGE = 86400 * 7  # 7 days
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'

# Email settings for password reset
EMAIL_BACKEND = os.environ.get('EMAIL_BACKEND', 'django.core.mail.backends.console.EmailBackend')
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', 587))
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'True') == 'True'
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')


# ShadowIQ specific settings
PROJECT_ID_PREFIX = 'SIQ'
MAX_FILE_UPLOAD_SIZE = 500 * 1024 * 1024  # 500 MB
DATA_RETENTION_DAYS = 180

# AWS S3 Configuration
AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID', '')
AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY', '')
AWS_STORAGE_BUCKET_NAME = os.environ.get('AWS_STORAGE_BUCKET_NAME', '')
AWS_S3_REGION_NAME = os.environ.get('AWS_S3_REGION_NAME', 'us-east-1')
AWS_S3_CUSTOM_DOMAIN = os.environ.get('AWS_S3_CUSTOM_DOMAIN', '')

PAYPAL_CLIENT_ID = os.getenv("PAYPAL_CLIENT_ID", "")
PAYPAL_CLIENT_SECRET = os.getenv("PAYPAL_SECRET", "")
PAYPAL_SECRET = os.getenv("PAYPAL_SECRET", "")  
PAYPAL_MODE = os.getenv("PAYPAL_MODE", "sandbox")
#PAYPAL_BASE_URL = "https://api-m.sandbox.paypal.com" if PAYPAL_MODE == "sandbox" else "https://api-m.paypal.com"
PAYPAL_BASE_URL = "https://api-m.paypal.com"


# Paystack API keys
PAYSTACK_PUBLIC_KEY = os.getenv("PAYSTACK_PUBLIC_KEY", "")
PAYSTACK_SECRET_KEY = os.getenv("PAYSTACK_SECRET_KEY", "")
PAYSTACK_MODE = os.getenv("PAYSTACK_MODE")

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
}

SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "SAMEORIGIN"

CSRF_TRUSTED_ORIGINS = get_list_env(
    'CSRF_TRUSTED_ORIGINS',
    'https://*.ngrok-free.app',
)

# Vercel/Serverless configuration
IS_VERCEL = os.environ.get('VERCEL', 'False').lower() == 'true'

if IS_VERCEL:
    # Allow Vercel domains
    ALLOWED_HOSTS = get_list_env('ALLOWED_HOSTS', 'localhost,127.0.0.1')
    allowed_host = os.environ.get('VERCEL_BRANCH_URL', '')
    if allowed_host:
        ALLOWED_HOSTS.append(allowed_host)
    allowed_host = os.environ.get('VERCEL_URL', '')
    if allowed_host:
        ALLOWED_HOSTS.append(allowed_host)
    
    # CSRF trusted origins for Vercel
    CSRF_TRUSTED_ORIGINS = get_list_env('CSRF_TRUSTED_ORIGINS', 'https://*.ngrok-free.app')
    vercel_url = os.environ.get('VERCEL_URL', '')
    if vercel_url:
        CSRF_TRUSTED_ORIGINS.append(f'https://{vercel_url}')
    vercel_branch_url = os.environ.get('VERCEL_BRANCH_URL', '')
    if vercel_branch_url:
        CSRF_TRUSTED_ORIGINS.append(f'https://{vercel_branch_url}')
    
    # Security settings for production behind Vercel's HTTPS
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    
    # Disable persistent database connections for serverless
    if 'default' in DATABASES:
        DATABASES['default']['CONN_MAX_AGE'] = 0
        if 'OPTIONS' not in DATABASES['default']:
            DATABASES['default']['OPTIONS'] = {}
        DATABASES['default']['OPTIONS']['sslmode'] = 'require'

# Default Security Settings (Handled by environment)
if not DEBUG and not IS_VERCEL:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
else:
    SECURE_SSL_REDIRECT = False
    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SECURE = False
