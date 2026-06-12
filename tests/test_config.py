import pytest

from config import Settings, load_settings


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
