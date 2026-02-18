"""
Intelligent URL finder for municipal websites
Tries multiple patterns and verifies the URLs are valid municipal sites
"""

import requests
from typing import Optional, Tuple
import time
import json
import os
from cities_database import normalize_city_name

# Cache file to store discovered URLs
CACHE_FILE = 'data/url_cache.json'

def load_url_cache() -> dict:
    """Load cached URLs from file"""
    cache_path = os.path.join(os.path.dirname(__file__), '..', CACHE_FILE)
    if os.path.exists(cache_path):
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_url_cache(cache: dict):
    """Save URL cache to file"""
    cache_path = os.path.join(os.path.dirname(__file__), '..', CACHE_FILE)
    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
    with open(cache_path, 'w', encoding='utf-8') as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)

def generate_url_patterns(city_name: str) -> list:
    """
    Generate possible URL patterns for a city
    
    Args:
        city_name: City name (e.g., 'Clermont-Ferrand')
    
    Returns:
        List of possible URLs to try
    """
    normalized = normalize_city_name(city_name)
    
    patterns = [
        f'https://www.{normalized}.fr/',
        f'https://{normalized}.fr/',
        f'https://www.mairie-{normalized}.fr/',
        f'https://mairie-{normalized}.fr/',
        f'https://www.ville-{normalized}.fr/',
        f'https://ville-{normalized}.fr/',
        f'https://www.mairie{normalized}.fr/',
        f'https://www.{normalized}.com/',
    ]
    
    return patterns

def verify_municipal_site(url: str, timeout: int = 10) -> bool:
    """
    Verify if a URL is a valid municipal website
    
    Args:
        url: URL to verify
        timeout: Request timeout in seconds
    
    Returns:
        True if the site appears to be a municipal website
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        }
        
        response = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
        
        if response.status_code != 200:
            return False
        
        # Check if content contains municipal keywords
        content_lower = response.text.lower()
        municipal_keywords = [
            'mairie',
            'conseil municipal',
            'ville de',
            'commune de',
            'hôtel de ville',
            'services municipaux',
            'délibération',
        ]
        
        # At least 2 keywords should be present
        keyword_count = sum(1 for keyword in municipal_keywords if keyword in content_lower)
        
        return keyword_count >= 2
        
    except Exception as e:
        return False

def find_city_url(city_name: str, dept_code: str, use_cache: bool = True) -> Optional[str]:
    """
    Find the official website URL for a city
    
    Args:
        city_name: Name of the city
        dept_code: Department code
        use_cache: Whether to use cached results
    
    Returns:
        URL of the city's website, or None if not found
    """
    cache_key = f"{dept_code}_{normalize_city_name(city_name)}"
    
    # Check cache first
    if use_cache:
        cache = load_url_cache()
        if cache_key in cache:
            cached_url = cache[cache_key]
            if cached_url:  # Could be None if previously not found
                print(f"  ✓ Cache hit: {city_name} -> {cached_url}")
                return cached_url
            else:
                print(f"  ✗ Cache: {city_name} previously not found")
                return None
    
    print(f"  🔍 Searching URL for {city_name}...")
    
    # Try different URL patterns
    patterns = generate_url_patterns(city_name)
    
    for i, url in enumerate(patterns, 1):
        try:
            print(f"    [{i}/{len(patterns)}] Trying: {url[:50]}...")
            
            # Quick HEAD request first to check if site exists
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.head(url, headers=headers, timeout=5, allow_redirects=True)
            
            if response.status_code == 200:
                # Verify it's actually a municipal site
                if verify_municipal_site(url):
                    print(f"    ✓ Found valid municipal site: {url}")
                    
                    # Save to cache
                    cache = load_url_cache()
                    cache[cache_key] = url
                    save_url_cache(cache)
                    
                    return url
                else:
                    print(f"    ✗ Site exists but doesn't appear to be municipal")
            
            # Small delay to avoid rate limiting
            time.sleep(0.5)
            
        except requests.exceptions.Timeout:
            print(f"    ⏱ Timeout")
            continue
        except requests.exceptions.RequestException:
            continue
    
    print(f"  ✗ No valid URL found for {city_name}")
    
    # Save negative result to cache to avoid retrying
    cache = load_url_cache()
    cache[cache_key] = None
    save_url_cache(cache)
    
    return None

def find_urls_for_cities(cities: list, dept_code: str, max_cities: int = None) -> dict:
    """
    Find URLs for multiple cities
    
    Args:
        cities: List of city dictionaries with 'name' key
        dept_code: Department code
        max_cities: Maximum number of cities to process (for testing)
    
    Returns:
        Dictionary mapping city names to URLs
    """
    results = {}
    
    cities_to_process = cities[:max_cities] if max_cities else cities
    
    print(f"\n🔍 Finding URLs for {len(cities_to_process)} cities in department {dept_code}...\n")
    
    for i, city in enumerate(cities_to_process, 1):
        city_name = city['name']
        print(f"[{i}/{len(cities_to_process)}] {city_name} (pop: {city['population']:,})")
        
        url = find_city_url(city_name, dept_code)
        if url:
            results[city_name] = url
        
        # Small delay between cities
        time.sleep(0.3)
    
    print(f"\n✓ Found {len(results)}/{len(cities_to_process)} URLs")
    
    return results
