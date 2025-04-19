import json
from bs4 import BeautifulSoup
import bs4
from Selectors import *
import yaml

TEST_FILE_NAME="airscience-yamls/mapping.yaml"

yam_scraper = Selector.fromFilePath(TEST_FILE_NAME)

target_url = "https://www.airscience.com/product-category-page?brandname=safekeeper-forensic-evidence-drying-cabinets&brand=20"
new_soup = BeautifulSoup(requests.get(target_url).text, 'html.parser')
ns_selected = Selected(new_soup, SelectedType.SINGLE)


result = yam_scraper.select(ns_selected).collapsed_value

