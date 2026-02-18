#!/usr/bin/env python3
"""Общая логика получения транскрипта YouTube: прокси и один запрос по video_id."""
import logging
import os
from pathlib import Path
from requests import Session
from requests.exceptions import ProxyError, ConnectTimeout, ReadTimeout
from youtube_transcript_api import YouTubeTranscriptApi

PROXY_FILE = Path(__file__).parent / "proxy_working.txt"
log = logging.getLogger(__name__)


def get_http_client() -> Session | None:
    """Сессия с прокси только для YouTube (не трогает Telegram). Приоритет: YOUTUBE_PROXY → HTTP_PROXY/HTTPS_PROXY → proxy_working.txt."""
    px = os.environ.get("YOUTUBE_PROXY", "").strip()
    if px:
        client = Session()
        client.proxies["http"] = client.proxies["https"] = px
        return client
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


def _fetch_with_client(api: YouTubeTranscriptApi, video_id: str):
    """Один запрос через переданный api (уже привязан к client)."""
    t = api.fetch(video_id, languages=("ru", "en"))
    return t


def fetch_transcript(video_id: str) -> tuple[str | None, str | None]:
    """
    Получить текст транскрипта для video_id. Языки: ru, en.
    Сначала через прокси (если задан), при ProxyError/таймауте — повтор без прокси.
    """
    client = get_http_client() or Session()
    api = YouTubeTranscriptApi(http_client=client)
    try:
        t = _fetch_with_client(api, video_id)
        return " ".join(s.text for s in t.snippets), None
    except (ProxyError, ConnectTimeout, ReadTimeout, OSError) as e:
        log.warning("fetch_transcript %s (proxy/timeout): %s, retry without proxy", video_id, e)
        api_direct = YouTubeTranscriptApi(http_client=Session())
        try:
            t = _fetch_with_client(api_direct, video_id)
            return " ".join(s.text for s in t.snippets), None
        except Exception as e2:
            err = f"{type(e2).__name__}: {e2}"
            log.warning("fetch_transcript %s direct: %s", video_id, err)
            return None, err
    except Exception as e:
        err = f"{type(e).__name__}: {e}"
        log.warning("fetch_transcript %s: %s", video_id, err)
        return None, err


def fetch_transcript_timestamped(video_id: str) -> tuple[list[tuple[float, str]] | None, str | None]:
    """
    Получить транскрипт с таймкодами. Сначала через прокси, при ошибке прокси — без прокси.
    """
    client = get_http_client() or Session()
    api = YouTubeTranscriptApi(http_client=client)
    try:
        t = _fetch_with_client(api, video_id)
        return [(s.start, s.text) for s in t.snippets], None
    except (ProxyError, ConnectTimeout, ReadTimeout, OSError) as e:
        log.warning("fetch_transcript_timestamped %s (proxy/timeout): %s, retry without proxy", video_id, e)
        api_direct = YouTubeTranscriptApi(http_client=Session())
        try:
            t = _fetch_with_client(api_direct, video_id)
            return [(s.start, s.text) for s in t.snippets], None
        except Exception as e2:
            err = f"{type(e2).__name__}: {e2}"
            log.warning("fetch_transcript_timestamped %s direct: %s", video_id, err)
            return None, err
    except Exception as e:
        err = f"{type(e).__name__}: {e}"
        log.warning("fetch_transcript_timestamped %s: %s", video_id, err)
        return None, err
