import pytest

from handlers.generation import parse_mode_argument


def test_parse_mode_argument_returns_none_without_mode():
    assert parse_mode_argument("/gm") is None


def test_parse_mode_argument_returns_valid_mode():
    assert parse_mode_argument("/demgen chaos") == "chaos"


def test_parse_mode_argument_rejects_invalid_mode_with_valid_modes():
    with pytest.raises(ValueError, match="normal.*absurd.*chaos|normal.*chaos.*absurd|absurd.*normal.*chaos|absurd.*chaos.*normal|chaos.*normal.*absurd|chaos.*absurd.*normal"):
        parse_mode_argument("/gm cursed")
