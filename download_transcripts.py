#!/usr/bin/env python3
"""Скачать транскрипты всех видео из video_ids.txt в папку transcripts/."""
import os
import time
from pathlib import Path
from requests import Session
from youtube_transcript_api import YouTubeTranscriptApi

IDS_FILE = Path(__file__).parent / "video_ids.txt"
OUT_DIR = Path(__file__).parent / "transcripts"
PROXY_FILE = Path(__file__).parent / "proxy_working.txt"
PROGRESS_FILE = Path(__file__).parent / "progress.txt"  # сюда пишем прогресс — открывай и смотри
# Чтобы не получить бан: пауза между каждым запросом и длинный перерыв каждые N скачиваний
DELAY_SEC = 6
PAUSE_EVERY_N_OK = 15   # после каждых N успешных — длинная пауза
PAUSE_MINUTES = 3       # минут ждать

def main():
    ids = [s.strip() for s in IDS_FILE.read_text(encoding="utf-8").splitlines() if s.strip()]
    OUT_DIR.mkdir(exist_ok=True)
    # Прокси: 1) HTTP_PROXY/HTTPS_PROXY 2) иначе proxy_working.txt (найденный check_proxies.py)
    http_client = None
    if os.environ.get("HTTP_PROXY") or os.environ.get("HTTPS_PROXY"):
        http_client = Session()
        px_http = os.environ.get("HTTP_PROXY")
        px_https = os.environ.get("HTTPS_PROXY") or px_http
        if px_http:
            http_client.proxies["http"] = px_http
        if px_https:
            http_client.proxies["https"] = px_https
        print("Прокси (env):", http_client.proxies, flush=True)
    elif PROXY_FILE.exists():
        px = PROXY_FILE.read_text(encoding="utf-8").strip()
        if px:
            http_client = Session()
            http_client.proxies["http"] = http_client.proxies["https"] = px
            print("Прокси (proxy_working.txt):", px, flush=True)
    api = YouTubeTranscriptApi(http_client=http_client)
    ok = skip = err = 0
    total = len(ids)

    def write_progress(i, vid, status):
        t = time.strftime("%H:%M:%S", time.localtime())
        PROGRESS_FILE.write_text(
            f"Обработано: {i+1}/{total}  |  последнее: {vid}  {status}\n"
            f"OK: {ok}  skip: {skip}  err: {err}  |  {t}\n",
            encoding="utf-8",
        )

    for i, vid in enumerate(ids):
        out = OUT_DIR / f"{vid}.txt"
        if out.exists():
            skip += 1
            write_progress(i, vid, "(skip)")
            continue
        try:
            t = api.fetch(vid, languages=("ru", "en"))
            text = " ".join(x.text for x in t.snippets)
            out.write_text(text, encoding="utf-8")
            ok += 1
            write_progress(i, vid, "OK")
            print(f"{i+1}/{total} {vid} OK {len(text)}", flush=True)
            if ok > 0 and ok % PAUSE_EVERY_N_OK == 0:
                print(f"--- Пауза {PAUSE_MINUTES} мин (скачано {ok})...", flush=True)
                time.sleep(PAUSE_MINUTES * 60)
        except Exception as e:
            err += 1
            write_progress(i, vid, f"ERR {type(e).__name__}")
            print(f"{i+1}/{total} {vid} ERR {type(e).__name__}", flush=True)
        time.sleep(DELAY_SEC)
    PROGRESS_FILE.write_text(f"--- Готово: ok={ok} skip={skip} err={err}\n", encoding="utf-8")
    print(f"--- Готово: ok={ok} skip={skip} err={err}", flush=True)

if __name__ == "__main__":
    main()
