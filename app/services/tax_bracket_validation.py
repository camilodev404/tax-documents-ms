from __future__ import annotations

from collections import defaultdict

from app.infrastructure.ai.extractor import ExtractedTaxBracket


class TaxBracketValidationError(ValueError):
    pass


def validate_extracted_tax_brackets(records: list[ExtractedTaxBracket]) -> None:
    _validate_unique_source_record_ids(records)
    _validate_bracket_continuity(records)


def _validate_unique_source_record_ids(records: list[ExtractedTaxBracket]) -> None:
    seen: set[int] = set()
    duplicates: set[int] = set()
    for record in records:
        if record.source_record_id in seen:
            duplicates.add(record.source_record_id)
        seen.add(record.source_record_id)

    if duplicates:
        duplicate_list = ", ".join(str(value) for value in sorted(duplicates))
        raise TaxBracketValidationError(f"Duplicate source_record_id values: {duplicate_list}")


def _validate_bracket_continuity(records: list[ExtractedTaxBracket]) -> None:
    grouped: dict[tuple[int, str], list[ExtractedTaxBracket]] = defaultdict(list)
    for record in records:
        grouped[(record.tax_year, record.jurisdiction)].append(record)

    for (tax_year, jurisdiction), group in grouped.items():
        sorted_group = sorted(group, key=lambda record: record.income_min)
        for index in range(len(sorted_group) - 1):
            current = sorted_group[index]
            next_record = sorted_group[index + 1]
            if current.income_max is None:
                raise TaxBracketValidationError(
                    f"Only the last bracket may have income_max=None for {tax_year} {jurisdiction}"
                )
            if current.income_max != next_record.income_min:
                raise TaxBracketValidationError(
                    "Income brackets must be continuous for "
                    f"{tax_year} {jurisdiction}: "
                    f"{current.income_max} != {next_record.income_min}"
                )
