#!/usr/bin/env python3
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.production')
import django
django.setup()

from django.conf import settings
from django.contrib.staticfiles.storage import staticfiles_storage

# Show basic settings
print(f"STATIC_URL: {settings.STATIC_URL}")
print(f"STATIC_ROOT: {settings.STATIC_ROOT}")
print(f"Storage class: {staticfiles_storage.__class__.__name__}")

# Try to find a specific file
print("\nTrying to find specific files:")
try:
    url1 = staticfiles_storage.url('css/base_site.css')
    print(f"URL for base_site.css: {url1}")
    
    url2 = staticfiles_storage.url('img/Triad_Logo_Red.svg')
    print(f"URL for Triad_Logo_Red.svg: {url2}")
    
    # Try to get the absolute path
    path1 = staticfiles_storage.path('css/base_site.css')
    print(f"Physical path: {path1}")
    print(f"File exists: {os.path.exists(path1)}")
except Exception as e:
    print(f"Error: {e}")

# Try to get the actual URLs that should be used in templates
print("\nActual URLs that should be used in templates:")
try:
    css_url = staticfiles_storage.url('css/base_site.css')
    img_url = staticfiles_storage.url('img/Triad_Logo_Red.svg')
    print(f"CSS URL: {css_url}")
    print(f"Image URL: {img_url}")
except Exception as e:
    print(f"Error: {e}")

# Check static file finders
from django.contrib.staticfiles import finders
print("\nStatic file finders:")
for finder in settings.STATICFILES_FINDERS:
    print(f"- {finder}")

# Try to find files with finders
print("\nFinding files with finders:")
try:
    css_path = finders.find('css/base_site.css')
    print(f"Found css/base_site.css at: {css_path}")
    
    img_path = finders.find('img/Triad_Logo_Red.svg')
    print(f"Found img/Triad_Logo_Red.svg at: {img_path}")
except Exception as e:
    print(f"Error using finders: {e}")

# Check manifest contents
print("\nManifest contents:")
try:
    if hasattr(staticfiles_storage, 'hashed_files'):
        print(f"Number of entries: {len(staticfiles_storage.hashed_files)}")
        for key in list(staticfiles_storage.hashed_files.keys())[:5]:
            print(f"  {key} -> {staticfiles_storage.hashed_files[key]}")
    else:
        print("No hashed_files attribute found")
except Exception as e:
    print(f"Error checking manifest: {e}")
