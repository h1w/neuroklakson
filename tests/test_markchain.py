import random
from typing import get_args

import pytest

import markchain

MESSAGES = [
    "alpha beta gamma delta epsilon zeta",
    "beta gamma delta eta theta iota",
    "gamma delta epsilon kappa lambda mu",
    "delta epsilon zeta nu xi omicron",
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


def test_generate_markov_text_rejects_invalid_mode():
    with pytest.raises(ValueError, match="mode"):
        markchain.generate_markov_text(MESSAGES, mode="quiet", rng=random.Random(1))


async def test_make_short_sentence_compatibility_wrapper_respects_max_words():
    result = await markchain.makeShortSentence("\n".join(MESSAGES), max_words=4)

    assert result is not None
    assert len(result.split()) <= 4


async def test_make_short_sentence_preserves_none_for_insufficient_corpus():
    assert await markchain.makeShortSentence("слишком мало", max_words=7) is None
