#!/usr/bin/env python
import logging
from url_discovery import TriadUrlDiscoverer

# Configure logging to show more details
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Test a small sample of categories
def test_sample():
    discoverer = TriadUrlDiscoverer()
    
    print("Discovering categories...")
    categories = discoverer.discover_main_categories()
    
    print(f"\nFound {len(categories)} categories")
    print("Processing first 5 categories as a sample...")
    
    total_products = 0
    
    # Only process the first 5 categories as a sample
    for i, category in enumerate(categories[:5]):
        if 'url' in category and 'category_name' in category:
            print(f"\nProcessing category {i+1}: {category['category_name']}")
            products = discoverer.discover_product_urls(category['url'])
            print(f"  Found {len(products)} products")
            total_products += len(products)
    
    print(f"\nSample test completed. Found {total_products} products from 5 categories")
    print("Saving results to sample_product_urls.txt")
    
    discoverer.save_results('sample_product_urls.txt')
    
    # Print a few product entries as examples
    if discoverer.product_urls:
        print("\nSample product entries:")
        for i, product in enumerate(discoverer.product_urls[:5]):
            if 'url' in product and 'product_name' in product:
                print(f"{i+1}. {product['product_name']}: {product['url']}")
            elif 'url' in product:
                print(f"{i+1}. {product['url']}")
            
            if i >= 4:  # Show only first 5
                break

if __name__ == "__main__":
    test_sample() 