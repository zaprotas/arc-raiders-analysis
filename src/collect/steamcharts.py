"""Coleta a média e o pico mensais de jogadores simultâneos (Steam) no SteamCharts.

Saída: data/raw/steamcharts_monthly_<data>.csv  [O] Observado (somente Steam)
"""
import sys
import time
from datetime import date
from io import StringIO

import pandas as pd
import requests

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1]))
from config import GAMES, RAW  # noqa: E402

HEADERS = {"User-Agent": "Mozilla/5.0"}


def fetch(appid: int) -> pd.DataFrame:
    r = requests.get(f"https://steamcharts.com/app/{appid}", headers=HEADERS, timeout=30)
    r.raise_for_status()
    table = pd.read_html(StringIO(r.text), attrs={"class": "common-table"})[0]
    table.columns = ["month", "avg_players", "gain", "pct_gain", "peak_players"]
    # "Last 30 Days" vira o mês corrente, marcado como parcial
    table["partial_month"] = table["month"] == "Last 30 Days"
    table["month"] = table["month"].replace("Last 30 Days", date.today().strftime("%B %Y"))
    table["month"] = pd.to_datetime(table["month"], format="%B %Y")
    table["appid"] = appid
    table["game"], table["group"] = GAMES[appid]
    return table[["appid", "game", "group", "month", "avg_players", "peak_players", "partial_month"]]


def main():
    frames = []
    for appid in GAMES:
        try:
            frames.append(fetch(appid))
            print("ok", appid, GAMES[appid][0])
        except Exception as exc:  # registra e segue para os demais jogos
            print("falhou", appid, GAMES[appid][0], exc)
        time.sleep(1.5)
    out = RAW / f"steamcharts_monthly_{date.today():%Y-%m-%d}.csv"
    pd.concat(frames).sort_values(["appid", "month"]).to_csv(out, index=False)
    print("salvo em", out)


if __name__ == "__main__":
    main()
