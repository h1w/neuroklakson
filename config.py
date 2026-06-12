from __future__ import annotations

import os
from configparser import ConfigParser
from dataclasses import dataclass

GENERATION_MODES = {"normal", "absurd", "chaos"}

LEGACY_BOT_DEFAULTS = {
    "BredoDemotivatorMinWordSize": "3",
    "BredoDemotivatorMaxWordSize": "8",
    "BredoDemotivatorSecondLineMinWordSize": "3",
    "BredoDemotivatorSecondLineMaxWordSize": "12",
    "BredoMessageMinWordSize": "5",
    "BredoMessageMaxWordSize": "30",
    "BredoBugurtMessageMinWordSize": "8",
    "BredoBugurtMessageMaxWordSize": "40",
    "BredoBugurtMessageMinWordsPerLine": "2",
    "BredoBugurtMessageMaxWordsPerLine": "8",
    "BredoBugurtMessageMinLines": "2",
    "BredoBugurtMessageMaxLines": "8",
}


@dataclass(frozen=True)
class Settings:
    bot_token: str
    database_url: str
    default_generation_mode: str = "absurd"
    bredo_generation_probability: int = 3
    bredo_message_voiceover_probability: int = 1
    bredo_demotivator_watermark: str = "neuroklakson"
    bredo_demotivator_text_font: str = "fonts/OpenSans-Bold.ttf"
    bredo_quote_headline_text: str = "Great minds of Telegram"
    bredo_quote_headline_text_font: str = "fonts/OpenSans-Bold.ttf"
    bredo_quote_author_name_text_font: str = "fonts/OpenSans-Regular.ttf"
    bredo_quote_quote_text_font: str = "fonts/OpenSans-Italic.ttf"
    bredo_demotivator_min_word_size: int = 3
    bredo_demotivator_max_word_size: int = 8
    bredo_demotivator_second_line_min_word_size: int = 3
    bredo_demotivator_second_line_max_word_size: int = 12
    bredo_message_min_word_size: int = 5
    bredo_message_max_word_size: int = 30
    bredo_bugurt_message_min_word_size: int = 8
    bredo_bugurt_message_max_word_size: int = 40
    bredo_bugurt_message_min_words_per_line: int = 2
    bredo_bugurt_message_max_words_per_line: int = 8
    bredo_bugurt_message_min_lines: int = 2
    bredo_bugurt_message_max_lines: int = 8

    def __post_init__(self) -> None:
        if self.default_generation_mode not in GENERATION_MODES:
            raise ValueError("DEFAULT_GENERATION_MODE must be one of: normal, absurd, chaos")
        _validate_probability("BREDO_GENERATION_PROBABILITY", self.bredo_generation_probability)
        _validate_probability(
            "BREDO_MESSAGE_VOICEOVER_PROBABILITY",
            self.bredo_message_voiceover_probability,
        )


def _validate_probability(name: str, value: int) -> None:
    if value < 0 or value > 100:
        raise ValueError(f"{name} must be between 0 and 100")


def _required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise ValueError(f"{name} is required")
    return value


def _int_env(name: str, default: int) -> int:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    try:
        return int(raw_value)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer") from exc


def load_settings() -> Settings:
    return Settings(
        bot_token=_required_env("BOT_TOKEN"),
        database_url=_required_env("DATABASE_URL"),
        default_generation_mode=os.getenv("DEFAULT_GENERATION_MODE", "absurd"),
        bredo_generation_probability=_int_env("BREDO_GENERATION_PROBABILITY", 3),
        bredo_message_voiceover_probability=_int_env("BREDO_MESSAGE_VOICEOVER_PROBABILITY", 1),
        bredo_demotivator_watermark=os.getenv("BREDO_DEMOTIVATOR_WATERMARK", "neuroklakson"),
        bredo_demotivator_text_font=os.getenv(
            "BREDO_DEMOTIVATOR_TEXT_FONT", "fonts/OpenSans-Bold.ttf"
        ),
        bredo_quote_headline_text=os.getenv(
            "BREDO_QUOTE_HEADLINE_TEXT", "Great minds of Telegram"
        ),
        bredo_quote_headline_text_font=os.getenv(
            "BREDO_QUOTE_HEADLINE_TEXT_FONT", "fonts/OpenSans-Bold.ttf"
        ),
        bredo_quote_author_name_text_font=os.getenv(
            "BREDO_QUOTE_AUTHOR_NAME_TEXT_FONT", "fonts/OpenSans-Regular.ttf"
        ),
        bredo_quote_quote_text_font=os.getenv(
            "BREDO_QUOTE_QUOTE_TEXT_FONT", "fonts/OpenSans-Italic.ttf"
        ),
        bredo_demotivator_min_word_size=_int_env("BREDO_DEMOTIVATOR_MIN_WORD_SIZE", 3),
        bredo_demotivator_max_word_size=_int_env("BREDO_DEMOTIVATOR_MAX_WORD_SIZE", 8),
        bredo_demotivator_second_line_min_word_size=_int_env(
            "BREDO_DEMOTIVATOR_SECOND_LINE_MIN_WORD_SIZE", 3
        ),
        bredo_demotivator_second_line_max_word_size=_int_env(
            "BREDO_DEMOTIVATOR_SECOND_LINE_MAX_WORD_SIZE", 12
        ),
        bredo_message_min_word_size=_int_env("BREDO_MESSAGE_MIN_WORD_SIZE", 5),
        bredo_message_max_word_size=_int_env("BREDO_MESSAGE_MAX_WORD_SIZE", 30),
        bredo_bugurt_message_min_word_size=_int_env("BREDO_BUGURT_MESSAGE_MIN_WORD_SIZE", 8),
        bredo_bugurt_message_max_word_size=_int_env("BREDO_BUGURT_MESSAGE_MAX_WORD_SIZE", 40),
        bredo_bugurt_message_min_words_per_line=_int_env(
            "BREDO_BUGURT_MESSAGE_MIN_WORDS_PER_LINE", 2
        ),
        bredo_bugurt_message_max_words_per_line=_int_env(
            "BREDO_BUGURT_MESSAGE_MAX_WORDS_PER_LINE", 8
        ),
        bredo_bugurt_message_min_lines=_int_env("BREDO_BUGURT_MESSAGE_MIN_LINES", 2),
        bredo_bugurt_message_max_lines=_int_env("BREDO_BUGURT_MESSAGE_MAX_LINES", 8),
    )


def load_legacy_config() -> ConfigParser:
    settings = load_settings()
    legacy_config = ConfigParser()
    legacy_config["BOT"] = {
        "Token": settings.bot_token,
        "BredoGenerationProbability": str(settings.bredo_generation_probability),
        "BredoMessageVoiceoverProbability": str(settings.bredo_message_voiceover_probability),
        "BredoDemotivatorWatermark": settings.bredo_demotivator_watermark,
        "BredoDemotivatorTextFont": settings.bredo_demotivator_text_font,
        "BredoQuoteHeadlineText": settings.bredo_quote_headline_text,
        "BredoQuoteHeadlineTextFont": settings.bredo_quote_headline_text_font,
        "BredoQuoteAuthorNameTextFont": settings.bredo_quote_author_name_text_font,
        "BredoQuoteQuoteTextFont": settings.bredo_quote_quote_text_font,
        **{
            key: os.getenv(_legacy_key_to_env_name(key), default)
            for key, default in LEGACY_BOT_DEFAULTS.items()
        },
    }
    return legacy_config


def _legacy_key_to_env_name(key: str) -> str:
    env_name = []
    for index, character in enumerate(key):
        if index > 0 and character.isupper() and not key[index - 1].isupper():
            env_name.append("_")
        env_name.append(character.upper())
    return "".join(env_name)
