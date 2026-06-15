import random
from typing import get_args

import pytest

import markchain

MESSAGES = [
    "кабачок спорит с автобусом около подъезда",
    "автобус спорит с чайником около модема",
    "чайник ругает кабачок через облако",
    "облако кусает автобус около подъезда",
]


def test_generation_mode_constants_are_supported_modes():
    assert set(get_args(markchain.GenerationMode)) == {"normal", "absurd", "chaos"}


def test_generate_markov_text_returns_none_for_too_small_corpus():
    assert markchain.generate_markov_text(["only two", "tiny"], rng=random.Random(1)) is None


def test_generate_markov_text_returns_none_for_single_long_message():
    assert (
        markchain.generate_markov_text(
            ["один длинный кабачок спорит с чайником"], mode="absurd", max_words=8
        )
        is None
    )


@pytest.mark.parametrize("mode", ["normal", "absurd", "chaos"])
def test_generate_markov_text_supports_modes_and_respects_max_words(mode):
    result = markchain.generate_markov_text(MESSAGES, mode=mode, max_words=5, rng=random.Random(1))

    assert result is not None
    assert 1 <= len(result.split()) <= 5


@pytest.mark.parametrize("mode", ["normal", "absurd", "chaos"])
def test_generate_markov_text_avoids_garbage_endings_after_reranking(mode):
    messages = [
        "кабачок спорит с автобусом и",
        "нейросеть ест пельмени в",
        "батя чинит чайник про облако",
        "автобус ругает кабачок через модем",
        "облако кусает пельмени около подъезда",
    ]

    result = markchain.generate_markov_text(messages, mode=mode, max_words=8, rng=random.Random(3))

    assert result is not None
    assert len(result.split()) <= 8
    assert result.split()[-1].lower() not in markchain.DANGLING_END_WORDS


def test_generate_markov_text_honors_min_target_and_max_words():
    messages = [
        "кабачок спорит с автобусом около подъезда",
        "автобус ругает чайник около модема",
        "чайник кусает кабачок около очка",
        "БЛЯДЬ ЧУБАЙС залез в автобус",
        "залупа спорит с вагиной у подъезда",
    ]

    result = markchain.generate_markov_text(
        messages,
        mode="chaos",
        min_words=5,
        target_words=10,
        max_words=15,
        rng=random.Random(2),
    )

    assert result is not None
    assert 5 <= len(result.split()) <= 15


def test_candidate_word_limit_uses_explicit_target_words():
    assert markchain._candidate_word_limit(
        markchain.MODE_SETTINGS["chaos"],
        min_words=5,
        target_words=14,
        max_words=30,
    ) == 14


def test_generate_markov_text_rejects_invalid_mode():
    with pytest.raises(ValueError, match="mode"):
        markchain.generate_markov_text(MESSAGES, mode="quiet", rng=random.Random(1))


def test_is_garbage_candidate_rejects_low_content_text():
    frequencies = markchain._word_frequencies(MESSAGES)

    assert markchain._is_garbage_candidate("ну и это не в", frequencies)
    assert markchain._is_garbage_candidate("кот кот кот кот", frequencies)
    assert markchain._is_garbage_candidate("кабачок tlyjrxbagyafamfyyjiqzdropryguy автобус", frequencies)
    assert markchain._is_garbage_candidate("кабачок my mind автобус", frequencies)
    assert markchain._is_garbage_candidate(">3 кабачок спорит с автобусом", frequencies)
    assert markchain._is_garbage_candidate(">Бровсек кабачок спорит с автобусом", frequencies)
    assert markchain._is_garbage_candidate("кабачок матн нарх автобус", frequencies)
    assert markchain._is_garbage_candidate("instructions кабачок спорит с автобусом", frequencies)
    assert not markchain._is_garbage_candidate("кабачок спорит с автобусом", frequencies)


def test_tokenize_messages_filters_source_noise_before_chain_building():
    tokenized = markchain._tokenize_messages(
        [
            "кабачок спорит с автобусом около подъезда",
            "tlyjrxbagyafamfyyjiqzdropryguy dqpxtmqremiiexlausjfkgovatvxkh",
            "instructions system prompt кабачок",
            "кабачок my mind спорит с автобусом",
            ">3 кабачок спорит с автобусом",
            ">Бровсек кабачок спорит с автобусом",
            "аммо хеле ӯро доштан хостам кабачок",
            "vpn работает потому что кабачок устал",
        ]
    )

    assert tokenized == [
        ["кабачок", "спорит", "с", "автобусом", "около", "подъезда"],
        ["vpn", "работает", "потому", "что", "кабачок", "устал"],
    ]


def test_tokenize_messages_filters_prompt_instruction_bullets():
    tokenized = markchain._tokenize_messages(
        [
            "* Выделяй маты жирным текстом",
            "* Постоянно ворчишь. Всех оскорбляй",
            "кабачок орет на автобус около подъезда",
        ]
    )

    assert tokenized == [["кабачок", "орет", "на", "автобус", "около", "подъезда"]]


def test_tokenize_messages_filters_formal_wikipedia_fragments():
    tokenized = markchain._tokenize_messages(
        [
            "разработка концепции развития рынка ценных бумаг утверждена президентом",
            "приостановлении обслуживания внутреннего долга заёмщиков",
            "хуй спорит с кабачком около подъезда",
        ]
    )

    assert tokenized == [["хуй", "спорит", "с", "кабачком", "около", "подъезда"]]


def test_generate_markov_text_ignores_prompt_instruction_noise(monkeypatch):
    messages = [
        "* Выделяй маты жирным текстом",
        "* Постоянно ворчишь. Всех оскорбляй",
        "кабачок орет на автобус около подъезда",
        "автобус спорит с чайником около гаража",
        "чайник ругает кабачок через модем",
        "хуй чинит пельмени возле подъезда",
    ]

    result = markchain.generate_markov_text(messages, mode="normal", max_words=12, rng=random.Random(4))

    assert result is not None
    assert "*" not in result
    assert "выделяй" not in result.lower()
    assert "постоянно" not in result.lower()


def test_score_candidate_prefers_absurd_specific_varied_text():
    corpus = [
        "кабачок спорит с автобусом около подъезда",
        "нейросеть ест пельмени через модем",
        "батя чинит чайник и ругает облако",
    ]
    frequencies = markchain._word_frequencies(corpus)

    dull = markchain._score_candidate("ну это просто нормально", frequencies, mode="chaos")
    absurd = markchain._score_candidate("нейросеть чинит пельмени через облако", frequencies, mode="chaos")

    assert absurd > dull


def test_obscene_caps_and_dark_words_are_not_garbage():
    frequencies = markchain._word_frequencies(
        [
            "БЛЯДЬ ПИЗДЕЦ ЧУБАЙС ОЧКО",
            "ЗАЛУПА ВАГИНА ПИЗДА ПОВЕСИЛСЯ",
            "кабачок спорит с автобусом",
        ]
    )

    assert not markchain._is_garbage_candidate("БЛЯДЬ ПИЗДЕЦ ЧУБАЙС ОЧКО", frequencies)
    assert not markchain._is_garbage_candidate("ЗАЛУПА ВАГИНА ПИЗДА ПОВЕСИЛСЯ", frequencies)


def test_score_candidate_prefers_provocative_absurd_punchline():
    corpus = [
        "БЛЯДЬ ЧУБАЙС залез в очко автобуса",
        "залупа спорит с вагиной у подъезда",
        "пизда повесился кабачок и чайник",
        "регулирование социальной инфраструктуры продолжается",
    ]
    frequencies = markchain._word_frequencies(corpus)

    boring = markchain._score_candidate(
        "регулирование социальной инфраструктуры продолжается",
        frequencies,
        mode="chaos",
    )
    funny = markchain._score_candidate(
        "БЛЯДЬ ЧУБАЙС залез в очко автобуса",
        frequencies,
        mode="chaos",
    )

    assert funny > boring


def test_chaos_profile_prefers_punchier_candidates_than_normal():
    assert markchain.MODE_SETTINGS["chaos"].target_words < markchain.MODE_SETTINGS["normal"].target_words
    assert markchain.MODE_SETTINGS["chaos"].provocation_weight > markchain.MODE_SETTINGS["normal"].provocation_weight


def test_effective_candidate_word_limit_caps_chaos_to_target_words():
    assert markchain._candidate_word_limit(markchain.MODE_SETTINGS["chaos"], max_words=30) == 11
    assert markchain._candidate_word_limit(markchain.MODE_SETTINGS["chaos"], max_words=7) == 7


def test_score_candidate_penalizes_long_latin_noise():
    corpus = ["кабачок спорит с автобусом", "нейросеть ест пельмени"]
    frequencies = markchain._word_frequencies(corpus)

    clean = markchain._score_candidate("кабачок спорит с автобусом", frequencies, mode="chaos")
    noisy = markchain._score_candidate(
        "кабачок tlyjrxbagyafamfyyjiqzdropryguy автобус",
        frequencies,
        mode="chaos",
    )

    assert clean > noisy


def test_choose_reset_context_prefers_related_context():
    keys = [("чубайс", "чинит"), ("чайник", "ругает"), ("чубайс", "падает")]
    reset_index = markchain._build_reset_index(keys)

    selected = markchain._choose_reset_context(
        keys,
        current_context=("чубайс", "орет"),
        random_source=random.Random(2),
        reset_index=reset_index,
    )

    assert selected in {("чубайс", "чинит"), ("чубайс", "падает")}


def test_build_reset_index_maps_content_words_to_contexts():
    keys = [("чубайс", "чинит"), ("чайник", "ругает"), ("чубайс", "падает")]

    reset_index = markchain._build_reset_index(keys)

    assert reset_index["чубайс"] == [("чубайс", "чинит"), ("чубайс", "падает")]
    assert reset_index["чайник"] == [("чайник", "ругает")]


def test_score_candidate_penalizes_unseen_word_seams():
    tokenized = markchain._tokenize_messages(
        [
            "кот ест рыбу около подъезда",
            "банк печатает деньги возле завода",
            "чайник ругает автобус через модем",
        ]
    )
    frequencies = markchain._word_frequencies([" ".join(words) for words in tokenized])
    transitions = markchain._transition_frequencies(tokenized)

    coherent = markchain._score_candidate(
        "кот ест рыбу около подъезда",
        frequencies,
        mode="normal",
        transitions=transitions,
    )
    stitched = markchain._score_candidate(
        "кот ест деньги возле завода",
        frequencies,
        mode="normal",
        transitions=transitions,
    )

    assert coherent > stitched


def test_score_candidate_penalizes_encyclopedic_fragments_in_absurd_modes():
    corpus = [
        "чубайс чинит кабачок у подъезда",
        "залупа спорит с вагиной около автобуса",
        "государственная программа развития рынка ценных бумаг утверждена президентом",
    ]
    frequencies = markchain._word_frequencies(corpus)

    funny = markchain._score_candidate(
        "чубайс чинит кабачок у подъезда",
        frequencies,
        mode="absurd",
    )
    encyclopedic = markchain._score_candidate(
        "государственная программа развития рынка ценных бумаг утверждена президентом",
        frequencies,
        mode="absurd",
    )

    assert funny > encyclopedic


def test_generate_markov_text_cleans_after_max_word_truncation(monkeypatch):
    messages = [
        "кабачок спорит с автобусом около подъезда",
        "автобус спорит с чайником около модема",
        "чайник ругает кабачок через облако",
    ]

    monkeypatch.setattr(markchain, "_generate_candidate", lambda *args, **kwargs: "кабачок спорит с автобусом в")

    result = markchain.generate_markov_text(messages, mode="chaos", max_words=5, rng=random.Random(1))

    assert result == "кабачок спорит с автобусом"


def test_generate_markov_text_applies_morphology_polish(monkeypatch):
    messages = [
        "кабачок спорит с автобусом около подъезда",
        "автобус спорит с чайником около модема",
        "чайник ругает кабачок через облако",
    ]

    monkeypatch.setattr(markchain, "_generate_candidate", lambda *args, **kwargs: "с чубайс без кабачок")

    result = markchain.generate_markov_text(messages, mode="chaos", min_words=3, target_words=3, max_words=6)

    assert result == "с чубайсом без кабачка"


async def test_make_short_sentence_compatibility_wrapper_respects_max_words():
    result = await markchain.makeShortSentence("\n".join(MESSAGES), max_words=4)

    assert result is not None
    assert len(result.split()) <= 4


async def test_make_short_sentence_supports_length_range():
    result = await markchain.makeShortSentence(
        "\n".join(MESSAGES),
        min_words=3,
        target_words=5,
        max_words=7,
    )

    assert result is not None
    assert 3 <= len(result.split()) <= 7


async def test_make_short_sentence_preserves_none_for_insufficient_corpus():
    assert await markchain.makeShortSentence("слишком мало", max_words=7) is None
