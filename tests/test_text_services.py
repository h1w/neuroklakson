from services.text import clean_generated_text, normalize_training_text


def test_normalize_training_text_rejects_commands_and_empty_text():
    assert normalize_training_text(None) is None
    assert normalize_training_text("") is None
    assert normalize_training_text("   \t\n") is None
    assert normalize_training_text("/start hello") is None


def test_normalize_training_text_strips_links_and_collapses_spaces():
    assert normalize_training_text("смотри https://example.com  вот") == "смотри вот"


def test_normalize_training_text_keeps_short_messages():
    assert normalize_training_text("ок") == "ок"


def test_normalize_training_text_trims_extreme_word_lengths():
    long_word = "а" * 40

    assert normalize_training_text(f"{long_word} кабачок") == f"{'а' * 32} кабачок"


def test_clean_generated_text_removes_repeated_words_and_normalizes_punctuation_spacing():
    assert clean_generated_text("кот кот кот ,  орет   .") == "кот, орет."


def test_clean_generated_text_preserves_repeated_punctuation_clusters():
    assert clean_generated_text("привет!!! ну??") == "привет!!! ну??"


def test_clean_generated_text_spaces_after_dot_clusters_without_splitting_them():
    assert clean_generated_text("да...нет") == "да... нет"
