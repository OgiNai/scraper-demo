import html
import json
from collections.abc import Iterator
from typing import Any, ClassVar

import scrapy
from scrapy.http import Response

from scraper_demo.items import ProductRecord


class OmsightSpider(scrapy.Spider):
    name = "omsight"
    allowed_domains: ClassVar[list[str]] = ["omsight.com"]

    start_urls: ClassVar[list[str]] = [
        "https://omsight.com/jackets/",
    ]

    CATEGORY_LINK_LABELS: ClassVar[frozenset[str]] = frozenset(
        {
            "ski pants & bib’s",
            "urban & climbing pants",
            "urban & climbing shorts",
            "bike pants",
            "rain jackets",
            "jackets",
            "sweaters & hoodies",
            "base layers",
            "jerseys",
            "pants",
            "shorts",
            "hats",
        }
    )

    def parse(self, response: Response) -> Iterator[scrapy.Request]:
        """Discover all product-category pages from the site navigation."""
        for url in self._extract_category_urls(response):
            yield scrapy.Request(
                url,
                callback=self.parse_category,
            )

    def parse_category(self, response: Response) -> Iterator[scrapy.Request]:
        """Discover product pages from a product-category page."""
        product_urls: set[str] = set()

        for href in response.css('a[href*="/product/"]::attr(href)').getall():
            url = response.urljoin(href).split("#", maxsplit=1)[0]
            product_urls.add(url)

        for url in sorted(product_urls):
            yield scrapy.Request(
                url,
                callback=self.parse_product,
            )

        next_page = response.css(
            "a.next.page-numbers::attr(href), a.next::attr(href)"
        ).get()

        if next_page:
            yield scrapy.Request(
                response.urljoin(next_page),
                callback=self.parse_category,
            )

    def parse_product(self, response: Response) -> Iterator[dict[str, Any]]:
        """Extract deterministic product data and variant data."""

        product = self._extract_schema_product(response)

        if product is None:
            self.logger.warning(
                "No Schema.org Product found: %s",
                response.url,
            )
            return

        record = self._build_product_record(product, response.url)

        yield {
            **record.to_dict(),
            "categories": self._extract_categories(response),
            "variants": self._extract_variants(response),
            "description": self._extract_description(response),
        }

    @classmethod
    def _extract_category_urls(cls, response: Response) -> list[str]:
        """Return unique product-category URLs from the site navigation."""
        category_urls: set[str] = set()

        for link in response.css("a[href]"):
            label = " ".join(link.css("::text").getall()).strip().casefold()

            if label not in cls.CATEGORY_LINK_LABELS:
                continue

            href = link.attrib.get("href")

            if not href:
                continue

            category_urls.add(response.urljoin(href).split("#", maxsplit=1)[0])

        return sorted(category_urls)

    @staticmethod
    def _extract_schema_product(
        response: Response,
    ) -> dict[str, Any] | None:
        """Return the Schema.org Product object from JSON-LD."""

        for script in response.css('script[type="application/ld+json"]::text').getall():
            try:
                data = json.loads(script)
            except json.JSONDecodeError:
                continue

            product = OmsightSpider._find_product_object(data)

            if product is not None:
                return product

        return None

    @staticmethod
    def _find_product_object(
        data: Any,
    ) -> dict[str, Any] | None:
        """Find a Product object inside arbitrary JSON-LD."""

        if isinstance(data, dict):
            type_value = data.get("@type")

            if type_value == "Product":
                return data

            if isinstance(type_value, list) and "Product" in type_value:
                return data

            graph = data.get("@graph")

            if isinstance(graph, list):
                for item in graph:
                    product = OmsightSpider._find_product_object(item)

                    if product is not None:
                        return product

            for value in data.values():
                if isinstance(value, (dict, list)):
                    product = OmsightSpider._find_product_object(value)

                    if product is not None:
                        return product

        elif isinstance(data, list):
            for item in data:
                product = OmsightSpider._find_product_object(item)

                if product is not None:
                    return product

        return None

    @staticmethod
    def _build_product_record(
        product: dict[str, Any],
        response_url: str,
    ) -> ProductRecord:
        """Map Schema.org Product data into our canonical record."""

        name = OmsightSpider._clean_string(product.get("name"))
        url = OmsightSpider._clean_string(product.get("url")) or response_url
        sku = OmsightSpider._normalise_sku(product.get("sku"))
        brand = OmsightSpider._extract_brand(product.get("brand"))
        image = OmsightSpider._extract_image(product.get("image"))
        offer = OmsightSpider._extract_primary_offer(product.get("offers"))
        price = OmsightSpider._parse_price(offer.get("price") if offer else None)
        currency = (
            OmsightSpider._clean_string(offer.get("priceCurrency")) if offer else None
        )
        availability = (
            OmsightSpider._normalise_availability(offer.get("availability"))
            if offer
            else None
        )

        return ProductRecord(
            name=name or "",
            url=url,
            sku=sku,
            brand=brand,
            price=price,
            currency=currency,
            availability=availability,
            image=image,
        )

    @staticmethod
    def _extract_primary_offer(
        offers: Any,
    ) -> dict[str, Any] | None:
        if isinstance(offers, dict):
            return offers

        if isinstance(offers, list):
            for offer in offers:
                if isinstance(offer, dict):
                    return offer

        return None

    @staticmethod
    def _extract_brand(brand: Any) -> str | None:
        if isinstance(brand, str):
            return OmsightSpider._clean_string(brand)

        if isinstance(brand, dict):
            return OmsightSpider._clean_string(brand.get("name"))

        return None

    @staticmethod
    def _extract_image(image: Any) -> str | None:
        if isinstance(image, str):
            return OmsightSpider._clean_string(image)

        if isinstance(image, list):
            for value in image:
                if isinstance(value, str):
                    return OmsightSpider._clean_string(value)

                if isinstance(value, dict):
                    url = value.get("url")

                    if isinstance(url, str):
                        return OmsightSpider._clean_string(url)

        if isinstance(image, dict):
            return OmsightSpider._clean_string(image.get("url"))

        return None

    @staticmethod
    def _normalise_sku(value: Any) -> str | None:
        if value is None:
            return None

        if isinstance(value, str):
            value = value.strip()

            if not value or value.upper() in {"N/A", "NA", "NONE"}:
                return None

            return value

        if isinstance(value, int):
            return str(value)

        return None

    @staticmethod
    def _parse_price(value: Any) -> float | None:
        if value is None:
            return None

        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _normalise_availability(value: Any) -> str | None:
        if not isinstance(value, str):
            return None

        value = value.rstrip("/")

        if "/" in value:
            value = value.rsplit("/", maxsplit=1)[-1]

        value = value.strip()

        return value or None

    @staticmethod
    def _clean_string(value: Any) -> str | None:
        if not isinstance(value, str):
            return None

        value = " ".join(value.split())

        return value or None

    @staticmethod
    def _extract_variants(
        response: Response,
    ) -> list[dict[str, Any]]:
        """
        Extract WooCommerce variation data from data-product_variations.

        This is kept separate from ProductRecord because variants are
        product-option data rather than canonical product identity.
        """
        variation_attributes = response.css(
            "form.variations_form::attr(data-product_variations)"
        ).get()

        if not variation_attributes:
            return []

        try:
            variations = json.loads(html.unescape(variation_attributes))
        except json.JSONDecodeError:
            return []

        if not isinstance(variations, list):
            return []

        result: list[dict[str, Any]] = []

        for variation in variations:
            if not isinstance(variation, dict):
                continue

            attributes = variation.get("attributes", {})

            if not isinstance(attributes, dict):
                attributes = {}

            normalised_attributes = {
                OmsightSpider._normalise_attribute_name(key): value
                for key, value in attributes.items()
                if isinstance(value, str) and value
            }

            result.append(
                {
                    "variation_id": variation.get("variation_id"),
                    "attributes": normalised_attributes,
                    "price": OmsightSpider._parse_price(variation.get("display_price")),
                    "regular_price": OmsightSpider._parse_price(
                        variation.get("display_regular_price")
                    ),
                    "in_stock": variation.get("is_in_stock"),
                    "purchasable": variation.get("is_purchasable"),
                    "sku": OmsightSpider._normalise_sku(variation.get("sku")),
                    "image": (
                        variation.get("image", {}).get("url")
                        if isinstance(variation.get("image"), dict)
                        else None
                    ),
                }
            )

        return result

    @staticmethod
    def _normalise_attribute_name(name: str) -> str:
        name = name.removeprefix("attribute_")
        return name.replace("-", "_")

    @staticmethod
    def _extract_categories(response: Response) -> list[str]:
        """Extract deterministic WooCommerce product categories."""
        categories = response.css(".product_meta .posted_in a::text").getall()

        if not categories:
            categories = response.css(".product_meta .posted_in::text").getall()

        result: list[str] = []
        seen: set[str] = set()

        for value in categories:
            category = " ".join(value.split()).strip().casefold()

            if not category or category in seen:
                continue

            seen.add(category)
            result.append(category)

        return result

    @staticmethod
    def _extract_description(response: Response) -> str:
        """Extract product description and additional information."""

        sections = (
            ("Description", "#accordion-description-content"),
            (
                "",
                "#accordion-additional_information",
            ),
        )

        parts: list[str] = []

        for heading, selector in sections:
            element = response.css(selector)

            if not element:
                continue

            text_parts = element.css("::text").getall()

            text = " ".join(
                " ".join(text.split()) for text in text_parts if text.strip()
            )

            if text:
                parts.append(f"{heading}:\n{text}")

        return "\n\n".join(parts)
