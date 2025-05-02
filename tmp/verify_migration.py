#!/usr/bin/env python3
"""
Migration Verification Script

This script:
1. Connects to both SQLite and PostgreSQL databases
2. Counts records in key tables
3. Reports any discrepancies

Usage:
    python tmp/verify_migration.py
"""
import os
import sys
import sqlite3
import subprocess
from pathlib import Path
from tabulate import tabulate

# Set up base directory
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

def switch_environment(env_type):
    """Switch to the specified environment"""
    script_path = str(BASE_DIR / "tmp" / "switch_env.py")
    result = subprocess.run(['python', script_path, env_type], 
                            capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"Error switching environment: {result.stderr}")
        return False
    
    print(f"Switched to {env_type} environment")
    return True

def get_sqlite_counts():
    """Get record counts from SQLite database"""
    # Switch to dev environment to use SQLite
    if not switch_environment('dev'):
        return None
    
    # Connect to SQLite
    sqlite_path = BASE_DIR / 'db.sqlite3'
    if not sqlite_path.exists():
        print(f"Error: SQLite database not found at {sqlite_path}")
        return None
    
    conn = sqlite3.connect(str(sqlite_path))
    cursor = conn.cursor()
    
    # Get list of tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
    tables = [row[0] for row in cursor.fetchall()]
    
    # Count records in each table
    counts = {}
    for table in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table};")
        count = cursor.fetchone()[0]
        counts[table] = count
    
    conn.close()
    return counts

def get_postgresql_counts():
    """Get record counts from PostgreSQL database"""
    # Switch to production environment to use PostgreSQL
    if not switch_environment('prod'):
        return None
    
    # Set Django settings
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.production')
    
    # Import Django and set it up
    import django
    django.setup()
    
    # Verify we're using PostgreSQL
    from django.conf import settings
    db_engine = settings.DATABASES['default']['ENGINE']
    if 'postgresql' not in db_engine:
        print(f"Error: Not using PostgreSQL! Current engine: {db_engine}")
        return None
    
    # Connect to PostgreSQL via Django
    from django.db import connection
    cursor = connection.cursor()
    
    # Get list of tables (excluding schema-related tables)
    cursor.execute("""
        SELECT tablename FROM pg_catalog.pg_tables 
        WHERE schemaname = 'public';
    """)
    tables = [row[0] for row in cursor.fetchall()]
    
    # Count records in each table
    counts = {}
    for table in tables:
        cursor.execute(f'SELECT COUNT(*) FROM "{table}";')
        count = cursor.fetchone()[0]
        counts[table] = count
    
    return counts

def compare_counts(sqlite_counts, pg_counts):
    """Compare record counts between SQLite and PostgreSQL"""
    # Get all unique table names
    all_tables = set(list(sqlite_counts.keys()) + list(pg_counts.keys()))
    
    # Build comparison results
    comparison = []
    
    for table in sorted(all_tables):
        sqlite_count = sqlite_counts.get(table, 0)
        pg_count = pg_counts.get(table, 0)
        status = "✅" if sqlite_count == pg_count else "❌"
        comparison.append([table, sqlite_count, pg_count, status])
    
    # Calculate totals
    sqlite_total = sum(sqlite_counts.values())
    pg_total = sum(pg_counts.values())
    comparison.append(["TOTAL", sqlite_total, pg_total, "✅" if sqlite_total == pg_total else "❌"])
    
    return comparison

def main():
    """Main function"""
    print("Migration Verification")
    print("=====================\n")
    
    # Get record counts from SQLite
    print("Counting records in SQLite...")
    sqlite_counts = get_sqlite_counts()
    if not sqlite_counts:
        print("Error retrieving SQLite counts. Exiting.")
        return False
    
    # Get record counts from PostgreSQL
    print("\nCounting records in PostgreSQL...")
    pg_counts = get_postgresql_counts()
    if not pg_counts:
        print("Error retrieving PostgreSQL counts. Exiting.")
        return False
    
    # Compare counts
    print("\nComparing record counts:")
    comparison = compare_counts(sqlite_counts, pg_counts)
    
    # Print results
    headers = ["Table", "SQLite Count", "PostgreSQL Count", "Status"]
    print("\n" + tabulate.tabulate(comparison, headers=headers))
    
    # Report overall success
    success = all(row[3] == "✅" for row in comparison)
    print("\nMigration Status:", "✅ Successful" if success else "❌ Incomplete")
    
    return success

if __name__ == "__main__":
    # Check if tabulate is installed
    try:
        import tabulate
    except ImportError:
        print("Error: The 'tabulate' package is required. Please install it with:")
        print("  pip install tabulate")
        sys.exit(1)
    
    success = main()
    sys.exit(0 if success else 1) 