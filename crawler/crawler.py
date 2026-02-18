import asyncio
import aiohttp
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from .robots_utils import is_allowed
from .section_matcher import is_section_relevant
from .utils import normalize_url
import os
import json
from datetime import datetime

DOC_EXTS = ('.pdf', '.docx', '.odt')

class AsyncCrawler:
    def __init__(self, base_url, max_pages=50, max_depth=3, user_agent='MyCrawler'):
        self.base_url = base_url
        self.max_pages = max_pages
        self.max_depth = max_depth
        self.user_agent = user_agent
        self.visited = set()
        self.docs_found = []  # List of dicts (metadata)

    async def fetch(self, session, url):
        try:
            async with session.get(url, timeout=10, allow_redirects=True) as resp:
                print(f"[HTTP] {url} -> {resp.status}")
                if resp.status == 200 and 'text/html' in resp.headers.get('Content-Type', ''):
                    return await resp.text()
        except Exception as e:
            print(f"[ERROR] Fetch failed: {url} ({e})")
        return None

    async def crawl(self):
        queue = [(self.base_url, 0)]
        now = datetime.utcnow().isoformat()
        async with aiohttp.ClientSession(headers={'User-Agent': self.user_agent}) as session:
            while queue and len(self.visited) < self.max_pages:
                url, depth = queue.pop(0)
                if url in self.visited or depth > self.max_depth:
                    continue
                if not await is_allowed(url, self.user_agent):
                    print(f"[robots.txt] Blocked: {url}")
                    continue
                self.visited.add(url)
                html = await self.fetch(session, url)
                if not html:
                    continue
                soup = BeautifulSoup(html, 'lxml')
                # Extraction des documents
                for a in soup.find_all('a', href=True):
                    href = normalize_url(url, a['href'])
                    ext = os.path.splitext(href.split('?')[0])[1].lower()
                    if ext in DOC_EXTS:
                        meta = {
                            'site_url': self.base_url,
                            'page_source': url,
                            'document_url': href,
                            'type': ext.lstrip('.'),
                            'nom_fichier': os.path.basename(href.split('?')[0]),
                            'date_detection': now
                        }
                        print(f"[DOC] {meta['document_url']}")
                        self.docs_found.append(meta)
                    # Exploration intelligente
                    if is_section_relevant(a.get_text(), a['href']):
                        queue.append((href, depth + 1))
                await asyncio.sleep(0.5)  # Respect rate limiting
        self.export_results()

    def export_results(self):
        if not self.docs_found:
            print("[EXPORT] Aucun document à sauvegarder.")
            return
        outdir = os.path.join(os.path.dirname(__file__), '../data/crawl_results')
        os.makedirs(outdir, exist_ok=True)
        netloc = urlparse(self.base_url).netloc.replace('.', '_')
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        fname = f"crawl_{netloc}_{timestamp}.json"
        fpath = os.path.abspath(os.path.join(outdir, fname))
        with open(fpath, 'w', encoding='utf-8') as f:
            json.dump(self.docs_found, f, ensure_ascii=False, indent=2)
        print(f"[EXPORT] Résultats sauvegardés dans : {fpath}")

    def get_results(self):
        return self.docs_found
