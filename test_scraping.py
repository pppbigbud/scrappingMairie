#!/usr/bin/env python3

import os
import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin

def test_scraping():
    """Test scraping function to debug issues"""
    
    # Test with Villeurbanne
    base_url = "https://www.villeurbanne.fr"
    
    print(f"Testing scraping for: {base_url}")
    
    # Document patterns
    document_patterns = [
        r'.*[Pp]lan.*[Cc]limat.*',
        r'.*[Pp][Cc][Aa][Ee][Tt].*',
        r'.*[Bb]udget.*',
        r'.*[Dd][ée]libération.*',
        r'.*[Cc]onseil.*[Mm]unicipal.*',
        r'.*[Bb]ulletin.*[Mm]unicipal.*',
        r'.*[Éé]nergie.*',
        r'.*[Ss]olaire.*',
        r'.*[Bb]iomasse.*',
        r'.*[Rr][ée]seau.*[Cc]haleur.*',
        r'.*[Pp][Vv].*',
        r'.*[Pp]hotovolt.*',
        r'.*[Tt]ransition.*',
        r'.*[Ee]nvironnement.*',
        r'.*[Dd][éé]veloppement.*',
        r'.*[Dd]urable.*',
        r'.*[Aa]genda.*',
        r'.*[Pp]rogramme.*'
    ]
    
    doc_extensions = ['.pdf', '.doc', '.docx']
    
    # Common municipal sections to explore
    sections_to_explore = [
        "/conseil-municipal",
        "/deliberations", 
        "/budget",
        "/environnement",
        "/energie",
        "/urbanisme",
        "/publications",
        "/documents",
        "/actualites",
        "/vie-municipale"
    ]
    
    all_document_links = []
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # Test main page first
        print(f"\n=== TESTING MAIN PAGE ===")
        test_page(base_url, headers, document_patterns, doc_extensions, all_document_links)
        
        # Test common sections
        for section in sections_to_explore:
            section_url = urljoin(base_url, section)
            print(f"\n=== TESTING SECTION: {section} ===")
            test_page(section_url, headers, document_patterns, doc_extensions, all_document_links)
        
        print(f"\n=== FINAL SUMMARY ===")
        print(f"Total matching documents found: {len(all_document_links)}")
        for i, doc in enumerate(all_document_links):
            print(f"  {i+1}. {doc['filename']}")
            print(f"     URL: {doc['url']}")
            print(f"     From: {doc['from_page']}")
            print(f"     Text: {doc['text'][:100]}...")
            print()
        
        return all_document_links
        
    except Exception as e:
        print(f"Error: {e}")
        return []

def test_page(url, headers, patterns, extensions, doc_links):
    """Test a specific page for documents"""
    try:
        response = requests.get(url, headers=headers, timeout=30)
        print(f"Response status: {response.status_code}")
        
        if response.status_code != 200:
            return
            
        soup = BeautifulSoup(response.content, 'html.parser')
        all_links = soup.find_all('a', href=True)
        print(f"Found {len(all_links)} links on {url}")
        
        for link in all_links:
            href = link.get('href')
            full_url = urljoin(url, href)
            
            # Check if it's a document
            if any(full_url.lower().endswith(ext) for ext in extensions):
                filename = os.path.basename(full_url)
                
                # Check if filename matches patterns
                matches_pattern = any(re.search(pattern, filename, re.IGNORECASE) for pattern in patterns)
                
                if matches_pattern:
                    # Test if URL is accessible
                    try:
                        head_response = requests.head(full_url, headers=headers, timeout=10)
                        if head_response.status_code == 200:
                            doc_links.append({
                                'filename': filename,
                                'url': full_url,
                                'from_page': url,
                                'text': link.get_text().strip(),
                                'status': head_response.status_code
                            })
                            print(f"  ✓ Found: {filename}")
                    except Exception as e:
                        print(f"  ✗ Error accessing {filename}: {e}")
        
    except Exception as e:
        print(f"Error testing {url}: {e}")

if __name__ == "__main__":
    test_scraping()
