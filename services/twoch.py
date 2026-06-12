from __future__ import annotations

import re
from dataclasses import dataclass
from html import unescape
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

BOARD_RE = re.compile(r"^/(?P<board>[^/]+)/?$")
THREAD_RE = re.compile(r"^/(?P<board>[^/]+)/res/(?P<thread_id>\d+)(?:\.html)?/?$")
IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".gif", ".webp")
BOARD_THREAD_LIMIT = 50


@dataclass(frozen=True)
class TwochThreadUrl:
    board: str
    thread_id: str
    normalized_url: str


@dataclass(frozen=True)
class TwochBoardUrl:
    board: str
    normalized_url: str


@dataclass(frozen=True)
class TwochThread:
    texts: list[str]
    image_urls: list[str]


@dataclass(frozen=True)
class TwochImport:
    texts: list[str]
    image_urls: list[str]
    thread_count: int
    failed_thread_count: int = 0


def parse_thread_url(url: str) -> TwochThreadUrl:
    parsed = urlparse(url.strip())
    match = THREAD_RE.match(parsed.path)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc or match is None:
        raise ValueError("expected 2ch thread URL like https://2ch.hk/b/res/123.html")

    board = match.group("board")
    thread_id = match.group("thread_id")
    return TwochThreadUrl(
        board=board,
        thread_id=thread_id,
        normalized_url=f"https://{parsed.netloc}/{board}/res/{thread_id}.html",
    )


def parse_board_url(url: str) -> TwochBoardUrl:
    parsed = urlparse(url.strip())
    match = BOARD_RE.match(parsed.path)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc or match is None:
        raise ValueError("expected 2ch board URL like https://2ch.hk/b/")

    board = match.group("board")
    return TwochBoardUrl(board=board, normalized_url=f"https://{parsed.netloc}/{board}/")


def extract_thread_urls_from_board_html(html: str, *, board: str, base_url: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    urls: list[str] = []
    seen: set[str] = set()
    thread_pattern = re.compile(rf"^/{re.escape(board)}/res/(\d+)(?:\.html)?")

    for tag in soup.find_all("a", href=True):
        absolute_url = urljoin(base_url, str(tag["href"]))
        parsed = urlparse(absolute_url)
        match = thread_pattern.match(parsed.path)
        if match is None:
            continue
        normalized_url = f"https://{parsed.netloc}/{board}/res/{match.group(1)}.html"
        if normalized_url not in seen:
            seen.add(normalized_url)
            urls.append(normalized_url)

    return urls


def parse_thread_html(html: str, *, base_url: str) -> TwochThread:
    soup = BeautifulSoup(html, "html.parser")
    texts: list[str] = []
    image_urls: list[str] = []

    for article in soup.find_all("article", class_="post__message"):
        for link in article.find_all("a"):
            link.decompose()
        text = " ".join(article.get_text(" ", strip=True).split())
        if text:
            texts.append(text)

    for tag in soup.find_all("a", href=True):
        href = str(tag["href"])
        if href.lower().split("?", 1)[0].endswith(IMAGE_EXTENSIONS):
            image_urls.append(urljoin(base_url, href))

    return TwochThread(texts=texts, image_urls=list(dict.fromkeys(image_urls)))


def _html_to_text(html: str) -> str:
    soup = BeautifulSoup(unescape(html), "html.parser")
    for link in soup.find_all("a"):
        link.decompose()
    return " ".join(soup.get_text(" ", strip=True).split())


def _iter_posts(payload: Any):
    if isinstance(payload, dict):
        if isinstance(payload.get("posts"), list):
            yield from payload["posts"]
        for value in payload.values():
            yield from _iter_posts(value)
    elif isinstance(payload, list):
        for item in payload:
            yield from _iter_posts(item)


def parse_thread_json(payload: Any, *, base_url: str) -> TwochThread:
    texts: list[str] = []
    image_urls: list[str] = []

    for post in _iter_posts(payload):
        if not isinstance(post, dict):
            continue
        comment = post.get("comment") or post.get("message") or post.get("text")
        if isinstance(comment, str):
            text = _html_to_text(comment)
            if text:
                texts.append(text)
        for file_info in post.get("files") or []:
            if not isinstance(file_info, dict):
                continue
            url = file_info.get("path") or file_info.get("url") or file_info.get("src")
            if isinstance(url, str) and url.lower().split("?", 1)[0].endswith(IMAGE_EXTENSIONS):
                image_urls.append(urljoin(base_url, url))

    return TwochThread(texts=texts, image_urls=list(dict.fromkeys(image_urls)))


async def fetch_thread(url: str) -> TwochThread:
    parsed = parse_thread_url(url)
    json_url = parsed.normalized_url.removesuffix(".html") + ".json"
    async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
        json_response = await client.get(json_url)
        if json_response.status_code == 200:
            return parse_thread_json(json_response.json(), base_url=parsed.normalized_url)
        response = await client.get(parsed.normalized_url)
    response.raise_for_status()
    return parse_thread_html(response.text, base_url=parsed.normalized_url)


async def fetch_board(url: str, *, limit: int = BOARD_THREAD_LIMIT) -> TwochImport:
    parsed = parse_board_url(url)
    async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
        response = await client.get(parsed.normalized_url)
    response.raise_for_status()

    thread_urls = extract_thread_urls_from_board_html(
        response.text,
        board=parsed.board,
        base_url=parsed.normalized_url,
    )[:limit]
    texts: list[str] = []
    image_urls: list[str] = []
    imported_threads = 0
    failed_threads = 0

    for thread_url in thread_urls:
        try:
            thread = await fetch_thread(thread_url)
        except Exception:
            failed_threads += 1
            continue
        imported_threads += 1
        texts.extend(thread.texts)
        image_urls.extend(thread.image_urls)

    return TwochImport(
        texts=texts,
        image_urls=list(dict.fromkeys(image_urls)),
        thread_count=imported_threads,
        failed_thread_count=failed_threads,
    )


async def fetch_twoch_import(url: str) -> TwochImport:
    try:
        thread = await fetch_thread(url)
    except ValueError:
        return await fetch_board(url)
    return TwochImport(texts=thread.texts, image_urls=thread.image_urls, thread_count=1)
