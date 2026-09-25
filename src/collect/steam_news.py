"""Coleta os anúncios oficiais (patches, hotfixes, eventos) publicados na Steam.

Saída: data/raw/steam_news_<data>.csv  [O] Observado
Usado para marcar patches e grandes atualizações nas séries de jogadores.
"""
import re
import sys
import time
from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import GAMES, RAW  # noqa: E402

URL = "https://api.steampowered.com/ISteamNews/GetNewsForApp/v2/"

# Classificação simples pelo título; revisada à mão na etapa de limpeza.
KINDS = [
    ("survey", r"survey"),
    ("hotfix", r"hotfix"),
    ("store", r"store update|bundle|\bset\b|skin"),
    ("major_update", r"major update|update is (?:live|out)|season|expedition|frozen trail|riven tides|\bchapter\b|operation"),
    ("patch", r"patch|update \d|\d+\.\d+(?:\.\d+)?|live update|balanc"),
    ("event", r"event|weekend|free|anniversary|collab|partnership"),
]


def kind(title: str) -> str:
    t = title.lower()
    for name, pattern in KINDS:
        if re.search(pattern, t):
            return name
    return "other"


def fetch(appid: int) -> pd.DataFrame:
    params = {"appid": appid, "count": 1000, "maxlength": 400, "feeds": "steam_community_announcements"}
    items = requests.get(URL, params=params, timeout=30).json()["appnews"]["newsitems"]
    df = pd.DataFrame(items)
    if df.empty:
        return df
    df["date"] = df["date"].map(lambda s: datetime.fromtimestamp(s, tz=timezone.utc).date())
    df["kind"] = df["title"].map(kind)
    df["appid"] = appid
    df["game"] = GAMES[appid][0]
    return df[["appid", "game", "date", "kind", "title", "url", "contents"]]


def main():
    frames = []
    for appid in GAMES:
        try:
            frames.append(fetch(appid))
            print("ok", appid, GAMES[appid][0], len(frames[-1]))
        except Exception as exc:
            print("falhou", appid, GAMES[appid][0], exc)
        time.sleep(1)
    out = RAW / f"steam_news_{date.today():%Y-%m-%d}.csv"
    pd.concat(frames).sort_values(["appid", "date"]).to_csv(out, index=False)
    print("salvo em", out)


if __name__ == "__main__":
    main()
