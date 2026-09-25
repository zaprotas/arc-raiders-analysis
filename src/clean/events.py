"""Monta a linha do tempo de eventos do ARC Raiders a partir dos anúncios da Steam.

Entrada:  API de notícias da Steam (texto integral, com cache em data/raw/steam_news_full_1808500.json)
Saída:    data/interim/arc_events.csv

Cada anúncio recebe um tipo (revisado à mão, ver OVERRIDES) e marcadores de conteúdo
contados no texto integral das notas: balanceamento, anti-cheat, exploits, bugs,
pareamento e conteúdo novo. O impacto de cada evento é medido na Etapa 4.
"""
import json
import re
import sys
from pathlib import Path

import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import ARC_RAIDERS, INTERIM, RAW  # noqa: E402

CACHE = RAW / f"steam_news_full_{ARC_RAIDERS}.json"

# Tipo por título. A ordem importa: a primeira regra que casar vence.
RULES = [
    ("survey", r"survey"),
    ("hotfix", r"hotfix"),
    ("store_update", r"store update"),
    ("major_update", r"^riven tides$|north line|cold snap|headwinds|shared watch|shrouded sky|flashpoint|expedition"),
    ("live_update", r"live update|patch notes|update \d"),
    ("launch", r"launch day"),
    ("pre_launch", r"trailer|tech test|playtest|releases october|coming in 2025|what.s next|rust belt|gameplay reveal"),
    ("communication", r"fair play|matchmaking|changing how we update|nominate|departure issue"),
]
# Revisão manual de casos que a regra não resolve bem.
OVERRIDES = {
    "Riven Tides - Patch Notes Update 1.26.0": "major_update",
    "COLD SNAP": "major_update_announcement",
    "Riven Tides": "major_update_announcement",
    "Preparing for your Second Expedition": "expedition",
    "The Fourth Expedition": "expedition",
    "The 5th Expedition": "expedition",
    "Expedition Departure Issue Update": "communication",
    "Nomadic Envoy & No Free Loadout Survey": "survey",
    "Hotfix 1.25.0": "hotfix",
}
MARKERS = {
    "balance": r"\bbalanc|\bnerf|\bbuff|damage (?:increased|reduced|decreased)|reduced .{0,30}damage|increased .{0,30}damage",
    "anticheat": r"cheat|anti-cheat|\bban",
    "exploit": r"exploit",
    "bugfix": r"\bfix(?:ed|es)?\b",
    "matchmaking": r"matchmaking",
    "new_content": r"\bnew (?:map|weapon|arc|enemy|trader|quest|event|item|outfit|project|condition)",
}


def fetch_full() -> list[dict]:
    if CACHE.exists():
        return json.loads(CACHE.read_text(encoding="utf-8"))
    params = {"appid": ARC_RAIDERS, "count": 1000, "maxlength": 0, "feeds": "steam_community_announcements"}
    items = requests.get("https://api.steampowered.com/ISteamNews/GetNewsForApp/v2/", params=params, timeout=60).json()["appnews"]["newsitems"]
    CACHE.write_text(json.dumps(items, ensure_ascii=False), encoding="utf-8")
    return items


def kind(title: str) -> str:
    t = title.strip()
    if t in OVERRIDES:
        return OVERRIDES[t]
    for name, pattern in RULES:
        if re.search(pattern, t.lower()):
            return name
    return "other"


def main():
    df = pd.DataFrame(fetch_full())
    df["date"] = pd.to_datetime(df["date"], unit="s").dt.normalize()
    df["title"] = df["title"].str.strip()
    df["kind"] = df["title"].map(kind)
    text = df["contents"].str.lower()
    for name, pattern in MARKERS.items():
        df[f"n_{name}"] = text.str.count(pattern)
    df["text_len"] = df["contents"].str.len()
    df = df.sort_values("date")
    cols = ["date", "kind", "title", "text_len"] + [f"n_{m}" for m in MARKERS] + ["url"]
    df[cols].to_csv(INTERIM / "arc_events.csv", index=False)
    print(df["kind"].value_counts().to_string())
    print()
    print(df[cols[:-1]].to_string(index=False, max_colwidth=45))


if __name__ == "__main__":
    main()
