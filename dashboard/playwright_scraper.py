"""
Playwright-based scraper for JavaScript-heavy municipal sites
Handles dynamic content loading and SPA (Single Page Applications)
"""

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
from typing import List, Dict, Optional
import time

def scrape_with_playwright(url: str, wait_for_selector: str = None, 
                           timeout: int = 30000) -> Dict:
    """
    Scrape a JavaScript-heavy site using Playwright
    
    Args:
        url: URL to scrape
        wait_for_selector: Optional CSS selector to wait for before scraping
        timeout: Timeout in milliseconds
    
    Returns:
        Dict with html, links, and pdf_links
    """
    try:
        with sync_playwright() as p:
            # Launch browser in headless mode
            browser = p.chromium.launch(headless=True)
            
            # Create context with realistic settings
            context = browser.new_context(
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                viewport={'width': 1920, 'height': 1080},
                locale='fr-FR'
            )
            
            # Create page
            page = context.new_page()
            
            # Navigate to URL
            page.goto(url, wait_until='networkidle', timeout=timeout)
            
            # Wait for specific selector if provided
            if wait_for_selector:
                try:
                    page.wait_for_selector(wait_for_selector, timeout=timeout)
                except PlaywrightTimeout:
                    print(f"Warning: Selector {wait_for_selector} not found, continuing anyway")
            
            # Additional wait for dynamic content
            time.sleep(2)
            
            # Get HTML content
            html = page.content()
            
            # Extract all links
            links = page.evaluate('''() => {
                const anchors = Array.from(document.querySelectorAll('a[href]'));
                return anchors.map(a => ({
                    href: a.href,
                    text: a.textContent.trim()
                }));
            }''')
            
            # Extract PDF links specifically
            pdf_links = page.evaluate('''() => {
                const anchors = Array.from(document.querySelectorAll('a[href]'));
                return anchors
                    .filter(a => a.href.toLowerCase().includes('.pdf'))
                    .map(a => ({
                        href: a.href,
                        text: a.textContent.trim()
                    }));
            }''')
            
            # Close browser
            browser.close()
            
            return {
                'success': True,
                'html': html,
                'links': links,
                'pdf_links': pdf_links,
                'total_links': len(links),
                'total_pdfs': len(pdf_links)
            }
            
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'html': None,
            'links': [],
            'pdf_links': [],
            'total_links': 0,
            'total_pdfs': 0
        }

def should_use_playwright(url: str, initial_html: str = None) -> bool:
    """
    Determine if Playwright should be used for a site
    
    Args:
        url: URL to check
        initial_html: Optional initial HTML to analyze
    
    Returns:
        True if Playwright should be used
    """
    # Check for known JS frameworks in URL or HTML
    js_indicators = [
        'react',
        'angular',
        'vue',
        'next.js',
        'nuxt',
        'gatsby',
        'app.js',
        'bundle.js',
        'webpack'
    ]
    
    if initial_html:
        html_lower = initial_html.lower()
        for indicator in js_indicators:
            if indicator in html_lower:
                return True
    
    # If very few links found with requests, try Playwright
    return False

def scrape_section_with_playwright(base_url: str, section: str) -> Dict:
    """
    Scrape a specific section using Playwright
    
    Args:
        base_url: Base URL of the site
        section: Section path (e.g., '/deliberations')
    
    Returns:
        Dict with scraping results
    """
    from urllib.parse import urljoin
    
    section_url = urljoin(base_url, section)
    
    # Try to scrape with Playwright
    result = scrape_with_playwright(
        section_url,
        wait_for_selector='a[href]',  # Wait for links to load
        timeout=30000
    )
    
    return result
