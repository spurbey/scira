#!/usr/bin/env python3
"""
Demo script showing how to run the ZLine variant scraper with different configurations.
"""

import asyncio
import json
from zline_scraper import ZLineVariantScraper, main
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig
from crawl4ai.extraction_strategy import JsonCssExtractionStrategy

async def quick_demo():
    """Run a quick demo with limited iterations for testing"""
    print("🚀 Running Quick Demo (Limited to 5 pages)")
    print("=" * 60)
    
    browser_config = BrowserConfig(
        headless=True,
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )

    css_extraction = {
        "name": "ZLine Products Demo",
        "baseSelector": ".ecom-sections",
        "fields": [
            {
                "name": "title",
                "selector": ".ecom-product__heading h1, .ecom-product__heading",
                "type": "text"
            },
            {
                "name": "price", 
                "selector": "[data-price]",
                "type": "attribute",
                "attribute": "data-price"
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
                    }
                ]
            }
        ]
    }

    extraction_strategy = JsonCssExtractionStrategy(css_extraction)
    
    config = CrawlerRunConfig(
        extraction_strategy=extraction_strategy,
        js_code="""
        await new Promise(resolve => setTimeout(resolve, 2000));
        document.querySelectorAll('[swatch-url], .swatch-button').forEach(el => {
            el.dispatchEvent(new Event('mouseenter'));
        });
        await new Promise(resolve => setTimeout(resolve, 1000));
        """,
        wait_for="css:.ecom-sections",
        delay_before_return_html=3.0
    )
    
    # Custom scraper with limited iterations for demo
    class DemoScraper(ZLineVariantScraper):
        async def get_all_variants(self, start_url, crawler, config):
            start_url_normalized = self.normalize_url(start_url)
            self.queue.append(start_url_normalized)
            
            max_iterations = 5  # Limited for demo
            iteration = 0
            
            while self.queue and iteration < max_iterations:
                current_url = self.queue.pop(0)
                iteration += 1
                
                if current_url in self.visited:
                    continue
                    
                self.visited.add(current_url)
                full_url = f"{self.base_url}{current_url}"
                print(f"📄 [{iteration}] {current_url}")
                
                try:
                    result = await crawler.arun(full_url, config=config)
                    if result.success:
                        data = json.loads(result.extracted_content)[0]
                        variant_info = {
                            'url': current_url,
                            'title': data.get('title', 'Unknown'),
                            'price': data.get('price', '0'),
                            'variant_count': len(data.get('variant_urls', []))
                        }
                        self.all_variants.append(variant_info)
                        
                        # Add new URLs to queue
                        new_urls = 0
                        for variant in data.get('variant_urls', []):
                            variant_url = self.normalize_url(variant.get('url', ''))
                            if variant_url and variant_url not in self.visited and variant_url not in self.queue:
                                self.queue.append(variant_url)
                                new_urls += 1
                        
                        print(f"   ✅ Found {variant_info['variant_count']} variants, added {new_urls} new URLs")
                        
                except Exception as e:
                    print(f"   ❌ Error: {e}")
                
                await asyncio.sleep(0.5)  # Faster for demo
            
            return self.all_variants
    
    start_url = "/products/zline-autograph-edition-30-paramount-gas-range-stainless-steel-champagne-bronze-sgrz-30-cb"
    scraper = DemoScraper()
    
    async with AsyncWebCrawler(config=browser_config) as crawler:
        variants = await scraper.get_all_variants(start_url, crawler, config)
        
        print(f"\n🎉 Demo Complete!")
        print(f"📊 Found {len(variants)} variants in {len(scraper.visited)} pages")
        print(f"🔗 Remaining in queue: {len(scraper.queue)}")
        
        print(f"\n📋 Sample Results:")
        for i, variant in enumerate(variants[:3], 1):
            price = f"${int(variant['price'])/100:.2f}" if variant['price'] != '0' else "N/A"
            print(f"{i}. {variant['title'][:60]}...")
            print(f"   💰 {price} | 🔗 {variant['url']}")

async def run_custom_url(url):
    """Run scraper with a custom URL"""
    print(f"🎯 Custom URL Scraper")
    print(f"📍 Target: {url}")
    print("=" * 60)
    
    # Use the main scraper but modify the URL
    # You would modify the main() function to accept a parameter
    print("For custom URLs, modify the start_url in zline_scraper.py")

def show_usage():
    """Show usage examples"""
    print("""
🔧 ZLine Scraper Usage Examples:

1. Run Full Scraper (discovers all variants):
   python3 zline_scraper.py

2. Run Quick Demo (limited to 5 pages):
   python3 run_scraper.py demo

3. Custom URL (modify code):
   python3 run_scraper.py custom /products/your-zline-product

4. Analysis Mode:
   python3 run_scraper.py analyze

Available Commands:
- demo: Quick demonstration
- custom: Custom URL (requires modification)
- analyze: Show discovered variant network
- help: Show this help
""")

async def analyze_results():
    """Analyze and display variant network structure"""
    print("📊 Variant Network Analysis")
    print("=" * 60)
    print("This would analyze the variant connections and show network structure.")
    print("Features:")
    print("- Variant relationship mapping")
    print("- Price range analysis")
    print("- Category distribution")
    print("- URL pattern analysis")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        show_usage()
    elif sys.argv[1] == "demo":
        asyncio.run(quick_demo())
    elif sys.argv[1] == "custom":
        url = sys.argv[2] if len(sys.argv) > 2 else "/products/default"
        asyncio.run(run_custom_url(url))
    elif sys.argv[1] == "analyze":
        asyncio.run(analyze_results())
    elif sys.argv[1] == "help":
        show_usage()
    elif sys.argv[1] == "full":
        print("Running full scraper...")
        asyncio.run(main())
    else:
        show_usage()