"""Valida a transcrição dos prints do TwitchTracker e gera a série mensal limpa.

Entrada: data/external/twitchtracker_monthly.csv (transcrito à mão dos prints)
Saída:   data/interim/twitch_monthly.csv

Checagens:
  1. "gain" = média de espectadores do mês - média da linha anterior (pega erro de digitação).
  2. horas assistidas ~ média de espectadores x 24 x dias do mês (tolerância de 12%).

Correção de rótulo: a tabela do TwitchTracker exibe cada mês com o rótulo do mês
anterior. Evidência: o resumo da própria página data os picos do Battlefield 6
(868.520, 06/08/2025) e do Marathon (523.301, 11/04/2025), que a tabela lista em
"Jul 2025" e "Mar 2025". Por isso month = label_month + 1 mês.
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import INTERIM, ROOT  # noqa: E402

SRC = ROOT / "data" / "external" / "twitchtracker_monthly.csv"


def parse_abbrev(value) -> float:
    s = str(value).strip()
    mult = {"K": 1e3, "M": 1e6, "B": 1e9}.get(s[-1:], 1)
    return float(s[:-1] if mult != 1 else s) * mult


def main():
    df = pd.read_csv(SRC, dtype={"label_month": str})
    df["hours_watched"] = df["hours_watched"].map(parse_abbrev)
    df["label_month"] = pd.to_datetime(df["label_month"], format="%Y-%m")
    df = df.sort_values(["game", "label_month"]).reset_index(drop=True)

    problems = []
    for game, g in df.groupby("game"):
        diff = g["avg_viewers"].diff()
        bad = g[g["gain"].notna() & (diff != g["gain"])]
        for _, row in bad.iterrows():
            problems.append(f"{game} {row.label_month:%Y-%m}: gain {row.gain} != diferença {diff[row.name]}")

    df["month"] = df["label_month"] + pd.offsets.MonthBegin(1)
    days = df["month"].dt.days_in_month
    expected = df["avg_viewers"] * 24 * days
    ratio = df["hours_watched"] / expected
    # linhas com poucas horas são arredondadas demais para a checagem
    suspicious = df[(df["hours_watched"] > 50_000) & ((ratio < 0.88) | (ratio > 1.12))]
    for _, row in suspicious.iterrows():
        problems.append(f"{row.game} {row.label_month:%Y-%m}: horas {row.hours_watched:,.0f} vs esperado {expected[row.name]:,.0f} (razão {ratio[row.name]:.2f})")

    print(f"{len(df)} linhas, {df.game.nunique()} jogos")
    print("\n".join(problems) if problems else "nenhuma inconsistência encontrada")

    # o último mês (set/2026) está em andamento
    last = df.groupby("game")["month"].transform("max")
    df["partial_month"] = df["month"] == last
    out = INTERIM / "twitch_monthly.csv"
    df[["game", "month", "label_month", "avg_viewers", "peak_viewers", "avg_streams", "peak_streams",
        "hours_watched", "partial_month"]].to_csv(out, index=False)
    print("salvo em", out)


if __name__ == "__main__":
    main()
