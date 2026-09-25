"""Limpa as séries de jogadores simultâneos e confere uma fonte contra a outra.

Entradas:
  data/raw/steamcharts_monthly_<data>.csv   média e pico mensais (15 jogos)
  data/external/steamdb_chart_1808500.csv   ARC Raiders, diário e depois a cada 10 min
Saídas:
  data/interim/players_monthly.csv          série mensal de todos os jogos
  data/interim/arc_players_daily.csv        ARC Raiders por dia (pico e média)

Validação: a média e o pico mensais do SteamCharts devem bater com os
calculados a partir do SteamDB (tolerância de 5%).
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import INTERIM, RAW, ROOT  # noqa: E402

STEAMDB = ROOT / "data" / "external" / "steamdb_chart_1808500.csv"


def load_steamcharts() -> pd.DataFrame:
    path = sorted(RAW.glob("steamcharts_monthly_*.csv"))[-1]
    df = pd.read_csv(path, parse_dates=["month"])
    launch = df.groupby("appid")["month"].transform("min")
    df["months_since_launch"] = ((df["month"].dt.year - launch.dt.year) * 12 + df["month"].dt.month - launch.dt.month)
    df["peak_index"] = df["avg_players"] / df.groupby("appid")["avg_players"].transform("max") * 100
    return df


def load_steamdb_daily() -> pd.DataFrame:
    raw = pd.read_csv(STEAMDB, sep=";", parse_dates=["DateTime"])
    raw = raw.rename(columns={"DateTime": "ts", "Players": "players", "Average Players": "avg_players_steamdb"})
    raw["date"] = raw["ts"].dt.normalize()
    # Até ~ago/2026 o SteamDB exporta 1 ponto por dia (o pico diário); depois, 1 a cada 10 min.
    daily = raw.groupby("date").agg(peak_players=("players", "max"), mean_players=("players", "mean"),
                                    points=("players", "size")).reset_index()
    # Em dias com um único ponto, a "média" é o próprio pico: marcamos para não confundir.
    daily.loc[daily["points"] == 1, "mean_players"] = pd.NA
    return daily


def main():
    monthly = load_steamcharts()
    daily = load_steamdb_daily()

    arc = monthly[monthly["appid"] == 1808500].set_index("month")
    check = daily.assign(month=daily["date"].dt.to_period("M").dt.to_timestamp()).groupby("month").agg(
        steamdb_peak=("peak_players", "max"))
    check = check.join(arc[["peak_players"]].rename(columns={"peak_players": "steamcharts_peak"}), how="inner")
    check["diff_pct"] = (check["steamdb_peak"] / check["steamcharts_peak"] - 1) * 100
    print("Pico mensal: SteamDB x SteamCharts (ARC Raiders)")
    print(check.round(1).to_string())
    off = check[check["diff_pct"].abs() > 5]
    print("divergências acima de 5%:", "nenhuma" if off.empty else off.index.strftime("%Y-%m").tolist())

    monthly.to_csv(INTERIM / "players_monthly.csv", index=False)
    daily.to_csv(INTERIM / "arc_players_daily.csv", index=False)
    print("dias no SteamDB:", len(daily), "| de", daily["date"].min().date(), "a", daily["date"].max().date())


if __name__ == "__main__":
    main()
