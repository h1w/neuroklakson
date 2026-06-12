from io import BytesIO

import pytest
from PIL import Image

from demotivate import generateDemotivator, generateQuote


def _png_image(size=(16, 16), color="white"):
    image = Image.new("RGB", size, color=color)
    image_bytes = BytesIO()
    image.save(image_bytes, format="PNG")
    image_bytes.seek(0)
    return image_bytes


@pytest.mark.asyncio
async def test_generate_demotivator_supports_pillow_10_text_measurement():
    result = await generateDemotivator(
        _png_image(),
        "top text",
        "bottom text",
        watermark="neuroklakson",
        font="fonts/OpenSans-Bold.ttf",
    )

    assert result.size == (1280, 1024)


@pytest.mark.asyncio
async def test_generate_quote_supports_pillow_10_text_measurement_and_resampling():
    result = await generateQuote(
        _png_image(),
        "author",
        "quote text",
        headline_text="headline",
        headline_text_font="fonts/OpenSans-Bold.ttf",
        author_name_font="fonts/OpenSans-Regular.ttf",
        quote_text_font="fonts/OpenSans-Italic.ttf",
    )

    assert result.size == (1000, 550)
