import random
from collections.abc import Iterable
from typing import Literal

from services.text import clean_generated_text, normalize_training_text

GenerationMode = Literal["normal", "absurd", "chaos"]

VALID_MODES: set[GenerationMode] = {"normal", "absurd", "chaos"}
MODE_SETTINGS: dict[GenerationMode, tuple[int, float]] = {
    "normal": (2, 0.05),
    "absurd": (2, 0.22),
    "chaos": (1, 0.38),
}


def _tokenize_messages(messages: Iterable[str | None]) -> list[list[str]]:
    tokenized: list[list[str]] = []
    for message in messages:
        normalized = normalize_training_text(message)
        if normalized is None:
            continue

        words = normalized.split()
        if len(words) >= 3:
            tokenized.append(words)

    return tokenized


def _build_chain(tokenized_messages: Iterable[list[str]], order: int) -> dict[tuple[str, ...], list[str]]:
    chain: dict[tuple[str, ...], list[str]] = {}
    for words in tokenized_messages:
        for index in range(len(words) - order):
            key = tuple(words[index : index + order])
            chain.setdefault(key, []).append(words[index + order])

    return chain


def _validate_mode(mode: str) -> GenerationMode:
    if mode not in VALID_MODES:
        valid_modes = ", ".join(sorted(VALID_MODES))
        raise ValueError(f"mode must be one of: {valid_modes}")
    return mode  # type: ignore[return-value]


def generate_markov_text(
    messages: Iterable[str | None],
    mode: GenerationMode = "absurd",
    max_words: int = 30,
    rng: random.Random | None = None,
) -> str | None:
    selected_mode = _validate_mode(mode)
    if max_words <= 0:
        return None

    order, reset_probability = MODE_SETTINGS[selected_mode]
    tokenized_messages = _tokenize_messages(messages)
    if len(tokenized_messages) < 3:
        return None

    chain = _build_chain(tokenized_messages, order)
    if not chain:
        return None

    random_source = rng or random
    keys = list(chain)
    context = random_source.choice(keys)
    output = list(context[:max_words])

    while len(output) < max_words:
        if random_source.random() < reset_probability:
            context = random_source.choice(keys)

        next_words = chain.get(context)
        if not next_words:
            context = random_source.choice(keys)
            continue

        next_word = random_source.choice(next_words)
        output.append(next_word)
        context = (*context[1:], next_word) if order > 1 else (next_word,)

    cleaned = clean_generated_text(" ".join(output[:max_words]))
    if not cleaned:
        return None
    return " ".join(cleaned.split()[:max_words])


async def create_chain(text: str, chain_length: int = 2):
    return _build_chain(_tokenize_messages([text]), chain_length)


async def generate_text(chain, chain_length: int = 2, max_words: int = 100):
    if max_words <= 0 or not chain:
        return ""

    keys = list(chain)
    context = random.choice(keys)
    output = list(context[:max_words])

    while len(output) < max_words:
        next_words = chain.get(context)
        if not next_words:
            break
        next_word = random.choice(next_words)
        output.append(next_word)
        context = (*context[1:], next_word) if chain_length > 1 else (next_word,)

    return clean_generated_text(" ".join(output[:max_words]))


async def makeShortSentence(text: str, max_words: int = 100) -> str | None:
    messages = text.splitlines() or [text]
    return generate_markov_text(messages, max_words=max_words)


async def textCleaner(text: str):
    return clean_generated_text(text)
