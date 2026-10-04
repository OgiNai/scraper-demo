from dataclasses import asdict, dataclass
from typing import Any


@dataclass(slots=True)
class ProductRecord:
    name: str
    url: str
    sku: str | None
    brand: str | None
    price: float | None
    currency: str | None
    availability: str | None
    image: str | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
