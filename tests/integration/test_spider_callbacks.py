import json
from scrapy.http import HtmlResponse, Request
from scraper_demo.spiders.omsight import OmsightSpider

def response(url, body):
    return HtmlResponse(url=url, request=Request(url=url), body=body.encode(), encoding="utf-8")

def test_parse_discovers_category_requests():
    spider = OmsightSpider()
    requests = list(spider.parse(response("https://omsight.test/", '<a href="/jackets/">Jackets</a><a href="/pants/">Pants</a>')))
    assert [r.url for r in requests] == ["https://omsight.test/jackets/", "https://omsight.test/pants/"]
    assert all(r.callback == spider.parse_category_page for r in requests)

def test_category_callback_deduplicates_products_and_paginates():
    spider = OmsightSpider()
    requests = list(spider.parse_category_page(response(
        "https://omsight.test/jackets/",
        '<a href="/product/a/">A</a><a href="/product/a/#x">duplicate</a>'
        '<a href="/product/b/">B</a><a class="next page-numbers" href="?paged=2">Next</a>')))
    products = [r for r in requests if r.callback == spider.parse_product]
    pages = [r for r in requests if r.callback == spider.parse_category_page]
    assert [r.url for r in products] == ["https://omsight.test/product/a/", "https://omsight.test/product/b/"]
    assert len(pages) == 1 and pages[0].url.endswith("?paged=2")

def test_product_callback_extracts_jsonld_and_other_fields():
    spider = OmsightSpider()
    data = {"@graph": [{"@type": "Product", "name": "Spark", "sku": "5181",
        "brand": {"name": "Omsight"}, "image": "https://x.test/spark.jpg",
        "offers": {"price": "35.10", "priceCurrency": "EUR",
                   "availability": "https://schema.org/InStock"}}]}
    body = f'<script type="application/ld+json">{json.dumps(data)}</script><div class="product_meta"><span class="posted_in"><a>Jackets</a></span></div><div id="accordion-description-content">Waterproof shell.</div>'
    items = list(spider.parse_product(response("https://omsight.test/product/spark/", body)))
    assert len(items) == 1
    assert items[0]["sku"] == "5181" and items[0]["price"] == 35.1
    assert items[0]["availability"] == "InStock"
    assert items[0]["categories"] == ["jackets"]
    assert "Waterproof shell." in items[0]["description"]

def test_product_callback_skips_malformed_json_and_finds_next_script():
    spider = OmsightSpider()
    body = '<script type="application/ld+json">{bad</script><script type="application/ld+json">{"@type":"Product","name":"Later","sku":"1"}</script>'
    items = list(spider.parse_product(response("https://omsight.test/product/later/", body)))
    assert len(items) == 1 and items[0]["name"] == "Later"

def test_product_callback_without_product_returns_empty(caplog):
    spider = OmsightSpider()
    items = list(spider.parse_product(response("https://omsight.test/product/none/", '<script type="application/ld+json">{"@type":"WebPage"}</script>')))
    assert items == []
    assert "No Schema.org Product found" in caplog.text
