from pydantic import BaseModel, Field


class StructuredProductAttributes(BaseModel):
    """LLM-extracted attributes from an unstructured product description."""

    materials: list[str] = Field(
        description=(
            "Textile, fabric, fiber, insulation, or other physical materials "
            "explicitly stated as being used in the product. Include material "
            "composition and material percentages when stated. Examples include "
            "'98% cashmere wool', '2% Lycra', 'recycled polyester', or "
            "'down insulation'. Do not include product features, performance "
            "properties, hardware, or construction details. For example, "
            "'YKK zippers', 'pockets', 'breathable', and 'waterproof' are not "
            "materials."
        ),
    )

    features: list[str] = Field(
        description=(
            "Functional, construction, performance, or hardware characteristics "
            "of the product that are explicitly stated. This includes features "
            "such as pockets, zippers, closures, breathability, waterproofing, "
            "water resistance, insulation, moisture wicking, quick drying, "
            "durability, packability, collars, hoods, and other functional or "
            "construction characteristics. Include named hardware such as YKK "
            "zippers when presented as a product feature. Do not include actual "
            "materials or sports/activities."
        ),
    )

    intended_activities: list[str] = Field(
        description=(
            "Specific sports, physical activities, or explicit use cases that "
            "the product is stated to be designed for, suitable for, or used "
            "for. Examples include 'climbing', 'biking', 'skiing', 'hiking', "
            "or 'outdoor activities'. Do not include product characteristics "
            "or benefits such as 'storm protection', 'breathability', "
            "'warmth', or 'durability'. Only extract an activity or use case "
            "when it is explicitly associated with using the product."
        ),
    )

    fit: str | None = Field(
        default=None,
        description=(
            "The fit of the product when explicitly stated, such as 'normal "
            "fit', 'slim fit', 'loose fit', 'relaxed fit', or 'oversized fit'. "
            "Do not infer fit from other descriptions. If multiple explicit "
            "fit descriptions are present, return the most specific explicit "
            "fit description that describes how the product is intended to "
            "fit. Return null when no fit is explicitly stated."
        ),
    )

    care_instructions: list[str] = Field(
        description=(
            "Actual product-care instructions explicitly stated in the "
            "description, such as washing, drying, ironing, or cleaning "
            "instructions. Extract instructions only when they contain an "
            "actual care action or requirement. Do not treat headings such "
            "as 'PRODUCT CARE' as an instruction, and do not invent care "
            "instructions that are not present."
        ),
    )

    environmental_claims: list[str] = Field(
        description=(
            "Explicit environmental or sustainability-related claims about "
            "the product or its materials. Examples include 'environmentally "
            "friendly', '100% recycled polyester', 'recycled insulation', "
            "'organic cotton', or other explicitly stated sustainability "
            "claims. Include the environmental aspect only when it is "
            "explicitly stated. Do not classify ordinary material composition, "
            "performance characteristics, or product features as environmental "
            "claims merely because they may have environmental implications."
        ),
    )
