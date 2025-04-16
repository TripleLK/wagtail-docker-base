#!/usr/bin/env python3
# sample_scrape.py

import requests
from bs4 import BeautifulSoup
import bs4
from Selectors import *


target_url = "https://webscraper.io/test-sites/e-commerce/allinone/computers/laptops"
new_soup = BeautifulSoup(requests.get(target_url).text, 'html.parser')
ns_selected = Selected(new_soup, SelectedType.SINGLE)

# thumbnails selector will retrieve each of the thumbnail boxes
thumbnails_selector = SoupSelector({"class": "thumbnail"})

# name el selector will retrieve the title element for a single thumbnail
name_el_selector = SoupSelector({"class": "title"}, index=0)

# title selector will retrieve the title value of a tag (title is present on the names of the thumbnails)
title_selector = AttrSelector("title")

# name selector will retrieve the value of title in a single thumbnail (which gives us the name of that item)
name_selector = SeriesSelector([name_el_selector, title_selector])

# and all names selector will retrieve all the thumbnails, then get all of their names!
all_names_selector = SeriesSelector([thumbnails_selector, ForEachSelector(name_selector)])

thumbnails = thumbnails_selector(ns_selected)
a_thumb = thumbnails.value[0]
