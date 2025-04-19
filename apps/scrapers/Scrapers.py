from scrapers.Selectors import *
from bs4 import BeautifulSoup

class Scraper:
    def __init__(self, filepath):
        self.selector = Selector.fromFilePath(filepath)

    def scrape(self, href):
        new_soup = BeautifulSoup(requests.get(href).text, 'html.parser')
        return self.selector.select(Selected(new_soup, SelectedType.SINGLE)).collapsed_value

