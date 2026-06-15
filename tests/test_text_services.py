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


def test_clean_generated_text_trims_dangling_service_word_endings():
    assert clean_generated_text("кабачок спорит с чайником и") == "кабачок спорит с чайником"
    assert clean_generated_text("батя уехал в") == "батя уехал"


def test_clean_generated_text_collapses_repeated_service_words():
    assert clean_generated_text("ну ну ну кабачок это это база") == "ну кабачок это база"


def test_clean_generated_text_removes_standalone_at_separators():
    assert clean_generated_text("кабачок @ спорит @ с автобусом") == "кабачок спорит с автобусом"


def test_clean_generated_text_removes_prompt_noise_tokens():
    assert clean_generated_text("кофеин в глотку instructions") == "кофеин в глотку"


def test_normalize_training_text_removes_wikipedia_citation_markers():
    assert normalize_training_text("лекарства»[32] и дефолт[151].") == "лекарства» и дефолт."


def test_clean_generated_text_removes_wikipedia_citation_markers():
    assert clean_generated_text("Чубайс осудил решение[63].") == "Чубайс осудил решение."
