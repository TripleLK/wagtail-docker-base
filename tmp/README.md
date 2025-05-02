# Django SQLite to PostgreSQL Migration Tools

This directory contains tools for migrating data between SQLite and PostgreSQL for the Django/Wagtail application.

## Available Tools

### 1. Environment Switching

`switch_env.py` - Switch between different database environments:

```bash
# Usage
python tmp/switch_env.py [dev|prod|safari]
```

- `dev`: Use SQLite database (development mode)
- `prod`: Use PostgreSQL database (production mode)
- `safari`: Use SQLite with Safari-compatible settings

### 2. Database Migration

`migrate_direct.py` - Migrate data from SQLite to PostgreSQL:

```bash
# Usage
python tmp/migrate_direct.py [--tables TABLE1,TABLE2] [--skip-tables TABLE3,TABLE4] [--disable-fk]
```

Options:
- `--tables`: Comma-separated list of tables to migrate (migrates all tables if not specified)
- `--skip-tables`: Comma-separated list of tables to skip
- `--disable-fk`: Temporarily disable foreign key constraints during migration (useful for circular dependencies)

### 3. Migration Fixes

`fix_migration.py` - Fix issues with circular dependencies in tables:

```bash
# Usage
python tmp/fix_migration.py
```

This script temporarily disables triggers on problematic tables, runs the migration for those tables, and then re-enables the triggers.

### 4. Migration Verification

`verify_migration.py` - Compare record counts between SQLite and PostgreSQL:

```bash
# Usage
python tmp/verify_migration.py
```

This script counts records in both databases and reports any discrepancies.

## Migration Process

1. **Switch to development environment**:
   ```bash
   python tmp/switch_env.py dev
   ```

2. **Verify SQLite database**:
   ```bash
   python manage.py check
   ```

3. **Switch to production environment**:
   ```bash
   python tmp/switch_env.py prod
   ```

4. **Create PostgreSQL schema**:
   ```bash
   python manage.py migrate
   ```

5. **Migrate data**:
   ```bash
   python tmp/migrate_direct.py --disable-fk
   ```

6. **Fix any circular dependency issues**:
   ```bash
   python tmp/fix_migration.py
   ```

7. **Verify migration**:
   ```bash
   python tmp/verify_migration.py
   ```

8. **Run server with PostgreSQL**:
   ```bash
   python manage.py runserver
   ```

## Notes

- The full-text search tables specific to SQLite (`wagtailsearch_indexentry_fts*`) are not migrated to PostgreSQL as they use different search implementations. These will be automatically rebuilt when search is used.
- Some text fields may be truncated if they exceed the maximum length defined in PostgreSQL.

For full migration details, see the [migration_summary.md](migration_summary.md) document. 