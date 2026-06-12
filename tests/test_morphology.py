from services.morphology import polish_morphology


def test_polish_morphology_inflects_nouns_after_safe_prepositions():
    assert polish_morphology("с чубайс без кабачок к автобус") == "с чубайсом без кабачка к автобусу"


def test_polish_morphology_handles_profanity_without_replacing_roots():
    assert polish_morphology("с залупа у пизда для очко") == "с залупой у пизды для очка"


def test_polish_morphology_preserves_uppercase_style():
    assert polish_morphology("с ЧУБАЙС без ОЧКО") == "с ЧУБАЙСОМ без ОЧКА"


def test_polish_morphology_leaves_latin_and_unknown_noise_unchanged():
    assert polish_morphology("с vpn без tlyjrxbagyafamfyy") == "с vpn без tlyjrxbagyafamfyy"
