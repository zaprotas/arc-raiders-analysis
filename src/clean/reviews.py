"""Converte as análises da Steam em uma tabela compacta, sem dados pessoais.

Entrada: data/raw/steam_reviews_1808500_recent_all.jsonl
Saída:   data/interim/arc_reviews.parquet (fora do git)

Removidos por privacidade: steamid, apelido, link do perfil e avatar do autor.
O projeto não precisa identificar ninguém: cada linha é uma análise.
"""
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import INTERIM, RAW  # noqa: E402

SRC = RAW / "steam_reviews_1808500_recent_all.jsonl"
COLLECTED_AT = pd.Timestamp("2026-09-25")


def rows():
    with SRC.open(encoding="utf-8") as fh:
        for line in fh:
            r = json.loads(line)
            a = r["author"]
            yield {
                "review_id": int(r["recommendationid"]),
                "created": r["timestamp_created"],
                "updated": r["timestamp_updated"],
                "language": r["language"],
                "voted_up": r["voted_up"],
                "text": r.get("review", ""),
                "votes_up": r["votes_up"],
                "votes_funny": r["votes_funny"],
                "weighted_vote_score": float(r["weighted_vote_score"]),
                "steam_purchase": r["steam_purchase"],
                "received_for_free": r["received_for_free"],
                "primarily_steam_deck": r.get("primarily_steam_deck", False),
                # perfil de jogo do autor (minutos), sem identificá-lo
                "playtime_forever_min": a.get("playtime_forever", 0),
                "playtime_at_review_min": a.get("playtime_at_review", 0),
                "playtime_2weeks_min": a.get("playtime_last_two_weeks", 0),
                "last_played": a.get("last_played", 0),
                "author_games_owned": a.get("num_games_owned", 0),
                "author_num_reviews": a.get("num_reviews", 0),
            }


def main():
    df = pd.DataFrame(rows())
    n_raw = len(df)
    df = df.drop_duplicates("review_id")
    for col in ["created", "updated", "last_played"]:
        df[col] = pd.to_datetime(df[col], unit="s")
    df.loc[df["last_played"] < "2025-01-01", "last_played"] = pd.NaT  # 0 = não informado
    df["month"] = df["created"].dt.to_period("M").dt.to_timestamp()
    df["text_len"] = df["text"].str.len()
    df["days_since_last_played"] = (COLLECTED_AT - df["last_played"]).dt.days

    print(f"{n_raw} linhas brutas, {len(df)} análises únicas")
    print("período:", df["created"].min(), "a", df["created"].max())
    print("sem texto:", (df["text_len"] == 0).sum(), "| texto < 20 caracteres:", (df["text_len"] < 20).sum())
    print("last_played ausente:", df["last_played"].isna().sum())
    print("jogo recebido de graça:", df["received_for_free"].sum(), "| fora da Steam (key):", (~df["steam_purchase"]).sum())
    print(df[["playtime_forever_min", "playtime_at_review_min", "playtime_2weeks_min"]].describe().round(0).to_string())
    df.to_parquet(INTERIM / "arc_reviews.parquet", index=False)
    print("salvo em", INTERIM / "arc_reviews.parquet")


if __name__ == "__main__":
    main()
