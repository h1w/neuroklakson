from services.imports import parse_history_text


def test_parse_history_text_accepts_plain_lines_and_counts_rejections():
    parsed = parse_history_text(
        "\n".join(
            [
                "кабачок объявил войну чайнику",
                "/start",
                "смотри https://example.com",
                "ок",
            ]
        )
    )

    assert parsed.accepted == ["кабачок объявил войну чайнику"]
    assert parsed.rejected_count == 3


def test_parse_history_text_extracts_telegram_export_lines_and_rejects_short_lines():
    parsed = parse_history_text(
        "\n".join(
            [
                "[12.06.2026 10:00] Ivan: кабачок объявил войну чайнику",
                "[12.06.2026 10:01] Ivan: ок",
            ]
        )
    )

    assert parsed.accepted == ["кабачок объявил войну чайнику"]
    assert parsed.rejected_count == 1
