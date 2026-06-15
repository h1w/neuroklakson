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
MAX_NOUN_PHRASE_LOOKAHEAD = 3


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


def _join_token(prefix: str, word: str, suffix: str) -> str:
    return f"{prefix}{word}{suffix}"


@lru_cache(maxsize=4096)
def _parse_word(word: str):
    return _morph().parse(word)[0]


@lru_cache(maxsize=4096)
def _parse_word_options(word: str):
    return tuple(_morph().parse(word))


def _select_noun_parse(word: str):
    parses = [
        parsed
        for parsed in _parse_word_options(word)
        if "NOUN" in parsed.tag or "Name" in parsed.tag or "Surn" in parsed.tag
    ]
    if not parses:
        return None
    if word.lower().replace("ё", "е").endswith(("ы", "и")):
        plural_parse = next((parsed for parsed in parses if parsed.tag.number == "plur"), None)
        if plural_parse is not None:
            return plural_parse
    return parses[0]


def _select_adjective_parse(word: str):
    parses = _parse_word_options(word)
    return next((parsed for parsed in parses if "ADJF" in parsed.tag), None) or next(
        (parsed for parsed in parses if "PRTF" in parsed.tag),
        None,
    )


def _inflect_unknown_feminine_adjective(word: str, grammemes: set[str]) -> str | None:
    lower_word = word.lower().replace("ё", "е")
    if lower_word.endswith("ая"):
        stem = word[:-2]
        soft = False
    elif lower_word.endswith("яя"):
        stem = word[:-2]
        soft = True
    else:
        return None

    if "plur" in grammemes:
        ending = "ие" if soft else "ые"
    elif {"gent", "datv", "ablt", "loct"} & grammemes:
        ending = "ей" if soft else "ой"
    elif "accs" in grammemes:
        ending = "юю" if soft else "ую"
    else:
        ending = "яя" if soft else "ая"
    return _match_case(word, f"{stem}{ending}")


def _is_noun_like(word: str) -> bool:
    if not WORD_RE.match(word):
        return False
    return _select_noun_parse(word) is not None


def _is_adjective_like(word: str) -> bool:
    if not WORD_RE.match(word):
        return False
    lower_word = word.lower().replace("ё", "е")
    return _select_adjective_parse(word) is not None or lower_word.endswith(("ая", "яя"))


def _noun_agreement_grammemes(word: str, target_case: str | None = None) -> set[str]:
    parsed = _select_noun_parse(word)
    if parsed is None:
        return set()
    grammemes: set[str] = set()
    noun_case = target_case or parsed.tag.case
    if noun_case is not None:
        grammemes.add(noun_case)
    if parsed.tag.number is not None:
        grammemes.add(parsed.tag.number)
    if parsed.tag.gender is not None and parsed.tag.number != "plur":
        grammemes.add(parsed.tag.gender)
    return grammemes


def _inflect_with_grammemes(word: str, grammemes: set[str]) -> str | None:
    if not WORD_RE.match(word):
        return None

    parsed = _select_adjective_parse(word) or _parse_word(word)
    inflected = parsed.inflect(grammemes)
    if inflected is None or "ADJF" not in inflected.tag:
        return _inflect_unknown_feminine_adjective(word, grammemes)
    return _match_case(word, inflected.word)


def _inflect_word(word: str, target_case: str) -> str | None:
    if not WORD_RE.match(word):
        return None

    parsed = _select_noun_parse(word)
    if parsed is None:
        return None
    inflected = parsed.inflect({target_case})
    if inflected is None:
        return None
    return _match_case(word, inflected.word)


def _find_following_noun_phrase(words: list[str], start_index: int) -> tuple[list[int], int] | None:
    adjective_indexes: list[int] = []
    stop_index = min(len(words), start_index + MAX_NOUN_PHRASE_LOOKAHEAD)
    for index in range(start_index, stop_index):
        word = words[index]
        if _is_adjective_like(word):
            adjective_indexes.append(index)
            continue
        if _is_noun_like(word):
            return adjective_indexes, index
        return None
    return None


def _apply_word(parts: list[tuple[str, str, str]], tokens: list[str], index: int, word: str) -> None:
    prefix, _, suffix = parts[index]
    parts[index] = (prefix, word, suffix)
    tokens[index] = _join_token(prefix, word, suffix)


def _polish_prepositional_phrases(parts: list[tuple[str, str, str]], tokens: list[str]) -> set[int]:
    words = [word for _, word, _ in parts]
    protected_adjectives: set[int] = set()
    for index, word in enumerate(words):
        target_case = PREPOSITION_CASES.get(word.lower().replace("ё", "е"))
        if target_case is None:
            continue

        phrase = _find_following_noun_phrase(words, index + 1)
        if phrase is None:
            continue

        adjective_indexes, noun_index = phrase
        noun = words[noun_index]
        inflected_noun = _inflect_word(noun, target_case)
        if inflected_noun is None:
            continue

        agreement = _noun_agreement_grammemes(noun, target_case)
        _apply_word(parts, tokens, noun_index, inflected_noun)
        words[noun_index] = inflected_noun
        for adjective_index in adjective_indexes:
            inflected_adjective = _inflect_with_grammemes(words[adjective_index], agreement)
            if inflected_adjective is not None:
                _apply_word(parts, tokens, adjective_index, inflected_adjective)
                words[adjective_index] = inflected_adjective
                protected_adjectives.add(adjective_index)
    return protected_adjectives


def _polish_adjective_agreement(
    parts: list[tuple[str, str, str]], tokens: list[str], protected_adjectives: set[int]
) -> None:
    words = [word for _, word, _ in parts]
    for index, word in enumerate(words):
        if index in protected_adjectives:
            continue
        if not _is_adjective_like(word):
            continue

        phrase = _find_following_noun_phrase(words, index)
        if phrase is None:
            continue

        adjective_indexes, noun_index = phrase
        if index not in adjective_indexes:
            continue

        agreement = _noun_agreement_grammemes(words[noun_index])
        for adjective_index in adjective_indexes:
            inflected_adjective = _inflect_with_grammemes(words[adjective_index], agreement)
            if inflected_adjective is not None:
                _apply_word(parts, tokens, adjective_index, inflected_adjective)
                words[adjective_index] = inflected_adjective


def polish_morphology(text: str) -> str:
    tokens = text.split()
    parts = [_split_edge_punctuation(token) for token in tokens]

    protected_adjectives = _polish_prepositional_phrases(parts, tokens)
    _polish_adjective_agreement(parts, tokens, protected_adjectives)

    return " ".join(tokens)
