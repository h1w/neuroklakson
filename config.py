from __future__ import annotations

import os
from dataclasses import dataclass

GENERATION_MODES = {"normal", "absurd", "chaos"}


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
    )
