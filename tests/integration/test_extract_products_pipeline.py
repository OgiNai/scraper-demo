import json
from pathlib import Path
from unittest.mock import Mock

from scraper_demo import extract_products
from scraper_demo.llm_models import StructuredProductAttributes


def test_extract_products_pipeline_reads_products_and_writes_llm_attributes(tmp_path, monkeypatch):
    input_path = tmp_path / "products.jsonl"
    output_path = tmp_path / "llm_products.jsonl"
    input_product = {
        "name": "Spark",
        "sku": "5181",
        "description": "Breathable merino wool jacket.",
        "url": "https://omsight.test/product/spark/",
    }
    input_path.write_text(json.dumps(input_product) + "\n", encoding="utf-8")
    monkeypatch.setattr(extract_products, "INPUT_PATH", input_path)
    monkeypatch.setattr(extract_products, "OUTPUT_PATH", output_path)
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    monkeypatch.setenv("GEMINI_MODEL", "fake-model")

    parsed = StructuredProductAttributes(
        materials=["merino wool"],
        features=["breathable"],
        intended_activities=[],
        fit=None,
        care_instructions=[],
        environmental_claims=[],
    )
    fake_extractor = Mock()
    fake_extractor.extract.return_value = parsed
    monkeypatch.setattr(extract_products.genai, "Client", Mock(return_value=Mock()))
    monkeypatch.setattr(
        extract_products,
        "ProductLLMExtractor",
        Mock(return_value=fake_extractor),
    )
    monkeypatch.setattr("builtins.print", lambda *args, **kwargs: None)

    extract_products.main()

    output_records = [
        json.loads(line)
        for line in output_path.read_text(encoding="utf-8").splitlines()
        if line
    ]
    assert len(output_records) == 1
    assert output_records[0]["sku"] == "5181"
    assert output_records[0]["name"] == "Spark"
    assert output_records[0]["llm_attributes"]["materials"] == ["merino wool"]
    assert output_records[0]["llm_attributes"]["features"] == ["breathable"]
    fake_extractor.extract.assert_called_once_with(
        product_name="Spark",
        description="Breathable merino wool jacket.",
    )


def test_extract_products_requires_gemini_api_key(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setenv("GEMINI_MODEL", "fake-model")

    try:
        from scraper_demo import extract_products
        import pytest
        with pytest.raises(RuntimeError, match="GEMINI_API_KEY"):
            extract_products.main()
    finally:
        pass


def test_extract_products_requires_model_name(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    monkeypatch.delenv("GEMINI_MODEL", raising=False)

    import pytest
    with pytest.raises(RuntimeError, match="GEMINI_MODEL"):
        extract_products.main()
