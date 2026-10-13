# Test suite

The suite covers:
- Unit tests: ProductRecord serialization, evaluator normalization/scoring/JSONL validation, spider extraction helpers, and mocked Gemini extractor/schema behavior.
- Integration tests: navigation discovery, product-link deduplication, pagination, JSON-LD extraction, mocked LLM enrichment pipeline, and failure handling.
- End-to-end test: real Scrapy engine crawling a local fixture website and exporting JSONL. It makes no external requests and uses no Gemini API key.

Install and run:

```bash
uv add --dev pytest
uv run pytest
```

Run layers separately:

```bash
uv run pytest tests/unit
uv run pytest tests/integration
uv run pytest tests/e2e
```

The evaluator test for `SPARK` vs `Spark` assumes the current case-insensitive name comparator change. The E2E test supplies `start_urls` in a test-only subclass; the production spider currently has no `start_urls` of its own. Also add a no-script regression test after fixing `parse_product` to initialize `product = None` before the JSON-LD loop; the current implementation can raise `UnboundLocalError` when there are no JSON-LD script tags.
