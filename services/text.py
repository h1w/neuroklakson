import re

LINK_RE = re.compile(r"https?://\S+", re.IGNORECASE)
CONTROL_RE = re.compile(r"[\x00-\x1f\x7f-\x9f]")
EXPORT_LINE_RE = re.compile(r"^\[[^\]]+\]\s*[^:]+:\s*(.*)$")
REPEATED_WORD_RE = re.compile(r"\b(?P<word>\w+)(?:\s+(?P=word))+\b", re.IGNORECASE)
SPACE_BEFORE_PUNCTUATION_RE = re.compile(r"\s+([,.;:!?])")
SPACE_AFTER_PUNCTUATION_RE = re.compile(r"([,.;:!?])(?=\S)")
LONG_WORD_RE = re.compile(r"\w+")


def _trim_words(text: str, max_word_length: int) -> str:
    return LONG_WORD_RE.sub(lambda match: match.group(0)[:max_word_length], text)


def extract_export_text(line: str) -> str:
    match = EXPORT_LINE_RE.match(line)
    if match is None:
        return line
    return match.group(1)


def normalize_training_text(text: str | None, max_word_length: int = 32) -> str | None:
    if text is None:
        return None

    cleaned = text.strip()
    if not cleaned or cleaned.startswith("/"):
        return None

    cleaned = LINK_RE.sub(" ", cleaned)
    cleaned = CONTROL_RE.sub(" ", cleaned)
    cleaned = " ".join(cleaned.split())
    cleaned = _trim_words(cleaned, max_word_length)

    if len(cleaned) < 8:
        return None

    return cleaned


def clean_generated_text(text: str, max_word_length: int = 32) -> str:
    cleaned = CONTROL_RE.sub(" ", text)
    cleaned = " ".join(cleaned.split())

    while True:
        deduplicated = REPEATED_WORD_RE.sub(lambda match: match.group("word"), cleaned)
        if deduplicated == cleaned:
            break
        cleaned = deduplicated

    cleaned = SPACE_BEFORE_PUNCTUATION_RE.sub(r"\1", cleaned)
    cleaned = SPACE_AFTER_PUNCTUATION_RE.sub(r"\1 ", cleaned)
    cleaned = _trim_words(cleaned, max_word_length)
    return cleaned.strip()
