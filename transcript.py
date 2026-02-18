#!/usr/bin/env python3
"""Общая логика получения транскрипта YouTube: прокси и один запрос по video_id."""
import logging
import os
from pathlib import Path
from requests import Session
from youtube_transcript_api import YouTubeTranscriptApi

PROXY_FILE = Path(__file__).parent / "proxy_working.txt"
log = logging.getLogger(__name__)


def get_http_client() -> Session | None:
    """Сессия с прокси из env или proxy_working.txt. None = без прокси."""
    if os.environ.get("HTTP_PROXY") or os.environ.get("HTTPS_PROXY"):
        client = Session()
        px_http = os.environ.get("HTTP_PROXY")
        px_https = os.environ.get("HTTPS_PROXY") or px_http
        if px_http:
            client.proxies["http"] = px_http
        if px_https:
            client.proxies["https"] = px_https
        return client
    if PROXY_FILE.exists():
        px = PROXY_FILE.read_text(encoding="utf-8").strip()
        if px:
            client = Session()
            client.proxies["http"] = client.proxies["https"] = px
            return client
    return None


def fetch_transcript(video_id: str) -> tuple[str | None, str | None]:
    """
    Получить текст транскрипта для video_id. Языки: ru, en.
    Без прокси (мало запросов — можно без него).
    Возвращает (текст, None) при успехе, (None, сообщение_ошибки) при неудаче.
    """
    api = YouTubeTranscriptApi(http_client=Session())
    try:
        t = api.fetch(video_id, languages=("ru", "en"))
        return " ".join(s.text for s in t.snippets), None
    except Exception as e:
        last_error = f"{type(e).__name__}: {e}"
        log.warning("fetch_transcript %s: %s", video_id, last_error)
        return None, last_error


def fetch_transcript_timestamped(video_id: str) -> tuple[list[tuple[float, str]] | None, str | None]:
    """
    Получить транскрипт с таймкодами: список (start_sec, text).
    Для режима «оглавление».
    """
    api = YouTubeTranscriptApi(http_client=Session())
    try:
        t = api.fetch(video_id, languages=("ru", "en"))
        snippets = [(s.start, s.text) for s in t.snippets]
        return snippets, None
    except Exception as e:
        last_error = f"{type(e).__name__}: {e}"
        log.warning("fetch_transcript_timestamped %s: %s", video_id, last_error)
        return None, last_error
