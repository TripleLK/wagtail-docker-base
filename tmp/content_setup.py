#!/usr/bin/env python3
"""
Content Setup Helper

This script helps to initialize essential content in a new PostgreSQL database.
It's intended to be run after setting up a fresh PostgreSQL database with tmp/setup_postgres.py.

This script will:
1. Create a home page with basic content
2. Create a contact page
3. Set up essential categories and tags

Usage:
    python tmp/content_setup.py
"""

import os
import sys
from pathlib import Path

# Set up base directory
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

def setup_environment():
    """Set up the Django environment"""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.production')
    
    import django
    django.setup()
    
    from django.conf import settings
    print(f"Using database: {settings.DATABASES['default']['ENGINE']}")
    
    if 'postgresql' not in settings.DATABASES['default']['ENGINE']:
        print("ERROR: Not using PostgreSQL database! Check your environment settings.")
        return False
    
    return True

def create_homepage():
    """Create a basic home page if it doesn't exist"""
    from wagtail.models import Page, Site
    from apps.base_site.models import HomePage
    
    print("Setting up homepage...")
    
    # Get the root page
    try:
        root_page = Page.objects.get(id=1)
    except Page.DoesNotExist:
        print("Error: Root page does not exist. Database may be corrupted.")
        return None
    
    # Check if a HomePage already exists
    existing_home = HomePage.objects.first()
    if existing_home:
        print(f"Homepage already exists: '{existing_home.title}' (id: {existing_home.id})")
        
        # Make sure it's set as the site root
        site = Site.objects.first()
        if site and site.root_page_id != existing_home.id:
            site.root_page = existing_home
            site.save()
            print(f"Updated site root page to '{existing_home.title}' (id: {existing_home.id})")
            
        return existing_home
    
    # Check if a page with slug 'home' already exists under root
    existing_home_slug = Page.objects.filter(slug='home', path__startswith=root_page.path, depth=root_page.depth + 1).first()
    if existing_home_slug:
        print(f"A page with slug 'home' already exists (id: {existing_home_slug.id})")
        print("Trying to convert it to a HomePage...")
        
        try:
            # Get the specific page
            specific_page = existing_home_slug.specific
            
            # If it's already a HomePage, use it
            if isinstance(specific_page, HomePage):
                print(f"The page is already a HomePage: '{specific_page.title}'")
                return specific_page
                
            # Otherwise, we can't easily convert it
            print(f"Cannot convert page of type {specific_page.__class__.__name__} to HomePage")
            print("Please delete this page in the admin interface and run this script again.")
            return None
        except Exception as e:
            print(f"Error accessing specific page: {str(e)}")
            return None
    
    # Create a new home page with a unique slug if 'home' is taken
    slug = 'home'
    counter = 1
    while Page.objects.filter(slug=slug, path__startswith=root_page.path, depth=root_page.depth + 1).exists():
        slug = f'home-{counter}'
        counter += 1
        
    home_page = HomePage(
        title="Home",
        slug=slug,
        hero_title="Welcome to Triad Scientific",
        hero_subtitle="Your trusted source for high-quality lab equipment and scientific supplies",
        about_title="About Triad Scientific",
        about_content="Triad Scientific has been a leading provider of laboratory equipment for over 20 years. We offer a comprehensive range of high-quality scientific instruments, supplies, and accessories."
    )
    
    # Add it to the tree
    try:
        root_page.add_child(instance=home_page)
        
        # Publish it
        home_page.save_revision().publish()
        
        # Update the site root page
        site = Site.objects.first()
        if site:
            site.root_page = home_page
            site.save()
            print(f"Set site root page to '{home_page.title}' (id: {home_page.id})")
        
        print(f"Created homepage: '{home_page.title}' (id: {home_page.id}, slug: '{slug}')")
        return home_page
    except Exception as e:
        print(f"Error creating homepage: {str(e)}")
        return None

def create_contact_page(parent_page):
    """Create a contact page if it doesn't exist"""
    from apps.base_site.models import ContactPage
    from wagtail.models import Page
    
    print("Setting up contact page...")
    
    # Check if a ContactPage already exists
    existing_contact = ContactPage.objects.first()
    if existing_contact:
        print(f"Contact page already exists: '{existing_contact.title}' (id: {existing_contact.id})")
        return existing_contact
    
    # Generate a unique slug
    slug = 'contact'
    counter = 1
    while Page.objects.filter(slug=slug, path__startswith=parent_page.path, depth=parent_page.depth + 1).exists():
        slug = f'contact-{counter}'
        counter += 1
    
    # Create a new contact page
    contact_page = ContactPage(
        title="Contact Us",
        slug=slug,
        intro_title="Contact Us",
        intro_text="Feel free to get in touch with us using the form below.",
        thank_you_text="Thank you for contacting us. We will get back to you as soon as possible.",
        quote_request_title="Request a Quote",
        quote_request_text="Fill out the form below to request a quote for the items in your cart."
    )
    
    # Add it to the tree
    try:
        parent_page.add_child(instance=contact_page)
        
        # Publish it
        contact_page.save_revision().publish()
        
        print(f"Created contact page: '{contact_page.title}' (id: {contact_page.id}, slug: '{slug}')")
        return contact_page
    except Exception as e:
        print(f"Error creating contact page: {str(e)}")
        return None

def create_categories():
    """Create tag categories if they don't exist"""
    from apps.categorized_tags.models import TagCategory
    
    print("Setting up tag categories...")
    
    # Default categories
    categories = [
        {"name": "Product Type", "slug": "product-type"},
        {"name": "Features", "slug": "features"},
        {"name": "Applications", "slug": "applications"}
    ]
    
    created_count = 0
    for category in categories:
        obj, created = TagCategory.objects.get_or_create(
            slug=category["slug"],
            defaults={"name": category["name"]}
        )
        
        if created:
            created_count += 1
            print(f"Created category: {obj.name}")
        else:
            print(f"Category '{obj.name}' already exists")
    
    print(f"Created {created_count} new categories")

def main():
    """Main function to run the setup process"""
    print("Content Setup Helper")
    print("===================\n")
    
    if not setup_environment():
        return False
    
    # Create homepage
    home_page = create_homepage()
    if not home_page:
        return False
    
    # Create contact page as a child of the homepage
    contact_page = create_contact_page(home_page)
    if not contact_page:
        return False
    
    # Create categories for tags
    create_categories()
    
    print("\nSetup completed successfully!")
    print("You can now add additional content through the admin interface at:")
    print("  http://localhost:8000/admin/")
    print("\nLogin with the superuser credentials you created earlier.")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 