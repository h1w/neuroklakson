import importlib
import sys
import tomllib
from pathlib import Path

import pytest

from config import Settings, load_legacy_config, load_settings


def test_load_settings_from_environment(monkeypatch):
    monkeypatch.setenv("BOT_TOKEN", "123:test")
    monkeypatch.setenv("DATABASE_URL", "postgresql://bot:bot@postgres:5432/neuroklakson")
    monkeypatch.setenv("DEFAULT_GENERATION_MODE", "chaos")
    monkeypatch.setenv("BREDO_GENERATION_PROBABILITY", "17")

    settings = load_settings()

    assert settings.bot_token == "123:test"
    assert settings.database_url == "postgresql://bot:bot@postgres:5432/neuroklakson"
    assert settings.default_generation_mode == "chaos"
    assert settings.bredo_generation_probability == 17


def test_default_generation_mode_must_be_valid(monkeypatch):
    monkeypatch.setenv("BOT_TOKEN", "123:test")
    monkeypatch.setenv("DATABASE_URL", "postgresql://bot:bot@postgres:5432/neuroklakson")
    monkeypatch.setenv("DEFAULT_GENERATION_MODE", "goblin")

    with pytest.raises(ValueError, match="DEFAULT_GENERATION_MODE"):
        load_settings()


def test_probability_must_be_between_zero_and_one_hundred():
    with pytest.raises(ValueError, match="BREDO_GENERATION_PROBABILITY"):
        Settings(
            bot_token="123:test",
            database_url="postgresql://bot:bot@postgres:5432/neuroklakson",
            default_generation_mode="absurd",
            bredo_generation_probability=101,
            bredo_message_voiceover_probability=0,
        )


def test_load_legacy_config_from_environment(monkeypatch):
    monkeypatch.setenv("BOT_TOKEN", "123:test")
    monkeypatch.setenv("DATABASE_URL", "postgresql://bot:bot@postgres:5432/neuroklakson")
    monkeypatch.setenv("BREDO_GENERATION_PROBABILITY", "17")

    legacy_config = load_legacy_config()

    assert legacy_config["BOT"]["Token"] == "123:test"
    assert legacy_config["BOT"]["BredoGenerationProbability"] == "17"
    assert legacy_config["BOT"]["BredoMessageVoiceoverProbability"] == "1"
    assert legacy_config["BOT"]["BredoDemotivatorMinWordSize"] == "3"
    assert legacy_config["BOT"]["BredoDemotivatorMaxWordSize"] == "8"
    assert legacy_config["BOT"]["BredoDemotivatorSecondLineMinWordSize"] == "3"
    assert legacy_config["BOT"]["BredoDemotivatorSecondLineMaxWordSize"] == "12"
    assert legacy_config["BOT"]["BredoMessageMinWordSize"] == "5"
    assert legacy_config["BOT"]["BredoMessageMaxWordSize"] == "30"
    assert legacy_config["BOT"]["BredoBugurtMessageMinWordSize"] == "8"
    assert legacy_config["BOT"]["BredoBugurtMessageMaxWordSize"] == "40"
    assert legacy_config["BOT"]["BredoBugurtMessageMinWordsPerLine"] == "2"
    assert legacy_config["BOT"]["BredoBugurtMessageMaxWordsPerLine"] == "8"
    assert legacy_config["BOT"]["BredoBugurtMessageMinLines"] == "2"
    assert legacy_config["BOT"]["BredoBugurtMessageMaxLines"] == "8"
    assert legacy_config["BOT"]["BredoDemotivatorWatermark"] == "neuroklakson"
    assert legacy_config["BOT"]["BredoDemotivatorTextFont"] == "fonts/OpenSans-Bold.ttf"
    assert legacy_config["BOT"]["BredoQuoteHeadlineText"] == "Great minds of Telegram"
    assert legacy_config["BOT"]["BredoQuoteHeadlineTextFont"] == "fonts/OpenSans-Bold.ttf"
    assert legacy_config["BOT"]["BredoQuoteAuthorNameTextFont"] == "fonts/OpenSans-Regular.ttf"
    assert legacy_config["BOT"]["BredoQuoteQuoteTextFont"] == "fonts/OpenSans-Italic.ttf"


def test_aiosqlite_is_available_as_transitional_runtime_dependency():
    with open("pyproject.toml", "rb") as project_file:
        project = tomllib.load(project_file)

    assert "aiosqlite>=0.20,<1" in project["project"]["dependencies"]
    assert "markovify>=0.9,<1" in project["project"]["dependencies"]


def test_bot_import_uses_env_config_without_credentials_file(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("BOT_TOKEN", "123:test")
    monkeypatch.setenv("DATABASE_URL", "postgresql://bot:bot@postgres:5432/neuroklakson")
    sys.modules.pop("bot", None)

    bot_module = importlib.import_module("bot")

    assert bot_module.config["BOT"]["Token"] == "123:test"
    assert bot_module.config["BOT"]["BredoMessageMinWordSize"] == "5"

    sys.modules.pop("bot", None)


def test_dockerignore_excludes_local_runtime_files():
    dockerignore_entries = set(Path(".dockerignore").read_text().splitlines())

    assert ".venv" in dockerignore_entries
    assert "credentials.cfg" in dockerignore_entries
