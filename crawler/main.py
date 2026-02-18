import asyncio
from crawler.crawler import AsyncCrawler
from crawler.config import USER_AGENT, MAX_PAGES, MAX_DEPTH

if __name__ == "__main__":
    url = input("URL de départ à crawler : ").strip()
    crawler = AsyncCrawler(url, max_pages=MAX_PAGES, max_depth=MAX_DEPTH, user_agent=USER_AGENT)
    print(f"[START] Crawl {url} (max_pages={MAX_PAGES}, max_depth={MAX_DEPTH})")
    asyncio.run(crawler.crawl())
    print("\n[RESULTS] Documents trouvés :")
    for doc in crawler.get_results():
        print(doc)
    print(f"\n[STATS] Pages visitées : {len(crawler.visited)} | Docs collectés : {len(crawler.docs_found)}")
