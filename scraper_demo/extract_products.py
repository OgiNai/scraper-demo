import json
import os
from pathlib import Path
from typing import Any

from google import genai

from scraper_demo.llm_extractor import ProductLLMExtractor

INPUT_PATH = Path("output/products.jsonl")
OUTPUT_PATH = Path("output/llm_products.jsonl")


def main() -> None:
    api_key = os.environ.get("GEMINI_API_KEY")
    model = os.environ.get("GEMINI_MODEL")

    if not api_key:
        raise RuntimeError("GEMINI_API_KEY environment variable is required.")

    if not model:
        raise RuntimeError("GEMINI_MODEL environment variable is required.")

    products: list[dict[str, Any]] = []

    with INPUT_PATH.open(encoding="utf-8") as file:
        for line in file:
            line = line.strip()

            if line:
                products.append(json.loads(line))

    client = genai.Client(api_key=api_key)
    extractor = ProductLLMExtractor(
        client=client,
        model=model,
    )

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    with OUTPUT_PATH.open("w", encoding="utf-8") as file:
        for index, product in enumerate(products, start=1):
            name = product.get("name") or ""
            description = product.get("description") or ""

            print(f"[{index}/{len(products)}] {name}")

            extracted = extractor.extract(
                product_name=name,
                description=description,
            )

            result = {
                **product,
                "llm_attributes": extracted.model_dump(),
            }

            file.write(json.dumps(result, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
