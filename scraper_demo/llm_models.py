from pydantic import BaseModel, Field


class StructuredProductAttributes(BaseModel):
    """LLM-extracted attributes from unstructured product description."""

    materials: list[str] = Field(
        description="Materials explicitly stated in the product description.",
    )

    features: list[str] = Field(
        description=(
            "Product features explicitly stated in the product description, "
            "such as pockets, zippers, breathability, waterproofing, or "
            "other functional characteristics."
        ),
    )

    intended_activities: list[str] = Field(
        description=(
            "Sports, activities, or use cases explicitly associated with the product."
        ),
    )

    fit: str | None = Field(
        default=None,
        description=(
            "The explicitly stated fit, such as normal fit, slim fit, "
            "loose fit, or relaxed fit. Null when not stated."
        ),
    )

    care_instructions: list[str] = Field(
        description=(
            "Product-care instructions explicitly stated in the description. "
            "Do not invent care instructions when they are absent."
        ),
    )

    environmental_claims: list[str] = Field(
        description=(
            "Explicit environmental or sustainability-related claims made "
            "about the product."
        ),
    )
