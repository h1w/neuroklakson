from __future__ import annotations

from io import BytesIO

import httpx


async def download_external_image(url: str) -> BytesIO:
    async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
        response = await client.get(url)
    response.raise_for_status()
    content_type = response.headers.get("content-type", "")
    if content_type and not content_type.startswith("image/"):
        raise ValueError("external URL did not return an image")
    buffer = BytesIO(response.content)
    buffer.seek(0)
    return buffer
