"""Etapa 7: curva de receita do ARC Raiders.

O que é público (Nexon):
  - unidades por trimestre: Q4/25 10,9 mi · Q1/26 4,6 mi · Q2/26 0,8 mi (16,3 mi acumulado)
  - receita reconhecida: ¥18,3 bi em Q2/26 e ¥88 bi acumulados até Q2/26
  - ¥27,7 bi de vendas na Steam diferidos em Q4/25 (reconhecidos ao longo de 2026+)
Não é público: receita por trimestre antes de Q2, divisão vendas x loja interna.

Modelo (Monte Carlo, 20 mil simulações), em base econômica (antes do diferimento):
  receita acumulada até Q2 = reconhecida (¥88 bi) + saldo ainda diferido (D)
  vendas do jogo            = unidades x receita líquida por unidade (p)
  loja interna (cosméticos)  = receita acumulada - vendas do jogo
  Distribuição mensal: unidades de cada trimestre repartidas pelo nº de análises do mês
  (validado na Etapa 4); loja interna proporcional às horas jogadas (média de
  jogadores x dias), premissa de gasto constante por hora jogada [P].
  3º trimestre (jul-set/26): unidades pela razão de análises Q3/Q2; loja pela razão de horas.

Uso: python src/analysis/revenue.py
"""
import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from analysis.diagnostics import month_label  # noqa: E402
from config import INTERIM, ROOT  # noqa: E402
from viz import style  # noqa: E402

N_SIM = 20_000
RNG = np.random.default_rng(42)
UNITS_Q = {"2025Q4": 10.9e6, "2026Q1": 4.6e6, "2026Q2": 0.8e6}
RECOGNIZED_CUM_Q2_JPY = 88e9
RECOGNIZED_Q2_JPY = 18.3e9
METRICS: dict = {}

# Premissas (faixas uniformes) — cada uma justificada no notebook
ASSUMPTIONS = {
    "fx_jpy_usd": (154, 161),          # câmbio médio Q4/25-Q2/26 (Q2 = 160,7 no release)
    "deferred_left_jpy": (5e9, 20e9),  # saldo diferido ao fim de Q2: sobra dos ¥27,7 bi + novas vendas na Steam
    "net_per_unit_usd": (21, 32),      # 30,6 US$/unidade bruto na Steam (Sensor Tower); 21 = líquido de 30% das lojas
    "q3_units_factor": (0.7, 1.3),     # incerteza sobre a razão análises/unidades no Q3
}


def draw(name):
    lo, hi = ASSUMPTIONS[name]
    return RNG.uniform(lo, hi, N_SIM)


def monthly_base() -> pd.DataFrame:
    reviews = pd.read_parquet(INTERIM / "arc_reviews.parquet", columns=["month"])
    n = reviews["month"].value_counts().sort_index().astype(float)
    # set/2026 coletado até o dia 25: escala para o mês inteiro
    n[pd.Timestamp("2026-09-01")] = n[pd.Timestamp("2026-09-01")] * 30 / 25
    daily = pd.read_csv(INTERIM / "arc_players_daily.csv", parse_dates=["date"])
    players = pd.read_csv(INTERIM / "players_monthly.csv", parse_dates=["month"])
    arc = players[players["appid"] == 1808500].set_index("month")["avg_players"]
    # out/2025 (2 dias) não está no SteamCharts: usa a média diária do SteamDB
    arc[pd.Timestamp("2025-10-01")] = daily[daily["date"] < "2025-11-01"]["peak_players"].mean() * 0.6
    months = pd.date_range("2025-10-01", "2026-09-01", freq="MS")
    base = pd.DataFrame(index=months)
    base["reviews"] = n.reindex(months).fillna(0)
    days = pd.Series(months.days_in_month, index=months).astype(float)
    days[pd.Timestamp("2025-10-01")] = 2
    base["player_hours"] = arc.reindex(months) * days * 24
    base["quarter"] = base.index.to_period("Q").astype(str).str.replace("Q", "Q")
    return base


def simulate(base: pd.DataFrame) -> dict:
    fx = draw("fx_jpy_usd")
    deferred = draw("deferred_left_jpy")
    p = draw("net_per_unit_usd")
    q3f = draw("q3_units_factor")

    units_total = sum(UNITS_Q.values())
    econ_cum_q2 = (RECOGNIZED_CUM_Q2_JPY + deferred) / fx
    game_sales_q2 = units_total * p
    store_cum_q2 = econ_cum_q2 - game_sales_q2

    hist = base[base.index <= "2026-06-01"]
    q3 = base[base.index >= "2026-07-01"]
    rev_q2 = base.loc[base["quarter"] == "2026Q2", "reviews"].sum()
    units_q3 = UNITS_Q["2026Q2"] * q3["reviews"].sum() / rev_q2 * q3f
    hours_share_q3 = q3["player_hours"].sum() / hist["player_hours"].sum()
    store_q3 = store_cum_q2 * hours_share_q3

    # distribuição mensal (matriz simulações x meses)
    months = base.index
    units_m = np.zeros((N_SIM, len(months)))
    for j, m in enumerate(months):
        q = base.loc[m, "quarter"]
        if q in UNITS_Q:
            share = base.loc[m, "reviews"] / base.loc[base["quarter"] == q, "reviews"].sum()
            units_m[:, j] = UNITS_Q[q] * share
        else:
            share = base.loc[m, "reviews"] / q3["reviews"].sum()
            units_m[:, j] = units_q3 * share
    hours = base["player_hours"].values
    store_m = np.zeros((N_SIM, len(months)))
    hist_mask = months <= "2026-06-01"
    store_m[:, hist_mask] = store_cum_q2[:, None] * hours[hist_mask] / hours[hist_mask].sum()
    store_m[:, ~hist_mask] = store_q3[:, None] * hours[~hist_mask] / hours[~hist_mask].sum()
    game_m = units_m * p[:, None]
    return {"fx": fx, "p": p, "deferred": deferred, "econ_cum_q2": econ_cum_q2, "game_sales_q2": game_sales_q2,
            "store_cum_q2": store_cum_q2, "units_q3": units_q3, "store_q3": store_q3, "game_q3": units_q3 * p,
            "game_m": game_m, "store_m": store_m, "months": months}


def pct(a, q=(10, 50, 90)):
    return [float(np.percentile(a, x)) for x in q]


def fig_curve(sim: dict):
    months = sim["months"]
    total_m = sim["game_m"] + sim["store_m"]
    cum = np.cumsum(total_m, axis=1) / 1e6
    p10, p50, p90 = (np.percentile(cum, q, axis=0) for q in (10, 50, 90))
    x = months + pd.Timedelta(days=14)
    fig, ax = plt.subplots(figsize=(12.5, 6))
    ax.fill_between(x, p10, p90, color=style.ARC, alpha=0.12, lw=0, label="Faixa de 80% da estimativa")
    ax.plot(x, p50, color=style.ARC, lw=2.4, label="Receita econômica estimada (vendas + loja interna)")
    # pontos oficiais (receita reconhecida, com diferimento)
    fx = np.median(sim["fx"])
    official = {pd.Timestamp("2026-03-31"): (RECOGNIZED_CUM_Q2_JPY - RECOGNIZED_Q2_JPY) / fx / 1e6,
                pd.Timestamp("2026-06-30"): RECOGNIZED_CUM_Q2_JPY / fx / 1e6}
    ax.plot(list(official), list(official.values()), "o", ms=9, color=style.SLOTS[1], mec=style.SURFACE, mew=2, zorder=4,
            label="Receita reconhecida pela Nexon (oficial, com diferimento)")
    for d, v in official.items():
        ax.annotate(f"US$ {v:.0f} mi", (d, v), xytext=(10, -14), textcoords="offset points", fontsize=9, color=style.INK_2)
    ax.annotate(f"US$ {p50[-1]:.0f} mi\n({p10[-1]:.0f}–{p90[-1]:.0f})", (x[-1], p50[-1]), xytext=(8, 0), textcoords="offset points",
                va="center", fontsize=9.5, color=style.INK, fontweight="bold")
    ax.axvspan(pd.Timestamp("2026-07-01"), pd.Timestamp("2026-10-01"), color=style.GRID, alpha=0.5, lw=0)
    ax.text(pd.Timestamp("2026-07-05"), 30, "3º tri: estimado\n(Nexon divulga em nov)", fontsize=8.5, color=style.INK_2)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"US$ {v:.0f} mi"))
    ax.set_xticks(months[::2], [month_label(m) for m in months[::2]])
    ax.set_xlim(months[0], months[-1] + pd.Timedelta(days=60))
    ax.set_ylim(0, p90[-1] * 1.12)
    ax.legend(loc="upper left", fontsize=9)
    ax.set_title("Receita acumulada do ARC Raiders desde o lançamento")
    style.subtitle(ax, "Estimativa mensal calibrada nos números oficiais da Nexon; faixa = 10º a 90º percentil de 20 mil simulações")
    style.source_note(fig, "Fontes: Nexon (unidades por trimestre, receita reconhecida, diferimento de ¥27,7 bi) [O]; Sensor Tower (US$ 30,6/unidade na Steam) [E]; "
                           "análises e jogadores na Steam [O]. Receita econômica = antes do diferimento contábil. Loja interna distribuída pelas horas jogadas [P].")
    return style.save(fig, "10a_receita_acumulada")


def fig_monthly(sim: dict):
    months = sim["months"]
    game = np.median(sim["game_m"], axis=0) / 1e6
    store = np.median(sim["store_m"], axis=0) / 1e6
    fig, ax = plt.subplots(figsize=(12.5, 5.6))
    x = np.arange(len(months))
    ax.bar(x, game, width=0.6, color=style.SLOTS[0], label="Vendas do jogo")
    ax.bar(x, store, width=0.6, bottom=game, color=style.SLOTS[2], label="Loja interna (cosméticos, passes)",
           edgecolor=style.SURFACE, linewidth=2)
    for xi, (g, s) in enumerate(zip(game, store)):
        ax.text(xi, g + s, f"{g + s:.0f}", ha="center", va="bottom", fontsize=8.5, color=style.INK_2)
    labels = [month_label(m) + ("*" if m >= pd.Timestamp("2026-07-01") else "") for m in months]
    ax.set_xticks(x, labels)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"US$ {v:.0f} mi"))
    ax.legend(loc="upper right")
    ax.set_title("Receita mensal estimada: vendas do jogo x loja interna (mediana)")
    style.subtitle(ax, "O jogo vendeu quase tudo nos primeiros 3 meses; desde abril, a loja interna responde pela maior parte da receita")
    style.source_note(fig, "Estimativa [E/P] em US$ milhões, mediana de 20 mil simulações. *jul-set/2026 estimados (sem número oficial). "
                           "Out/2025 = 2 dias. Mesmas fontes e premissas do gráfico anterior.")
    return style.save(fig, "10b_receita_mensal_composicao")


def fig_assumptions(sim: dict):
    """Tornado: quanto cada premissa move a loja interna acumulada."""
    target = sim["store_cum_q2"] / 1e6
    base = np.median(target)
    rows = []
    for name, key, label in [("net_per_unit_usd", "p", "Receita líquida por unidade (US$ 21–32)"),
                             ("deferred_left_jpy", "deferred", "Saldo ainda diferido (¥5–20 bi)"),
                             ("fx_jpy_usd", "fx", "Câmbio (¥154–161 por US$)")]:
        v = sim[key]
        lo_mask, hi_mask = v <= np.percentile(v, 10), v >= np.percentile(v, 90)
        rows.append((label, np.median(target[lo_mask]) - base, np.median(target[hi_mask]) - base))
    rows.sort(key=lambda r: abs(r[2] - r[1]))
    fig, ax = plt.subplots(figsize=(11, 4))
    y = np.arange(len(rows))
    for yi, (label, lo, hi) in zip(y, rows):
        ax.barh(yi, lo, height=0.5, color=style.SLOTS[7])
        ax.barh(yi, hi, height=0.5, color=style.SLOTS[0])
        for v in (lo, hi):
            ax.text(v, yi, f"  {v:+.0f}  ", ha="left" if v >= 0 else "right", va="center", fontsize=9, color=style.INK_2)
    ax.axvline(0, color=style.INK_2, lw=1)
    ax.set_yticks(y, [r[0] for r in rows])
    ax.grid(axis="y", visible=False)
    ax.grid(axis="x", visible=True)
    lim = max(abs(r[1]) for r in rows + [(0, 0, 0)]) * 1.4
    ax.set_xlim(-lim, lim)
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:+.0f}"))
    ax.set_xlabel("variação na receita da loja interna acumulada até jun/2026 (US$ milhões)")
    ax.set_title("Quais premissas mais mudam a estimativa da loja interna")
    style.subtitle(ax, f"Mediana: US$ {base:.0f} mi. Vermelho = premissa no 10º percentil; azul = no 90º percentil")
    style.source_note(fig, "Análise de sensibilidade sobre as 20 mil simulações. A maior incerteza é contábil: se a Nexon registra as vendas "
                           "líquidas ou brutas da taxa das lojas.")
    return style.save(fig, "10c_sensibilidade_premissas")


def main():
    style.apply()
    base = monthly_base()
    sim = simulate(base)
    paths = [fig_curve(sim), fig_monthly(sim), fig_assumptions(sim)]
    total = sim["game_m"].sum(axis=1) + sim["store_m"].sum(axis=1)
    q3_total = sim["game_q3"] + sim["store_q3"]
    store_share = sim["store_cum_q2"] / sim["econ_cum_q2"] * 100
    METRICS.update({
        "premissas": {k: list(v) for k, v in ASSUMPTIONS.items()},
        "receita_economica_ate_jun26_usd_mi": pct(sim["econ_cum_q2"] / 1e6),
        "vendas_jogo_ate_jun26_usd_mi": pct(sim["game_sales_q2"] / 1e6),
        "loja_interna_ate_jun26_usd_mi": pct(sim["store_cum_q2"] / 1e6),
        "loja_interna_pct_da_receita": pct(store_share),
        "q3_26_unidades_mi": pct(sim["units_q3"] / 1e6),
        "q3_26_receita_usd_mi": pct(q3_total / 1e6),
        "q3_26_loja_interna_usd_mi": pct(sim["store_q3"] / 1e6),
        "receita_economica_ate_set26_usd_mi": pct(total / 1e6),
        "unidades_ate_set26_mi": pct((sum(UNITS_Q.values()) + sim["units_q3"]) / 1e6),
        "receita_por_unidade_ate_jun26_usd": pct(sim["econ_cum_q2"] / sum(UNITS_Q.values())),
        "oficial_reconhecida_ate_jun26_usd_mi": RECOGNIZED_CUM_Q2_JPY / np.median(sim["fx"]) / 1e6,
    })
    (ROOT / "reports" / "metrics_receita.json").write_text(json.dumps(METRICS, ensure_ascii=False, indent=2), encoding="utf-8")
    for p in paths:
        print("figura:", p.name)
    print(json.dumps({k: v for k, v in METRICS.items() if k != "premissas"}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
