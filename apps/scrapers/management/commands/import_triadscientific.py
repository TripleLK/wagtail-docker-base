#!/usr/bin/env python3
import logging
import sys
import requests
import re
import time
import traceback
from bs4 import BeautifulSoup
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify
from wagtail.models import Page
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

from apps.base_site.models import (
    LabEquipmentPage, 
    EquipmentModel, 
    SpecGroup, 
    Spec, 
    EquipmentModelSpecGroup,
    LabEquipmentGalleryImage,
    LabEquipmentPageSpecGroup
)
from apps.scrapers.Scrapers import Scraper
from apps.scrapers.utils.image_downloader import ImageDownloader

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Import Triad Scientific product data from web scraper into Django models'

    def add_arguments(self, parser):
        parser.add_argument(
            '--url',
            type=str,
            help='URL to scrape'
        )
        parser.add_argument(
            '--url-file',
            type=str,
            help='File containing URLs to scrape, one per line'
        )
        parser.add_argument(
            '--parent-page',
            type=int,
            default=None,
            help='ID of parent page to add equipment pages under (required for new pages)'
        )
        parser.add_argument(
            '--update-existing',
            action='store_true',
            help='Update existing pages instead of creating new ones'
        )
        parser.add_argument(
            '--skip-images',
            action='store_true',
            help='Skip downloading images'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Perform a dry run without committing changes'
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=None,
            help='Limit the number of URLs to process'
        )
        parser.add_argument(
            '--retry',
            type=int,
            default=3,
            help='Number of retry attempts for failed requests (default: 3)'
        )
        parser.add_argument(
            '--retry-delay',
            type=int,
            default=5,
            help='Delay in seconds between retry attempts (default: 5)'
        )

    def handle(self, *args, **options):
        url = options.get('url')
        url_file = options.get('url_file')
        parent_page_id = options.get('parent_page')
        update_existing = options.get('update_existing')
        skip_images = options.get('skip_images')
        dry_run = options.get('dry_run')
        limit = options.get('limit')
        retry_attempts = options.get('retry')
        retry_delay = options.get('retry_delay')
        
        # Setup logging for the scraping process
        self._setup_logging()
        
        if not url and not url_file:
            self.stderr.write("Either --url or --url-file argument is required")
            return
            
        urls = []
        
        # Process single URL
        if url:
            urls.append(url)
            
        # Process URL file
        if url_file:
            try:
                with open(url_file, 'r') as f:
                    for line in f:
                        # Support the format from test files: url | product_name
                        line = line.strip()
                        if line and not line.startswith('#'):
                            url_part = line.split('|')[0].strip()
                            if url_part:
                                urls.append(url_part)
            except FileNotFoundError:
                self.stderr.write(f"File not found: {url_file}")
                return
                
        # Apply limit if specified
        if limit and len(urls) > limit:
            urls = urls[:limit]
            
        if dry_run:
            self.stdout.write("Performing dry run - no changes will be committed")

        # Create a session with retry capability
        session = self._create_session_with_retry(retry_attempts, retry_delay)
        
        # Initialize the scraper with the Triad Scientific mapping and our custom session
        scraper = Scraper("apps/scrapers/triadscientific-yamls/mapping.yaml")
        
        # Keep track of successful and failed imports
        success_count = 0
        failure_count = 0
        skipped_count = 0
        
        # Create a log of errors for later inspection
        errors_log = []
        
        # Process each URL
        for index, url in enumerate(urls):
            self.stdout.write(f"[{index+1}/{len(urls)}] Processing: {url}")
            logger.info(f"Processing URL: {url}")
            
            try:
                # Add delay to avoid overloading the website
                if index > 0:
                    time.sleep(1)
                
                # Scrape the product page with retry mechanism
                result = None
                retry_count = 0
                while retry_count <= retry_attempts:
                    try:
                        result = scraper.scrape(url)
                        break
                    except requests.RequestException as e:
                        retry_count += 1
                        if retry_count > retry_attempts:
                            raise
                        self.stdout.write(f"  Request failed ({e}), retrying ({retry_count}/{retry_attempts}) in {retry_delay} seconds...")
                        time.sleep(retry_delay)
                
                if not result:
                    self.stderr.write(f"No data extracted from {url}")
                    failure_count += 1
                    errors_log.append({"url": url, "error": "No data extracted", "traceback": None})
                    continue
                    
                product_name = result.get('name', 'Unknown Product')
                short_description = result.get('short_description', '')
                full_description = result.get('full_description', '')
                models_data = result.get('models', {})
                images_data = result.get('imgs', [])
                
                # Validate the extracted data
                validation_errors = self._validate_data(product_name, short_description, full_description, models_data, images_data)
                if validation_errors:
                    self.stderr.write(f"Validation errors for {url}:")
                    for error in validation_errors:
                        self.stderr.write(f"  - {error}")
                    failure_count += 1
                    errors_log.append({"url": url, "error": "Validation errors", "validation": validation_errors})
                    continue
                
                self.stdout.write(f"Found product: {product_name}")
                self.stdout.write(f"Number of models: {len(models_data)}")
                self.stdout.write(f"Number of images: {len(images_data)}")
                
                # Log detailed information if verbosity is high
                if options['verbosity'] > 1:
                    self.stdout.write("\nShort description:")
                    self.stdout.write(short_description[:100] + '...' if len(short_description) > 100 else short_description)
                    
                    self.stdout.write("\nImages:")
                    for i, img_url in enumerate(images_data[:5]):  # Show only first 5 images
                        self.stdout.write(f"  Image {i+1}: {img_url}")
                    if len(images_data) > 5:
                        self.stdout.write(f"  ... and {len(images_data) - 5} more")
                        
                # Process the data and import into the database
                if not dry_run:
                    # Check if page already exists and we're not updating
                    slug = slugify(product_name)
                    existing_page = LabEquipmentPage.objects.filter(slug=slug).first()
                    
                    if existing_page and not update_existing:
                        self.stdout.write(f"Page exists and update_existing is False. Skipping: {product_name}")
                        skipped_count += 1
                        continue
                    
                    # Use transaction to ensure data consistency
                    try:
                        with transaction.atomic():
                            self.import_data(
                                product_name, 
                                short_description, 
                                full_description, 
                                models_data,
                                images_data,
                                parent_page_id,
                                update_existing,
                                skip_images,
                                url
                            )
                        success_count += 1
                        self.stdout.write(self.style.SUCCESS(f"Successfully imported: {product_name}"))
                        logger.info(f"Successfully imported: {product_name}")
                    except Exception as e:
                        self.stderr.write(self.style.ERROR(f"Error importing {product_name}: {e}"))
                        tb = traceback.format_exc()
                        self.stderr.write(tb)
                        logger.error(f"Error importing {product_name}: {e}\n{tb}")
                        failure_count += 1
                        errors_log.append({"url": url, "error": str(e), "traceback": tb})
                else:
                    self.stdout.write("Dry run - not importing data")
                    success_count += 1
                    
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"Error processing {url}: {e}"))
                tb = traceback.format_exc()
                self.stderr.write(tb)
                logger.error(f"Error processing {url}: {e}\n{tb}")
                failure_count += 1
                errors_log.append({"url": url, "error": str(e), "traceback": tb})
                
        # Print summary
        self.stdout.write("\n--- Import Summary ---")
        self.stdout.write(f"Total URLs processed: {len(urls)}")
        self.stdout.write(f"Successful imports: {success_count}")
        self.stdout.write(f"Failed imports: {failure_count}")
        self.stdout.write(f"Skipped (already exist): {skipped_count}")
        
        if errors_log:
            self.stdout.write(f"\nErrors occurred during import. Check the log for details.")
            
        if dry_run:
            self.stdout.write("This was a dry run - no changes were committed to the database")
    
    def _create_session_with_retry(self, retry_attempts, retry_delay):
        """
        Create a requests session with retry capability
        """
        session = requests.Session()
        retry_strategy = Retry(
            total=retry_attempts,
            backoff_factor=retry_delay,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session
        
    def _setup_logging(self):
        """
        Configure logging for the import process
        """
        logger.setLevel(logging.INFO)
        
        # Create a file handler if not already present
        if not any(isinstance(handler, logging.FileHandler) for handler in logger.handlers):
            handler = logging.FileHandler('triad_import.log')
            handler.setLevel(logging.INFO)
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
    
    def _validate_data(self, product_name, short_description, full_description, models_data, images_data):
        """
        Validate the extracted data before importing
        
        Returns: List of validation error messages, empty if no errors
        """
        errors = []
        
        # Check product name
        if not product_name or product_name == 'Unknown Product':
            errors.append("Product name is missing or invalid")
        
        # Check descriptions
        if not short_description and not full_description:
            errors.append("Both short and full descriptions are missing")
        
        # Check models data format
        if models_data and not isinstance(models_data, dict):
            errors.append(f"Models data has invalid format: {type(models_data)}")
        
        # Check images data format
        if not isinstance(images_data, list):
            errors.append(f"Images data has invalid format: {type(images_data)}")
        
        # Check image URLs for basic validity
        for img_url in images_data:
            if not isinstance(img_url, str) or not (img_url.startswith('http://') or img_url.startswith('https://')):
                errors.append(f"Invalid image URL format: {img_url}")
        
        return errors

    @transaction.atomic
    def import_data(self, product_name, short_description, full_description, 
                   models_data, images_data, parent_page_id, update_existing, skip_images, url=None):
        """
        Import the extracted data into Django models.
        
        Args:
            product_name: Name of the product
            short_description: Short description text
            full_description: Full description text
            models_data: Dictionary of models with their specifications
            images_data: List of image URLs
            parent_page_id: ID of the parent page
            update_existing: Whether to update existing pages
            skip_images: Whether to skip downloading images
            url: Original URL of the product page
        """
        # Clean the product name to remove excessive spaces and line breaks
        product_name = re.sub(r'\s+', ' ', product_name).strip()
        
        # Create a slug for the page title
        slug = slugify(product_name)
        
        # Check if page already exists
        existing_page = LabEquipmentPage.objects.filter(slug=slug).first()
        
        if existing_page and update_existing:
            # Update existing page
            self.stdout.write(f"Updating existing page: {product_name}")
            page = existing_page
            page.title = product_name
            page.short_description = short_description
            page.full_description = full_description
            if url:
                page.source_url = url
            page.save()
            
            # Clear existing models and images if we're going to replace them
            if not skip_images:
                page.gallery_images.all().delete()
            page.models.all().delete()
        elif not existing_page:
            # Create new page
            if not parent_page_id:
                raise ValueError("Parent page ID is required for creating new pages")
                
            try:
                parent_page = Page.objects.get(id=parent_page_id)
            except Page.DoesNotExist:
                raise ValueError(f"Parent page with ID {parent_page_id} does not exist")
                
            self.stdout.write(f"Creating new page: {product_name}")
            page = LabEquipmentPage(
                title=product_name,
                short_description=short_description,
                full_description=full_description,
                source_url=url
            )
            
            # Add the page as a child of the parent page
            parent_page.add_child(instance=page)
        else:
            # Page exists but we're not updating
            self.stdout.write(f"Page already exists (not updating): {product_name}")
            return
            
        # Handle images if not skipping
        if not skip_images and images_data:
            self.handle_images(page, images_data)
            
        # Handle models and specifications
        self.handle_models(page, models_data)
        
        # Save and publish the page
        revision = page.save_revision()
        revision.publish()
        
    def handle_images(self, page, images_data):
        """
        Handle the creation of gallery images for a page.
        
        Args:
            page: The LabEquipmentPage instance
            images_data: List of image URLs
        """
        for image_url in images_data:
            try:
                # Create gallery image with external URL
                gallery_image = LabEquipmentGalleryImage(
                    page=page,
                    external_image_url=image_url
                )
                gallery_image.save()
            except Exception as e:
                logger.error(f"Error adding image {image_url}: {e}")
                
    def handle_models(self, page, models_data):
        """
        Handle the creation of equipment models and their specifications.
        
        Args:
            page: The LabEquipmentPage instance
            models_data: Dictionary of models with their specifications
        """
        # Create a single model with the same name as the product
        model = EquipmentModel(
            page=page,
            name=page.title
        )
        model.save()
        
        # Create a simple specification group
        spec_group = EquipmentModelSpecGroup(
            equipment_model=model,
            name="Specifications"
        )
        spec_group.save()
        
        # Add a generic spec that refers to the full description
        Spec.objects.create(
            spec_group=spec_group,
            key="Specs",
            value="Specs not available, please refer to the full description above"
        )
        
