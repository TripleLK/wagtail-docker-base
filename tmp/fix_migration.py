#!/usr/bin/env python3
"""
Fix Migration Script

This script:
1. Temporarily disables foreign key triggers for specific tables
2. Runs migrations for those tables
3. Re-enables the triggers

Usage:
    python tmp/fix_migration.py
"""
import os
import sys
import time
import subprocess
from pathlib import Path

# Set up base directory
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

def setup_postgres():
    """Set up PostgreSQL connection"""
    # Set Django settings module
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.production')
    
    # Import Django and set it up
    import django
    django.setup()
    
    # Get connection details from Django settings
    from django.conf import settings
    db_settings = settings.DATABASES['default']
    
    # Return connection parameters
    return {
        'host': db_settings.get('HOST', 'localhost'),
        'port': db_settings.get('PORT', '5432'),
        'user': db_settings.get('USER', 'lucypatton'),
        'password': db_settings.get('PASSWORD', ''),
        'name': db_settings.get('NAME', 'triad_db')
    }

def execute_psql(command, db_params=None):
    """Execute a PostgreSQL command"""
    if db_params is None:
        db_params = setup_postgres()
    
    # Build psql command line
    cmd = ["psql"]
    
    if db_params['host']:
        cmd.extend(["-h", db_params['host']])
    
    if db_params['port']:
        cmd.extend(["-p", db_params['port']])
    
    if db_params['user']:
        cmd.extend(["-U", db_params['user']])
    
    # Add the database name and command
    cmd.extend(["-d", db_params['name'], "-c", command])
    
    # Run the command
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"PostgreSQL Error: {result.stderr}")
        return False
    
    return result.stdout.strip()

def disable_triggers(table_name):
    """Disable foreign key triggers for a table"""
    command = f'ALTER TABLE "{table_name}" DISABLE TRIGGER ALL;'
    result = execute_psql(command)
    if result is not False:
        print(f"Disabled triggers for {table_name}")
        return True
    return False

def enable_triggers(table_name):
    """Re-enable foreign key triggers for a table"""
    command = f'ALTER TABLE "{table_name}" ENABLE TRIGGER ALL;'
    result = execute_psql(command)
    if result is not False:
        print(f"Enabled triggers for {table_name}")
        return True
    return False

def migrate_specific_tables():
    """Migrate data for tables with circular dependencies"""
    # Tables that need special handling
    problem_tables = [
        "base_site_equipmentmodel",
        "base_site_equipmentmodelspecgroup",
        "base_site_labequipmentgalleryimage"
    ]
    
    # Disable triggers for all problem tables
    for table in problem_tables:
        disable_triggers(table)
    
    # Run the migration script for these tables
    tables_param = ",".join(problem_tables)
    migration_cmd = ["python", "tmp/migrate_direct.py", "--tables", tables_param]
    
    print(f"Running migration for tables: {tables_param}")
    subprocess.run(migration_cmd)
    
    # Re-enable triggers for all problem tables
    for table in problem_tables:
        enable_triggers(table)
    
    return True

def verify_counts():
    """Verify counts in specific tables"""
    problem_tables = [
        "base_site_equipmentmodel",
        "base_site_equipmentmodelspecgroup", 
        "base_site_labequipmentgalleryimage"
    ]
    
    for table in problem_tables:
        result = execute_psql(f'SELECT COUNT(*) FROM "{table}";')
        print(f"Table {table} count: {result}")

def main():
    """Main function"""
    print("Fix Migration Script")
    print("===================\n")
    
    # Switch to production environment
    switch_cmd = ["python", "tmp/switch_env.py", "prod"]
    subprocess.run(switch_cmd)
    
    # Set up PostgreSQL connection
    db_params = setup_postgres()
    print(f"Connected to PostgreSQL database: {db_params['name']}")
    
    # Migrate tables with special handling for circular dependencies
    print("\nMigrating tables with circular dependencies...")
    migrate_specific_tables()
    
    # Verify counts
    print("\nVerifying counts in problematic tables:")
    verify_counts()
    
    print("\nFix completed.")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 