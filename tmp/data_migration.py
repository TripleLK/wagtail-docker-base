#!/usr/bin/env python3
"""
Data migration utility to move data from SQLite to PostgreSQL.

This script handles the migration by:
1. Dumping data from SQLite using Django's built-in serialization
2. Switching to PostgreSQL environment
3. Loading data into PostgreSQL using Django's built-in deserialization

Usage:
    python tmp/data_migration.py
"""

import os
import sys
import json
import logging
import tempfile
import subprocess
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('data_migration')

# Use the project directory as the base directory
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

# Temporary directory for migration files
MIGRATION_DIR = BASE_DIR / "tmp" / "migration_data"
MIGRATION_DIR.mkdir(exist_ok=True)

# Order of models to migrate - this ordering helps with dependencies
MIGRATION_ORDER = [
    # Auth models
    'auth.user',
    'auth.group',
    'auth.permission',
    # Wagtail core models
    'wagtailcore.site',
    'wagtailcore.page',
    'wagtailcore.collection',
    # Base site models
    'base_site.labequipmentpage',
    'base_site.equipmentmodel',
    'base_site.labequipmentgalleryimage',
    'base_site.specgroup',
    'base_site.equipmentmodelspecgroup',
    'base_site.spec',
    # Tags
    'categorized_tags.tagcategory',
    'categorized_tags.categorizedtag',
    'categorized_tags.categorizedpagetag',
    # Other models
    'base_site.homepage',
    'base_site.contactpage',
    'base_site.quotecartitem',
    'base_site.quoterequest',
]

def setup_django(settings_module):
    """Set up Django with the specified settings module"""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', settings_module)
    
    import django
    django.setup()
    
    from django.conf import settings
    return settings

def switch_env(env_type):
    """Switch to the specified environment using our script"""
    script_path = str(BASE_DIR / "tmp" / "switch_env.py")
    result = subprocess.run(['python', script_path, env_type], capture_output=True, text=True)
    if result.returncode != 0:
        logger.error(f"Failed to switch environment: {result.stderr}")
        return False
    logger.info(f"Switched to {env_type} environment")
    return True

def export_data_from_sqlite():
    """Export data from SQLite database"""
    logger.info("Exporting data from SQLite database")
    
    # Switch to dev environment
    if not switch_env('dev'):
        return False
    
    # Load Django with dev settings
    settings = setup_django('config.settings.dev')
    logger.info(f"Using database: {settings.DATABASES['default']['ENGINE']}")
    
    from django.core import serializers
    
    # Export models
    for model_name in MIGRATION_ORDER:
        output_file = MIGRATION_DIR / f"{model_name.replace('.', '_')}.json"
        logger.info(f"Exporting {model_name} to {output_file}")
        
        try:
            # Get the model class
            from django.apps import apps
            app_label, model = model_name.split('.')
            Model = apps.get_model(app_label, model)
            
            # Get all objects
            queryset = Model.objects.all()
            count = queryset.count()
            
            if count == 0:
                logger.info(f"No data for {model_name}, skipping")
                continue
                
            # Serialize to JSON
            with open(output_file, 'w') as f:
                # Disable output for serialization to prevent print statement interference
                original_stdout = sys.stdout
                sys.stdout = tempfile.TemporaryFile(mode='w')
                
                try:
                    serialized_data = serializers.serialize('json', queryset, indent=2)
                    f.write(serialized_data)
                    logger.info(f"Exported {count} {model_name} objects")
                finally:
                    # Restore stdout
                    sys.stdout.close()
                    sys.stdout = original_stdout
        
        except Exception as e:
            logger.error(f"Error exporting {model_name}: {str(e)}")
    
    logger.info("SQLite data export completed")
    return True

def import_data_to_postgres():
    """Import data into PostgreSQL database"""
    logger.info("Importing data to PostgreSQL database")
    
    # Switch to prod environment
    if not switch_env('prod'):
        return False
    
    # Set Django settings module explicitly
    os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings.production'
    
    # Load Django with production settings
    import django
    django.setup()
    
    from django.conf import settings
    logger.info(f"Using database: {settings.DATABASES['default']['ENGINE']}")
    
    # Verify we're using PostgreSQL
    if 'postgresql' not in settings.DATABASES['default']['ENGINE']:
        logger.error(f"Not using PostgreSQL! Current engine: {settings.DATABASES['default']['ENGINE']}")
        return False
    
    from django.core import serializers
    from django.db import transaction
    
    # Import models in order
    for model_name in MIGRATION_ORDER:
        input_file = MIGRATION_DIR / f"{model_name.replace('.', '_')}.json"
        
        if not input_file.exists():
            logger.info(f"No data file for {model_name}, skipping")
            continue
            
        logger.info(f"Importing {model_name} from {input_file}")
        
        try:
            # Read the file
            with open(input_file, 'r') as f:
                data = f.read()
            
            # Deserialize and save objects
            with transaction.atomic():
                # Get the model class to clear existing data
                from django.apps import apps
                app_label, model = model_name.split('.')
                Model = apps.get_model(app_label, model)
                
                # Clear existing data
                Model.objects.all().delete()
                
                # Load new data
                objects = list(serializers.deserialize('json', data))
                
                if not objects:
                    logger.warning(f"No objects found in {input_file}")
                    continue
                    
                for obj in objects:
                    obj.save()
                
                logger.info(f"Imported {len(objects)} {model_name} objects")
                
                # Update sequences for PostgreSQL if the model has an id field
                if hasattr(Model, 'id'):
                    from django.db import connection
                    with connection.cursor() as cursor:
                        table_name = Model._meta.db_table
                        cursor.execute(f"SELECT setval(pg_get_serial_sequence('{table_name}', 'id'), COALESCE(MAX(id), 1)) FROM {table_name};")
                        
        except Exception as e:
            logger.error(f"Error importing {model_name}: {str(e)}")
    
    logger.info("PostgreSQL data import completed")
    return True

def main():
    """Run the full migration process"""
    logger.info("Starting SQLite to PostgreSQL migration")
    
    # Export data from SQLite
    if not export_data_from_sqlite():
        logger.error("Failed to export data from SQLite")
        return False
    
    # Import data to PostgreSQL
    if not import_data_to_postgres():
        logger.error("Failed to import data to PostgreSQL")
        return False
    
    logger.info("Migration completed successfully")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 