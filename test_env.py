#!/usr/bin/env python3
"""
Test script to verify Django environment and database settings.
Run this on EC2 to check if the environment variables are loaded correctly.
"""
import os
import sys
from pathlib import Path

# Show current environment
print(f"Current environment variables:")
print(f"DJANGO_ENV: {os.environ.get('DJANGO_ENV', 'not set')}")
print(f"DJANGO_SETTINGS_MODULE: {os.environ.get('DJANGO_SETTINGS_MODULE', 'not set')}")

# Load environment from .env file
print("\nLoading environment from .env file:")
env_path = Path('.env').resolve()
print(f"Reading from: {env_path}")
print(f"Is symlink: {os.path.islink('.env')}")
if os.path.islink('.env'):
    print(f"Symlink target: {os.readlink('.env')}")
    
    # Read the content of the .env file
    with open(env_path, 'r') as f:
        print("\nContents of .env file:")
        for line in f:
            if line.strip() and not line.startswith('#'):
                print(f"  {line.strip()}")

# Initialize Django and check settings
print("\nInitializing Django and checking settings:")
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from django.conf import settings

print(f"\nActive Django settings:")
print(f"DEBUG: {settings.DEBUG}")
print(f"STATIC_URL: {settings.STATIC_URL}")
print(f"STATIC_ROOT: {settings.STATIC_ROOT}")
print(f"STATICFILES_STORAGE: {settings.STATICFILES_STORAGE}")

# Check database configuration
print("\nDatabase configuration:")
print(f"ENGINE: {settings.DATABASES['default']['ENGINE']}")
print(f"NAME: {settings.DATABASES['default']['NAME']}")
print(f"USER: {settings.DATABASES['default']['USER']}")
print(f"HOST: {settings.DATABASES['default']['HOST']}")

# Test database connection
print("\nTesting database connection:")
try:
    from django.db import connection
    with connection.cursor() as cursor:
        if 'sqlite' in connection.vendor:
            cursor.execute("SELECT sqlite_version();")
            version = cursor.fetchone()[0]
            print(f"SQLite version: {version}")
            print(f"Database path: {connection.settings_dict['NAME']}")
        elif 'postgresql' in connection.vendor:
            cursor.execute("SELECT version();")
            version = cursor.fetchone()[0]
            print(f"PostgreSQL version: {version}")
            cursor.execute("SELECT current_database();")
            dbname = cursor.fetchone()[0]
            print(f"Connected to database: {dbname}")
        else:
            print(f"Unknown database vendor: {connection.vendor}")
    print("✓ Database connection successful")
except Exception as e:
    print(f"✗ Database connection failed: {e}")

# Report success
print("\nEnvironment testing complete.")