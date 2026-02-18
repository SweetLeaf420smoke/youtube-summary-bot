#!/usr/bin/env python3
"""Проверить список прокси на YouTube transcript API. Первый рабочий — в proxy_working.txt.
Нерабочие пишем в proxy_failed.txt и больше не проверяем. Подтягивает свежий список из сети."""
import re
import sys
from pathlib import Path
from requests import Session
from youtube_transcript_api import YouTubeTranscriptApi

BASE = Path(__file__).parent
PROXY_FAILED_FILE = BASE / "proxy_failed.txt"
PROXY_FRESH_FILE = BASE / "proxies_fresh.txt"  # до 100 свежих с веба
PROXY_SOURCES = [
    "https://raw.githubusercontent.com/proxifly/free-proxy-list/main/proxies/protocols/http/data.txt",
    "http://pubproxy.com/api/proxy?limit=30&format=txt&type=http",
]

def fetch_proxies_from_web(limit=200):
    out = []
    for url in PROXY_SOURCES:
        if len(out) >= limit:
            break
        try:
            r = Session().get(url, timeout=15)
            if r.status_code != 200:
                continue
            for line in r.text.splitlines():
                line = line.strip()
                if re.match(r"^https?://[^\s:]+:\d+", line):
                    if not line.startswith("http"):
                        line = "http://" + line
                    out.append(line)
                    if len(out) >= limit:
                        break
        except Exception:
            pass
    return out

# Прокси статический список (запасной)
PROXIES_TO_TRY_RAW = """
http://47.56.110.204:8989
http://154.65.39.7:80
http://8.209.255.13:3128
http://45.65.138.48:999
http://93.180.221.205:8080
http://84.39.112.144:3128
http://160.248.7.177:80
http://190.7.138.78:8080
http://98.64.128.182:3128
http://36.253.18.38:8181
http://212.127.95.235:8081
http://38.194.246.34:999
http://103.76.108.14:8080
http://80.94.229.155:8080
http://140.227.61.201:3128
http://147.75.34.105:443
http://47.74.157.194:80
http://165.16.59.65:8080
http://37.238.40.153:8080
http://197.221.234.253:80
http://139.59.103.183:80
http://162.245.85.36:80
http://101.47.16.15:7890
http://188.116.37.3:8090
http://81.177.166.169:10809
http://51.178.76.203:80
http://79.137.17.104:80
http://89.238.200.81:80
http://163.172.167.48:80
http://193.107.170.193:8080
http://59.6.25.118:3128
http://77.242.177.57:3128
http://139.59.1.14:8080
http://159.203.61.169:3128
http://167.71.5.83:3128
http://198.199.86.11:3128
http://209.97.150.167:3128
http://138.68.60.8:3128
http://104.199.219.13:3128
http://34.80.202.6:3128
""".strip().splitlines()

VID = "ok_TCBX9clw"
TIMEOUT = 12

def main():
    failed = set()
    if PROXY_FAILED_FILE.exists():
        failed = {s.strip() for s in PROXY_FAILED_FILE.read_text(encoding="utf-8").splitlines() if s.strip()}
    # Свежие 100: из файла или подтянуть с веба и сохранить
    if PROXY_FRESH_FILE.exists():
        from_fresh = [s.strip() for s in PROXY_FRESH_FILE.read_text(encoding="utf-8").splitlines() if s.strip()]
    else:
        from_fresh = []
    if len(from_fresh) < 100:
        from_web = fetch_proxies_from_web(limit=100)
        PROXY_FRESH_FILE.write_text("\n".join(from_web[:100]), encoding="utf-8")
        from_fresh = from_web[:100]
    from_fresh = [p for p in from_fresh if p not in failed]
    from_static = [p.strip() for p in PROXIES_TO_TRY_RAW if p.strip() and p.strip() not in failed]
    to_try = from_fresh[:100] + from_static
    out_file = BASE / "proxy_working.txt"
    for i, px in enumerate(to_try):
        try:
            s = Session()
            s.proxies = {"http": px, "https": px}
            s.timeout = TIMEOUT
            api = YouTubeTranscriptApi(http_client=s)
            t = api.fetch(VID, languages=("ru", "en"))
            out_file.write_text(px, encoding="utf-8")
            print(f"OK {px} ({len(t.snippets)} snippets)")
            return 0
        except Exception as e:
            failed.add(px)
            PROXY_FAILED_FILE.write_text("\n".join(sorted(failed)), encoding="utf-8")
            print(f"{i+1}/{len(to_try)} {px} {type(e).__name__}", file=sys.stderr)
    print("Ни один прокси не сработал", file=sys.stderr)
    return 1

if __name__ == "__main__":
    sys.exit(main())
