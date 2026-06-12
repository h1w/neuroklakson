from io import BytesIO
from types import SimpleNamespace

import handlers.legacy as legacy_handler


class FakeBot:
    async def get_user_profile_photos(self, user_id):
        assert user_id == 55
        return SimpleNamespace(photos=[[SimpleNamespace(file_id="photo-file")]])

    async def download(self, file_id, *, destination):
        assert file_id == "photo-file"
        destination.write(b"fake-image")


async def test_create_quote_handler_uses_configured_eblanoid_headline(monkeypatch):
    calls = {}

    async def fake_generate_quote(
        author_profile_pic,
        author_name,
        quote_text,
        headline_text,
        headline_text_font,
        author_name_font,
        quote_text_font,
    ):
        assert isinstance(author_profile_pic, BytesIO)
        calls["author_name"] = author_name
        calls["quote_text"] = quote_text
        calls["headline_text"] = headline_text
        calls["fonts"] = (headline_text_font, author_name_font, quote_text_font)

        class FakeImage:
            def save(self, output, *, format):
                assert format == "PNG"
                output.write(b"png")

        return FakeImage()

    async def fake_normalize(text):
        return text

    monkeypatch.setattr("handlers.legacy.generateQuote", fake_generate_quote)
    monkeypatch.setattr("handlers.legacy.normalizeStringForDemotivator", fake_normalize)

    message = SimpleNamespace(
        reply_to_message=SimpleNamespace(
            text="умная цитата",
            caption=None,
            from_user=SimpleNamespace(id=55, username="vasya", full_name="Вася"),
        ),
        bot=FakeBot(),
        answers=[],
    )

    async def answer_photo(photo):
        message.answers.append(photo)

    message.answer_photo = answer_photo

    settings = SimpleNamespace(
        bredo_quote_headline_text="Цитаты ебланойдов",
        bredo_quote_headline_text_font="headline.ttf",
        bredo_quote_author_name_text_font="author.ttf",
        bredo_quote_quote_text_font="quote.ttf",
    )

    await legacy_handler.create_quote_handler(message, settings)

    assert calls == {
        "author_name": "vasya",
        "quote_text": "умная цитата",
        "headline_text": "Цитаты ебланойдов",
        "fonts": ("headline.ttf", "author.ttf", "quote.ttf"),
    }
    assert len(message.answers) == 1
