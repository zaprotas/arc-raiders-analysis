"""Baixa o texto completo de publicações oficiais estratégicas da Embark.

Saída: data/external/official_posts/<slug>.txt  [O] Observado
Fontes: arcraiders.com/news e anúncios da Steam (via steam_news.py).
"""
import re
import sys
import time
from pathlib import Path

import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import ARC_RAIDERS, RAW, ROOT  # noqa: E402

OUT = ROOT / "data" / "external" / "official_posts"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140 Safari/537.36"}

SITE_SLUGS = [
    "frozen-trail-is-coming-october-8th",
    "frozen-trail-content-preview",
    "pve-toggle-beta-test",
    "the-5th-expedition",
    "development-update",
]
# Títulos de anúncios na Steam cujo texto completo interessa à análise
STEAM_TITLES = [
    "We’re changing how we update ARC Raiders",
    "Ensuring Fair Play",
    "Notes on The Matchmaking System",
    "Riven Tides",
    "The Fourth Expedition",
    "Preparing for your Second Expedition",
    "Nomadic Envoy & No Free Loadout Survey",
]


def html_to_text(html: str) -> str:
    html = re.sub(r"<script.*?</script>|<style.*?</style>", " ", html, flags=re.S)
    text = re.sub(r"<[^>]+>", "\n", html)
    text = re.sub(r"&#x27;|&#39;", "'", text).replace("&amp;", "&").replace("&quot;", '"')
    return re.sub(r"\n\s*\n+", "\n", text).strip()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for slug in SITE_SLUGS:
        r = requests.get(f"https://arcraiders.com/news/{slug}", headers=HEADERS, timeout=30)
        r.raise_for_status()
        (OUT / f"{slug}.txt").write_text(f"URL: {r.url}\n\n{html_to_text(r.text)}", encoding="utf-8")
        print("ok", slug)
        time.sleep(1)

    # Texto integral dos anúncios da Steam (a coleta de notícias guarda só o início)
    params = {"appid": ARC_RAIDERS, "count": 1000, "maxlength": 0, "feeds": "steam_community_announcements"}
    items = requests.get("https://api.steampowered.com/ISteamNews/GetNewsForApp/v2/", params=params, timeout=30).json()["appnews"]["newsitems"]
    for item in items:
        if any(item["title"].strip().startswith(t) for t in STEAM_TITLES):
            slug = re.sub(r"[^a-z0-9]+", "-", item["title"].lower()).strip("-")[:60]
            date = pd.to_datetime(item["date"], unit="s").date()
            body = re.sub(r"\[/?[^\]]+\]", "", item["contents"])  # remove marcações BBCode
            (OUT / f"steam-{date}-{slug}.txt").write_text(f"URL: {item['url']}\nData: {date}\n\n{item['title']}\n\n{body}", encoding="utf-8")
            print("ok steam", date, item["title"])


if __name__ == "__main__":
    main()
