from dataclasses import dataclass

from services.text import extract_export_text, normalize_training_text


@dataclass(frozen=True)
class ParsedHistory:
    accepted: list[str]
    rejected_count: int


def parse_history_text(raw_text: str) -> ParsedHistory:
    accepted: list[str] = []
    rejected_count = 0

    for line in raw_text.splitlines():
        normalized = normalize_training_text(extract_export_text(line))
        if normalized is None:
            rejected_count += 1
            continue
        accepted.append(normalized)

    return ParsedHistory(accepted=accepted, rejected_count=rejected_count)
