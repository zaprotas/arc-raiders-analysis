"""Coleta análises da Steam pela API pública appreviews.

Uso:
  python steam_reviews.py summary          -> resumo (positivas/negativas) de todos os jogos
  python steam_reviews.py full [appid] [ordem] [idioma]
      -> análises de um jogo (padrão: ARC Raiders, ordem "recent", todos os idiomas).
         A API limita a profundidade de cada ordem; combinar ordens e idiomas amplia a cobertura.

A coleta completa grava em JSONL e pode ser retomada (o cursor fica salvo).
Saídas em data/raw/  [O] Observado (somente Steam)
"""
import json
import sys
import time
from datetime import date
from pathlib import Path

import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import ARC_RAIDERS, GAMES, RAW  # noqa: E402

URL = "https://store.steampowered.com/appreviews/{appid}"
BASE_PARAMS = {"json": 1, "language": "all", "purchase_type": "all", "filter_offtopic_activity": 0}


def summary():
    rows = []
    for appid, (name, group) in GAMES.items():
        q = requests.get(URL.format(appid=appid), params={**BASE_PARAMS, "num_per_page": 0}, timeout=30).json()["query_summary"]
        rows.append({"appid": appid, "game": name, "group": group, **q})
        time.sleep(1)
    out = RAW / f"steam_reviews_summary_{date.today():%Y-%m-%d}.csv"
    pd.DataFrame(rows).to_csv(out, index=False)
    print("salvo em", out)


def full(appid: int, order: str = "recent", language: str = "all"):
    tag = f"{appid}_{order}_{language}"
    out = RAW / f"steam_reviews_{tag}.jsonl"
    state = RAW / f"steam_reviews_{tag}.cursor"
    cursor = state.read_text().strip() if state.exists() else "*"
    seen = 0
    with out.open("a", encoding="utf-8") as fh:
        while True:
            params = {**BASE_PARAMS, "language": language, "filter": order, "num_per_page": 100, "cursor": cursor}
            # Uma página vazia pode ser limite de requisições passageiro, não o fim da lista:
            # só encerra depois de várias páginas vazias seguidas.
            for attempt in range(10):
                try:
                    data = requests.get(URL.format(appid=appid), params=params, timeout=30).json()
                    reviews = data.get("reviews", [])
                    if reviews and data.get("cursor") not in (None, cursor):
                        break
                    reason = "página vazia"
                except Exception as exc:
                    reason = exc
                wait = min(30 * (attempt + 1), 300)
                print("nova tentativa em", wait, "s:", reason, flush=True)
                time.sleep(wait)
            else:
                break
            for rv in reviews:
                fh.write(json.dumps(rv, ensure_ascii=False) + "\n")
            seen += len(reviews)
            cursor = data["cursor"]
            state.write_text(cursor)
            if seen % 5000 < 100:
                print(seen, "análises coletadas", flush=True)
            time.sleep(0.4)
    print("fim:", seen, "análises nesta execução ->", out)


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "summary"
    if mode == "summary":
        summary()
    else:
        args = sys.argv[2:]
        full(int(args[0]) if args else ARC_RAIDERS, *args[1:3])
