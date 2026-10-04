BOT_NAME = "scraper_demo"

SPIDER_MODULES = ["scraper_demo.spiders"]
NEWSPIDER_MODULE = "scraper_demo.spiders"

ROBOTSTXT_OBEY = True

USER_AGENT = "scraper-demo/0.1 (educational AI data-engineering portfolio project)"

CONCURRENT_REQUESTS_PER_DOMAIN = 2
DOWNLOAD_DELAY = 1.0

AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 1.0
AUTOTHROTTLE_MAX_DELAY = 10.0
AUTOTHROTTLE_TARGET_CONCURRENCY = 1.0

FEED_EXPORT_ENCODING = "utf-8"

FEEDS = {
    "output/products.jsonl": {
        "format": "jsonlines",
        "overwrite": True,
    },
}
