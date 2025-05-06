#!/usr/bin/env python3
# apps/scrapers/examples/css_selector_example.py

"""
Example showing how to use the new CSS selector to simplify HTML scraping.

This demonstrates:
1. How to parse HTML with BeautifulSoup
2. How to use the CSSSelector to extract elements
3. How to chain selectors together
4. How to serialize and deserialize selectors to/from YAML
"""

import requests
from bs4 import BeautifulSoup
import yaml

# Import the selectors
from ..selectors import (
    Selector, Selected, SelectedType,
    CSSSelector, TextSelector, IndexedSelector
)

def fetch_and_parse(url):
    """Fetch a URL and parse it with BeautifulSoup."""
    response = requests.get(url)
    response.raise_for_status()  # Raise exception for bad status codes
    return BeautifulSoup(response.text, 'html.parser')

def basic_css_example():
    """Basic example of using CSS selectors."""
    # Parse a simple HTML document
    html = """
    <html>
        <body>
            <div class="container">
                <h1>Title</h1>
                <p class="intro">First paragraph</p>
                <p>Second paragraph</p>
                <ul>
                    <li>Item 1</li>
                    <li>Item 2</li>
                    <li>Item 3</li>
                </ul>
            </div>
        </body>
    </html>
    """
    soup = BeautifulSoup(html, 'html.parser')
    
    # Wrap the soup in a Selected object
    soup_selected = Selected(soup, SelectedType.SINGLE)
    
    # Example 1: Select all paragraphs
    p_selector = CSSSelector('p')
    p_elements = p_selector.select(soup_selected)
    print("All paragraphs:")
    for i, p in enumerate(p_elements.value):
        print(f"  {i}: {p.value.get_text()}")
    
    # Example 2: Select a specific paragraph with class "intro"
    intro_selector = CSSSelector('p.intro')
    intro_elements = intro_selector.select(soup_selected)
    if intro_elements.value:
        intro_element = intro_elements.value[0]
        print("\nIntro paragraph:", intro_element.value.get_text())
    
    # Example 3: Select list items and get the second one using IndexedSelector
    li_selector = CSSSelector('li')
    li_elements = li_selector.select(soup_selected)
    second_li = IndexedSelector(1).select(li_elements)
    print("\nSecond list item:", second_li.value.get_text())
    
    # Example 4: Using the index parameter of CSSSelector directly
    third_li_selector = CSSSelector('li', index=2)
    third_li = third_li_selector.select(soup_selected)
    print("\nThird list item (direct):", third_li.value.get_text())
    
    # Example 5: Chaining selectors to get text
    h1_text_selector = CSSSelector('h1')
    h1_elements = h1_text_selector.select(soup_selected)
    h1_element = IndexedSelector(0).select(h1_elements)
    h1_text = TextSelector().select(h1_element)
    print("\nTitle text:", h1_text.value)

def yaml_serialization_example():
    """Example of serializing selectors to YAML and back."""
    # Create a selector
    title_selector = CSSSelector('h1')
    
    # Serialize to YAML dict
    yaml_dict = title_selector.toYamlDict()
    print("\nYAML dict:", yaml_dict)
    
    # Convert to YAML string
    yaml_str = yaml.dump(yaml_dict, default_flow_style=False)
    print("\nYAML string:")
    print(yaml_str)
    
    # Deserialize from YAML
    parsed_yaml = yaml.safe_load(yaml_str)
    recreated_selector = Selector.fromYamlDict(parsed_yaml)
    
    print("\nRecreated selector:", type(recreated_selector).__name__)
    
    # Validate it works the same
    html = "<html><body><h1>Test Title</h1></body></html>"
    soup = BeautifulSoup(html, 'html.parser')
    soup_selected = Selected(soup, SelectedType.SINGLE)
    
    # Apply the recreated selector
    result = recreated_selector.select(soup_selected)
    if result.value:
        print("Selected title:", result.value[0].value.get_text())
        
def real_world_example():
    """A more practical example with a real website."""
    try:
        # Fetch a web page (using a stable example)
        soup = fetch_and_parse('https://quotes.toscrape.com/')
        soup_selected = Selected(soup, SelectedType.SINGLE)
        
        # Create a selector to extract quotes
        quotes_selector = CSSSelector('.quote')
        quotes = quotes_selector.select(soup_selected)
        
        print(f"\nFound {len(quotes.value)} quotes:")
        
        # Process the first 3 quotes
        for i, quote_selected in enumerate(quotes.value[:3]):
            # For each quote, extract the text, author, and tags
            quote_text_selector = CSSSelector('.text')
            quote_author_selector = CSSSelector('.author')
            quote_tags_selector = CSSSelector('.tag')
            
            # Apply the selectors to the quote element
            quote_text_elements = quote_text_selector.select(quote_selected)
            quote_author_elements = quote_author_selector.select(quote_selected)
            quote_tags_elements = quote_tags_selector.select(quote_selected)
            
            # Extract text from the first (and only) text element
            if quote_text_elements.value:
                text_element = IndexedSelector(0).select(quote_text_elements)
                text = TextSelector().select(text_element).value
            else:
                text = "No text found"
                
            # Extract author
            if quote_author_elements.value:
                author_element = IndexedSelector(0).select(quote_author_elements)
                author = TextSelector().select(author_element).value
            else:
                author = "Unknown author"
                
            # Extract tags
            tags = []
            for tag_selected in quote_tags_elements.value:
                tag_text = TextSelector().select(tag_selected).value
                tags.append(tag_text)
                
            # Print the results
            print(f"\nQuote {i+1}:")
            print(f"  Text: {text}")
            print(f"  Author: {author}")
            print(f"  Tags: {', '.join(tags)}")
            
    except Exception as e:
        print(f"Error in real_world_example: {e}")
        
if __name__ == "__main__":
    print("=== Basic CSS Selector Example ===")
    basic_css_example()
    
    print("\n=== YAML Serialization Example ===")
    yaml_serialization_example()
    
    print("\n=== Real World Example ===")
    real_world_example() 