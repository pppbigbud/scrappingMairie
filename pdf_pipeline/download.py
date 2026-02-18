import aiohttp
import os
import asyncio

async def download_pdf(url, outdir):
    os.makedirs(outdir, exist_ok=True)
    fname = os.path.basename(url.split('?')[0])
    fpath = os.path.join(outdir, fname)
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=30) as resp:
                if resp.status == 200 and resp.content_type == 'application/pdf':
                    with open(fpath, 'wb') as f:
                        f.write(await resp.read())
                    return fpath
                else:
                    return None
    except Exception as e:
        print(f"[ERROR] Download failed: {url} ({e})")
        return None

# Pour usage batch
async def batch_download(pdf_urls, outdir):
    tasks = [download_pdf(url, outdir) for url in pdf_urls]
    return await asyncio.gather(*tasks)
