from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

BASE_URL = "https://omsight.com/"

CATEGORY_URL = "https://omsight.com/jackets/"

PRODUCT_URLS = [
    "https://omsight.com/product/dyneema-jacket/",
    "https://omsight.com/product/spark-3l-jacket/",
]

OUTPUT_DIR = Path("inspection_output")

USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/126.0.0.0 Safari/537.36"
)


def fetch_page(client: httpx.Client, url: str) -> str:
    """Fetch a page and return its HTML."""
    print(f"\nFetching: {url}")

    response = client.get(url)
    response.raise_for_status()

    print(f"Status: {response.status_code}")
    print(f"Content-Type: {response.headers.get('content-type')}")
    print(f"Response size: {len(response.text):,} characters")

    return response.text


def extract_json_ld(soup: BeautifulSoup) -> list[dict]:
    """Extract JSON-LD objects from a page."""
    objects: list[dict] = []

    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        raw = script.string or script.get_text(strip=True)

        if not raw:
            continue

        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            print(f"  Failed to parse JSON-LD: {exc}")
            continue

        if isinstance(data, list):
            objects.extend(item for item in data if isinstance(item, dict))
        elif isinstance(data, dict):
            objects.append(data)

    return objects


def find_schema_objects(
    objects: list[dict],
    schema_type: str,
) -> list[dict]:
    """Find JSON-LD objects matching a schema.org type."""
    matches: list[dict] = []

    for obj in objects:
        obj_type = obj.get("@type")

        if isinstance(obj_type, list):
            if schema_type in obj_type:
                matches.append(obj)
        elif obj_type == schema_type:
            matches.append(obj)

    return matches


def print_json_ld(objects: list[dict]) -> None:
    """Print discovered JSON-LD objects."""
    print("\n=== JSON-LD ===")

    if not objects:
        print("No JSON-LD objects found.")
        return

    for index, obj in enumerate(objects, start=1):
        print(f"\n--- JSON-LD object {index} ---")
        print(json.dumps(obj, indent=2, ensure_ascii=False))


def inspect_product_schema(objects: list[dict]) -> None:
    """Inspect Product and Offer schema objects."""
    print("\n=== PRODUCT / OFFER SCHEMA ===")

    products = find_schema_objects(objects, "Product")
    offers = find_schema_objects(objects, "Offer")

    print(f"Product objects: {len(products)}")
    print(f"Offer objects: {len(offers)}")

    for index, product in enumerate(products, start=1):
        print(f"\n--- Product {index} ---")

        fields = [
            "name",
            "description",
            "sku",
            "url",
            "image",
            "brand",
            "offers",
            "aggregateRating",
        ]

        for field in fields:
            value = product.get(field)

            if value is not None:
                print(f"{field}:")
                print(json.dumps(value, indent=2, ensure_ascii=False))

    for index, offer in enumerate(offers, start=1):
        print(f"\n--- Offer {index} ---")

        fields = [
            "url",
            "price",
            "priceCurrency",
            "availability",
            "itemCondition",
            "seller",
        ]

        for field in fields:
            value = offer.get(field)

            if value is not None:
                print(f"{field}:")
                print(json.dumps(value, indent=2, ensure_ascii=False))


def inspect_html_structure(
    soup: BeautifulSoup,
    page_type: str,
) -> None:
    """Inspect useful HTML structure for extraction."""
    print(f"\n=== HTML STRUCTURE: {page_type.upper()} ===")

    title = soup.title.get_text(" ", strip=True) if soup.title else None
    print(f"\nTitle: {title}")

    headings = soup.find_all(["h1", "h2", "h3"])

    print(f"\nHeadings found: {len(headings)}")

    for heading in headings:
        text = heading.get_text(" ", strip=True)

        if text:
            print(f"{heading.name}: {text}")

    if page_type == "product":
        print("\n=== PRODUCT-SPECIFIC TEXT ===")

        for label in ["Description", "Additional information"]:
            element = next(
                (
                    text_node
                    for text_node in soup.find_all(string=True)
                    if text_node.strip().lower() == label.lower()
                ),
                None,
            )

            if element:
                print(f"\nFound section: {label}")
                parent = element.parent

                if parent:
                    print(
                        parent.parent.get_text(
                            "\n",
                            strip=True,
                        )[:5000]
                    )


def get_internal_links(
    soup: BeautifulSoup,
    base_url: str,
) -> list[str]:
    """Return unique absolute internal links."""
    base_domain = urlparse(base_url).netloc

    links: set[str] = set()

    for anchor in soup.find_all("a", href=True):
        href = anchor["href"].strip()

        if not href:
            continue

        absolute_url = urljoin(base_url, href)
        parsed = urlparse(absolute_url)

        if parsed.scheme not in {"http", "https"}:
            continue

        if parsed.netloc != base_domain:
            continue

        normalized = absolute_url.split("#", 1)[0].rstrip("/") + "/"
        links.add(normalized)

    return sorted(links)


def inspect_product_links(
    soup: BeautifulSoup,
    base_url: str,
) -> list[str]:
    """Find links that appear to point to Omsight product pages."""
    all_links = get_internal_links(soup, base_url)

    product_links = [
        url
        for url in all_links
        if "/product/" in url and "/product-category/" not in url
    ]

    print("\n=== PRODUCT LINKS ===")
    print(f"Product links found: {len(product_links)}")

    for url in product_links:
        print(f"  {url}")

    return product_links


def inspect_category_page(
    client: httpx.Client,
    url: str,
) -> list[str]:
    """Inspect a category page and return discovered product URLs."""
    print("\n")
    print("=" * 80)
    print("CATEGORY PAGE")
    print("=" * 80)

    html = fetch_page(client, url)

    soup = BeautifulSoup(html, "html.parser")

    json_ld = extract_json_ld(soup)

    print_json_ld(json_ld)
    inspect_html_structure(soup, "category")

    product_links = inspect_product_links(soup, url)

    save_raw_html(
        html,
        "category_jackets.html",
    )

    return product_links


def inspect_product_page(
    client: httpx.Client,
    url: str,
    index: int,
) -> None:
    """Inspect one product page."""
    print("\n")
    print("=" * 80)
    print(f"PRODUCT PAGE {index}")
    print("=" * 80)

    html = fetch_page(client, url)

    soup = BeautifulSoup(html, "html.parser")

    json_ld = extract_json_ld(soup)

    print_json_ld(json_ld)
    inspect_product_schema(json_ld)
    inspect_html_structure(soup, "product")

    product_links = inspect_product_links(soup, url)

    print("\n=== PRODUCT LINK COUNT ===")
    print(f"Internal product links: {len(product_links)}")

    filename = f"product_{index}.html"

    save_raw_html(html, filename)


def save_raw_html(
    html: str,
    filename: str,
) -> None:
    """Save a raw HTML snapshot."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    path = OUTPUT_DIR / filename
    path.write_text(html, encoding="utf-8")

    print(f"\nSaved HTML snapshot: {path}")


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    headers = {
        "User-Agent": USER_AGENT,
        "Accept": (
            "text/html,application/xhtml+xml,"
            "application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
        ),
        "Accept-Language": "en-US,en;q=0.9",
    }

    timeout = httpx.Timeout(
        connect=10.0,
        read=30.0,
        write=30.0,
        pool=30.0,
    )

    with httpx.Client(
        headers=headers,
        timeout=timeout,
        follow_redirects=True,
    ) as client:
        discovered_product_links = inspect_category_page(
            client,
            CATEGORY_URL,
        )

        print("\n")
        print("=" * 80)
        print("DISCOVERED PRODUCTS")
        print("=" * 80)

        for url in discovered_product_links:
            print(url)

        print("\n")
        print("=" * 80)
        print("REPRESENTATIVE PRODUCT INSPECTION")
        print("=" * 80)

        for index, product_url in enumerate(PRODUCT_URLS, start=1):
            inspect_product_page(
                client,
                product_url,
                index,
            )


if __name__ == "__main__":
    main()
