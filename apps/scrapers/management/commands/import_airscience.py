#!/usr/bin/env python3
import logging
import sys
import requests
from bs4 import BeautifulSoup
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify
from wagtail.models import Page

from apps.base_site.models import (
    LabEquipmentPage, 
    EquipmentModel, 
    SpecGroup, 
    Spec, 
    EquipmentModelSpecGroup,
    LabEquipmentGalleryImage
)
from apps.scrapers.selectors.base import Selector, Selected, SelectedType
from apps.scrapers.utils.image_downloader import ImageDownloader

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Import AirScience product data from web scraper into Django models'

    def add_arguments(self, parser):
        parser.add_argument(
            '--url',
            type=str,
            default="https://www.airscience.com/product-category-page?brandname=purair-advanced-ductless-fume-hoods&brand=9",
            help='URL to scrape (default: Purair Advanced Ductless Fume Hoods)'
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

    def handle(self, *args, **options):
        url = options['url']
        parent_page_id = options['parent_page']
        update_existing = options['update_existing']
        skip_images = options['skip_images']
        dry_run = options['dry_run']

        if dry_run:
            self.stdout.write("Performing dry run - no changes will be committed")

        # Fetch the URL content
        self.stdout.write(f"Fetching content from {url}")
        response = requests.get(url)
        if response.status_code != 200:
            self.stderr.write(f"Failed to fetch URL: {response.status_code}")
            return

        # Parse the HTML content
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Create a Selected object with the parsed HTML
        page_selected = Selected(soup, SelectedType.SINGLE)
        
        # Load the mapping selector
        mapping_selector = Selector.fromFilePath("apps/scrapers/airscience-yamls/mapping.yaml")
        
        # Apply the mapping selector to extract data
        try:
            result = mapping_selector(page_selected)
            
            if result.selected_type == SelectedType.VALUE and isinstance(result.value, dict):
                extracted_data = result.value
                
                # Process the extracted data
                product_name = extracted_data.get('name', 'Unknown Product')
                short_description = extracted_data.get('short_description', '')
                full_description = extracted_data.get('full_description', '')
                models_data = extracted_data.get('models', {})
                images_data = extracted_data.get('imgs', [])
                
                self.stdout.write(f"Found product: {product_name}")
                self.stdout.write(f"Number of models: {len(models_data)}")
                self.stdout.write(f"Number of images: {len(images_data)}")
                
                # If verbosity is high, print more details
                if options['verbosity'] > 1:
                    self.stdout.write("\nModel details:")
                    for model_name, model_specs in models_data.items():
                        self.stdout.write(f"\n  Model: {model_name}")
                        
                        # Print sections and specs
                        for section in model_specs:
                            if isinstance(section, dict):
                                section_title = section.get('section_title', 'Specifications')
                                self.stdout.write(f"    Section: {section_title}")
                                
                                # Print specs
                                if 'vals' in section and isinstance(section['vals'], list):
                                    for spec_array in section['vals']:
                                        if isinstance(spec_array, list):
                                            for spec_data in spec_array:
                                                if isinstance(spec_data, dict) and 'spec_name' in spec_data and 'spec_value' in spec_data:
                                                    spec_name = spec_data['spec_name']
                                                    spec_value = spec_data['spec_value']
                                                    
                                                    # Skip specs where both name and value are None/empty or just "None"
                                                    if (spec_name is None or spec_name.strip() == "" or spec_name.lower() == "none") and \
                                                       (spec_value is None or spec_value.strip() == "" or spec_value.lower() == "none"):
                                                        continue
                                                    
                                                    # Clean up spec name and value
                                                    if spec_name is not None:
                                                        # Remove trailing colons from spec names
                                                        spec_name = spec_name.rstrip(':')
                                                    
                                                    if spec_value is not None:
                                                        # Remove leading/trailing whitespace
                                                        spec_value = spec_value.strip()
                                                        
                                                        # Special handling for Monitoring Options field
                                                        if spec_name == "Monitoring Options" and "/" in spec_value:
                                                            # Clean up the multiple slashes with spaces
                                                            spec_value = "Standard" if "Standard" in spec_value else spec_value
                                                            spec_value = spec_value.replace('/ /', '')
                                                            spec_value = spec_value.replace('/', '')
                                                            spec_value = spec_value.strip()
                                                    
                                                    self.stdout.write(f"      {spec_name}: {spec_value}")
                    
                    # Print image URLs
                    if images_data:
                        self.stdout.write("\nImage URLs:")
                        for i, url in enumerate(images_data):
                            self.stdout.write(f"  Image {i+1}: {url}")
                
                # Process the data and import into the database
                if not dry_run:
                    self.import_data(
                        product_name, 
                        short_description, 
                        full_description, 
                        models_data,
                        images_data,
                        parent_page_id,
                        update_existing,
                        skip_images
                    )
                else:
                    self.stdout.write("Dry run complete - data was not imported")
            else:
                self.stderr.write(f"Unexpected result type: {result.selected_type}")
                
        except Exception as e:
            self.stderr.write(f"Error during extraction: {e}")
            import traceback
            self.stderr.write(traceback.format_exc())

    @transaction.atomic
    def import_data(self, product_name, short_description, full_description, 
                   models_data, images_data, parent_page_id, update_existing, skip_images):
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
        """
        # Create a slug for the page title
        slug = slugify(product_name)
        
        # Check if page already exists
        existing_page = LabEquipmentPage.objects.filter(slug=slug).first()
        
        if existing_page and update_existing:
            # Update existing page
            self.stdout.write(f"Updating existing page: {product_name}")
            page = existing_page
            page.short_description = short_description
            page.full_description = full_description
            page.save()
        elif not existing_page:
            # Create new page
            if not parent_page_id:
                self.stderr.write("Parent page ID is required for creating new pages")
                return
                
            try:
                parent_page = Page.objects.get(id=parent_page_id)
            except Page.DoesNotExist:
                self.stderr.write(f"Parent page with ID {parent_page_id} does not exist")
                return
                
            self.stdout.write(f"Creating new page: {product_name}")
            page = LabEquipmentPage(
                title=product_name,
                short_description=short_description,
                full_description=full_description,
                slug=slug
            )
            parent_page.add_child(instance=page)
            page.save_revision().publish()
        else:
            self.stdout.write(f"Page already exists: {product_name}. Use --update-existing to update it.")
            return
        
        # Handle images
        if not skip_images and images_data:
            self.handle_images(page, images_data, update_existing)
            
        # Process models
        for model_name, model_specs in models_data.items():
            self.stdout.write(f"Processing model: {model_name}")
            
            # Extract model number from the name or use name as fallback
            model_number = model_name
            
            # Check if model already exists
            equipment_model, created = EquipmentModel.objects.get_or_create(
                page=page,
                name=model_name,
                defaults={'model_number': model_number}
            )
            
            if not created:
                # Clear existing spec groups for this model
                EquipmentModelSpecGroup.objects.filter(equipment_model=equipment_model).delete()
            
            # Process spec sections
            for section in model_specs:
                if not isinstance(section, dict):
                    continue
                    
                section_title = section.get('section_title', 'Specifications')
                
                # Create a spec group for this section
                spec_group = EquipmentModelSpecGroup.objects.create(
                    equipment_model=equipment_model,
                    name=section_title
                )
                
                # Process specs in this section
                if 'vals' in section and isinstance(section['vals'], list):
                    for spec_array in section['vals']:
                        if isinstance(spec_array, list):
                            for spec_data in spec_array:
                                if isinstance(spec_data, dict) and 'spec_name' in spec_data and 'spec_value' in spec_data:
                                    spec_name = spec_data['spec_name']
                                    spec_value = spec_data['spec_value']
                                    
                                    # Skip specs where both name and value are None/empty or just "None"
                                    if (spec_name is None or spec_name.strip() == "" or spec_name.lower() == "none") and \
                                       (spec_value is None or spec_value.strip() == "" or spec_value.lower() == "none"):
                                        continue
                                    
                                    # Clean up spec name and value
                                    if spec_name is not None:
                                        # Remove trailing colons from spec names
                                        spec_name = spec_name.rstrip(':')
                                    
                                    if spec_value is not None:
                                        # Remove leading/trailing whitespace
                                        spec_value = spec_value.strip()
                                        
                                        # Special handling for Monitoring Options field
                                        if spec_name == "Monitoring Options" and "/" in spec_value:
                                            # Clean up the multiple slashes with spaces
                                            spec_value = "Standard" if "Standard" in spec_value else spec_value
                                            spec_value = spec_value.replace('/ /', '')
                                            spec_value = spec_value.replace('/', '')
                                            spec_value = spec_value.strip()
                                    
                                    # Create spec
                                    Spec.objects.create(
                                        spec_group=spec_group,
                                        key=spec_name,
                                        value=spec_value
                                    )
                                    
        self.stdout.write(f"Successfully imported {product_name} with {len(models_data)} models")
        
    def handle_images(self, page, images_data, update_existing):
        """
        Download and attach images to the page.
        
        Args:
            page: LabEquipmentPage instance
            images_data: List of image URLs
            update_existing: Whether to update existing images
        """
        # Clear existing images if updating
        if update_existing:
            LabEquipmentGalleryImage.objects.filter(page=page).delete()
        
        # Download and save images
        self.stdout.write(f"Downloading {len(images_data)} images...")
        
        for i, image_url in enumerate(images_data):
            self.stdout.write(f"Downloading image {i+1}/{len(images_data)}: {image_url}")
            
            # Use external URL approach for simplicity
            gallery_image = LabEquipmentGalleryImage(
                page=page,
                external_image_url=image_url
            )
            gallery_image.save()
            
        self.stdout.write(f"Added {len(images_data)} images to the page") 