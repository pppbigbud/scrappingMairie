"""
Intelligent site structure cache system
Memorizes successful scraping patterns for each municipal site
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional

CACHE_FILE = 'data/site_structure_cache.json'

def load_site_cache() -> dict:
    """Load site structure cache from file"""
    cache_path = os.path.join(os.path.dirname(__file__), '..', CACHE_FILE)
    if os.path.exists(cache_path):
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_site_cache(cache: dict):
    """Save site structure cache to file"""
    cache_path = os.path.join(os.path.dirname(__file__), '..', CACHE_FILE)
    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
    with open(cache_path, 'w', encoding='utf-8') as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)

def get_site_structure(domain: str) -> Optional[Dict]:
    """
    Get cached structure for a site
    
    Returns:
        Dict with successful_sections, document_patterns, last_updated
    """
    cache = load_site_cache()
    return cache.get(domain)

def update_site_structure(domain: str, successful_sections: List[str], 
                          documents_found: int, patterns_matched: List[str]):
    """
    Update cache with successful scraping information
    
    Args:
        domain: Site domain (e.g., 'www.mairie-trevoux.fr')
        successful_sections: List of sections that had documents
        documents_found: Number of documents found
        patterns_matched: List of patterns that matched documents
    """
    cache = load_site_cache()
    
    # Get existing entry or create new one
    site_data = cache.get(domain, {
        'domain': domain,
        'successful_sections': [],
        'total_documents_found': 0,
        'successful_patterns': [],
        'scrape_count': 0,
        'first_scraped': datetime.now().isoformat(),
        'last_updated': datetime.now().isoformat()
    })
    
    # Update with new information
    site_data['scrape_count'] += 1
    site_data['last_updated'] = datetime.now().isoformat()
    site_data['total_documents_found'] += documents_found
    
    # Merge successful sections (keep unique)
    existing_sections = set(site_data.get('successful_sections', []))
    existing_sections.update(successful_sections)
    site_data['successful_sections'] = list(existing_sections)
    
    # Merge successful patterns (keep unique)
    existing_patterns = set(site_data.get('successful_patterns', []))
    existing_patterns.update(patterns_matched)
    site_data['successful_patterns'] = list(existing_patterns)
    
    # Save back to cache
    cache[domain] = site_data
    save_site_cache(cache)
    
    return site_data

def get_priority_sections(domain: str) -> List[str]:
    """
    Get priority sections to explore based on cache
    Returns sections that have been successful before
    """
    site_data = get_site_structure(domain)
    
    if site_data and site_data.get('successful_sections'):
        # Return cached successful sections first
        return site_data['successful_sections']
    
    # Return default sections if no cache
    return [
        '/deliberations',
        '/deliberation',
        '/conseil-municipal',
        '/publications',
        '/documents',
        '/vie-municipale',
        '/bulletin-municipal',
        '/bulletins-municipaux',
        '/magazine-municipal'
    ]

def get_cache_stats() -> Dict:
    """Get statistics about cached sites"""
    cache = load_site_cache()
    
    total_sites = len(cache)
    total_documents = sum(site.get('total_documents_found', 0) for site in cache.values())
    
    # Most successful sites
    top_sites = sorted(
        cache.items(),
        key=lambda x: x[1].get('total_documents_found', 0),
        reverse=True
    )[:10]
    
    return {
        'total_sites_cached': total_sites,
        'total_documents_found': total_documents,
        'top_sites': [
            {
                'domain': domain,
                'documents': data.get('total_documents_found', 0),
                'scrape_count': data.get('scrape_count', 0)
            }
            for domain, data in top_sites
        ]
    }
