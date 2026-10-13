import json
import pytest
from scraper_demo.evaluate import (
    DEFAULT_WEIGHTS, SCORED_FIELDS, _normalize_case_insensitive,
    _normalize_price, _normalize_string, _normalize_url, evaluate,
    load_jsonl, parse_weights,
)

def test_normalize_string_collapses_whitespace():
    assert _normalize_string("  Spark\n  3L\tJacket ") == "Spark 3L Jacket"

def test_normalize_casefold():
    assert _normalize_case_insensitive(" SPARK ") == "spark"
    assert _normalize_case_insensitive("Straße") == "strasse"
    assert _normalize_case_insensitive(None) is None

def test_normalize_url_trailing_slash():
    assert _normalize_url(" https://example.test/product/ ") == "https://example.test/product"

@pytest.mark.parametrize(("value", "expected"), [(None, None), ("", None), (35, 35.0), ("35.10", 35.1)])
def test_normalize_price(value, expected):
    assert _normalize_price(value) == expected

def test_normalize_price_rejects_invalid():
    with pytest.raises(ValueError, match="Invalid price"):
        _normalize_price("oops")

def test_name_comparison_is_case_insensitive(golden, product):
    golden["name"] = "SPARK"
    assert evaluate([golden], [product]).overall_score == 1.0

def test_url_comparison_ignores_trailing_slash(golden, product):
    golden["url"] = golden["url"].rstrip("/")
    assert evaluate([golden], [product]).field_scores["url"] == 1.0

def test_currency_and_availability_case_insensitive(golden, product):
    golden["currency"] = "eur"
    golden["availability"] = "instock"
    report = evaluate([golden], [product])
    assert report.field_scores["currency"] == report.field_scores["availability"] == 1.0

def test_numeric_price_equivalence(golden, product):
    golden["price"] = "35.10"
    assert evaluate([golden], [product]).field_scores["price"] == 1.0

def test_price_mismatch_reported(golden, product):
    product["price"] = 36
    report = evaluate([golden], [product])
    assert report.field_scores["price"] == 0
    assert not report.products[0].fields["price"].correct

def test_missing_optional_values_compare_equal(golden, product):
    for key in ("brand", "price", "currency", "availability", "image"):
        golden[key] = product[key] = None
    assert all(x.correct for x in evaluate([golden], [product]).products[0].fields.values())

def test_missing_field_is_failure(golden, product):
    product.pop("image")
    assert evaluate([golden], [product]).field_scores["image"] == 0

def test_matching_uses_sku_not_url(golden, product):
    product["url"] = "https://omsight.test/renamed/"
    report = evaluate([golden], [product])
    assert report.matched_count == 1
    assert report.field_scores["url"] == 0

def test_missing_unexpected_and_duplicate_skus(golden, product):
    report = evaluate(
        [golden, {**golden, "sku": "777"}],
        [product, {**product, "sku": "999"}, dict(product)],
    )
    assert report.missing_skus == ["777"]
    assert report.unexpected_skus == ["999"]
    assert report.duplicate_actual_skus == ["5181"]

@pytest.mark.parametrize("records", [[{"name": "x"}], [{"sku": None}], [{"sku": ""}], [{"sku": "  "}]])
def test_invalid_sku_rejected(records):
    with pytest.raises(ValueError, match="non-empty SKU"):
        evaluate(records, [])

def test_empty_input_scores_zero():
    report = evaluate([], [])
    assert report.overall_score == 0
    assert all(report.field_scores[f] == 0 for f in SCORED_FIELDS)

def test_custom_weights_affect_score(golden, product):
    product["name"] = "Wrong"
    report = evaluate([golden], [product], weights={**DEFAULT_WEIGHTS, "name": 10})
    assert report.overall_score < 1

@pytest.mark.parametrize("weights", [
    {"unknown": 1}, {"name": -1}, {f: 0 for f in SCORED_FIELDS}
])
def test_invalid_weights_rejected(golden, product, weights):
    with pytest.raises(ValueError):
        evaluate([golden], [product], weights=weights)

def test_report_json_serializable(golden, product):
    report = evaluate([golden], [product])
    data = json.loads(json.dumps(report.to_dict()))
    assert data["summary"]["matched_count"] == 1

def test_load_jsonl_skips_blank_lines_and_reads_unicode(tmp_path):
    path = tmp_path / "input.jsonl"
    path.write_text('{"sku":"1","name":"WoolVerine"}\n\n{"sku":"2","name":"Ž"}\n', encoding="utf-8")
    assert len(load_jsonl(path)) == 2

def test_load_jsonl_invalid_json_has_line_number(tmp_path):
    path = tmp_path / "bad.jsonl"
    path.write_text('{"sku":"1"}\n{bad}\n', encoding="utf-8")
    with pytest.raises(ValueError, match="line 2"):
        load_jsonl(path)

def test_load_jsonl_requires_object_per_line(tmp_path):
    path = tmp_path / "bad.jsonl"
    path.write_text('["not","object"]\n', encoding="utf-8")
    with pytest.raises(TypeError, match="JSON object"):
        load_jsonl(path)

def test_parse_weights_override_defaults():
    weights = parse_weights(["name=3", "price=2"])
    assert weights["name"] == 3
    assert weights["price"] == 2
    assert weights["url"] == DEFAULT_WEIGHTS["url"]

@pytest.mark.parametrize(("value", "message"), [
    ("name", "FIELD=NUMBER"), ("bogus=1", "Unknown field"), ("name=-1", "cannot be negative")
])
def test_parse_weights_rejects_invalid(value, message):
    with pytest.raises(ValueError, match=message):
        parse_weights([value])
