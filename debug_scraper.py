#!/usr/bin/env python3
"""Debug scraper to see what HTML is actually being retrieved"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'venv/lib/python3.14/site-packages'))

import requests
from bs4 import BeautifulSoup

url = 'https://www.mairie-trevoux.fr/'

# Test with the same headers as the scraper
headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
}

print(f"🔍 Testing scraper on: {url}\n")

try:
    session = requests.Session()
    session.headers.update(headers)
    
    print("📡 Sending request...")
    response = session.get(url, timeout=30)
    
    print(f"✅ Status: {response.status_code}")
    print(f"📦 Content length: {len(response.content)} bytes")
    print(f"📝 Content type: {response.headers.get('content-type', 'unknown')}\n")
    
    # Check for redirects
    if response.history:
        print("🔀 Redirects detected:")
        for i, r in enumerate(response.history, 1):
            print(f"  {i}. {r.status_code} -> {r.url}")
        print(f"  Final: {response.url}\n")
    
    # Parse HTML - use response.text to handle gzip properly
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Find all links
    all_links = soup.find_all('a', href=True)
    print(f"🔗 Links found: {len(all_links)}\n")
    
    if len(all_links) == 0:
        print("❌ NO LINKS FOUND!")
        print("\n📄 First 500 chars of HTML:")
        print("=" * 80)
        print(response.text[:500])
        print("=" * 80)
        
        # Check if it's a JavaScript-heavy site
        if 'react' in response.text.lower() or 'vue' in response.text.lower() or 'angular' in response.text.lower():
            print("\n⚠️ DETECTED: JavaScript framework (React/Vue/Angular)")
            print("This site likely loads content dynamically with JavaScript.")
            print("The scraper needs a headless browser to render JavaScript.\n")
        
        # Check for common anti-bot measures
        if 'cloudflare' in response.text.lower():
            print("\n⚠️ DETECTED: Cloudflare protection")
            print("This site uses Cloudflare which may block automated requests.\n")
        
        if 'captcha' in response.text.lower():
            print("\n⚠️ DETECTED: CAPTCHA")
            print("This site requires CAPTCHA verification.\n")
    else:
        print("✅ Links found successfully!")
        print("\nFirst 10 links:")
        for i, link in enumerate(all_links[:10], 1):
            href = link.get('href', '')
            text = link.get_text(strip=True)[:50]
            print(f"  {i}. {href[:60]} - {text}")
        
        # Count PDF links
        pdf_links = [l for l in all_links if l.get('href', '').lower().endswith('.pdf')]
        print(f"\n📄 PDF links found: {len(pdf_links)}")
        
        if pdf_links:
            print("\nPDF links:")
            for i, link in enumerate(pdf_links[:10], 1):
                href = link.get('href', '')
                print(f"  {i}. {href}")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
