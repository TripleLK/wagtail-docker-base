#!/usr/bin/env python3
import logging
import sys
import requests
import re
import time
import traceback
import os
import importlib.util
from bs4 import BeautifulSoup
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify
from wagtail.models import Page
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
import concurrent.futures
import threading
import queue
import datetime
import json
from tqdm import tqdm
import signal

from apps.base_site.models import (
    LabEquipmentPage, 
    EquipmentModel, 
    SpecGroup, 
    Spec, 
    EquipmentModelSpecGroup,
    LabEquipmentGalleryImage,
    LabEquipmentPageSpecGroup
)
from apps.categorized_tags.models import (
    CategorizedTag,
    CategorizedPageTag,
    TagCategory
)
from apps.scrapers.Scrapers import Scraper
from apps.scrapers.utils.image_downloader import ImageDownloader

# Import the URL discoverer using dynamic import to handle the hyphenated directory name
discoverer_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                              'triadscientific-yamls', 'url_discovery.py')
spec = importlib.util.spec_from_file_location("url_discovery", discoverer_path)
url_discovery = importlib.util.module_from_spec(spec)
sys.modules["url_discovery"] = url_discovery
spec.loader.exec_module(url_discovery)
TriadUrlDiscoverer = url_discovery.TriadUrlDiscoverer

# Setup module-level logger
logger = logging.getLogger(__name__)

# Global variables for process management
stop_processing = False
stats_lock = threading.Lock()

# Define a signal handler for graceful shutdown
def signal_handler(sig, frame):
    global stop_processing
    print("\nGracefully shutting down... (This may take a moment)")
    stop_processing = True

class Command(BaseCommand):
    help = 'Import Triad Scientific product data from web scraper into Django models'

    def add_arguments(self, parser):
        # Original URL arguments
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
        
        # New URL discovery arguments
        parser.add_argument(
            '--discover-urls',
            action='store_true',
            help='Discover product URLs from the Triad Scientific website'
        )
        parser.add_argument(
            '--category',
            type=str,
            help='Specific category to discover URLs for (e.g., "ftir-systems")'
        )
        parser.add_argument(
            '--output-file',
            type=str,
            default='discovered_product_urls.txt',
            help='File to save discovered URLs to'
        )
        parser.add_argument(
            '--request-delay',
            type=float,
            default=1.0,
            help='Delay between requests during URL discovery (in seconds)'
        )
        
        # Original import arguments
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
        
        # New tagging arguments
        parser.add_argument(
            '--process-tags',
            action='store_true',
            help='Process tags after importing data'
        )
        parser.add_argument(
            '--tags-only',
            action='store_true',
            help='Only process tags, no import'
        )
        parser.add_argument(
            '--add-manufacturer-tag',
            action='store_true',
            help='Add manufacturer tag to imported products'
        )
        
        # Step 6: Parallel processing arguments
        parser.add_argument(
            '--workers',
            type=int,
            default=4,
            help='Number of worker threads for parallel processing (default: 4)'
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=10,
            help='Number of items to process in a single batch (default: 10)'
        )
        parser.add_argument(
            '--checkpoint-file',
            type=str,
            default='triad_checkpoint.json',
            help='Checkpoint file to save/resume progress'
        )
        parser.add_argument(
            '--resume',
            action='store_true',
            help='Resume from the last checkpoint'
        )
        parser.add_argument(
            '--stats-interval',
            type=int,
            default=60,
            help='Interval in seconds for printing statistics during processing (default: 60)'
        )
        parser.add_argument(
            '--log-file',
            type=str,
            default='triad_import.log',
            help='Log file for detailed import information'
        )

    def handle(self, *args, **options):
        # Register signal handler for graceful shutdown
        signal.signal(signal.SIGINT, signal_handler)
        
        # Extract options
        url = options.get('url')
        url_file = options.get('url_file')
        parent_page_id = options.get('parent_page')
        update_existing = options.get('update_existing')
        skip_images = options.get('skip_images')
        dry_run = options.get('dry_run')
        limit = options.get('limit')
        retry_attempts = options.get('retry')
        retry_delay = options.get('retry_delay')
        discover_urls = options.get('discover_urls')
        category = options.get('category')
        output_file = options.get('output_file')
        request_delay = options.get('request_delay')
        process_tags = options.get('process_tags')
        tags_only = options.get('tags_only')
        add_manufacturer_tag = options.get('add_manufacturer_tag')
        
        # Step 6: New parallel processing options
        workers = options.get('workers')
        batch_size = options.get('batch_size')
        checkpoint_file = options.get('checkpoint_file')
        resume = options.get('resume')
        stats_interval = options.get('stats_interval')
        log_file = options.get('log_file')
        
        # Setup logging for the scraping process
        self._setup_logging(log_file)
        
        # Initialize stats for reporting
        stats = {
            'urls_discovered': 0,
            'urls_processed': 0,
            'success_count': 0,
            'failure_count': 0,
            'skipped_count': 0,
            'tags_applied': 0,
            'start_time': time.time(),
            'last_report_time': time.time(),
            'errors': [],
        }
        
        # Load checkpoint if resume is enabled
        checkpoint_data = None
        if resume and os.path.exists(checkpoint_file):
            try:
                with open(checkpoint_file, 'r') as f:
                    checkpoint_data = json.load(f)
                    self.stdout.write(f"Resuming from checkpoint with {len(checkpoint_data.get('processed_urls', []))} previously processed URLs")
                    # Update stats from checkpoint if available
                    if 'stats' in checkpoint_data:
                        for key, value in checkpoint_data['stats'].items():
                            if key in stats and key not in ['start_time', 'last_report_time']:
                                stats[key] = value
            except Exception as e:
                logger.error(f"Error loading checkpoint file: {str(e)}")
                checkpoint_data = None
        
        # Only process tags if requested with --tags-only flag
        if tags_only:
            self.stdout.write("Running in tags-only mode, processing existing products...")
            tag_stats = self.process_tags(dry_run, add_manufacturer_tag)
            stats['tags_applied'] = tag_stats.get('tags_applied', 0)
            self.stdout.write(f"Tags processing complete. Applied {stats['tags_applied']} tags to {tag_stats.get('pages_processed', 0)} pages.")
            return
            
        # URL discovery mode - now with parallel processing
        if discover_urls:
            self.stdout.write("Starting URL discovery process...")
            discovered_urls = self.discover_urls_parallel(category, request_delay, output_file, workers)
            stats['urls_discovered'] = len(discovered_urls)
                
            # If we're also importing, use the discovered URLs
            if not url and not url_file:
                self.stdout.write(f"Using {len(discovered_urls)} discovered URLs for import")
                urls = [url_info['url'] for url_info in discovered_urls]
            else:
                self.stdout.write("URLs provided with --url or --url-file will be used instead of discovered URLs")
        
        # Handle URL input (if URL discovery not used or additional URLs provided)
        if not discover_urls or url or url_file:
            if not url and not url_file and not discover_urls:
                self.stderr.write("Either --url, --url-file, or --discover-urls argument is required")
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
        
        # Filter out already processed URLs if resuming
        if resume and checkpoint_data and 'processed_urls' in checkpoint_data:
            processed_urls = set(checkpoint_data['processed_urls'])
            original_count = len(urls)
            urls = [url for url in urls if url not in processed_urls]
            self.stdout.write(f"Filtered out {original_count - len(urls)} already processed URLs")
        
        # Apply limit if specified
        if limit and len(urls) > limit:
            self.stdout.write(f"Limiting to {limit} URLs (out of {len(urls)})")
            urls = urls[:limit]
            
        if dry_run:
            self.stdout.write("Performing dry run - no changes will be committed")

        # Create a session with retry capability
        session = self._create_session_with_retry(retry_attempts, retry_delay)
        
        # Initialize the scraper with the Triad Scientific mapping and our custom session
        scraper = Scraper("apps/scrapers/triadscientific-yamls/mapping.yaml")
        
        # Start the stats reporting thread
        stop_stats_thread = threading.Event()
        stats_thread = threading.Thread(
            target=self._stats_reporting_thread, 
            args=(stats, stats_interval, stop_stats_thread)
        )
        stats_thread.daemon = True
        stats_thread.start()
        
        try:
            # Process URLs in parallel
            self.process_urls_parallel(
                urls, 
                scraper, 
                session, 
                parent_page_id, 
                update_existing, 
                skip_images, 
                dry_run, 
                workers, 
                batch_size, 
                checkpoint_file, 
                stats, 
                process_tags, 
                add_manufacturer_tag
            )
            
            # Final stats report
            self._print_stats_report(stats)
            
            # Save final checkpoint
            if not dry_run:
                self._save_checkpoint(checkpoint_file, stats, urls)
            
        except Exception as e:
            logger.error(f"Error in main process: {str(e)}")
            traceback.print_exc()
        finally:
            # Stop the stats reporting thread
            stop_stats_thread.set()
            stats_thread.join(timeout=1)
        
        if process_tags and not dry_run:
            self.stdout.write("Processing tags for imported products...")
            tag_stats = self.process_tags(dry_run, add_manufacturer_tag)
            stats['tags_applied'] = tag_stats.get('tags_applied', 0)
            self.stdout.write(f"Tags processing complete. Applied {stats['tags_applied']} tags to {tag_stats.get('pages_processed', 0)} pages.")
    
    def _stats_reporting_thread(self, stats, interval, stop_event):
        """Thread for periodic reporting of statistics during processing."""
        while not stop_event.is_set():
            if stop_event.wait(interval):
                break
            
            with stats_lock:
                self._print_stats_report(stats, final=False)
    
    def _print_stats_report(self, stats, final=True):
        """Print a statistics report."""
        elapsed = time.time() - stats['start_time']
        hours, remainder = divmod(elapsed, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        prefix = "Final" if final else "Current"
        
        self.stdout.write(f"\n{prefix} Statistics Report:")
        self.stdout.write(f"Runtime: {int(hours)}h {int(minutes)}m {int(seconds)}s")
        self.stdout.write(f"URLs discovered: {stats['urls_discovered']}")
        self.stdout.write(f"URLs processed: {stats['urls_processed']}")
        self.stdout.write(f"Successful imports: {stats['success_count']}")
        self.stdout.write(f"Failed imports: {stats['failure_count']}")
        self.stdout.write(f"Skipped items: {stats['skipped_count']}")
        self.stdout.write(f"Tags applied: {stats['tags_applied']}")
        
        if stats['urls_processed'] > 0:
            success_rate = (stats['success_count'] / stats['urls_processed']) * 100
            self.stdout.write(f"Success rate: {success_rate:.2f}%")
        
        if stats['urls_processed'] > 0 and elapsed > 0:
            rate = stats['urls_processed'] / elapsed
            self.stdout.write(f"Processing rate: {rate:.2f} URLs/sec")
        
        if not final and stats['failure_count'] > 0:
            self.stdout.write(f"Recent errors: {len(stats['errors'][-5:])}")
    
    def _save_checkpoint(self, checkpoint_file, stats, all_urls, processed_urls=None):
        """Save a checkpoint to resume processing later."""
        if processed_urls is None:
            processed_urls = []
            
        checkpoint_data = {
            'timestamp': datetime.datetime.now().isoformat(),
            'processed_urls': processed_urls,
            'total_urls': len(all_urls),
            'stats': {k: v for k, v in stats.items() if not isinstance(v, (list, dict)) and k not in ['start_time', 'last_report_time']}
        }
        
        try:
            with open(checkpoint_file, 'w') as f:
                json.dump(checkpoint_data, f)
            logger.info(f"Checkpoint saved to {checkpoint_file}")
        except Exception as e:
            logger.error(f"Error saving checkpoint: {str(e)}")

    def discover_urls_parallel(self, category=None, request_delay=1.0, output_file=None, workers=4):
        """Discover URLs in parallel using multiple threads."""
        try:
            self.stdout.write(f"Starting parallel URL discovery with {workers} workers...")
            
            # Create the URL discoverer
            discoverer = TriadUrlDiscoverer(request_delay=request_delay)
            
            # If a specific category is requested, only discover URLs for that category
            if category:
                # First, get all categories
                html = discoverer._make_request(discoverer.base_url)
                if not html:
                    self.stderr.write("Failed to fetch the homepage")
                    return []
                
                categories = discoverer._apply_selector(html, 'categories')
                matching_categories = [cat for cat in categories if category.lower() in cat.get('url', '').lower()]
                
                if not matching_categories:
                    self.stderr.write(f"No categories found matching '{category}'")
                    return []
                
                # Process matching categories in parallel
                with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
                    futures = {}
                    for cat in matching_categories:
                        self.stdout.write(f"Discovering products for category: {cat.get('url', '')}")
                        future = executor.submit(discoverer.discover_product_urls, cat['url'])
                        futures[future] = cat.get('url', '')
                    
                    # Process results as they complete
                    products = []
                    for future in tqdm(concurrent.futures.as_completed(futures), total=len(futures), desc="Categories processed"):
                        category_url = futures[future]
                        try:
                            category_products = future.result()
                            products.extend(category_products)
                            self.stdout.write(f"Found {len(category_products)} products in {category_url}")
                        except Exception as exc:
                            self.stderr.write(f"Error processing {category_url}: {exc}")
                
                discoverer.product_urls = products
            else:
                # Discover categories first
                categories = discoverer.discover_main_categories()
                
                # Process categories in parallel
                with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
                    futures = {}
                    for cat in categories:
                        if 'url' in cat:
                            future = executor.submit(discoverer.discover_product_urls, cat['url'])
                            futures[future] = cat.get('url', '')
                    
                    # Process results as they complete
                    for future in tqdm(concurrent.futures.as_completed(futures), total=len(futures), desc="Categories processed"):
                        category_url = futures[future]
                        try:
                            # Results are automatically added to discoverer.product_urls
                            future.result()
                        except Exception as exc:
                            self.stderr.write(f"Error processing {category_url}: {exc}")
            
            # Save results if output file is specified
            if output_file:
                discoverer.save_results(output_file)
                self.stdout.write(f"Saved {len(discoverer.product_urls)} discovered URLs to {output_file}")
            
            return discoverer.product_urls
            
        except Exception as e:
            self.stderr.write(f"Error in URL discovery: {str(e)}")
            logger.error(f"URL discovery error: {traceback.format_exc()}")
            return []

    def process_urls_parallel(self, urls, scraper, session, parent_page_id, update_existing, skip_images, 
                             dry_run, workers, batch_size, checkpoint_file, stats, process_tags, add_manufacturer_tag):
        """Process URLs in parallel using a thread pool."""
        global stop_processing
        
        self.stdout.write(f"Processing {len(urls)} URLs with {workers} workers...")
        
        # Create queues for task distribution and result collection
        task_queue = queue.Queue()
        result_queue = queue.Queue()
        processed_urls = []
        
        # Add tasks to the queue
        for url in urls:
            task_queue.put(url)
        
        # Setup progress bar
        progress_bar = tqdm(total=len(urls), desc="URLs processed")
        
        # Create and start worker threads
        def worker_thread():
            worker_session = self._create_session_with_retry(3, 5)  # Each worker gets its own session
            worker_scraper = Scraper("apps/scrapers/triadscientific-yamls/mapping.yaml")
            
            while not task_queue.empty() and not stop_processing:
                try:
                    url = task_queue.get(block=False)
                except queue.Empty:
                    break
                
                try:
                    result = self._process_single_url(
                        url, worker_scraper, worker_session, parent_page_id, 
                        update_existing, skip_images, dry_run, process_tags, add_manufacturer_tag
                    )
                    result_queue.put((url, result, None))  # (url, result, error)
                except Exception as e:
                    logger.error(f"Error processing {url}: {str(e)}")
                    result_queue.put((url, None, str(e)))  # (url, result, error)
                finally:
                    task_queue.task_done()
        
        # Start worker threads
        threads = []
        for _ in range(workers):
            thread = threading.Thread(target=worker_thread)
            thread.daemon = True
            thread.start()
            threads.append(thread)
        
        # Process results as they come in
        checkpoint_timer = time.time()
        try:
            processed_count = 0
            while processed_count < len(urls) and not stop_processing:
                try:
                    url, result, error = result_queue.get(timeout=1)
                    processed_urls.append(url)
                    
                    with stats_lock:
                        stats['urls_processed'] += 1
                        if result is not None:
                            if result:
                                stats['success_count'] += 1
                            else:
                                stats['skipped_count'] += 1
                        else:
                            stats['failure_count'] += 1
                            stats['errors'].append((url, error))
                    
                    processed_count += 1
                    progress_bar.update(1)
                    
                    # Save checkpoint periodically (every 5 minutes)
                    if time.time() - checkpoint_timer > 300:  # 5 minutes
                        self._save_checkpoint(checkpoint_file, stats, urls, processed_urls)
                        checkpoint_timer = time.time()
                        
                except queue.Empty:
                    continue
        except KeyboardInterrupt:
            self.stdout.write("Interrupted by user. Waiting for workers to complete...")
            stop_processing = True
        finally:
            progress_bar.close()
            
            # Wait for workers to finish (with timeout)
            for thread in threads:
                thread.join(timeout=5)
            
            # Save final checkpoint
            if not dry_run:
                self._save_checkpoint(checkpoint_file, stats, urls, processed_urls)
    
    def _process_single_url(self, url, scraper, session, parent_page_id, update_existing, 
                           skip_images, dry_run, process_tags, add_manufacturer_tag):
        """Process a single URL and return True if successful, False if skipped, or raise an exception on error."""
        logger.info(f"Processing URL: {url}")
        
        try:
            # Scrape the product data - note: not passing session as the Scraper doesn't support it
            result = scraper.scrape(url)
            if not result:
                logger.warning(f"No data extracted from {url}")
                return False
            
            # Extract the data components
            product_name = result.get("name", "")
            short_description = result.get("short_description", "")
            full_description = result.get("full_description", "")
            models_data = result.get("models", [])
            images_data = result.get("imgs", [])
            
            # Validate the extracted data
            if not self._validate_data(product_name, short_description, full_description, models_data, images_data):
                logger.warning(f"Validation failed for {url}")
                return False
            
            # Extract category information
            category_info = self._extract_category_from_url(url)
            
            # Import the data
            if not dry_run:
                with transaction.atomic():
                    page = self.import_data(product_name, short_description, full_description, 
                                           models_data, images_data, parent_page_id, 
                                           update_existing, skip_images, url)
                    
                    if page and process_tags:
                        self._apply_tags(page, category_info, add_manufacturer_tag)
            else:
                logger.info(f"[DRY RUN] Would import: {product_name}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error processing {url}: {str(e)}")
            logger.error(traceback.format_exc())
            raise

    def _create_session_with_retry(self, retry_attempts, retry_delay):
        """
        Create a requests session with retry capability.
        
        Args:
            retry_attempts: Number of retry attempts
            retry_delay: Delay between retries in seconds
            
        Returns:
            Requests session with retry capability
        """
        session = requests.Session()
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=retry_attempts,
            backoff_factor=retry_delay,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"]
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        return session

    def _setup_logging(self, log_file):
        """Configure logging for the scraping process."""
        log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        
        # Configure file handler
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(log_formatter)
        file_handler.setLevel(logging.INFO)
        
        # Configure console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(log_formatter)
        console_handler.setLevel(logging.WARNING)
        
        # Add handlers to the logger
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        logger.setLevel(logging.INFO)

    def _validate_data(self, product_name, short_description, full_description, models_data, images_data):
        """
        Validate the extracted data to ensure it meets our requirements before import.
        
        Returns:
            True if valid, False otherwise
        """
        validation_errors = []
        
        # Check product name
        if not product_name:
            validation_errors.append("Missing product name")
        elif len(product_name) < 3:
            validation_errors.append("Product name too short")
            
        # Check descriptions
        if not short_description and not full_description:
            validation_errors.append("Missing description (both short and full)")
            
        # Check model data - must have at least one model
        if not models_data:
            validation_errors.append("No model data found")
        
        # Note: Not checking for images as they're not mandatory
        # (images may be missing on some products)
        
        # Log any validation errors
        if validation_errors:
            logger.warning(f"Validation errors for {product_name}:")
            for error in validation_errors:
                logger.warning(f"- {error}")
                
        return len(validation_errors) == 0

    def _extract_category_from_url(self, url):
        """
        Extract category information from a product URL.
        
        Args:
            url: The product URL
            
        Returns:
            Dictionary with category_name and optionally subcategory_name
        """
        # Extract category from URL pattern
        # Expected format: http://www.triadscientific.com/en/products/[category]/[id]/[product-name]/[id]
        pattern = r'/en/products/([a-z0-9\-]+)/\d+'
        match = re.search(pattern, url)
        
        if not match:
            logger.warning(f"Could not extract category from URL: {url}")
            return None
            
        category_slug = match.group(1)
        
        # Convert slug to readable name
        category_name = category_slug.replace('-', ' ').title()
        
        # Advanced processing for improved readability
        # Handle common abbreviations
        category_name = category_name.replace('Gc ', 'GC ')
        category_name = category_name.replace('Hplc ', 'HPLC ')
        category_name = category_name.replace('Ftir ', 'FTIR ')
        category_name = category_name.replace('Uv ', 'UV ')
        category_name = category_name.replace('Aa ', 'AA ')
        
        return {
            'category_slug': category_slug,
            'category_name': category_name
        }

    @transaction.atomic
    def import_data(self, product_name, short_description, full_description, 
                   models_data, images_data, parent_page_id, update_existing, skip_images, url=None):
        """
        Import extracted data into Wagtail models.
        
        Returns:
            The created or updated LabEquipmentPage
        """
        logger.info(f"Importing data for product: {product_name}")
        
        # Validation already done in _process_single_url
        slug = slugify(product_name)
        
        # Check if page already exists
        existing_page = LabEquipmentPage.objects.filter(slug=slug).first()
        
        # Handle existing pages based on update_existing flag
        if existing_page:
            if update_existing:
                logger.info(f"Updating existing page: {product_name}")
                page = existing_page
            else:
                logger.info(f"Page exists and update_existing is False. Skipping: {product_name}")
                return None
        else:
            # Create new page if it doesn't exist
            if parent_page_id is None:
                logger.error("parent_page_id is required for new pages")
                raise ValueError("parent_page_id is required for new pages")
                
            parent_page = Page.objects.get(id=parent_page_id)
            
            logger.info(f"Creating new page: {product_name}")
            page = LabEquipmentPage(
                title=product_name[:255],  # Title has a max length
                draft_title=product_name[:255],
                slug=slug,
                show_in_menus=False,
                search_description=short_description[:255] if short_description else "",
            )
            
            # Save the page to generate an ID
            parent_page.add_child(instance=page)
            page.save_revision()
        
        # Update content fields
        page.title = product_name[:255]
        page.short_description = short_description[:1024] if short_description else ""
        page.full_description = full_description
        
        # Store the source URL if provided
        if url:
            page.source_url = url
        
        # Save the page
        page.save_revision().publish()
        
        # Process images
        if not skip_images:
            self.handle_images(page, images_data)
        
        # Process models and specs
        self.handle_models(page, models_data)
        
        return page

    def handle_images(self, page, images_data):
        """Process images for a LabEquipmentPage."""
        if not images_data:
            logger.warning(f"No images to process for {page.title}")
            return
            
        logger.info(f"Processing {len(images_data)} images for {page.title}")
        
        # Delete existing images if we're updating
        LabEquipmentGalleryImage.objects.filter(page=page).delete()
        
        # Create image downloader with error handling
        downloader = ImageDownloader()
        
        # Process each image URL
        for index, image_url in enumerate(images_data):
            try:
                # Download and create the image
                image = downloader.download_and_create_image(image_url)
                
                if image:
                    # Create gallery image
                    gallery_image = LabEquipmentGalleryImage(
                        page=page,
                        image=image,
                        title=f"{page.title} - Image {index + 1}",
                        sort_order=index
                    )
                    gallery_image.save()
                    logger.info(f"Added image {index + 1} to {page.title}")
                else:
                    logger.warning(f"Failed to download image: {image_url}")
            except Exception as e:
                # Log but continue with next image
                logger.error(f"Error processing image {image_url}: {str(e)}")
                logger.debug(traceback.format_exc())

    def handle_models(self, page, models_data):
        """Process model data for a LabEquipmentPage."""
        if not models_data:
            logger.warning(f"No models to process for {page.title}")
            return
            
        logger.info(f"Processing model data for {page.title}")
        
        # Delete existing models if we're updating
        EquipmentModel.objects.filter(equipment_page=page).delete()
        LabEquipmentPageSpecGroup.objects.filter(page=page).delete()
        
        # Create the model
        model = EquipmentModel(
            equipment_page=page,
            name=page.title,
            description=page.short_description,
        )
        model.save()
        
        # Process specifications if available
        if 'specs' in models_data:
            # We're using a simplified approach for specs in Triad
            # Create a single spec group for all specifications
            spec_group = SpecGroup(name="Specifications")
            spec_group.save()
            
            # Link the spec group to the page
            page_spec_group = LabEquipmentPageSpecGroup(
                page=page,
                spec_group=spec_group,
                sort_order=0
            )
            page_spec_group.save()
            
            # Link the spec group to the model
            model_spec_group = EquipmentModelSpecGroup(
                model=model,
                spec_group=spec_group,
                sort_order=0
            )
            model_spec_group.save()
            
            # Add placeholder spec directing to full description
            spec = Spec(
                name="Technical Specifications",
                value="Please see the full description for detailed specifications",
                sort_order=0,
                spec_group=spec_group
            )
            spec.save()
            
            logger.info(f"Added specification group for {page.title}")

    def _apply_tags(self, page, category_info, add_manufacturer_tag=False):
        """Apply tags to a page based on category information."""
        if not category_info:
            logger.warning(f"No category info for {page.title}")
            return
            
        # Apply category tag
        if 'category_name' in category_info:
            category_tag_added = self._add_tag(
                page, 
                "Product Category", 
                category_info['category_name']
            )
            
            if category_tag_added:
                logger.info(f"Added category tag '{category_info['category_name']}' to {page.title}")
        
        # Apply manufacturer tag if requested
        if add_manufacturer_tag:
            manufacturer_tag_added = self._add_tag(
                page,
                "Manufacturer",
                "Triad Scientific"
            )
            
            if manufacturer_tag_added:
                logger.info(f"Added manufacturer tag 'Triad Scientific' to {page.title}")

    def _add_tag(self, page, category, tag_name):
        """
        Add a tag in a specific category to a page.
        
        Returns:
            True if tag was added, False otherwise
        """
        # Get or create the tag category
        tag_category, created = TagCategory.objects.get_or_create(name=category)
        
        # Get or create the tag
        tag, created = CategorizedTag.objects.get_or_create(
            category=tag_category,
            name=tag_name
        )
        
        # Check if the page already has this tag
        if CategorizedPageTag.objects.filter(page=page, tag=tag).exists():
            return False
            
        # Add the tag to the page
        CategorizedPageTag.objects.create(
            page=page,
            tag=tag
        )
        
        return True

    def process_tags(self, dry_run=False, add_manufacturer_tag=False):
        """
        Process tags for existing products.
        
        Returns:
            Stats dictionary with tagging results
        """
        logger.info("Processing tags for existing products")
        
        # Get all LabEquipmentPages with a source_url
        pages = LabEquipmentPage.objects.filter(source_url__isnull=False)
        
        tags_applied = 0
        pages_processed = 0
        
        for page in pages:
            if not page.source_url:
                continue
                
            # Extract category from URL
            category_info = self._extract_category_from_url(page.source_url)
            if not category_info:
                continue
                
            # Apply tags
            if not dry_run:
                self._apply_tags(page, category_info, add_manufacturer_tag)
                tags_added = 1 + (1 if add_manufacturer_tag else 0)
                tags_applied += tags_added
                logger.info(f"Applied {tags_added} tags to {page.title}")
            
            pages_processed += 1
            
        logger.info(f"Processed tags for {pages_processed} pages, applied {tags_applied} tags")
        
        return {
            'pages_processed': pages_processed,
            'tags_applied': tags_applied
        }

