from dataclasses import asdict
from scraper_demo.items import ProductRecord

def test_product_record_serialization_has_expected_fields():
    record = ProductRecord("Spark", "https://x.test/spark", "5181", "Omsight",
                           35.1, "EUR", "InStock", "https://x.test/spark.jpg")
    assert record.to_dict() == asdict(record)
    assert set(record.to_dict()) == {"name", "url", "sku", "brand", "price",
                                     "currency", "availability", "image"}

def test_optional_product_fields_can_be_none():
    record = ProductRecord("Unknown", "https://x.test/unknown", None, None,
                           None, None, None, None)
    assert record.to_dict()["sku"] is None
    assert record.to_dict()["price"] is None
