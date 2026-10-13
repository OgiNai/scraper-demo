import pytest

@pytest.fixture
def product():
    return {"name": "Spark", "url": "https://omsight.test/product/spark/",
            "sku": "5181", "brand": "Omsight", "price": 35.1,
            "currency": "EUR", "availability": "InStock",
            "image": "https://omsight.test/images/spark.jpg"}

@pytest.fixture
def golden(product):
    return dict(product)
