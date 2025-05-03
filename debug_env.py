import os
from pathlib import Path
from dotenv import load_dotenv

# Print current directory
print(f"Current directory: {os.getcwd()}")

# Print .env path
env_path = Path('.env').resolve()
print(f".env path: {env_path}")
print(f"Is symlink: {os.path.islink('.env')}")
if os.path.islink('.env'):
    print(f"Symlink target: {os.readlink('.env')}")

# Try to load .env
load_dotenv(env_path)

# Print loaded value
print(f"DJANGO_ENV: {os.getenv('DJANGO_ENV', 'not set')}")
print(f"DJANGO_SETTINGS_MODULE: {os.getenv('DJANGO_SETTINGS_MODULE', 'not set')}")

# Print all environment variables
print("\nAll environment variables:")
for key, value in os.environ.items():
    if "DJANGO" in key or "DB_" in key:
        print(f"{key}: {value}") 