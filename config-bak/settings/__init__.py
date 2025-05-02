import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
env_path = Path(__file__).resolve().parent.parent.parent / '.env'
load_dotenv(env_path)

# Import appropriate settings based on environment
django_env = os.getenv('DJANGO_ENV', 'development')

if django_env == 'production':
    from .production import *
else:
    from .development import *
