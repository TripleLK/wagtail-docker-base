import Selectors
from bs4 import BeautifulSoup
import requests
url = "https://www.airscience.com/product-category-page?brandname=purair-flow-laminar-flow-cabinets&brand=13"
print("url: " + url)
soup = BeautifulSoup(requests.get(url).text, "html.parser")

css_sel = Selectors.CSSSelector("#content-3 > p > strong:nth-child(1)")

print("sel: " + str(css_sel(soup)))

export = {
    "url": url,
    "css_sel": css_sel(soup)
}

# The following is for testing in ipython
from Selectors import *
url =  "https://www.airscience.com/product-category-page?brandname=purair-flow-laminar-flow-cabinets&brand=13"
soup = BeautifulSoup(requests.get(url).text, "html.parser")
soup_sel = Selected(soup, SelectedType.SINGLE)

css_sel = CSSSelector("#content-3 > p > strong:nth-child(1)")

name = Selector.fromFilePath("airscience-yamls/name.yaml")

print("name: " + str(name.select(soup_sel)))
