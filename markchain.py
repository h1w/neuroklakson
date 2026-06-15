import random
import re
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Literal

from services.morphology import polish_morphology
from services.text import clean_generated_text, normalize_training_text

GenerationMode = Literal["normal", "absurd", "chaos"]

VALID_MODES: set[GenerationMode] = {"normal", "absurd", "chaos"}
SERVICE_WORDS = {
    "а",
    "без",
    "бы",
    "в",
    "во",
    "вот",
    "да",
    "для",
    "до",
    "же",
    "за",
    "и",
    "или",
    "как",
    "к",
    "ли",
    "на",
    "не",
    "но",
    "ну",
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
    "это",
}
ALLOWED_LATIN_WORDS = {"ai", "api", "bot", "vpn", "youtube"}
NON_RUSSIAN_NOISE_WORDS = {
    "аммо",
    "доштан",
    "забонатро",
    "матн",
    "меомӯзад",
    "нарх",
    "хеле",
    "хостам",
    "худаш",
    "ӯро",
}
LONG_LATIN_RE = re.compile(r"\b[a-z]{16,}\b", re.IGNORECASE)
LATIN_RE = re.compile(r"[A-Za-z]")
CYRILLIC_RE = re.compile(r"[А-Яа-яЁё]")
PROMPT_NOISE_RE = re.compile(r"\b(?:instructions?|prompt|system)\b", re.IGNORECASE)
PROMPT_BULLET_RE = re.compile(
    r"^\s*[*-]\s+(?:выделяй|постоянно|отвечай|используй|пиши|оскорбляй|ворчишь|говори)\b",
    re.IGNORECASE,
)
QUOTE_TOKEN_RE = re.compile(r"(?:^|\s)>+\S+")
DANGLING_START_WORDS = {"а", "и", "или", "но", "что", "это"}
DANGLING_END_WORDS = {"а", "без", "в", "во", "для", "до", "за", "и", "или", "из", "к", "на", "не", "но", "о", "об", "от", "по", "под", "при", "про", "с", "со", "то", "у", "что"}
PROVOCATIVE_WORDS = {
    "ахуй",
    "блядь",
    "вагина",
    "ебал",
    "ебать",
    "еблет",
    "залупа",
    "мразь",
    "очко",
    "пизда",
    "пиздец",
    "повесился",
    "соси",
    "хуй",
    "хуйню",
    "хуйня",
    "чубайс",
}
BORING_WORDS = {
    "административными",
    "бумаг",
    "валютных",
    "государственная",
    "государственного",
    "группами",
    "денежная",
    "денежную",
    "денежные",
    "долгов",
    "должный",
    "заёмщиков",
    "инструменты",
    "инфраструктуры",
    "концепции",
    "масштабных",
    "оптимальной",
    "предприятие",
    "предприятиям",
    "приватизация",
    "приватизацией",
    "программы",
    "программа",
    "прямых",
    "развития",
    "рынка",
    "регулирование",
    "социальной",
    "собственника",
    "утверждена",
    "функциональности",
    "ценных",
}
FORMAL_SOURCE_WORDS = BORING_WORDS | {
    "авторы",
    "бюджета",
    "внутреннего",
    "выполнение",
    "дефолт",
    "дискредитатор",
    "долга",
    "думы",
    "заёмщиков",
    "комиссии",
    "концепция",
    "обвала",
    "обслуживания",
    "осуществлению",
    "подготовленном",
    "президентом",
    "прекратило",
    "приостановлении",
    "причинами",
    "реформ",
    "рубля",
    "специальной",
    "утверждены",
    "федерации",
}


@dataclass(frozen=True)
class ModeProfile:
    order: int
    reset_probability: float
    candidate_count: int
    rare_word_weight: float
    variety_weight: float
    provocation_weight: float
    seam_penalty_weight: float
    target_words: int


MODE_SETTINGS: dict[GenerationMode, ModeProfile] = {
    "normal": ModeProfile(order=2, reset_probability=0.04, candidate_count=12, rare_word_weight=0.6, variety_weight=1.0, provocation_weight=0.4, seam_penalty_weight=1.4, target_words=22),
    "absurd": ModeProfile(order=2, reset_probability=0.28, candidate_count=44, rare_word_weight=1.1, variety_weight=1.2, provocation_weight=1.4, seam_penalty_weight=0.9, target_words=16),
    "chaos": ModeProfile(order=1, reset_probability=0.48, candidate_count=96, rare_word_weight=1.4, variety_weight=1.5, provocation_weight=2.4, seam_penalty_weight=0.45, target_words=11),
}


def _tokenize_messages(messages: Iterable[str | None]) -> list[list[str]]:
    tokenized: list[list[str]] = []
    for message in messages:
        normalized = normalize_training_text(message)
        if normalized is None:
            continue
        if _is_noisy_source_message(normalized):
            continue

        words = normalized.split()
        if len(words) >= 3:
            tokenized.append(words)

    return tokenized


def _looks_like_latin_noise(word: str) -> bool:
    cleaned = word.strip(",.;:!?()[]{}\"'").lower()
    if cleaned in ALLOWED_LATIN_WORDS:
        return False
    return cleaned.isascii() and cleaned.isalpha()


def _has_latin_noise(words: Iterable[str]) -> bool:
    return any(_looks_like_latin_noise(word) for word in words if LATIN_RE.search(word))


def _has_non_russian_noise(words: Iterable[str]) -> bool:
    return any(word.strip(",.;:!?()[]{}\"'>").lower() in NON_RUSSIAN_NOISE_WORDS for word in words)


def _formal_source_ratio(words: Iterable[str]) -> float:
    cleaned_words = [word.strip(",.;:!?()[]{}\"'«»“”„—-").lower() for word in words]
    content_words = [word for word in cleaned_words if word and word not in SERVICE_WORDS]
    if not content_words:
        return 0.0
    formal_hits = sum(1 for word in content_words if word in FORMAL_SOURCE_WORDS)
    return formal_hits / len(content_words)


def _is_noisy_source_message(text: str) -> bool:
    if (
        PROMPT_NOISE_RE.search(text)
        or PROMPT_BULLET_RE.search(text)
        or LONG_LATIN_RE.search(text)
        or QUOTE_TOKEN_RE.search(text)
    ):
        return True
    words = [word.strip(",.;:!?()[]{}\"'") for word in text.split()]
    meaningful_words = [word for word in words if word]
    if not meaningful_words:
        return True
    if _has_non_russian_noise(meaningful_words):
        return True
    cyrillic_words = [word for word in meaningful_words if CYRILLIC_RE.search(word)]
    latin_words = [word for word in meaningful_words if LATIN_RE.search(word)]
    allowed_latin_words = [word for word in latin_words if word.lower() in ALLOWED_LATIN_WORDS]
    if latin_words and len(allowed_latin_words) != len(latin_words):
        return True
    if _formal_source_ratio(meaningful_words) >= 0.42:
        return True
    return len(cyrillic_words) < 2


def _build_chain(tokenized_messages: Iterable[list[str]], order: int) -> dict[tuple[str, ...], list[str]]:
    chain: dict[tuple[str, ...], list[str]] = {}
    for words in tokenized_messages:
        for index in range(len(words) - order):
            key = tuple(words[index : index + order])
            chain.setdefault(key, []).append(words[index + order])

    return chain


def _transition_frequencies(tokenized_messages: Iterable[list[str]]) -> Counter[tuple[str, str]]:
    transitions: Counter[tuple[str, str]] = Counter()
    for words in tokenized_messages:
        cleaned_words = [word.strip(",.;:!?").lower() for word in words if word.strip(",.;:!?")]
        transitions.update(zip(cleaned_words, cleaned_words[1:], strict=False))
    return transitions


def _word_frequencies(messages: Iterable[str | None]) -> Counter[str]:
    frequencies: Counter[str] = Counter()
    for words in _tokenize_messages(messages):
        frequencies.update(word.strip(",.;:!?").lower() for word in words)
    return frequencies


def _content_words(words: list[str]) -> list[str]:
    return [word for word in words if word.strip(",.;:!?").lower() not in SERVICE_WORDS]


def _content_word_set(words: Iterable[str]) -> set[str]:
    return {
        word.strip(",.;:!?").lower()
        for word in words
        if word.strip(",.;:!?").lower() not in SERVICE_WORDS
    }


def _build_reset_index(keys: Iterable[tuple[str, ...]]) -> dict[str, list[tuple[str, ...]]]:
    reset_index: dict[str, list[tuple[str, ...]]] = {}
    for key in keys:
        for word in _content_word_set(key):
            reset_index.setdefault(word, []).append(key)
    return reset_index


def _choose_reset_context(
    keys: list[tuple[str, ...]],
    *,
    current_context: tuple[str, ...],
    random_source: random.Random,
    reset_index: dict[str, list[tuple[str, ...]]] | None = None,
) -> tuple[str, ...]:
    current_words = _content_word_set(current_context)
    if not current_words:
        return random_source.choice(keys)

    if reset_index is None:
        related_keys = [key for key in keys if current_words & _content_word_set(key)]
    else:
        related_keys = []
        seen_keys: set[tuple[str, ...]] = set()
        for word in current_words:
            for key in reset_index.get(word, []):
                if key not in seen_keys:
                    related_keys.append(key)
                    seen_keys.add(key)
    return random_source.choice(related_keys or keys)


def _is_garbage_candidate(text: str, frequencies: Counter[str]) -> bool:
    words = [word.strip(",.;:!?").lower() for word in text.split() if word.strip(",.;:!?")]
    if (
        PROMPT_NOISE_RE.search(text)
        or QUOTE_TOKEN_RE.search(text)
        or _has_latin_noise(words)
        or _has_non_russian_noise(words)
    ):
        return True
    if len(words) < 3:
        return True
    if sum(1 for word in words if CYRILLIC_RE.search(word)) < 2:
        return True
    if words[0] in DANGLING_START_WORDS or words[-1] in DANGLING_END_WORDS:
        return True
    unique_ratio = len(set(words)) / len(words)
    if unique_ratio < 0.55:
        return True
    content_words = _content_words(words)
    if len(content_words) < 2:
        return True
    return len(content_words) / len(words) < 0.38


def _score_candidate(
    text: str,
    frequencies: Counter[str],
    *,
    mode: GenerationMode,
    target_words: int | None = None,
    transitions: Counter[tuple[str, str]] | None = None,
) -> float:
    selected_mode = _validate_mode(mode)
    profile = MODE_SETTINGS[selected_mode]
    words = [word.strip(",.;:!?").lower() for word in text.split() if word.strip(",.;:!?")]
    if not words:
        return -1000.0

    content_words = _content_words(words)
    cyrillic_content_words = [word for word in content_words if CYRILLIC_RE.search(word)]
    rare_score = sum(1 / max(frequencies.get(word, 1), 1) for word in cyrillic_content_words)
    variety_score = len(set(words)) / len(words)
    service_penalty = (len(words) - len(content_words)) / len(words)
    repeat_penalty = len(words) - len(set(words))
    latin_noise_penalty = sum(3 for word in words if _looks_like_latin_noise(word))
    effective_target_words = target_words or profile.target_words
    length_distance = abs(len(words) - effective_target_words)
    length_score = max(0.0, 1.0 - (length_distance / max(effective_target_words, 1)))
    corpus_hits = sum(1 for word in set(content_words) if word in frequencies)
    provocation_score = sum(1 for word in set(content_words) if word in PROVOCATIVE_WORDS)
    uppercase_score = sum(1 for word in set(text.split()) if len(word) >= 3 and word.isupper())
    boring_penalty = sum(1 for word in set(content_words) if word in BORING_WORDS)
    formal_ratio = boring_penalty / max(len(set(content_words)), 1)
    unseen_transition_penalty = 0
    if transitions is not None:
        pairs = list(zip(words, words[1:], strict=False))
        unseen_transition_penalty = sum(1 for pair in pairs if transitions.get(pair, 0) == 0)

    score = 0.0
    score += length_score * 1.4
    score += variety_score * profile.variety_weight
    score += rare_score * profile.rare_word_weight
    score += corpus_hits * 0.25
    score += provocation_score * profile.provocation_weight
    score += uppercase_score * profile.provocation_weight * 0.35
    score -= service_penalty * 2.2
    score -= repeat_penalty * 0.8
    score -= latin_noise_penalty
    score -= boring_penalty * 2.6
    score -= formal_ratio * 7.0
    score -= unseen_transition_penalty * profile.seam_penalty_weight
    if words[0] in DANGLING_START_WORDS:
        score -= 1.5
    if words[-1] in DANGLING_END_WORDS:
        score -= 2.0
    return score


def _generate_candidate(
    chain: dict[tuple[str, ...], list[str]],
    *,
    keys: list[tuple[str, ...]],
    order: int,
    reset_probability: float,
    max_words: int,
    random_source: random.Random,
    reset_index: dict[str, list[tuple[str, ...]]] | None = None,
) -> str:
    context = random_source.choice(keys)
    output = list(context[:max_words])

    while len(output) < max_words:
        if random_source.random() < reset_probability:
            context = _choose_reset_context(
                keys,
                current_context=context,
                random_source=random_source,
                reset_index=reset_index,
            )

        next_words = chain.get(context)
        if not next_words:
            context = _choose_reset_context(
                keys,
                current_context=context,
                random_source=random_source,
                reset_index=reset_index,
            )
            continue

        next_word = random_source.choice(next_words)
        output.append(next_word)
        context = (*context[1:], next_word) if order > 1 else (next_word,)

    return clean_generated_text(" ".join(output[:max_words]))


def _candidate_word_limit(
    profile: ModeProfile,
    *,
    min_words: int | None = None,
    target_words: int | None = None,
    max_words: int,
) -> int:
    lower_bound = min_words or 1
    requested_target = target_words or profile.target_words
    return max(lower_bound, min(max_words, requested_target))


def _validate_mode(mode: str) -> GenerationMode:
    if mode not in VALID_MODES:
        valid_modes = ", ".join(sorted(VALID_MODES))
        raise ValueError(f"mode must be one of: {valid_modes}")
    return mode  # type: ignore[return-value]


def generate_markov_text(
    messages: Iterable[str | None],
    mode: GenerationMode = "absurd",
    min_words: int | None = None,
    target_words: int | None = None,
    max_words: int = 30,
    rng: random.Random | None = None,
) -> str | None:
    selected_mode = _validate_mode(mode)
    if max_words <= 0:
        return None

    profile = MODE_SETTINGS[selected_mode]
    tokenized_messages = _tokenize_messages(messages)
    if len(tokenized_messages) < 3:
        return None

    chain = _build_chain(tokenized_messages, profile.order)
    if not chain:
        return None

    frequencies: Counter[str] = Counter()
    for words in tokenized_messages:
        frequencies.update(word.strip(",.;:!?").lower() for word in words)
    transitions = _transition_frequencies(tokenized_messages)

    random_source = rng or random
    keys = list(chain)
    reset_index = _build_reset_index(keys)
    minimum_words = min_words or 1
    candidate_max_words = _candidate_word_limit(
        profile,
        min_words=minimum_words,
        target_words=target_words,
        max_words=max_words,
    )
    best_candidate: str | None = None
    best_score = float("-inf")

    for _ in range(profile.candidate_count):
        candidate = _generate_candidate(
            chain,
            keys=keys,
            order=profile.order,
            reset_probability=profile.reset_probability,
            max_words=candidate_max_words,
            random_source=random_source,
            reset_index=reset_index,
        )
        word_count = len(candidate.split()) if candidate else 0
        if (
            not candidate
            or word_count < minimum_words
            or word_count > max_words
            or _is_garbage_candidate(candidate, frequencies)
        ):
            continue
        score = _score_candidate(
            candidate,
            frequencies,
            mode=selected_mode,
            target_words=target_words,
            transitions=transitions,
        )
        if score > best_score:
            best_candidate = candidate
            best_score = score

    if best_candidate is None:
        best_candidate = _generate_candidate(
            chain,
            keys=keys,
            order=profile.order,
            reset_probability=profile.reset_probability,
            max_words=candidate_max_words,
            random_source=random_source,
            reset_index=reset_index,
        )

    cleaned = polish_morphology(clean_generated_text(best_candidate))
    if not cleaned:
        return None
    return clean_generated_text(" ".join(cleaned.split()[:max_words]))


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


async def makeShortSentence(
    text: str,
    max_words: int = 100,
    min_words: int | None = None,
    target_words: int | None = None,
) -> str | None:
    messages = text.splitlines() or [text]
    return generate_markov_text(
        messages,
        min_words=min_words,
        target_words=target_words,
        max_words=max_words,
    )


async def textCleaner(text: str):
    return clean_generated_text(text)
