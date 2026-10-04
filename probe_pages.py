import json
import re
import time

import httpx
from bs4 import BeautifulSoup

BASE = "https://omsight.com"
URLS = [
    "/product/woolvarine-ms-i/",
    "/product/gas-2/",
    "/product/flow-6/",
    "/product/rockit-x/",
    "/product/flow-4-way-ruby-wine/",
]


def ld_types(s):
    out = []
    for j in s.select('script[type="application/ld+json"]'):
        try:
            d = json.loads(j.string)
        except json.JSONDecodeError:
            out.append("unparseable")
            continue
        nodes = d.get("@graph", [d]) if isinstance(d, dict) else d
        out.append([n.get("@type") for n in nodes if isinstance(n, dict)])
    return out


with httpx.Client(
    follow_redirects=True,
    timeout=30,
    headers={"User-Agent": "Mozilla/5.0 (research mini-project)"},
) as c:
    sm = c.get(BASE + "/product-sitemap.xml").text
    locs = re.findall(
        r"<loc><!\[CDATA\[(https://omsight\.com/product/[^\]]+)\]\]></loc>", sm
    )
    print("product urls in sitemap:", len(locs))
    print("woolvarine in sitemap:", [l for l in locs if "wool" in l.lower()])
    for u in URLS:
        time.sleep(3)
        r = c.get(BASE + u)
        print("=" * 70)
        print(u, r.status_code)
        if r.status_code != 200:
            continue
        s = BeautifulSoup(r.text, "html.parser")
        print("title:", s.title.string if s.title else None)
        print(
            "body postid:",
            re.findall(r"postid-(\d+)", " ".join(s.body.get("class", []))),
        )
        print(
            "breadcrumb:",
            [a.get_text(strip=True) for a in s.select("nav.woocommerce-breadcrumb a")],
        )
        print(
            "attributes:",
            {
                tr.th.get_text(strip=True): tr.td.get_text(" ", strip=True)
                for tr in s.select("table.woocommerce-product-attributes tr")
                if tr.th and tr.td
            },
        )
        print(
            "variation selects:",
            {
                sel.get("name"): [
                    o.get("value") for o in sel.select("option") if o.get("value")
                ]
                for sel in s.select("form.variations_form select")
            },
        )
        print("json-ld @types per block:", ld_types(s))
