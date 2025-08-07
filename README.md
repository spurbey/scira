# ZLine Kitchen Product Variant Scraper

A web scraper that implements BFS (Breadth-First Search) traversal to discover ALL product variants on ZLine Kitchen's website. This scraper solves the problem of discovering the complete variant network by following swatch-url attributes across all connected product pages.

## Problem Solved

ZLine Kitchen product pages contain `swatch-url` attributes that link to other product variants. The challenge is to traverse ALL connected variants without duplicates to map the entire variant network, not just get the variants listed on a single page.

## Features

- **Complete BFS Traversal**: Visits every unique variant URL until the entire network is mapped
- **Duplicate Prevention**: Uses visited set and queue management to avoid revisiting URLs
- **Enhanced JavaScript**: Triggers lazy loading and dynamic content for better variant discovery
- **Robust Error Handling**: Continues scraping even if individual pages fail
- **Detailed Logging**: Shows progress, queue status, and discovery metrics

## Technical Implementation

### BFS Algorithm
1. Start with one product URL
2. Extract all `[swatch-url]` attributes from that page
3. Add new URLs to queue (avoiding duplicates)
4. Visit each URL in queue and repeat process
5. Continue until no new URLs are found

### Key Components
- **ZLineVariantScraper Class**: Manages state and BFS traversal
- **URL Normalization**: Handles relative/absolute paths consistently
- **Enhanced JavaScript**: Triggers multiple selectors and events for variant discovery
- **JsonCssExtractionStrategy**: Extracts structured data from product pages

## Installation

```bash
pip install -r requirements.txt
```

## Usage

```bash
python zline_scraper.py
```

The scraper will:
1. Start with the predefined ZLine product URL
2. Discover all connected variants using BFS traversal
3. Extract title, price, description, and variant URLs from each page
4. Display a comprehensive summary of all discovered variants

## Output

The scraper provides:
- Real-time progress updates during crawling
- Queue size and visited URL counts
- Final summary with all discovered variants
- Price information and variant counts per page

## Configuration

You can modify the starting URL in the `main()` function:

```python
start_url = "/products/your-zline-product-url"
```

## Safety Features

- Maximum iteration limit (100) to prevent infinite loops
- 1-second delay between requests to be respectful to the server
- Comprehensive error handling for network issues
- Timeout settings for page loading

## Example Output

```
🎯 Starting ZLine variant discovery...
📍 Starting URL: /products/zline-autograph-edition-30-paramount-gas-range-stainless-steel-champagne-bronze-sgrz-30-cb
================================================================================
🔍 [1] Scraping: /products/zline-autograph-edition-30-paramount-gas-range-stainless-steel-champagne-bronze-sgrz-30-cb
✅ Found: ZLINE 30" Gas Range | Price: $2499.00
    Variants found on page: 17
    New URLs added to queue: 17
    Queue size: 17
    Total visited: 1
------------------------------------------------------------
[... continues for all variants ...]
================================================================================
🎉 DISCOVERY COMPLETE!
📊 Total variants discovered: 45
🔗 Total URLs visited: 45
```

## Troubleshooting

If you encounter issues:

1. **No variants found**: Check if the website structure has changed
2. **Connection errors**: Ensure stable internet connection
3. **JavaScript errors**: The enhanced JS handles most dynamic content cases
4. **Memory issues**: The scraper includes safety limits and delays

## Notes

- The scraper runs in non-headless mode by default for debugging
- Modify `headless=True` in browser config for production use
- The scraper respects the website's structure and includes appropriate delays
