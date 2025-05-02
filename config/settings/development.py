"""
Development settings for the project.
"""
import os
from .base import *

# Debug settings
DEBUG = True

# Database settings - using SQLite by default
DATABASES = {
    'default': {
        'ENGINE': os.getenv('DB_ENGINE', 'django.db.backends.sqlite3'),
        'NAME': os.path.join(BASE_DIR, os.getenv('DB_NAME', 'db.sqlite3')),
    }
}

# Email backend for development
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-dev-key-change-this-in-production')

# Allow all hosts in development
ALLOWED_HOSTS = ['*']

# CORS settings for development
CORS_ALLOW_ALL_ORIGINS = True

# Disable password validation in development
AUTH_PASSWORD_VALIDATORS = []

# Debug toolbar
try:
    import debug_toolbar
    INSTALLED_APPS += ['debug_toolbar']
    MIDDLEWARE += ['debug_toolbar.middleware.DebugToolbarMiddleware']
    INTERNAL_IPS = ['127.0.0.1']
except ImportError:
    pass
