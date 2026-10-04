import re

import httpx

BASE = "https://omsight.com"
PATHS = [
    "/robots.txt",
    "/sitemap_index.xml",
    "/product-sitemap.xml",
    "/wp-sitemap.xml",
    "/mens-bike-shorts/",
    "/mens-bike-shorts/page/2/",
]

with httpx.Client(
    follow_redirects=True,
    timeout=20,
    headers={"User-Agent": "Mozilla/5.0 (research mini-project)"},
) as c:
    for p in PATHS:
        r = c.get(BASE + p)
        print("=" * 70)
        print(p, "->", r.status_code, r.url, r.headers.get("content-type"))
        body = r.text
        if p.endswith((".xml", ".txt")):  # or p.endswith(".txt"):
            print(body[:1500])
            print("<loc> count:", len(re.findall(r"<loc>", body)))
        else:
            links = set(
                re.findall(r'href="(https://omsight\.com/product/[^"]+)"', body)
            )
            print("distinct product links:", len(links))
            for l in sorted(links)[:40]:
                print("  ", l)
            print(
                "pagination markers:",
                re.findall(r'page-numbers[^>]*href="([^"]+)"', body)[:10],
            )
