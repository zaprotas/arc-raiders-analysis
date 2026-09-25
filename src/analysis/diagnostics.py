"""Etapa 4: diagnóstico da trajetória do ARC Raiders (gráficos + métricas).

Gera as figuras em reports/figures/ e as métricas em reports/metrics_diagnostico.json.
Uso: python src/analysis/diagnostics.py
"""
import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import ARC_RAIDERS, INTERIM, LIFECYCLE_EXCLUDE, RAW, ROOT, STEAM_LAUNCH  # noqa: E402
from viz import style  # noqa: E402

REPORTS = ROOT / "reports"
METRICS: dict = {}
MONTHS_PT = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]


def month_label(ts) -> str:
    return f"{MONTHS_PT[ts.month - 1]}/{str(ts.year)[2:]}"


def load_players() -> pd.DataFrame:
    d = pd.read_csv(INTERIM / "players_monthly.csv", parse_dates=["month"])
    launch = d["appid"].map(STEAM_LAUNCH).pipe(pd.to_datetime)
    d["m"] = (d["month"].dt.year - launch.dt.year) * 12 + d["month"].dt.month - launch.dt.month
    return d


# ---------------------------------------------------------------------------
# 1. Posicionamento no lançamento
# ---------------------------------------------------------------------------
def fig_positioning(players: pd.DataFrame):
    groups = {"arc_raiders": "", "fps": "FPS", "extraction": "Extraction", "extraction_hybrid": "Extraction",
              "reference_pve": "PvE", "reference_updates": None}
    launch = players[(players["m"].between(0, 3)) & (~players["appid"].isin(LIFECYCLE_EXCLUDE))]
    peak3 = launch.groupby(["game", "group"])["peak_players"].max().reset_index()
    peak3 = peak3[peak3["group"].map(groups).notna()]

    reviews = pd.read_csv(sorted(RAW.glob("steam_reviews_summary_*.csv"))[-1])
    reviews["pct"] = reviews["total_positive"] / reviews["total_reviews"] * 100
    reviews = reviews[reviews["group"].map(groups).notna() & (reviews["total_reviews"] > 5000)]

    st = pd.read_csv(sorted(RAW.glob("sensortower_vgi_quickstats_*.csv"))[-1])
    st = st[st["units_sold"].notna() & ~st["game"].isin(["Counter-Strike 2", "PUBG: Battlegrounds", "Apex Legends"])]

    tw = pd.read_csv(INTERIM / "twitch_monthly.csv", parse_dates=["month"])
    tw_launch = {"arc_raiders": "2025-10", "battlefield_6": "2025-10", "marathon": "2026-03",
                 "escape_from_tarkov": "2025-11", "hunt_showdown": "2024-08"}
    tw_names = {"arc_raiders": "ARC Raiders", "battlefield_6": "Battlefield 6", "marathon": "Marathon",
                "escape_from_tarkov": "Escape from Tarkov", "hunt_showdown": "Hunt: Showdown 1896"}
    first_month = []
    for g, start in tw_launch.items():
        s = pd.Timestamp(start)
        rows = tw[(tw["game"] == g) & (tw["month"].between(s, s + pd.offsets.MonthBegin(1)))]
        first_month.append({"game": tw_names[g], "hours": rows["hours_watched"].sum()})
    tw_df = pd.DataFrame(first_month)

    panels = [
        ("Pico de jogadores nos 3 primeiros meses (Steam)", peak3.rename(columns={"peak_players": "v"}), style.thousands, "SteamCharts [O]"),
        ("Análises positivas na Steam (%)", reviews.rename(columns={"pct": "v"}), lambda x, _=None: f"{x:.0f}%", "Steam [O]"),
        ("Horas assistidas na Twitch no mês de lançamento e no seguinte", tw_df.rename(columns={"hours": "v"}), style.thousands, "TwitchTracker [O]"),
        ("Unidades vendidas na Steam, acumulado", st.rename(columns={"units_sold": "v"}), style.thousands, "Sensor Tower [E]"),
    ]
    fig, axes = plt.subplots(2, 2, figsize=(13, 9.5))
    for ax, (title, df, fmt, src) in zip(axes.flat, panels):
        df = df.sort_values("v")
        colors = [style.ARC if g == "ARC Raiders" else style.CONTEXT_GRAY for g in df["game"]]
        y = np.arange(len(df))
        ax.barh(y, df["v"], height=0.62, color=colors)
        ax.set_yticks(y, df["game"])
        ax.grid(axis="y", visible=False)
        ax.grid(axis="x", visible=True)
        ax.xaxis.set_major_formatter(mticker.FuncFormatter(fmt))
        for yi, v in zip(y, df["v"]):
            ax.text(v, yi, "  " + fmt(v), va="center", fontsize=8.5, color=style.INK_2)
        ax.set_xlim(0, df["v"].max() * 1.18)
        ax.set_title(title, fontsize=11)
        ax.text(1, -0.1, src, transform=ax.transAxes, ha="right", color=style.MUTED, fontsize=8)
        rank = int((df["v"] > df.loc[df["game"] == "ARC Raiders", "v"].iloc[0]).sum()) + 1
        METRICS.setdefault("posicionamento", {})[title] = {"arc": float(df.loc[df["game"] == "ARC Raiders", "v"].iloc[0]),
                                                           "posicao": rank, "de": len(df)}
    fig.tight_layout(rect=(0, 0, 1, 0.91), h_pad=3)
    fig.text(0.01, 0.985, "Como o ARC Raiders estreou frente aos concorrentes", fontsize=15, fontweight="bold", va="top")
    fig.text(0.01, 0.95, "ARC Raiders em azul. Concorrentes: FPS consolidados e extraction shooters com estreia comparável na Steam.",
             color=style.INK_2, fontsize=10, va="top")
    style.source_note(fig, "Twitch: Hunt no relançamento como Hunt: Showdown 1896 (ago/2024); Tarkov na versão 1.0 (nov/2025). "
                           "Unidades: acumulado desde o lançamento de cada jogo (Rainbow Six Siege: 2015); jogos gratuitos ficam de fora.\n"
                           "Pico de estreia: Apex, CS2 e Tarkov ficam de fora (não estrearam na Steam de forma comparável).")
    return style.save(fig, "01_posicionamento_lancamento")


# ---------------------------------------------------------------------------
# 2. Jogadores por mês: média e pico, e comparação com concorrentes
# ---------------------------------------------------------------------------
def fig_monthly(players: pd.DataFrame):
    arc = players[players["appid"] == ARC_RAIDERS].sort_values("month")
    fig, ax = plt.subplots(figsize=(12, 5.5))
    x = np.arange(len(arc))
    ax.bar(x, arc["peak_players"], width=0.55, color=style.BLUE_RAMP[1], label="Pico no mês")
    ax.bar(x, arc["avg_players"], width=0.55, color=style.ARC, label="Média no mês")
    for xi, (p, a) in enumerate(zip(arc["peak_players"], arc["avg_players"])):
        ax.text(xi, p, style.thousands(p), ha="center", va="bottom", fontsize=8.5, color=style.INK_2)
        ax.text(xi, a / 2, style.thousands(a), ha="center", va="center", fontsize=8.5, color="white")
    labels = [month_label(m) + ("*" if part else "") for m, part in zip(arc["month"], arc["partial_month"])]
    ax.set_xticks(x, labels)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(style.thousands))
    ax.legend(loc="upper right", ncols=2)
    ax.set_title("ARC Raiders na Steam: média e pico de jogadores simultâneos por mês")
    style.subtitle(ax, "A média de set/2026 é 92% menor que a de nov/2025; o pico, 92% menor que o recorde de jan/2026")
    style.source_note(fig, "Fonte: SteamCharts [O], só Steam. *set/2026: últimos 30 dias até 25/09. Out/2025 (2 dias) não aparece na fonte.")
    p1 = style.save(fig, "02a_jogadores_mes_arc")

    first, last = arc.iloc[0], arc.iloc[-1]
    METRICS["jogadores_mes"] = {
        "media_nov25": round(first["avg_players"]), "media_set26": round(last["avg_players"]),
        "queda_media_pct": round((last["avg_players"] / first["avg_players"] - 1) * 100, 1),
        "pico_recorde": int(arc["peak_players"].max()), "pico_set26": int(last["peak_players"]),
        "queda_pico_pct": round((last["peak_players"] / arc["peak_players"].max() - 1) * 100, 1),
    }

    # Comparação no mesmo calendário, escala logarítmica (magnitudes muito diferentes)
    window = players[players["month"] >= "2025-10-01"]
    show = ["ARC Raiders", "Counter-Strike 2", "PUBG: Battlegrounds", "Apex Legends", "Delta Force",
            "Tom Clancy's Rainbow Six Siege", "Battlefield 6", "Escape from Tarkov", "Hunt: Showdown 1896", "Marathon"]
    fig, ax = plt.subplots(figsize=(12, 6.5))
    labels = []
    last_month = window["month"].max()
    for g in show[::-1]:
        s = window[window["game"] == g].sort_values("month")
        is_arc = g == "ARC Raiders"
        ax.plot(s["month"], s["avg_players"], color=style.ARC if is_arc else style.CONTEXT_GRAY,
                lw=2.6 if is_arc else 1.4, zorder=3 if is_arc else 2)
        ax.plot(s["month"].iloc[-1], s["avg_players"].iloc[-1], "o", ms=6 if is_arc else 4,
                color=style.ARC if is_arc else style.CONTEXT_GRAY, mec=style.SURFACE, mew=1.5, zorder=4)
        name = g.replace("Tom Clancy's ", "").replace(": Battlegrounds", "").replace(": Showdown 1896", "")
        labels.append((s["month"].iloc[-1], s["avg_players"].iloc[-1],
                       f"{name}  {style.thousands(s['avg_players'].iloc[-1])}", is_arc))
    ax.set_yscale("log")
    style.end_labels(ax, labels, x_text=last_month + pd.Timedelta(days=25), min_gap=0.075, log=True)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(style.thousands))
    ax.set_xlim(window["month"].min() - pd.Timedelta(days=10), last_month + pd.Timedelta(days=10))
    ticks = pd.date_range(window["month"].min(), last_month, freq="2MS")
    ax.set_xticks(ticks, [month_label(t) for t in ticks])
    ax.set_title("Média mensal de jogadores simultâneos na Steam, ARC Raiders e concorrentes")
    style.subtitle(ax, "Escala logarítmica: cada linha de grade multiplica por 10. Valor à direita = média de set/2026")
    style.source_note(fig, "Fonte: SteamCharts [O], só Steam. Set/2026 = últimos 30 dias.")
    p2 = style.save(fig, "02b_jogadores_mes_concorrentes")
    return p1, p2


def lifecycle_index(players: pd.DataFrame) -> pd.DataFrame:
    """Média mensal em % do melhor mês entre os meses 0 e 3, nos 12 primeiros meses na Steam.

    Fora: jogos sem estreia comparável (LIFECYCLE_EXCLUDE), PUBG (cresceu 10x no acesso
    antecipado, outro fenômeno) e No Man's Sky (não é jogo de tiro; entra só como
    referência de atualizações na Etapa 8).
    """
    skip = LIFECYCLE_EXCLUDE | {578080, 275850}
    d = players[~players["appid"].isin(skip) & players["m"].between(0, 11)].copy()
    base = d[d["m"] <= 3].groupby("appid")["avg_players"].max()
    d["idx"] = d["avg_players"] / d["appid"].map(base) * 100
    return d


def fig_lifecycle(players: pd.DataFrame):
    d = lifecycle_index(players)
    fig, ax = plt.subplots(figsize=(12, 6))
    labels = []
    for appid, s in d.groupby("appid"):
        s = s.sort_values("m")
        g = s["game"].iloc[0]
        is_arc = appid == ARC_RAIDERS
        ax.plot(s["m"], s["idx"], color=style.ARC if is_arc else style.CONTEXT_GRAY, lw=2.8 if is_arc else 1.3,
                zorder=3 if is_arc else 2)
        end = s.iloc[-1]
        labels.append((end["m"], end["idx"], f"{g.replace(': Showdown 1896', '')}  {end['idx']:.0f}%", is_arc))
    style.end_labels(ax, labels, x_text=11.6, min_gap=6.5)
    ax.set_xticks(range(0, 12), [f"{i}" for i in range(12)])
    ax.set_xlabel("Meses desde a estreia na Steam")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:.0f}%"))
    ax.set_xlim(-0.2, 11.3)
    ax.set_title("Ciclo de vida: média de jogadores em % do melhor mês da estreia")
    style.subtitle(ax, "ARC Raiders em azul; demais jogos com estreia comparável na Steam em cinza. Valor à direita = último mês disponível")
    style.source_note(fig, "Fonte: SteamCharts [O]. 100% = maior média mensal entre os meses 0 e 3. "
                           "Fora: PUBG (cresceu 10x no acesso antecipado), Apex, CS2 e Tarkov (sem estreia comparável na Steam).")
    return style.save(fig, "02c_ciclo_de_vida")


# ---------------------------------------------------------------------------
# 3. Queda: variação mês a mês e retenção
# ---------------------------------------------------------------------------
def fig_decline(players: pd.DataFrame):
    arc = players[players["appid"] == ARC_RAIDERS].sort_values("month").reset_index(drop=True)
    arc["mom"] = arc["avg_players"].pct_change() * 100
    fig, ax = plt.subplots(figsize=(12, 5.2))
    s = arc.dropna(subset=["mom"])
    colors = [style.SLOTS[0] if v >= 0 else style.SLOTS[7] for v in s["mom"]]
    x = np.arange(len(s))
    ax.bar(x, s["mom"], width=0.55, color=colors)
    for xi, v in zip(x, s["mom"]):
        ax.text(xi, v + (1.2 if v >= 0 else -1.2), f"{v:+.0f}%", ha="center", va="bottom" if v >= 0 else "top",
                fontsize=9, color=style.INK_2)
    ax.axhline(0, color=style.AXIS, lw=1)
    ax.set_xticks(x, [month_label(m) for m in s["month"]])
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:.0f}%"))
    ax.set_ylim(s["mom"].min() - 10, max(s["mom"].max(), 0) + 10)
    ax.set_title("ARC Raiders: variação da média de jogadores em relação ao mês anterior")
    style.subtitle(ax, "Única alta em jan/2026 (Headwinds + recorde de 960 mil em todas as plataformas); três quedas acima de 30% entre mar e jun/2026")
    style.source_note(fig, "Fonte: SteamCharts [O], só Steam. Azul = alta, vermelho = queda. Set/2026 parcial (últimos 30 dias).")
    p1 = style.save(fig, "03a_queda_mes_a_mes")

    # Retenção medida diretamente (sem ajuste de curva): o ajuste exponencial distorce
    # jogos que desabam em 1-2 meses e depois estabilizam num patamar baixo.
    d = lifecycle_index(players)
    rows = []
    for appid, g in d.groupby("appid"):
        g = g.sort_values("m")
        best_m = g.loc[g["m"] <= 3].sort_values("idx").iloc[-1]["m"]
        after = g[g["m"] > best_m]
        below = after[after["idx"] < 50]
        rows.append({
            "game": g["game"].iloc[0],
            "meses_ate_metade": float(below["m"].iloc[0] - best_m) if len(below) else np.nan,
            "retencao_mes6": g.loc[g["m"] == 6, "idx"].squeeze() if (g["m"] == 6).any() else np.nan,
            "retencao_mes10": g.loc[g["m"] == 10, "idx"].squeeze() if (g["m"] == 10).any() else np.nan,
        })
    ret = pd.DataFrame(rows)
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.8))
    panels = [("meses_ate_metade", "Meses até a média cair à metade", lambda v: f"{v:.0f}"),
              ("retencao_mes10", "Média no 10º mês, em % do melhor mês da estreia", lambda v: f"{v:.0f}%")]
    for ax, (col, title, fmt) in zip(axes, panels):
        t = ret.dropna(subset=[col]).sort_values(col)
        y = np.arange(len(t))
        ax.barh(y, t[col], height=0.6, color=[style.ARC if g == "ARC Raiders" else style.CONTEXT_GRAY for g in t["game"]])
        for yi, v in zip(y, t[col]):
            ax.text(v, yi, "  " + fmt(v), va="center", fontsize=9, color=style.INK_2)
        ax.set_yticks(y, t["game"])
        ax.grid(axis="y", visible=False)
        ax.grid(axis="x", visible=True)
        ax.set_xlim(0, t[col].max() * 1.2)
        ax.set_title(title, fontsize=11)
    fig.tight_layout(rect=(0, 0, 1, 0.88), w_pad=4)
    fig.text(0.01, 0.985, "Retenção no primeiro ano: ARC Raiders x estreias comparáveis", fontsize=14, fontweight="bold", va="top")
    fig.text(0.01, 0.935, "O ARC Raiders segurou o público por mais tempo que a maioria, mas chegou ao 10º mês com uma das menores retenções",
             color=style.INK_2, fontsize=10, va="top")
    style.source_note(fig, "Fonte: SteamCharts [O]. Melhor mês = maior média entre os meses 0 e 3 na Steam. "
                           "Delta Force e Rainbow Six Siege nunca caíram à metade no primeiro ano. "
                           "Marathon (7 meses na Steam) só aparece no painel da esquerda.")
    p2 = style.save(fig, "03b_retencao")
    METRICS["retencao"] = ret.set_index("game").round(1).to_dict(orient="index")
    METRICS["queda_mes_a_mes_pct"] = {month_label(m): round(v, 1) for m, v in zip(s["month"], s["mom"])}
    return p1, p2


# ---------------------------------------------------------------------------
# 4. Lista de desejos -> vendas (cenários)
# ---------------------------------------------------------------------------
def fig_wishlist(reviews: pd.DataFrame):
    st = pd.read_csv(sorted(RAW.glob("sensortower_vgi_quickstats_*.csv"))[-1]).set_index("game")
    summary = pd.read_csv(sorted(RAW.glob("steam_reviews_summary_*.csv"))[-1]).set_index("game")
    units_per_review = st.loc["ARC Raiders", "units_sold"] / summary.loc["ARC Raiders", "total_reviews"]

    launch = pd.Timestamp("2025-10-30")
    first30 = (reviews["created"] < launch + pd.Timedelta(days=30)).sum()
    through_dec = (reviews["created"] < "2026-01-01").sum()
    steam_30d = first30 * units_per_review
    # Conferência: vendas na Steam até dez/2025 pelo método x oficial (10,9 mi em todas as plataformas x ~49% Steam)
    steam_dec_method = through_dec * units_per_review
    steam_dec_official = 10.9e6 * 0.486

    scenarios = {"2,5 mi (ago/2025, relato em rede social)": 2.5e6, "3,5 mi (hipótese)": 3.5e6, "5 mi (hipótese)": 5.0e6}
    conv = {k: steam_30d / v * 100 for k, v in scenarios.items()}
    bench = {"10% piores": 6, "Mediana": 27, "10% melhores": 134}

    fig, ax = plt.subplots(figsize=(12, 4.8))
    names = list(conv)[::-1]
    y = np.arange(len(names))
    ax.barh(y, [conv[n] for n in names], height=0.36, color=style.ARC)
    for yi, n in zip(y, names):
        ax.text(conv[n], yi, f"  {conv[n]:.0f}%", va="center", fontsize=9.5, color=style.INK)
    for (label, v), y_text in zip(bench.items(), [-0.74, -0.52, -0.52]):
        ax.axvline(v, color=style.INK_2, lw=1, zorder=0)
        ax.text(v, y_text, f" Steam, {label.lower()}: {v}%", color=style.INK_2, fontsize=8.5, va="center")
    ax.set_ylim(-0.85, len(names) - 0.5)
    ax.set_yticks(y, [f"Lista de desejos = {n}" for n in names])
    ax.grid(axis="y", visible=False)
    ax.grid(axis="x", visible=True)
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:.0f}%"))
    ax.set_xlim(0, max(max(conv.values()), 134) * 1.15)
    ax.set_title("Vendas na Steam nos primeiros 30 dias, em % da lista de desejos no lançamento")
    br = lambda v, d=1: f"{v:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    style.subtitle(ax, f"Vendas estimadas: {br(steam_30d / 1e6)} mi. Em qualquer cenário plausível, "
                       "o ARC Raiders converteu muito acima da mediana da Steam")
    style.source_note(fig, f"Vendas estimadas [E] = análises nos 30 primeiros dias ({br(first30, 0)}) x {br(units_per_review)} unidades por análise "
                           "(Sensor Tower: 8,7 mi unidades / 416,9 mil análises). Conferência: o método dá 5,35 mi até dez/2025; "
                           "o oficial (10,9 mi x 49% na Steam) dá 5,30 mi.\n"
                           "Referência: Gamalytic, ~700 jogos da Steam, 2023-2025 [G]. O número de desejos no lançamento não é público: "
                           "os cenários cobrem a faixa plausível.")
    path = style.save(fig, "04_lista_de_desejos_conversao")
    METRICS["lista_de_desejos"] = {
        "unidades_por_analise": round(units_per_review, 2), "analises_30d": int(first30),
        "vendas_steam_30d_estimadas": round(steam_30d), "conversao_por_cenario_pct": {k: round(v, 1) for k, v in conv.items()},
        "conferencia_vendas_steam_ate_dez25": {"metodo_analises": round(steam_dec_method), "oficial_x_participacao_steam": round(steam_dec_official)},
    }
    return path


# ---------------------------------------------------------------------------
# 5. Efeito de atualizações e patches (estudo de evento)
# ---------------------------------------------------------------------------
def event_effect(daily: pd.Series, date: pd.Timestamp, pre=28, window=7) -> float | None:
    """Variação (%) da média de 7 dias após o evento contra a tendência dos 28 dias anteriores.

    A tendência é um ajuste log-linear (queda exponencial) projetado para a semana do
    evento, então o efeito mede o que o evento mudou além do declínio que já vinha.
    Janelas de 7 dias neutralizam o efeito do fim de semana.
    """
    before = daily[(daily.index >= date - pd.Timedelta(days=pre)) & (daily.index < date)]
    after = daily[(daily.index >= date) & (daily.index < date + pd.Timedelta(days=window))]
    if len(before) < pre - 3 or len(after) < window:
        return None
    t = (before.index - date).days.values
    slope, intercept = np.polyfit(t, np.log(before.values), 1)
    expected = np.exp(intercept + slope * (after.index - date).days.values)
    return (after.values.mean() / expected.mean() - 1) * 100


def fig_events():
    daily = pd.read_csv(INTERIM / "arc_players_daily.csv", parse_dates=["date"]).set_index("date")["peak_players"]
    events = pd.read_csv(INTERIM / "arc_events.csv", parse_dates=["date"])
    events = events[events["date"] >= "2025-11-01"]
    major = events[events["kind"] == "major_update"].copy()
    balance = events[(events["kind"] == "live_update") & (events["n_balance"] > 0)].copy()
    for df in (major, balance):
        df["effect"] = [event_effect(daily, d) for d in df["date"]]

    fig, ax = plt.subplots(figsize=(13, 5.8))
    ax.plot(daily.index, daily.values, color=style.ARC, lw=1.6)
    for _, e in major.iterrows():
        ax.axvline(e["date"], color=style.AXIS, lw=1, zorder=0)
        name = e["title"].split(" - ")[0].split(" Patch")[0].title()
        ax.text(e["date"], daily.max() * 1.02, f" {name}", rotation=90, va="bottom", ha="center", fontsize=8, color=style.INK_2)
    for label, when in {"Anúncio: 2 grandes atualizações/ano": "2026-05-13"}.items():
        ax.axvline(pd.Timestamp(when), color=style.SLOTS[7], lw=1.2, zorder=0)
        ax.text(pd.Timestamp(when), daily.max() * 0.6, f" {label}", fontsize=8.5, color=style.INK_2)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(style.thousands))
    ticks = pd.date_range("2025-11-01", "2026-09-01", freq="MS")
    ax.set_xticks(ticks, [month_label(t) for t in ticks])
    ax.set_ylim(0, daily.max() * 1.28)
    ax.set_title("ARC Raiders: pico diário de jogadores na Steam e atualizações de conteúdo")
    style.subtitle(ax, "Cinza: atualizações de conteúdo com nome. Vermelho: anúncio da nova cadência. Depois de abril, nenhuma atualização de conteúdo")
    style.source_note(fig, "Fontes: SteamDB [O] (exportado pelo usuário) e anúncios oficiais na Steam [O].")
    p1 = style.save(fig, "05a_atualizacoes_linha_do_tempo")

    both = pd.concat([major.assign(tipo="Atualização de conteúdo"), balance.assign(tipo="Patch com balanceamento")]).dropna(subset=["effect"])
    both = both.sort_values("date")
    fig, ax = plt.subplots(figsize=(12, 6))
    colors = {"Atualização de conteúdo": style.SLOTS[0], "Patch com balanceamento": style.SLOTS[1]}
    y = np.arange(len(both))
    for yi, (_, e) in zip(y, both.iterrows()):
        ax.plot([0, e["effect"]], [yi, yi], color=style.GRID, lw=2, zorder=1)
        ax.plot(e["effect"], yi, "o", ms=9, color=colors[e["tipo"]], mec=style.SURFACE, mew=2, zorder=3)
        ax.text(e["effect"] + (1.2 if e["effect"] >= 0 else -1.2), yi, f"{e['effect']:+.0f}%",
                va="center", ha="left" if e["effect"] >= 0 else "right", fontsize=8.5, color=style.INK_2)
    ax.axvline(0, color=style.AXIS, lw=1)
    def short(title):
        name = title.split(" - ")[0].replace("Patch Notes ", "Patch ").strip()
        return name.title() if name.isupper() else name
    labels = [f"{e['date']:%d/%m/%y}  {short(e['title'])}" for _, e in both.iterrows()]
    ax.set_yticks(y, labels, fontsize=8.5)
    ax.invert_yaxis()
    ax.grid(axis="y", visible=False)
    ax.grid(axis="x", visible=True)
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:+.0f}%"))
    lim = both["effect"].abs().max() * 1.35
    ax.set_xlim(-lim, lim)
    for tipo, c in colors.items():
        ax.plot([], [], "o", ms=8, color=c, label=tipo)
    ax.legend(loc="lower right")
    ax.set_title("Efeito de cada atualização sobre o número de jogadores")
    style.subtitle(ax, "Pico diário médio na semana do lançamento da atualização, contra a tendência de queda dos 28 dias anteriores")
    style.source_note(fig, "Fonte: SteamDB [O]. Estudo de evento: tendência log-linear dos 28 dias anteriores projetada para os 7 dias seguintes. "
                           "Patch com balanceamento = live update com ajustes de dano/nerf/buff nas notas oficiais.")
    p2 = style.save(fig, "05b_efeito_atualizacoes")
    METRICS["efeito_eventos_pct"] = {f"{e['date']:%Y-%m-%d} {e['title']}": round(e["effect"], 1) for _, e in both.iterrows()}
    METRICS["efeito_medio_pct"] = both.groupby("tipo")["effect"].agg(["mean", "median", "count"]).round(1).to_dict(orient="index")
    return p1, p2


# ---------------------------------------------------------------------------
# 6. Hype x jogadores: Twitch contra Steam
# ---------------------------------------------------------------------------
def fig_twitch_vs_players(players: pd.DataFrame):
    arc = players[players["appid"] == ARC_RAIDERS].set_index("month")["avg_players"]
    tw = pd.read_csv(INTERIM / "twitch_monthly.csv", parse_dates=["month"])
    tw = tw[tw["game"] == "arc_raiders"].set_index("month")["avg_viewers"]
    both = pd.concat([arc.rename("jogadores"), tw.rename("espectadores")], axis=1, sort=True).dropna()
    idx = both / both.iloc[0] * 100
    fig, ax = plt.subplots(figsize=(12, 5.5))
    series = {"Jogadores na Steam (média mensal)": ("jogadores", style.SLOTS[0]),
              "Espectadores na Twitch (média mensal)": ("espectadores", style.SLOTS[1])}
    labels = []
    for name, (col, color) in series.items():
        ax.plot(idx.index, idx[col], color=color, marker="o", ms=5, mec=style.SURFACE, mew=1.5)
        labels.append((idx.index[-1], idx[col].iloc[-1], f"{name.split(' (')[0]}  {idx[col].iloc[-1]:.0f}", False))
    style.end_labels(ax, labels, x_text=idx.index[-1] + pd.Timedelta(days=20), min_gap=4)
    ax.axhline(100, color=style.AXIS, lw=1)
    ax.set_xlim(idx.index[0] - pd.Timedelta(days=10), idx.index[-1] + pd.Timedelta(days=10))
    ax.set_xticks(idx.index, [month_label(t) for t in idx.index])
    ax.legend(list(series), loc="upper right")
    ax.set_title("Hype e base de jogadores: Twitch x Steam, índice nov/2025 = 100")
    style.subtitle(ax, "A audiência na Twitch caiu antes e mais rápido que o número de jogadores: o hype saiu na frente")
    style.source_note(fig, "Fontes: SteamCharts [O] e TwitchTracker [O]. Set/2026 parcial nas duas fontes.")
    path = style.save(fig, "06_twitch_x_jogadores")
    METRICS["twitch_x_jogadores_indice_set26"] = idx.iloc[-1].round(1).to_dict()
    return path


# ---------------------------------------------------------------------------
# 7. Perfil dos jogadores
# ---------------------------------------------------------------------------
LANG_REGION = {"english": "Inglês (global)", "russian": "Russo", "german": "Alemão", "brazilian": "Português (BR)",
               "french": "Francês", "spanish": "Espanhol (Espanha)", "latam": "Espanhol (América Latina)", "turkish": "Turco",
               "polish": "Polonês", "schinese": "Chinês simplificado", "italian": "Italiano", "koreana": "Coreano",
               "ukrainian": "Ucraniano", "japanese": "Japonês"}


def fig_profile(reviews: pd.DataFrame):
    fig, axes = plt.subplots(2, 2, figsize=(13, 9.5))

    # Idioma das análises (indicador de região)
    ax = axes[0, 0]
    lang = reviews["language"].value_counts(normalize=True) * 100
    top = lang.head(10)
    top = pd.concat([top, pd.Series({"other": lang.iloc[10:].sum()})]).iloc[::-1]
    names = [LANG_REGION.get(k, "Outros idiomas") if k != "other" else "Outros idiomas" for k in top.index]
    y = np.arange(len(top))
    ax.barh(y, top.values, height=0.6, color=style.ARC)
    for yi, v in zip(y, top.values):
        ax.text(v, yi, f"  {v:.1f}%".replace(".", ","), va="center", fontsize=8.5, color=style.INK_2)
    ax.set_yticks(y, names, fontsize=9)
    ax.grid(axis="y", visible=False)
    ax.grid(axis="x", visible=True)
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:.0f}%"))
    ax.set_xlim(0, top.max() * 1.2)
    ax.set_title("Idioma das análises na Steam (indicador de região) [O]", fontsize=11)

    # Plataforma
    ax = axes[0, 1]
    steam, other = 48.6, 51.4
    ax.barh([1, 0], [steam, other], height=0.4, color=[style.ARC, style.CONTEXT_GRAY])
    for yi, v in zip([1, 0], [steam, other]):
        ax.text(v, yi, f"  {v:.0f}%", va="center", fontsize=10, color=style.INK)
    ax.set_yticks([1, 0], ["PC (Steam)", "Consoles e outras lojas"])
    ax.set_xlim(0, 70)
    ax.grid(axis="y", visible=False)
    ax.grid(axis="x", visible=True)
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:.0f}%"))
    ax.set_title("Plataforma: participação no pico de jan/2026 [O derivado]", fontsize=11)
    ax.text(0, -0.75, "Pico na Steam (466 mil, SteamDB) / pico em todas as plataformas (960 mil, Nexon)", fontsize=8.5, color=style.MUTED)

    # Estilo de jogo (Embark)
    ax = axes[1, 0]
    styles = [("Cooperativos (evitam PvP)", 37, style.SLOTS[2]), ("Mistos", 27, style.SLOTS[3]), ("Só PvP", 34, style.SLOTS[1])]
    left = 0
    for name, v, c in styles:
        ax.barh(0, v, left=left, height=0.45, color=c, edgecolor=style.SURFACE, linewidth=2)
        ax.text(left + v / 2, 0, f"{v}%", ha="center", va="center", fontsize=11, color=style.INK, fontweight="bold")
        ax.text(left + v / 2, -0.42, name, ha="center", va="top", fontsize=9, color=style.INK_2)
        left += v
    ax.set_xlim(0, 100)
    ax.set_ylim(-0.9, 0.5)
    ax.axis("off")
    ax.set_title("Estilo de jogo dos jogadores (Embark, set/2026) [O]", fontsize=11)
    ax.text(0, -0.85, "51% dos pesquisados querem um modo PvE dedicado. Grupo cooperativo cresce desde o lançamento.",
            fontsize=8.5, color=style.MUTED)

    # Horas jogadas
    ax = axes[1, 1]
    hours = (reviews["playtime_forever_min"] / 60).clip(upper=(reviews["playtime_forever_min"] / 60).quantile(0.999))
    bins = [0, 10, 25, 50, 100, 200, 400, 800, 10_000]
    labels = ["<10", "10-25", "25-50", "50-100", "100-200", "200-400", "400-800", "800+"]
    share = pd.cut(hours, bins=bins, labels=labels, right=False).value_counts(normalize=True).reindex(labels) * 100
    x = np.arange(len(share))
    ax.bar(x, share.values, width=0.6, color=style.ARC)
    for xi, v in zip(x, share.values):
        ax.text(xi, v, f"{v:.0f}%", ha="center", va="bottom", fontsize=8.5, color=style.INK_2)
    ax.set_xticks(x, labels, fontsize=8.5)
    ax.set_xlabel("Horas jogadas no total")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:.0f}%"))
    ax.set_title("Horas jogadas por quem avaliou o jogo [O]", fontsize=11)
    med = hours.median()
    ax.text(0, -0.28, f"Mediana: {med:.0f} horas. Só {(reviews['playtime_2weeks_min'] > 0).mean() * 100:.0f}% jogaram nas duas semanas antes da coleta.",
            transform=ax.transAxes, fontsize=8.5, color=style.MUTED)

    fig.tight_layout(rect=(0, 0, 1, 0.91), h_pad=4, w_pad=4)
    fig.text(0.01, 0.985, "Quem joga ARC Raiders", fontsize=15, fontweight="bold", va="top")
    fig.text(0.01, 0.95, "Idade e gênero não são públicos: referências do gênero de tiro estão no README (Quantic Foundry, ESA)",
             color=style.INK_2, fontsize=10, va="top")
    style.source_note(fig, "Fontes: análises da Steam (416,8 mil) [O]; SteamDB e Nexon [O]; Embark, publicação de 24/09/2026 [O].")
    path = style.save(fig, "07_perfil_jogadores")
    METRICS["perfil"] = {"idiomas_pct": lang.head(12).round(2).to_dict(), "horas_mediana": round(med, 1),
                         "horas_faixas_pct": share.round(1).to_dict(),
                         "ativos_2_semanas_pct": round((reviews["playtime_2weeks_min"] > 0).mean() * 100, 1)}
    return path


def main():
    style.apply()
    players = load_players()
    reviews = pd.read_parquet(INTERIM / "arc_reviews.parquet",
                              columns=["created", "language", "voted_up", "playtime_forever_min", "playtime_2weeks_min"])
    paths = [fig_positioning(players), *fig_monthly(players), fig_lifecycle(players), *fig_decline(players),
             fig_wishlist(reviews), *fig_events(), fig_twitch_vs_players(players), fig_profile(reviews)]
    REPORTS.mkdir(exist_ok=True)
    (REPORTS / "metrics_diagnostico.json").write_text(json.dumps(METRICS, ensure_ascii=False, indent=2), encoding="utf-8")
    for p in paths:
        print("figura:", p.name)
    print(json.dumps(METRICS, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
