"""
WSGI config for ShadowIQ on Vercel.
This module is used by Vercel to serve the Django application.
"""

import os
import sys

# Add the project directory to the Python path
from pathlib import Path

# Set up settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'shadowiq.settings')

# Set Vercel environment variable if not already set
if 'VERCEL' not in os.environ:
    # Check if we're running in a Vercel-like environment
    if 'LAMBDA_TASK_ROOT' in os.environ or 'VERCEL_REGION' in os.environ:
        os.environ['VERCEL'] = '1'

# Setup Django
import django
django.setup()

# Import the Django WSGI handler
from django.core.wsgi import get_wsgi_application

# Get the WSGI application
application = get_wsgi_application()