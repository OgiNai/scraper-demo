import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from scrapy.crawler import CrawlerProcess
from scraper_demo.spiders.omsight import OmsightSpider

HOME = '<a href="/jackets/">Jackets</a>'
CATEGORY = '<a href="/product/spark/">Spark</a><a href="/product/spark/#details">duplicate</a>'
PRODUCT = """
<script type="application/ld+json">{
 "@context":"https://schema.org","@type":"Product","name":"Spark",
 "url":"http://127.0.0.1/product/spark/","sku":"5181",
 "brand":{"@type":"Brand","name":"Omsight"},
 "image":"http://127.0.0.1/images/spark.jpg",
 "offers":{"@type":"Offer","price":"35.10","priceCurrency":"EUR",
 "availability":"https://schema.org/InStock"}}
</script>
<div class="product_meta"><span class="posted_in"><a>Jackets</a></span></div>
<div id="accordion-description-content">Waterproof shell.</div>
"""

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        page = {"/": HOME, "/jackets/": CATEGORY, "/product/spark/": PRODUCT}.get(self.path.split("?")[0])
        self.send_response(200 if page is not None else 404)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        if page is not None:
            self.wfile.write(f"<html><body>{page}</body></html>".encode())

    def log_message(self, *args):
        pass

def test_full_local_crawl_exports_expected_jsonl(tmp_path: Path):
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{server.server_port}/"
    output = tmp_path / "products.jsonl"

    class LocalSpider(OmsightSpider):
        name = "omsight_test_e2e"
        start_urls = [base_url]

    process = CrawlerProcess(settings={
        "LOG_ENABLED": False, "ROBOTSTXT_OBEY": False, "DOWNLOAD_DELAY": 0,
        "TELNETCONSOLE_ENABLED": False,
        "FEEDS": {str(output): {"format": "jsonlines", "encoding": "utf-8", "overwrite": True}},
    })
    try:
        process.crawl(LocalSpider)
        process.start()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    records = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines() if line]
    assert len(records) == 1
    product = records[0]
    assert product["sku"] == "5181"
    assert product["name"] == "Spark"
    assert product["brand"] == "Omsight"
    assert product["price"] == 35.1
    assert product["currency"] == "EUR"
    assert product["availability"] == "InStock"
    assert product["categories"] == ["jackets"]
    assert "Waterproof shell." in product["description"]
