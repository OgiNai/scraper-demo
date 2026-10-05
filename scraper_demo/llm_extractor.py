from google import genai
from google.genai import types

from scraper_demo.llm_models import StructuredProductAttributes

SYSTEM_PROMPT = """
You extract structured product attributes from retailer product descriptions.

Rules:
- Extract only information explicitly supported by the supplied text.
- Never infer or invent product attributes.
- Preserve the meaning of the source text.
- Normalize obvious formatting differences, but do not add information.
- Use an empty list when a category is not present.
- Use null for fit when fit is not explicitly stated.
- Do not extract size, color, price, SKU, availability, or variants.
  Those fields are handled separately by deterministic extraction.
"""


class ProductLLMExtractor:
    """Extract structured product attributes using an LLM."""

    def __init__(
        self,
        client: genai.Client,
        model: str,
    ) -> None:
        self._client = client
        self._model = model

    def extract(
        self,
        *,
        product_name: str,
        description: str,
    ) -> StructuredProductAttributes:
        """Extract structured attributes from a product description."""
        if not description.strip():
            return StructuredProductAttributes(
                materials=[],
                features=[],
                intended_activities=[],
                fit=None,
                care_instructions=[],
                environmental_claims=[],
            )

        prompt = (
            f"{SYSTEM_PROMPT}\n\n"
            f"Product name:\n{product_name}\n\n"
            f"Product description:\n{description}"
        )

        response = self._client.models.generate_content(
            model=self._model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=StructuredProductAttributes,
                automatic_function_calling=types.AutomaticFunctionCallingConfig(
                    disable=True,
                ),
            ),
        )

        if response.parsed is None:
            raise RuntimeError(
                "Gemini response did not contain parsed structured output."
            )

        if not isinstance(response.parsed, StructuredProductAttributes):
            raise TypeError("Gemini returned an unexpected structured output type.")

        return response.parsed
