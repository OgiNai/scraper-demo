from __future__ import annotations

import argparse
import json
import math
import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

SCORED_FIELDS = (
    "name",
    "url",
    "brand",
    "price",
    "currency",
    "availability",
    "image",
)

DEFAULT_WEIGHTS: dict[str, float] = {
    "name": 1.0,
    "url": 1.0,
    "brand": 1.0,
    "price": 1.0,
    "currency": 0.2,
    "availability": 1.0,
    "image": 0.5,
}


@dataclass(slots=True)
class FieldResult:
    field: str
    expected: Any
    actual: Any
    correct: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "expected": self.expected,
            "actual": self.actual,
            "correct": self.correct,
        }


@dataclass(slots=True)
class ProductEvaluation:
    sku: str
    matched: bool
    fields: dict[str, FieldResult] = field(default_factory=dict)

    @property
    def score(self) -> float:
        if not self.fields:
            return 0.0

        return sum(result.correct for result in self.fields.values()) / len(self.fields)

    def to_dict(self) -> dict[str, Any]:
        return {
            "sku": self.sku,
            "matched": self.matched,
            "score": round(self.score, 4),
            "fields": {name: result.to_dict() for name, result in self.fields.items()},
        }


@dataclass(slots=True)
class EvaluationReport:
    golden_count: int
    actual_count: int
    matched_count: int
    missing_skus: list[str]
    unexpected_skus: list[str]
    duplicate_golden_skus: list[str]
    duplicate_actual_skus: list[str]
    field_scores: dict[str, float]
    overall_score: float
    products: list[ProductEvaluation]

    def to_dict(self) -> dict[str, Any]:
        return {
            "summary": {
                "golden_count": self.golden_count,
                "actual_count": self.actual_count,
                "matched_count": self.matched_count,
                "missing_count": len(self.missing_skus),
                "unexpected_count": len(self.unexpected_skus),
                "duplicate_golden_count": len(self.duplicate_golden_skus),
                "duplicate_actual_count": len(self.duplicate_actual_skus),
                "overall_score": round(self.overall_score, 4),
            },
            "field_scores": {
                field: round(score, 4) for field, score in self.field_scores.items()
            },
            "missing_skus": self.missing_skus,
            "unexpected_skus": self.unexpected_skus,
            "duplicate_golden_skus": self.duplicate_golden_skus,
            "duplicate_actual_skus": self.duplicate_actual_skus,
            "products": [product.to_dict() for product in self.products],
        }


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []

    with path.open(encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            line = line.strip()

            if not line:
                continue

            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Invalid JSON on line {line_number} of {path}: {exc}"
                ) from exc

            if not isinstance(record, dict):
                raise TypeError(
                    f"Line {line_number} of {path} must contain a JSON object."
                )

            records.append(record)

    return records


def _normalize_string(value: Any) -> str | None:
    if value is None:
        return None

    if not isinstance(value, str):
        value = str(value)

    normalized = re.sub(r"\s+", " ", value.strip())

    return normalized or None


def _normalize_url(value: Any) -> str | None:
    normalized = _normalize_string(value)

    if normalized is None:
        return None

    return normalized.rstrip("/")


def _normalize_case_insensitive(value: Any) -> str | None:
    normalized = _normalize_string(value)

    if normalized is None:
        return None

    return normalized.casefold()


def _normalize_price(value: Any) -> float | None:
    if value is None or value == "":
        return None

    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid price value: {value!r}") from exc


def _values_equal(
    expected: Any,
    actual: Any,
    normalizer: Callable[[Any], Any],
) -> bool:
    expected_normalized = normalizer(expected)
    actual_normalized = normalizer(actual)

    if expected_normalized is None and actual_normalized is None:
        return True

    return expected_normalized == actual_normalized


def _price_equal(expected: Any, actual: Any) -> bool:
    expected_price = _normalize_price(expected)
    actual_price = _normalize_price(actual)

    if expected_price is None and actual_price is None:
        return True

    if expected_price is None or actual_price is None:
        return False

    return math.isclose(
        expected_price,
        actual_price,
        rel_tol=1e-9,
        abs_tol=1e-9,
    )


FIELD_COMPARATORS: dict[str, Callable[[Any, Any], bool]] = {
    "name": lambda expected, actual: _values_equal(
        expected,
        actual,
        _normalize_string,
    ),
    "url": lambda expected, actual: _values_equal(
        expected,
        actual,
        _normalize_url,
    ),
    "brand": lambda expected, actual: _values_equal(
        expected,
        actual,
        _normalize_string,
    ),
    "price": _price_equal,
    "currency": lambda expected, actual: _values_equal(
        expected,
        actual,
        _normalize_case_insensitive,
    ),
    "availability": lambda expected, actual: _values_equal(
        expected,
        actual,
        _normalize_case_insensitive,
    ),
    "image": lambda expected, actual: _values_equal(
        expected,
        actual,
        _normalize_url,
    ),
}


def _index_by_sku(
    records: Iterable[dict[str, Any]],
) -> tuple[dict[str, dict[str, Any]], list[str]]:
    indexed: dict[str, dict[str, Any]] = {}
    duplicates: list[str] = []

    for record in records:
        sku = _normalize_string(record.get("sku"))

        if sku is None:
            raise ValueError("Every evaluation record must have a non-empty SKU.")

        if sku in indexed:
            duplicates.append(sku)
            continue

        indexed[sku] = record

    return indexed, sorted(set(duplicates))


def evaluate(
    golden_records: list[dict[str, Any]],
    actual_records: list[dict[str, Any]],
    weights: dict[str, float] | None = None,
) -> EvaluationReport:
    weights = weights or DEFAULT_WEIGHTS.copy()

    unknown_weights = set(weights) - set(SCORED_FIELDS)
    if unknown_weights:
        raise ValueError(f"Unknown field weights: {sorted(unknown_weights)}")

    for field_name in SCORED_FIELDS:
        weights.setdefault(field_name, 0.0)

    if any(weight < 0 for weight in weights.values()):
        raise ValueError("Field weights must not be negative.")

    total_weight = sum(weights.values())
    if total_weight <= 0:
        raise ValueError("At least one field must have a positive weight.")

    golden_by_sku, duplicate_golden_skus = _index_by_sku(golden_records)
    actual_by_sku, duplicate_actual_skus = _index_by_sku(actual_records)

    golden_skus = set(golden_by_sku)
    actual_skus = set(actual_by_sku)

    missing_skus = sorted(golden_skus - actual_skus)
    unexpected_skus = sorted(actual_skus - golden_skus)

    products: list[ProductEvaluation] = []

    field_correct: dict[str, int] = {field_name: 0 for field_name in SCORED_FIELDS}

    for sku in sorted(golden_skus & actual_skus):
        expected = golden_by_sku[sku]
        actual = actual_by_sku[sku]

        field_results: dict[str, FieldResult] = {}

        for field_name in SCORED_FIELDS:
            expected_value = expected.get(field_name)
            actual_value = actual.get(field_name)

            correct = FIELD_COMPARATORS[field_name](
                expected_value,
                actual_value,
            )

            field_results[field_name] = FieldResult(
                field=field_name,
                expected=expected_value,
                actual=actual_value,
                correct=correct,
            )

            if correct:
                field_correct[field_name] += 1

        products.append(
            ProductEvaluation(
                sku=sku,
                matched=True,
                fields=field_results,
            )
        )

    matched_count = len(products)

    field_scores = {
        field_name: (
            field_correct[field_name] / matched_count if matched_count else 0.0
        )
        for field_name in SCORED_FIELDS
    }

    overall_score = (
        sum(
            field_scores[field_name] * weights[field_name]
            for field_name in SCORED_FIELDS
        )
        / total_weight
    )

    return EvaluationReport(
        golden_count=len(golden_records),
        actual_count=len(actual_records),
        matched_count=matched_count,
        missing_skus=missing_skus,
        unexpected_skus=unexpected_skus,
        duplicate_golden_skus=duplicate_golden_skus,
        duplicate_actual_skus=duplicate_actual_skus,
        field_scores=field_scores,
        overall_score=overall_score,
        products=products,
    )


def print_report(report: EvaluationReport) -> None:
    summary = report.to_dict()["summary"]

    print("Scraper evaluation")
    print("==================")
    print(f"Golden products:   {summary['golden_count']}")
    print(f"Actual products:   {summary['actual_count']}")
    print(f"Matched products:  {summary['matched_count']}")
    print(f"Missing products:  {summary['missing_count']}")
    print(f"Unexpected:        {summary['unexpected_count']}")
    print(f"Duplicate golden:  {summary['duplicate_golden_count']}")
    print(f"Duplicate actual:  {summary['duplicate_actual_count']}")
    print()
    print("Field scores")
    print("------------")

    for field_name, score in report.field_scores.items():
        print(f"{field_name:15} {score:.1%}")

    print()
    print(f"Overall score:     {report.overall_score:.1%}")

    if report.missing_skus:
        print()
        print("Missing SKUs")
        print("------------")
        for sku in report.missing_skus:
            print(f"- {sku}")

    if report.unexpected_skus:
        print()
        print("Unexpected SKUs")
        print("----------------")
        for sku in report.unexpected_skus:
            print(f"- {sku}")

    failed_products = [
        product
        for product in report.products
        if any(not result.correct for result in product.fields.values())
    ]

    if failed_products:
        print()
        print("Field failures")
        print("--------------")

        for product in failed_products:
            print(f"\nSKU {product.sku}:")

            for field_name, result in product.fields.items():
                if not result.correct:
                    print(f"  {field_name}:")
                    print(f"    expected: {result.expected!r}")
                    print(f"    actual:   {result.actual!r}")


def parse_weights(values: list[str]) -> dict[str, float]:
    weights = DEFAULT_WEIGHTS.copy()

    for value in values:
        try:
            field_name, weight_string = value.split("=", maxsplit=1)
            weight = float(weight_string)
        except ValueError as exc:
            raise ValueError(
                f"Invalid weight {value!r}; expected FIELD=NUMBER."
            ) from exc

        if field_name not in SCORED_FIELDS:
            raise ValueError(
                f"Unknown field {field_name!r}. "
                f"Valid fields: {', '.join(SCORED_FIELDS)}"
            )

        if weight < 0:
            raise ValueError(f"Weight for {field_name!r} cannot be negative.")

        weights[field_name] = weight

    return weights


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evaluate scraper output against a golden JSONL dataset."
    )
    parser.add_argument(
        "--golden",
        type=Path,
        required=True,
        help="Path to the golden dataset JSONL file.",
    )
    parser.add_argument(
        "--actual",
        type=Path,
        required=True,
        help="Path to the scraper output JSONL file.",
    )
    parser.add_argument(
        "--report",
        type=Path,
        help="Optional path for a JSON evaluation report.",
    )
    parser.add_argument(
        "--weight",
        action="append",
        default=[],
        metavar="FIELD=NUMBER",
        help="Override a field weight. Can be supplied multiple times.",
    )

    args = parser.parse_args()

    golden_records = load_jsonl(args.golden)
    actual_records = load_jsonl(args.actual)
    weights = parse_weights(args.weight)

    report = evaluate(
        golden_records=golden_records,
        actual_records=actual_records,
        weights=weights,
    )

    print_report(report)

    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)

        with args.report.open("w", encoding="utf-8") as file:
            json.dump(
                report.to_dict(),
                file,
                ensure_ascii=False,
                indent=2,
            )

        print(f"\nJSON report: {args.report}")


if __name__ == "__main__":
    main()
