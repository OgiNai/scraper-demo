from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from scraper_demo.llm_extractor import ProductLLMExtractor
from scraper_demo.llm_models import StructuredProductAttributes


def attributes(**overrides):
    values = {
        "materials": ["merino wool"],
        "features": ["breathable"],
        "intended_activities": ["hiking"],
        "fit": "regular fit",
        "care_instructions": ["machine wash cold"],
        "environmental_claims": ["recycled polyester"],
    }
    values.update(overrides)
    return StructuredProductAttributes(**values)


def test_empty_description_returns_empty_attributes_without_llm_call():
    client = Mock()
    extractor = ProductLLMExtractor(client=client, model="test-model")

    result = extractor.extract(product_name="Spark", description=" \n ")

    assert result.materials == []
    assert result.features == []
    assert result.intended_activities == []
    assert result.fit is None
    assert result.care_instructions == []
    assert result.environmental_claims == []
    client.models.generate_content.assert_not_called()


def test_extract_returns_parsed_structured_attributes():
    expected = attributes()
    client = Mock()
    client.models.generate_content.return_value = SimpleNamespace(parsed=expected)
    extractor = ProductLLMExtractor(client=client, model="test-model")

    result = extractor.extract(
        product_name="Spark",
        description="Merino wool. Breathable. Suitable for hiking.",
    )

    assert result is expected
    client.models.generate_content.assert_called_once()
    kwargs = client.models.generate_content.call_args.kwargs
    assert kwargs["model"] == "test-model"
    assert "Spark" in kwargs["contents"]
    assert "Suitable for hiking." in kwargs["contents"]


def test_extract_raises_when_model_does_not_return_parsed_output():
    client = Mock()
    client.models.generate_content.return_value = SimpleNamespace(parsed=None)
    extractor = ProductLLMExtractor(client=client, model="test-model")

    with pytest.raises(RuntimeError, match="did not contain parsed"):
        extractor.extract(product_name="Spark", description="Some description")


def test_extract_raises_for_unexpected_parsed_type():
    client = Mock()
    client.models.generate_content.return_value = SimpleNamespace(parsed={"fit": "regular"})
    extractor = ProductLLMExtractor(client=client, model="test-model")

    with pytest.raises(TypeError, match="unexpected structured output type"):
        extractor.extract(product_name="Spark", description="Some description")


def test_structured_attributes_schema_accepts_empty_categories_and_null_fit():
    result = StructuredProductAttributes(
        materials=[],
        features=[],
        intended_activities=[],
        fit=None,
        care_instructions=[],
        environmental_claims=[],
    )

    assert result.model_dump() == {
        "materials": [],
        "features": [],
        "intended_activities": [],
        "fit": None,
        "care_instructions": [],
        "environmental_claims": [],
    }
