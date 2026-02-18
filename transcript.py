#!/usr/bin/env python3
"""Общая логика получения транскрипта YouTube: прокси и один запрос по video_id."""
import logging
import os
from pathlib import Path
from requests import Session
from requests.exceptions import ProxyError, ConnectTimeout, ReadTimeout
from youtube_transcript_api import YouTubeTranscriptApi

PROXY_FILE = Path(__file__).parent / "proxy_working.txt"
PROXY_LIST_FILE = Path(__file__).parent / "proxies_working_list.txt"
log = logging.getLogger(__name__)


def _get_proxy_list() -> list[str]:
    """Список прокси для YouTube: YOUTUBE_PROXY (через запятую/новую строку) → proxies_working_list.txt → proxy_working.txt."""
    raw = os.environ.get("YOUTUBE_PROXY", "").strip()
    if raw:
        out = [p.strip() for p in raw.replace(",", "\n").splitlines() if p.strip()]
        if out:
            return out
    if PROXY_LIST_FILE.exists():
        out = [p.strip() for p in PROXY_LIST_FILE.read_text(encoding="utf-8").splitlines() if p.strip()]
        if out:
            return out
    if PROXY_FILE.exists():
        p = PROXY_FILE.read_text(encoding="utf-8").strip()
        if p:
            return [p]
    return []


def _session_with_proxy(px: str) -> Session:
    s = Session()
    s.proxies["http"] = s.proxies["https"] = px
    return s


def _fetch_with_client(api: YouTubeTranscriptApi, video_id: str):
    t = api.fetch(video_id, languages=("ru", "en"))
    return t


def fetch_transcript(video_id: str) -> tuple[str | None, str | None]:
    """Текст транскрипта. Перебирает список прокси, при неудаче — без прокси."""
    proxies = _get_proxy_list()
    for px in proxies:
        try:
            client = _session_with_proxy(px)
            api = YouTubeTranscriptApi(http_client=client)
            t = _fetch_with_client(api, video_id)
            return " ".join(s.text for s in t.snippets), None
        except Exception as e:
            log.warning("fetch_transcript %s proxy %s: %s", video_id, px, type(e).__name__)
    try:
        api = YouTubeTranscriptApi(http_client=Session())
        t = _fetch_with_client(api, video_id)
        return " ".join(s.text for s in t.snippets), None
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"


def fetch_transcript_timestamped(video_id: str) -> tuple[list[tuple[float, str]] | None, str | None]:
    """Транскрипт с таймкодами. Перебирает прокси, затем без прокси."""
    proxies = _get_proxy_list()
    for px in proxies:
        try:
            client = _session_with_proxy(px)
            api = YouTubeTranscriptApi(http_client=client)
            t = _fetch_with_client(api, video_id)
            return [(s.start, s.text) for s in t.snippets], None
        except Exception as e:
            log.warning("fetch_transcript_timestamped %s proxy %s: %s", video_id, px, type(e).__name__)
    try:
        api = YouTubeTranscriptApi(http_client=Session())
        t = _fetch_with_client(api, video_id)
        return [(s.start, s.text) for s in t.snippets], None
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"
