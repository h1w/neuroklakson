import re

LINK_RE = re.compile(r"https?://\S+", re.IGNORECASE)
CONTROL_RE = re.compile(r"[\x00-\x1f\x7f-\x9f]")
EXPORT_LINE_RE = re.compile(r"^\[[^\]]+\]\s*[^:]+:\s*(.*)$")
REPEATED_WORD_RE = re.compile(r"\b(?P<word>\w+)(?:\s+(?P=word))+\b", re.IGNORECASE)
SPACE_BEFORE_PUNCTUATION_RE = re.compile(r"\s+([,.;:!?])")
SPACE_AFTER_PUNCTUATION_RE = re.compile(r"([,.;:!?]+)(?=[^\s,.;:!?])")
LONG_WORD_RE = re.compile(r"\w+")
STANDALONE_AT_RE = re.compile(r"(?:^|\s)@(?!\w)(?=\s|$)")
PROMPT_NOISE_RE = re.compile(r"\b(?:instructions?|prompt|system)\b", re.IGNORECASE)
WIKI_CITATION_RE = re.compile(r"\[\d+\]")
DANGLING_END_WORDS = {
    "а",
    "без",
    "в",
    "во",
    "для",
    "до",
    "за",
    "и",
    "или",
    "из",
    "к",
    "на",
    "над",
    "не",
    "но",
    "о",
    "об",
    "от",
    "по",
    "под",
    "при",
    "про",
    "с",
    "со",
    "то",
    "у",
    "что",
}


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
    cleaned = WIKI_CITATION_RE.sub("", cleaned)
    cleaned = CONTROL_RE.sub(" ", cleaned)
    cleaned = " ".join(cleaned.split())
    cleaned = _trim_words(cleaned, max_word_length)

    return cleaned


def clean_generated_text(text: str, max_word_length: int = 32) -> str:
    text = STANDALONE_AT_RE.sub(" ", text)
    text = PROMPT_NOISE_RE.sub(" ", text)
    text = WIKI_CITATION_RE.sub("", text)
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
    words = cleaned.split()
    while words and words[-1].strip(",.;:!?").lower() in DANGLING_END_WORDS:
        words.pop()
    cleaned = " ".join(words)
    return cleaned.strip()
