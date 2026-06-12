from pathlib import Path
from types import SimpleNamespace

import pytest

from handlers.generation import parse_mode_argument
from handlers.learning import select_history_document


def test_parse_mode_argument_returns_none_without_mode():
    assert parse_mode_argument("/gm") is None


def test_parse_mode_argument_returns_valid_mode():
    assert parse_mode_argument("/demgen chaos") == "chaos"


def test_parse_mode_argument_rejects_invalid_mode_with_valid_modes():
    with pytest.raises(ValueError, match="normal.*absurd.*chaos|normal.*chaos.*absurd|absurd.*normal.*chaos|absurd.*chaos.*normal|chaos.*normal.*absurd|chaos.*absurd.*normal"):
        parse_mode_argument("/gm cursed")


def test_runtime_code_does_not_use_bot_mapping_access():
    project_root = Path(__file__).resolve().parents[1]
    paths = [project_root / "bot.py", *sorted((project_root / "handlers").glob("*.py"))]
    runtime_source = "\n".join(path.read_text(encoding="utf-8") for path in paths)

    assert 'bot["' not in runtime_source
    assert "bot['" not in runtime_source
    assert "message.bot[" not in runtime_source


def test_select_history_document_prefers_attached_document_over_caption_text():
    document = SimpleNamespace(file_id="attached-file")
    message = SimpleNamespace(
        document=document,
        caption="/learn_history this caption is not the import source",
        text=None,
        reply_to_message=None,
    )

    assert select_history_document(message) is document


def test_select_history_document_uses_replied_document():
    document = SimpleNamespace(file_id="replied-file")
    message = SimpleNamespace(
        document=None,
        reply_to_message=SimpleNamespace(document=document),
    )

    assert select_history_document(message) is document
