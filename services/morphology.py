from __future__ import annotations

import re
from functools import lru_cache

import pymorphy3

PREPOSITION_CASES = {
    "без": "gent",
    "для": "gent",
    "к": "datv",
    "от": "gent",
    "с": "ablt",
    "со": "ablt",
    "у": "gent",
}
WORD_RE = re.compile(r"^[А-Яа-яЁё-]+$")


@lru_cache(maxsize=1)
def _morph() -> pymorphy3.MorphAnalyzer:
    return pymorphy3.MorphAnalyzer()


def _match_case(source: str, inflected: str) -> str:
    if source.isupper():
        return inflected.upper()
    if source[:1].isupper():
        return inflected.capitalize()
    return inflected


def _split_edge_punctuation(token: str) -> tuple[str, str, str]:
    prefix_length = len(token) - len(token.lstrip('"«([{'))
    suffix_length = len(token) - len(token.rstrip('"»)]},.;:!?'))
    prefix = token[:prefix_length]
    suffix = token[len(token) - suffix_length :] if suffix_length else ""
    word_end = len(token) - suffix_length if suffix_length else len(token)
    return prefix, token[prefix_length:word_end], suffix


def _inflect_word(word: str, target_case: str) -> str | None:
    if not WORD_RE.match(word):
        return None

    parsed = _morph().parse(word)[0]
    if "NOUN" not in parsed.tag and "Name" not in parsed.tag and "Surn" not in parsed.tag:
        return None
    inflected = parsed.inflect({target_case})
    if inflected is None:
        return None
    return _match_case(word, inflected.word)


def polish_morphology(text: str) -> str:
    tokens = text.split()
    result: list[str] = []
    pending_case: str | None = None

    for token in tokens:
        prefix, word, suffix = _split_edge_punctuation(token)
        lower_word = word.lower().replace("ё", "е")
        if pending_case is not None:
            inflected = _inflect_word(word, pending_case)
            if inflected is not None:
                token = f"{prefix}{inflected}{suffix}"
            pending_case = None

        result.append(token)
        pending_case = PREPOSITION_CASES.get(lower_word)

    return " ".join(result)
