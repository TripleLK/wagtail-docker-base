#!/usr/bin/env python3
"""
PostgreSQL Setup Script

This script:
1. Switches to production environment
2. Verifies PostgreSQL is running
3. Runs migrations to set up the database schema
4. Creates a superuser account

Usage:
    python tmp/setup_postgres.py
"""

import os
import sys
import subprocess
import getpass
from pathlib import Path

# Set up base directory
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

def check_postgres():
    """Check if PostgreSQL is running and accessible"""
    print("Checking PostgreSQL connection...")
    result = subprocess.run(['pg_isready', '-h', 'localhost', '-p', '5432'], 
                           capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"ERROR: PostgreSQL is not running. Please start PostgreSQL first.")
        print(f"Try running: brew services start postgresql")
        return False
    
    print("PostgreSQL is running and accepting connections")
    return True

def switch_environment():
    """Switch to production environment"""
    print("Switching to production environment...")
    script_path = str(BASE_DIR / "tmp" / "switch_env.py")
    result = subprocess.run(['python', script_path, 'prod'], 
                           capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"Failed to switch environment: {result.stderr}")
        return False
    
    print("Successfully switched to production environment")
    return True

def run_migrations():
    """Run Django migrations to set up database schema"""
    print("Setting up database schema...")
    
    # Set Django settings
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.production')
    
    # Import Django and set it up
    import django
    django.setup()
    
    # Check that we're using PostgreSQL
    from django.conf import settings
    db_engine = settings.DATABASES['default']['ENGINE']
    print(f"Using database engine: {db_engine}")
    
    if 'postgresql' not in db_engine:
        print("ERROR: Not using PostgreSQL database! Check your environment settings.")
        return False
    
    # Run migrations
    from django.core.management import call_command
    call_command('migrate')
    
    print("Database schema setup completed")
    return True

def create_superuser():
    """Create a superuser account"""
    print("\nCreating superuser account")
    print("==========================")
    
    # Set Django settings
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.production')
    
    # Import Django and set it up
    import django
    django.setup()
    
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    # Check if we already have any superusers
    if User.objects.filter(is_superuser=True).exists():
        print("Superuser(s) already exist:")
        for user in User.objects.filter(is_superuser=True):
            print(f"  - {user.username}")
        
        create_another = input("Create another superuser? (y/n): ").lower().strip()
        if create_another != 'y':
            return True
    
    # Get username
    username = input("Username: ").strip()
    while not username:
        print("Username cannot be empty.")
        username = input("Username: ").strip()
    
    # Get email
    email = input("Email: ").strip()
    
    # Get password
    password = getpass.getpass("Password: ")
    password_confirm = getpass.getpass("Password (again): ")
    
    while password != password_confirm or not password:
        print("Passwords don't match or are empty. Please try again.")
        password = getpass.getpass("Password: ")
        password_confirm = getpass.getpass("Password (again): ")
    
    # Create the superuser
    try:
        User.objects.create_superuser(username=username, email=email, password=password)
        print(f"Superuser '{username}' created successfully!")
        return True
    except Exception as e:
        print(f"Error creating superuser: {str(e)}")
        return False

def main():
    """Main function to run the setup process"""
    print("PostgreSQL Setup Script")
    print("======================\n")
    
    # Check if PostgreSQL is running
    if not check_postgres():
        return False
    
    # Switch to production environment
    if not switch_environment():
        return False
    
    # Run migrations
    if not run_migrations():
        return False
    
    # Create superuser
    if not create_superuser():
        return False
    
    print("\nSetup completed successfully!")
    print("You can now run the application with:")
    print("  python manage.py runserver")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 