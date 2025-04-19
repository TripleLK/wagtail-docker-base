from django.core.management.base import BaseCommand, CommandError
from scrapers.Scrapers import Scraper  # adjust the import based on your project structure

class Command(BaseCommand):
    help = 'Scrapes a given page and creates/updates Wagtail content'

    def add_arguments(self, parser):
        parser.add_argument('target_url', type=str, help='The URL to scrape')
        parser.add_argument('--config', type=str, default='default.yaml',
                            help='Path to the scraper YAML configuration file')

    def handle(self, *args, **options):
        target_url = options['target_url']
        config_path = options['config']
        self.stdout.write('Starting scraper for {} using config {}'.format(target_url, config_path))
        
        try:
            scraper = Scraper(config_path)
            result = scraper.scrape(target_url)
            # Process the result and integrate with your Wagtail pages here.
            self.stdout.write('Scrape successful. Result:')
            self.stdout.write(str(result))
        except Exception as e:
            raise CommandError('An error occurred: {}'.format(e))
