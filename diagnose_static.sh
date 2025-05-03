#!/bin/bash
# Create a complete diagnostic file for static files issue
echo "== STATIC FILES DIAGNOSTIC REPORT ==" > static_diagnosis.txt
date >> static_diagnosis.txt
echo "" >> static_diagnosis.txt

echo "== ENVIRONMENT ==" >> static_diagnosis.txt
echo "Python version:" >> static_diagnosis.txt
python --version >> static_diagnosis.txt 2>&1
echo "Django version:" >> static_diagnosis.txt
python -c "import django; print(django.__version__)" >> static_diagnosis.txt 2>&1
echo "" >> static_diagnosis.txt

echo "== STATIC FILES CONFIGURATION ==" >> static_diagnosis.txt
python -c "
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.production')
import django
django.setup()
from django.conf import settings
print(f'DEBUG: {settings.DEBUG}')
print(f'STATIC_URL: {settings.STATIC_URL}')
print(f'STATIC_ROOT: {settings.STATIC_ROOT}')
print(f'STATICFILES_DIRS: {getattr(settings, \"STATICFILES_DIRS\", [])}')
print(f'STATICFILES_STORAGE: {settings.STATICFILES_STORAGE}')
print('\\nSTATICFILES_FINDERS:')
for finder in settings.STATICFILES_FINDERS:
    print(f'- {finder}')
" >> static_diagnosis.txt 2>&1
echo "" >> static_diagnosis.txt

echo "== STATIC FILES DIRECTORY ==" >> static_diagnosis.txt
echo "Is STATIC_ROOT a directory?" >> static_diagnosis.txt
ls -la static/ >> static_diagnosis.txt 2>&1
echo "Number of files in static:" >> static_diagnosis.txt
find static/ -type f | wc -l >> static_diagnosis.txt 2>&1
echo "Example static files:" >> static_diagnosis.txt
find static/css -type f | head -5 >> static_diagnosis.txt 2>&1
find static/img -type f | head -5 >> static_diagnosis.txt 2>&1
echo "" >> static_diagnosis.txt

echo "== MANIFEST FILE ==" >> static_diagnosis.txt
echo "Does staticfiles.json exist?" >> static_diagnosis.txt
ls -la static/staticfiles.json >> static_diagnosis.txt 2>&1
echo "Content sample (first 20 lines):" >> static_diagnosis.txt
head -20 static/staticfiles.json >> static_diagnosis.txt 2>&1
echo "" >> static_diagnosis.txt

echo "== URL CONFIGURATION ==" >> static_diagnosis.txt
echo "URL handlers for static files:" >> static_diagnosis.txt
python -c "
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.production')
import django
django.setup()
from django.urls import get_resolver
resolver = get_resolver()
for pattern in resolver.url_patterns:
    if 'static' in str(pattern):
        print(f'Pattern: {pattern}')
" >> static_diagnosis.txt 2>&1
echo "" >> static_diagnosis.txt

echo "== HTTP SERVER TEST ==" >> static_diagnosis.txt
echo "Testing direct HTTP access to static files:" >> static_diagnosis.txt
curl -I http://localhost:7000/static/css/base_site.css >> static_diagnosis.txt 2>&1
echo "" >> static_diagnosis.txt
curl -I http://localhost:7000/static/css/base_site.6292d75af286.css >> static_diagnosis.txt 2>&1
echo "" >> static_diagnosis.txt
curl -I http://localhost:7000/static/img/Triad_Logo_Red.svg >> static_diagnosis.txt 2>&1
echo "" >> static_diagnosis.txt
curl -I http://localhost:7000/static/img/Triad_Logo_Red.e3ba3c16078e.svg >> static_diagnosis.txt 2>&1
echo "" >> static_diagnosis.txt

echo "== TEMPLATE DEBUGGING ==" >> static_diagnosis.txt
echo "Setting up a test view to verify static files:" >> static_diagnosis.txt
mkdir -p /tmp/debug
cat > /tmp/debug/test_static.py << 'ENDPYTHON'
#!/usr/bin/env python3
import os
import sys
import http.server
import socketserver

# Create a simple HTML file with static references
with open('/tmp/debug/test.html', 'w') as f:
    f.write('''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Static Files Test</title>
        <link rel="stylesheet" href="/static/css/base_site.css">
    </head>
    <body>
        <h1>Testing Static Files</h1>
        <p>This page tests various static file references</p>
        <img src="/static/img/Triad_Logo_Red.svg" alt="Logo" width="200">
        <img src="/static/img/Triad_Logo_Red.e3ba3c16078e.svg" alt="Logo Hashed" width="200">
        
        <h2>Network Requests</h2>
        <pre id="results"></pre>
        
        <script>
        // Check if files can be loaded
        async function checkFile(url) {
            try {
                const response = await fetch(url);
                return {
                    url: url,
                    status: response.status,
                    ok: response.ok
                };
            } catch (e) {
                return {
                    url: url,
                    error: e.message
                };
            }
        }
        
        // Test all static files
        async function runTests() {
            const results = document.getElementById('results');
            results.textContent = 'Running tests...';
            
            const files = [
                '/static/css/base_site.css',
                '/static/css/base_site.6292d75af286.css',
                '/static/img/Triad_Logo_Red.svg',
                '/static/img/Triad_Logo_Red.e3ba3c16078e.svg'
            ];
            
            const results_text = [];
            for (const file of files) {
                const result = await checkFile(file);
                results_text.push(JSON.stringify(result));
            }
            
            results.textContent = results_text.join('\\n');
        }
        
        // Run tests when page loads
        window.onload = runTests;
        </script>
    </body>
    </html>
    ''')

# Start a simple HTTP server
PORT = 8765
Handler = http.server.SimpleHTTPRequestHandler

class StaticHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory='/home/ec2-user/test/triad-docker-base', **kwargs)
    
    def log_message(self, format, *args):
        # Suppress log messages
        pass

print(f"Starting test server at http://localhost:{PORT}")
print(f"Open http://localhost:{PORT}/tmp/debug/test.html in your browser")
with socketserver.TCPServer(("", PORT), StaticHandler) as httpd:
    httpd.serve_forever()
ENDPYTHON

chmod +x /tmp/debug/test_static.py
echo "Created test script at /tmp/debug/test_static.py" >> static_diagnosis.txt
echo "Run with: python /tmp/debug/test_static.py" >> static_diagnosis.txt
echo "" >> static_diagnosis.txt

echo "== FINAL NOTES ==" >> static_diagnosis.txt
echo "Diagnosis completed. Please run:" >> static_diagnosis.txt
echo "1. python /tmp/debug/test_static.py" >> static_diagnosis.txt
echo "2. Access http://localhost:8765/tmp/debug/test.html in your browser" >> static_diagnosis.txt
echo "3. Check the results on the page" >> static_diagnosis.txt
echo "" >> static_diagnosis.txt

echo "Diagnostic report saved to static_diagnosis.txt"
