import asyncio
import json
from urllib.parse import urljoin, urlparse
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig
from crawl4ai.extraction_strategy import JsonCssExtractionStrategy

class ZLineVariantScraper:
    def __init__(self, base_url="https://zlinekitchen.com"):
        self.base_url = base_url
        self.visited = set()
        self.queue = []
        self.all_variants = []
        
    def normalize_url(self, url):
        """Normalize URL to handle relative and absolute paths"""
        if url.startswith('/'):
            return url
        elif url.startswith('http'):
            parsed = urlparse(url)
            return parsed.path + ('?' + parsed.query if parsed.query else '')
        return url
    
    async def get_all_variants(self, start_url, crawler, config):
        """BFS traversal to discover all product variants"""
        # Initialize with starting URL
        start_url_normalized = self.normalize_url(start_url)
        self.queue.append(start_url_normalized)
        
        iteration = 0
        max_iterations = 100  # Safety limit
        
        while self.queue and iteration < max_iterations:
            current_url = self.queue.pop(0)
            iteration += 1
            
            # Skip if already visited
            if current_url in self.visited:
                print(f"⚠️  Already visited: {current_url}")
                continue
                
            self.visited.add(current_url)
            full_url = urljoin(self.base_url, current_url)
            print(f"🔍 [{iteration}] Scraping: {current_url}")
            print(f"    Full URL: {full_url}")
            
            try:
                result = await crawler.arun(full_url, config=config)
                
                if not result.success:
                    print(f"❌ Failed to scrape {current_url}: {result.error_message}")
                    continue
                
                # Parse extracted data
                try:
                    extracted_data = json.loads(result.extracted_content)
                    if not extracted_data:
                        print(f"⚠️  No data extracted from {current_url}")
                        continue
                        
                    data = extracted_data[0] if isinstance(extracted_data, list) else extracted_data
                    
                    # Store variant data
                    variant_info = {
                        'url': current_url,
                        'title': data.get('title', 'Unknown Title'),
                        'price': data.get('price', '0'),
                        'description': data.get('description', ''),
                        'variant_count': len(data.get('variant_urls', []))
                    }
                    self.all_variants.append(variant_info)
                    
                    print(f"✅ Found: {variant_info['title']} | Price: ${int(variant_info['price'])/100:.2f}")
                    print(f"    Variants found on page: {variant_info['variant_count']}")
                    
                    # Extract and queue new variant URLs
                    new_urls_added = 0
                    variant_urls = data.get('variant_urls', [])
                    
                    for variant in variant_urls:
                        variant_url = variant.get('url', '')
                        if variant_url:
                            normalized_variant_url = self.normalize_url(variant_url)
                            
                            # Only add to queue if not visited and not already queued
                            if (normalized_variant_url not in self.visited and 
                                normalized_variant_url not in self.queue):
                                self.queue.append(normalized_variant_url)
                                new_urls_added += 1
                    
                    print(f"    New URLs added to queue: {new_urls_added}")
                    print(f"    Queue size: {len(self.queue)}")
                    print(f"    Total visited: {len(self.visited)}")
                    print("-" * 60)
                    
                except json.JSONDecodeError as e:
                    print(f"❌ JSON decode error for {current_url}: {e}")
                    print(f"Raw content: {result.extracted_content[:200]}...")
                    
            except Exception as e:
                print(f"❌ Error scraping {current_url}: {e}")
                continue
                
            # Small delay between requests
            await asyncio.sleep(1)
        
        return self.all_variants

async def main():
    browser_config = BrowserConfig(
        headless=True,
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        viewport_width=1920,
        viewport_height=1080
    )

    # Enhanced CSS extraction strategy
    css_extraction = {
        "name": "ZLine Products",
        "baseSelector": ".ecom-sections",
        "fields": [
            {
                "name": "title",
                "selector": ".ecom-product__heading h1, .ecom-product__heading, .product-title",
                "type": "text"
            },
            {
                "name": "price", 
                "selector": "[data-price], .price, .ecom-price",
                "type": "attribute",
                "attribute": "data-price"
            },
            {
                "name": "description",
                "selector": ".ecom-html-des, .product-description, .ecom-description",
                "type": "text"
            },
            {
                "name": "variant_urls",
                "selector": "[swatch-url]",
                "type": "list", 
                "fields": [
                    {
                        "name": "url",
                        "type": "attribute",
                        "attribute": "swatch-url"
                    },
                    {
                        "name": "variant_name",
                        "type": "text"
                    }
                ]
            }
        ]
    }

    extraction_strategy = JsonCssExtractionStrategy(css_extraction)
    
    # Enhanced JavaScript for better variant discovery
    enhanced_js = """
    console.log('🚀 Starting variant discovery...');
    
    // Wait for initial page load
    await new Promise(resolve => setTimeout(resolve, 3000));
    
    // Function to trigger all interactive elements
    function triggerVariantElements() {
        const selectors = [
            '[swatch-url]',
            '.swatch-button', 
            '.variant-option',
            '.product-variant',
            '.color-swatch',
            '.size-option',
            '[data-variant]',
            '.variant-selector button',
            '.variant-selector a'
        ];
        
        let foundElements = 0;
        selectors.forEach(selector => {
            const elements = document.querySelectorAll(selector);
            elements.forEach(el => {
                try {
                    // Hover and click to trigger any dynamic loading
                    el.dispatchEvent(new Event('mouseenter', {bubbles: true}));
                    el.dispatchEvent(new Event('mouseover', {bubbles: true}));
                    el.dispatchEvent(new Event('focus', {bubbles: true}));
                    
                    // Try clicking if it's clickable
                    if (el.tagName === 'BUTTON' || el.tagName === 'A' || el.onclick) {
                        el.click();
                    }
                    foundElements++;
                } catch (e) {
                    console.log('Error triggering element:', e);
                }
            });
        });
        
        console.log(`Triggered ${foundElements} variant elements`);
        return foundElements;
    }
    
    // Trigger variants multiple times to catch lazy-loaded content
    triggerVariantElements();
    await new Promise(resolve => setTimeout(resolve, 2000));
    
    triggerVariantElements();
    await new Promise(resolve => setTimeout(resolve, 2000));
    
    // Scroll to trigger any scroll-based loading
    window.scrollTo(0, document.body.scrollHeight);
    await new Promise(resolve => setTimeout(resolve, 1000));
    
    // Final trigger
    const finalCount = triggerVariantElements();
    
    // Log what we found
    const swatchElements = document.querySelectorAll('[swatch-url]');
    console.log(`Final swatch elements found: ${swatchElements.length}`);
    swatchElements.forEach((el, idx) => {
        console.log(`Swatch ${idx + 1}: ${el.getAttribute('swatch-url')}`);
    });
    
    console.log('✅ Variant discovery complete');
    """
    
    config = CrawlerRunConfig(
        extraction_strategy=extraction_strategy,
        js_code=enhanced_js,
        wait_for="css:.ecom-sections",
        delay_before_return_html=5.0,
        page_timeout=30000,
        remove_overlay_elements=True
    )
    
    start_url = "/products/zline-autograph-edition-30-paramount-gas-range-stainless-steel-champagne-bronze-sgrz-30-cb"
    
    scraper = ZLineVariantScraper()
    
    async with AsyncWebCrawler(config=browser_config) as crawler:
        print("🎯 Starting ZLine variant discovery...")
        print(f"📍 Starting URL: {start_url}")
        print("=" * 80)
        
        all_variants = await scraper.get_all_variants(start_url, crawler, config)
        
        print("=" * 80)
        print(f"🎉 DISCOVERY COMPLETE!")
        print(f"📊 Total variants discovered: {len(all_variants)}")
        print(f"🔗 Total URLs visited: {len(scraper.visited)}")
        print()
        
        print("📋 VARIANT SUMMARY:")
        print("-" * 60)
        for i, variant in enumerate(all_variants, 1):
            price_display = f"${int(variant['price'])/100:.2f}" if variant['price'] and variant['price'] != '0' else "Price not available"
            print(f"{i:2d}. {variant['title']}")
            print(f"    💰 {price_display}")
            print(f"    🔗 {variant['url']}")
            print(f"    🔢 Variants on page: {variant['variant_count']}")
            print()

if __name__ == "__main__":
    asyncio.run(main())