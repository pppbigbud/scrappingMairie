#!/usr/bin/env python3
"""Test scraping for mairie-trevoux.fr to diagnose why no documents are found"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'venv/lib/python3.14/site-packages'))

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import re

def test_trevoux_scraping():
    url = 'https://www.mairie-trevoux.fr/'
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7',
    }
    
    print(f"🔍 Testing scraping for: {url}\n")
    
    try:
        # Get main page
        print("📡 Fetching main page...")
        response = requests.get(url, headers=headers, timeout=30)
        print(f"✅ Status: {response.status_code}\n")
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Document patterns from the scraper - UPDATED
        document_patterns = [
            # Strategic documents
            r'.*[Pp]lan.*[Cc]limat.*',
            r'.*[Pp][Cc][Aa][Ee][Tt].*',
            r'.*[Bb]udget.*',
            r'.*[Dd][ée]libération.*',
            r'.*[Cc]onseil.*[Mm]unicipal.*',
            
            # Municipal bulletins - FLEXIBLE PATTERNS
            r'.*[Bb]ulletin.*[Mm]unicipal.*',
            r'.*[Ii]nfo.*[A-Z][a-z]+.*',  # Matches INFO-TREVOUX, Info-Paris, etc.
            r'.*[Mm]agazine.*[Mm]unicipal.*',
            r'.*[Jj]ournal.*[Mm]unicipal.*',
            r'.*[Mm]ag.*[Vv]ille.*',
            r'.*[Ee]cho.*[Mm]unicipal.*',
            
            # Energy-related
            r'.*[ÉéEe]nergie.*',
            r'.*[Ss]olaire.*',
            r'.*[Pp]hotovolt.*',
            r'.*[Bb]iomasse.*',
            r'.*[Rr][ée]seau.*[Cc]haleur.*',
            r'.*[Tt]ransition.*',
            r'.*[Dd][ée]veloppement.*[Dd]urable.*',
            r'.*[Ee]nvironnement.*',
            
            # Administrative
            r'.*[Aa]genda.*',
            r'.*[Pp]rogramme.*',
            r'.*[Pp]rocès.*[Vv]erbal.*',
            r'.*[Cc]ompte.*[Rr]endu.*',
            r'.*[Pp][Vv].*[0-9]{4}.*',  # PV-2024, etc.
            r'.*[Dd][ée]lib.*[0-9]+.*'  # Delib-123, etc.
        ]
        
        # Find all links
        all_links = soup.find_all('a', href=True)
        print(f"🔗 Total links found: {len(all_links)}\n")
        
        # Find PDF links
        pdf_links = []
        for link in all_links:
            href = link.get('href')
            if not href:
                continue
                
            full_url = urljoin(url, href)
            
            # Skip external links
            if urlparse(full_url).netloc != urlparse(url).netloc:
                continue
            
            # Check if it's a PDF
            if full_url.lower().endswith('.pdf'):
                filename = os.path.basename(full_url)
                pdf_links.append((filename, full_url))
        
        print(f"📄 Total PDF links found: {len(pdf_links)}\n")
        
        # Check which PDFs match our patterns
        matching_pdfs = []
        for filename, full_url in pdf_links:
            matches_pattern = any(re.search(pattern, filename, re.IGNORECASE) for pattern in document_patterns)
            
            if matches_pattern:
                matching_pdfs.append((filename, full_url))
        
        print(f"✅ PDFs matching our patterns: {len(matching_pdfs)}\n")
        
        # Show first 10 PDFs found
        print("=" * 80)
        print("ALL PDFs FOUND (first 10):")
        print("=" * 80)
        for i, (name, link) in enumerate(pdf_links[:10], 1):
            print(f"{i}. {name}")
            print(f"   URL: {link}")
            print()
        
        # Show matching PDFs
        print("=" * 80)
        print("PDFs MATCHING OUR PATTERNS:")
        print("=" * 80)
        if matching_pdfs:
            for i, (name, link) in enumerate(matching_pdfs, 1):
                print(f"{i}. {name}")
                print(f"   URL: {link}")
                print()
        else:
            print("❌ NO PDFs match our patterns!")
            print("\n🔍 DIAGNOSIS:")
            print("The scraper patterns are looking for specific keywords like:")
            print("- Plan Climat, PCAET, Budget, Délibération")
            print("- Conseil Municipal, Bulletin Municipal")
            print("- Énergie, Solaire, Biomasse, etc.")
            print("\nBut the PDFs on this site have names like:")
            if pdf_links:
                for name, _ in pdf_links[:5]:
                    print(f"  - {name}")
            print("\n💡 SOLUTION: The patterns need to be updated to match 'INFO-TREVOUX' or 'bulletin' type filenames")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_trevoux_scraping()
