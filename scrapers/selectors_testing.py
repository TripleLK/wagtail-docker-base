#!/usr/bin/env python3
# sample_scrape.py

import requests
from bs4 import BeautifulSoup
import bs4
from Selectors import *


target_url = "https://www.airscience.com/product-category-page?brandname=purair-pcr-laminar-flow-cabinets&brand=12"
new_soup = BeautifulSoup(requests.get(target_url).text, 'html.parser')
ns_selected = Selected(new_soup, SelectedType.SINGLE)

# thumbnails selector will retrieve each of the thumbnail boxes
thumbnails_selector = SoupSelector({"class": "thumbnail"})





"""
Example a_thumb:
<div class="card thumbnail" itemscope="" itemtype="https://schema.org/Product">
<div class="product-wrapper card-body">
<img alt="item" class="img-fluid card-img-top image img-responsive" itemprop="image" src="/images/test-sites/e-commerce/items/cart2.png"/>
<div class="caption">
<h4 class="price float-end card-title pull-right" itemprop="offers" itemscope="" itemtype="https://schema.org/Offer">
<span itemprop="price">$295.99</span>
<meta content="USD" itemprop="priceCurrency"/>
</h4>
<h4>
<a class="title" href="/test-sites/e-commerce/allinone/product/60" itemprop="name" title="Asus VivoBook X441NA-GA190">
						Asus VivoBook...
					</a>
</h4>
<p class="description card-text" itemprop="description">Asus VivoBook X441NA-GA190 Chocolate Black, 14", Celeron N3450, 4GB, 128GB SSD, Endless OS, ENG kbd</p>
</div>
<div class="ratings" itemprop="aggregateRating" itemscope="" itemtype="https://schema.org/AggregateRating">
<p class="review-count float-end">
<span itemprop="reviewCount">14</span> reviews
				</p>
<p data-rating="3">
<span class="ws-icon ws-icon-star"></span>
<span class="ws-icon ws-icon-star"></span>
<span class="ws-icon ws-icon-star"></span>
</p>
</div>
</div>
</div>

"""

img_src_selector = SeriesSelector([SoupSelector({'tag_name': 'img', 'class': 'card-img-top'}, index=0), AttrSelector('src')])

price_selector = SeriesSelector([SoupSelector({'tag_name': 'span', 'itemprop': 'price'}, index=0), TextSelector()])

currency_selector = SeriesSelector([SoupSelector({'tag_name': 'meta', 'itemprop': 'priceCurrency'}, index=0), AttrSelector('content')])

name_selector = SeriesSelector([SoupSelector({"class": "title"}, index=0), AttrSelector("title")])

review_count_selector = SeriesSelector([SoupSelector({'itemprop': 'reviewCount'}, 0), TextSelector()])

rating_selector = SeriesSelector([SoupSelector({'data-rating': True}, 0), AttrSelector('data-rating')])


mapping_selector = MappingSelector({'img': img_src_selector, 'price': price_selector, 'currency': currency_selector, 'name': name_selector, 'reviews': review_count_selector, 'rating': rating_selector})

# and all names selector will retrieve all the thumbnails, then get all of their names!
all_maps_selector = SeriesSelector([thumbnails_selector, ForEachSelector(mapping_selector)])

all_items = all_maps_selector.select(ns_selected)
