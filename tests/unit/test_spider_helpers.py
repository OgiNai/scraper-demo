import json
from scrapy.http import HtmlResponse, Request
from scraper_demo.spiders.omsight import OmsightSpider

def response(body, url="https://omsight.test/product/a/"):
    return HtmlResponse(url=url, request=Request(url=url), body=body.encode(), encoding="utf-8")

def test_find_product_in_nested_graph():
    data = {"@graph": [{"@type": "WebPage"}, {"@type": ["Thing", "Product"], "name": "Spark"}]}
    assert OmsightSpider._find_product_object(data)["name"] == "Spark"

def test_find_product_returns_none_when_absent():
    assert OmsightSpider._find_product_object({"@type": "WebPage"}) is None

def test_build_record_maps_jsonld_fields():
    record = OmsightSpider._build_product_record({
        "@type": "Product", "name": " Spark\n Jacket ", "sku": 5181,
        "brand": {"name": " Omsight "}, "image": [{"url": "https://x.test/a.jpg"}],
        "offers": {"price": "35.10", "priceCurrency": "EUR",
                   "availability": "https://schema.org/InStock"}
    }, "https://x.test/fallback/")
    assert (record.name, record.sku, record.brand, record.price) == ("Spark Jacket", "5181", "Omsight", 35.1)
    assert record.availability == "InStock"

def test_build_record_uses_response_url_and_allows_missing_fields():
    record = OmsightSpider._build_product_record({"@type": "Product", "name": "X"}, "https://x.test/x/")
    assert record.url == "https://x.test/x/"
    assert record.sku is None and record.price is None

def test_offer_brand_image_helpers_support_common_shapes():
    assert OmsightSpider._extract_primary_offer([{"price": 1}]) == {"price": 1}
    assert OmsightSpider._extract_brand({"name": "Brand"}) == "Brand"
    assert OmsightSpider._extract_image({"url": "https://x.test/a.jpg"}) == "https://x.test/a.jpg"

def test_scalar_normalizers():
    assert OmsightSpider._normalise_sku(" N/A ") is None
    assert OmsightSpider._normalise_sku(123) == "123"
    assert OmsightSpider._parse_price("bad") is None
    assert OmsightSpider._normalise_availability("https://schema.org/OutOfStock/") == "OutOfStock"
    assert OmsightSpider._clean_string(" A\n B ") == "A B"

def test_navigation_categories_deduplicated():
    r = response('<a href="/jackets/">Jackets</a><a href="/jackets/#top">JACKETS</a><a href="/random/">Random</a>', "https://omsight.test/")
    assert OmsightSpider._extract_category_urls(r) == ["https://omsight.test/jackets/"]

def test_product_categories_normalized():
    r = response('<div class="product_meta"><span class="posted_in"><a> Jackets </a><a>jackets</a></span></div>')
    assert OmsightSpider._extract_categories(r) == ["jackets"]

def test_variants_parse_escaped_attribute_json():
    variations = [{"variation_id": 1, "attributes": {"attribute_pa_color": "blue"},
                   "display_price": "25.5", "display_regular_price": "30",
                   "is_in_stock": True, "is_purchasable": True, "sku": "V1",
                   "image": {"url": "https://x.test/blue.jpg"}}]
    encoded = json.dumps(variations).replace('"', "&quot;")
    r = response(f'<form class="variations_form" data-product_variations="{encoded}"></form>')
    result = OmsightSpider._extract_variants(r)
    assert result[0]["attributes"] == {"pa_color": "blue"}
    assert result[0]["price"] == 25.5 and result[0]["sku"] == "V1"

def test_variants_and_description_handle_empty_page():
    r = response("<html></html>")
    assert OmsightSpider._extract_variants(r) == []
    assert OmsightSpider._extract_description(r) == ""
