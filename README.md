
# Triad Django Project

## Environment Setup

This project uses a flexible environment configuration system that supports both SQLite (development) and PostgreSQL (production) databases. All environment files are stored in the `envs/` directory.

## Available Scripts

### Main Scripts

- **`run.sh`**: The primary script to run the application in the current environment
- **`switch_env.sh`**: Switch between environments (dev/prod/safari)
- **`create_db.sh`**: Create the PostgreSQL database for production
- **`migrate_data.sh`**: Migrate data from SQLite to PostgreSQL

### Environment Types

- **Development (SQLite)**: `./switch_env.sh dev mac`
- **Production (PostgreSQL)**: `./switch_env.sh prod mac`
- **Safari-compatible**: `./switch_env.sh safari`

## Getting Started

1. Ensure you have Python and Django installed
2. For production mode, ensure PostgreSQL is installed and running
3. Run the appropriate commands to set up your environment:

```bash
# For development (SQLite)
./switch_env.sh dev mac
./run.sh

# For production (PostgreSQL)
./create_db.sh
./switch_env.sh prod mac
./run.sh
```

## Data Migration

To transfer data from SQLite to PostgreSQL:

```bash
./migrate_data.sh
```

## Environment Files

All environment configuration files are stored in the `envs/` directory:

- `envs/dev.mac.env`: Development environment with SQLite
- `envs/prod.mac.env`: Production environment with PostgreSQL
- `envs/dev.safari.env`: Safari-compatible environment

## Browser Compatibility

When accessing the site, always use `http://` explicitly in the URL, not `https://`.

## Notes

- The default port is 8000 for regular environments and 8765 for Safari-compatible mode
- In production mode, static files are automatically collected when running `run.sh`
- Database migrations are automatically run when starting the server




## AirScience Web Scraper Integration

The AirScience Web Scraper is integrated with the Django models to automate the process of importing product data from the AirScience website.

### Running the Scraper

The scraper is implemented as a Django management command and can be run using the following command:

```bash
python manage.py import_airscience [options]
```

Or using the convenience script:

```bash
./scripts/import_airscience_products.sh [options]
```

### Command Options

- `--parent-page=ID`: ID of the parent page to add equipment pages under (required for new pages)
- `--update-existing`: Update existing pages instead of creating new ones
- `--skip-images`: Skip downloading images
- `--dry-run`: Perform a dry run without committing changes
- `--url=URL`: URL to scrape (default: Purair Advanced Ductless Fume Hoods)

### Example Usage

Run a dry run to see what would be imported:

```bash
python manage.py import_airscience --parent-page=2 --dry-run
```

Import new products:

```bash
python manage.py import_airscience --parent-page=2
```

Update existing products:

```bash
python manage.py import_airscience --update-existing
```

### Data Extraction

The scraper extracts the following data from the AirScience website:

- Product name
- Short and full descriptions
- Model specifications organized by sections
- Product images

### Database Integration

The scraper integrates with the following Django models:

- `LabEquipmentPage`: Stores the product information
- `EquipmentModel`: Stores model variants for each product
- `EquipmentModelSpecGroup`: Organizes specifications by sections
- `Spec`: Stores individual specifications
- `LabEquipmentGalleryImage`: Stores product images

