from robotexclusionrulesparser import RobotExclusionRulesParser
from urllib.parse import urlparse
import aiohttp

# Asynchrone : vérifie si une URL est autorisée par robots.txt
async def is_allowed(url, user_agent='MyCrawler'):
    parsed = urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(robots_url, timeout=8) as resp:
                txt = await resp.text()
        rp = RobotExclusionRulesParser()
        rp.parse(txt)
        allowed = rp.is_allowed(user_agent, url)
        print(f"[robots.txt] {url} -> {'OK' if allowed else 'BLOCKED'}")
        return allowed
    except Exception:
        print(f"[robots.txt] {url} -> UNKNOWN (fail open)")
        return True
