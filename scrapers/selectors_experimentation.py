from bs4 import BeautifulSoup
import bs4
from Selectors import *
import yaml

TEST_FILE_NAME="mapping.yaml"

with open(TEST_FILE_NAME, 'r') as file:
    testing_yaml = file.read()

testing_dict = yaml.safe_load(testing_yaml)

yam_scraper = Selector.fromYamlDict(testing_dict)

target_url = "https://www.airscience.com/product-category-page?brandname=purair-pcr-laminar-flow-cabinets&brand=12"
new_soup = BeautifulSoup(requests.get(target_url).text, 'html.parser')
ns_selected = Selected(new_soup, SelectedType.SINGLE)

result = yam_scraper.select(ns_selected).collapsed_value

print("Resulting dict:")
print(result)

