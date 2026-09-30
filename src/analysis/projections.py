"""Etapa 8: projeções de jogadores e receita, out/2026 a dez/2027.

Cenários (acumulativos):
  S0  Sem ação          queda mensal contínua, sem grandes atualizações
  S1  Atualizações      grandes atualizações a cada 6 meses: Frozen Trail (out/26), abr/27, out/27
  S2  + Modo PvE        S1 + modo PvE permanente a partir da atualização de abr/27
  S3  + Skins de armas  S2 + Weapon Stencils (a partir de out/26), só efeito em receita

Duas variantes de premissas (faixas uniformes, 10 mil simulações cada):
  base        retenção calibrada nos comparáveis (mediana de 68% em 45 eventos) e queda
              mensal que desacelera 15% ao mês até um piso de 3% (comparáveis se
              estabilizam; o próprio ARC Raiders foi de -20% a -11% entre jul e set/26)
  pessimista  premissas propostas inicialmente: retenção de 20-45% e queda constante
Unidade de jogadores: média mensal de jogadores simultâneos na Steam (a mesma de todo o
projeto); todas as plataformas = Steam x 2,06 (pico de jan/26: 960 mil / 466 mil).

Uso: python src/analysis/projections.py
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
from config import INTERIM, RAW, ROOT  # noqa: E402
from viz import style  # noqa: E402

N_SIM = 10_000
RNG = np.random.default_rng(7)
MONTHS = pd.date_range("2026-10-01", "2027-12-01", freq="MS")
UPDATES = [pd.Timestamp("2026-10-01"), pd.Timestamp("2027-04-01"), pd.Timestamp("2027-10-01")]
PVE_START = pd.Timestamp("2027-04-01")
P0 = 20_730  # média de jogadores na Steam, últimos 30 dias até 25/09/2026 (SteamCharts)
ALL_PLATFORMS = 960_000 / 466_372
VETERAN_POOL = 0.30 * 264_430  # grupo "veteranos que abandonaram" (Etapa 6) x média de nov/25
Q3_PLAYER_MONTHS = (28_661.58 + 23_216.75 + 20_730.13)  # soma das médias de jul-set/26
METRICS: dict = {}

ASSUMPTIONS = {
    # nome: (mín, máx, etiqueta, descrição)
    "decline":        (0.10, 0.20, "P", "queda mensal sem novidade (jul-set/26: -20%, -19%, -11%)"),
    "bump":           (0.40, 1.50, "G", "alta de jogadores no mês de grande atualização"),
    "retained":       (0.45, 0.90, "G", "fração da alta que continua 3 meses depois"),
    "veteran_return": (0.05, 0.15, "P", "veteranos que abandonaram e voltam no Frozen Trail"),
    "pve_launch_bump":(0.10, 0.40, "P", "alta extra de jogadores cooperativos no lançamento do PvE"),
    "pve_adoption":   (0.25, 0.45, "G", "parcela dos jogadores que adota o modo PvE"),
    "pve_retention":  (0.00, 0.25, "G", "redução da queda mensal entre quem joga PvE"),
    "pvp_loss":       (0.00, 0.10, "P", "perda única de jogadores só-PvP quando o PvE chega"),
    "skin_conversion":(0.05, 0.15, "G", "jogadores ativos no mês que compram skins"),
    "skin_spend":     (5.0, 15.0, "G", "gasto mensal por comprador de skins (US$)"),
    "skin_loss":      (0.10, 0.40, "P", "desconto na conversão por skins serem perdidas ao morrer"),
    "mau_ratio":      (20.0, 30.0, "P", "jogadores ativos no mês por jogador simultâneo médio (Nexon: 6 mi semanais ≈ 17x)"),
    "store_rate":     (0.7, 1.3, "E", "gasto na loja por jogador-mês, fator sobre o 3º tri/26"),
    "net_per_unit":   (21.0, 32.0, "E", "receita líquida por unidade vendida (US$)"),
}


VARIANTS = {
    "base": {"decline_slowdown": 0.15, "decline_floor": 0.03, "overrides": {}},
    "pessimista": {"decline_slowdown": 0.0, "decline_floor": 0.0, "overrides": {"retained": (0.20, 0.45)}},
}


def draw(variant: str = "base", seed: int = 7) -> dict:
    rng = np.random.default_rng(seed)
    ranges = {k: v[:2] for k, v in ASSUMPTIONS.items()} | VARIANTS[variant]["overrides"]
    a = {k: rng.uniform(lo, hi, N_SIM) for k, (lo, hi) in ranges.items()}
    a["quality"] = rng.uniform(0.8, 1.2, (N_SIM, len(UPDATES)))  # variação entre atualizações
    v = VARIANTS[variant]
    t = np.arange(len(MONTHS))
    slowed = a["decline"][:, None] * (1 - v["decline_slowdown"]) ** t
    a["decline_t"] = np.maximum(slowed, v["decline_floor"]) if v["decline_slowdown"] else np.repeat(a["decline"][:, None], len(MONTHS), 1)
    return a


# ---------------------------------------------------------------------------
# Calibração com jogos comparáveis
# ---------------------------------------------------------------------------
COMPARABLES = ["HELLDIVERS 2", "Hunt: Showdown 1896", "Dark and Darker", "Gray Zone Warfare", "No Man's Sky", "The Cycle: Frontier"]


def calibration() -> pd.DataFrame:
    p = pd.read_csv(INTERIM / "players_monthly.csv", parse_dates=["month"])
    p = p[~p["partial_month"] & p["game"].isin(COMPARABLES) & (p["month"] >= "2019-01-01")]
    rows = []
    for game, g in p.groupby("game"):
        g = g.sort_values("month").reset_index(drop=True)
        prev_bump = False
        for i in range(1, len(g) - 3):
            pre, cur = g["avg_players"][i - 1], g["avg_players"][i]
            is_bump = cur / pre - 1 >= 0.20 and pre > 1000 and i >= 6
            if is_bump and not prev_bump:
                rows.append({"game": game, "month": g["month"][i], "bump": cur / pre - 1,
                             "after3_vs_pre": g["avg_players"][i + 3] / pre - 1,
                             "retained": (g["avg_players"][i + 3] - pre) / (cur - pre)})
            prev_bump = is_bump
    ev = pd.DataFrame(rows)
    METRICS["calibracao"] = {
        "eventos": len(ev),
        "alta_mediana": round(ev["bump"].median(), 3), "alta_p25_p75": ev["bump"].quantile([.25, .75]).round(3).tolist(),
        "retido_mediano": round(ev["retained"].clip(-1, 2).median(), 3),
        "retido_p25_p75": ev["retained"].clip(-1, 2).quantile([.25, .75]).round(3).tolist(),
        "nivel_3m_vs_antes_mediano": round(ev["after3_vs_pre"].median(), 3),
    }
    return ev


def fig_calibration(ev: pd.DataFrame):
    fig, axes = plt.subplots(1, 2, figsize=(14, 5.6), gridspec_kw={"width_ratios": [1, 1.25]})
    ax = axes[0]
    games = ev.groupby("game")["bump"].median().sort_values().index
    for yi, g in enumerate(games):
        vals = ev[ev["game"] == g]["bump"] * 100
        jitter = RNG.uniform(-0.15, 0.15, len(vals))
        ax.scatter(vals.clip(upper=400), yi + jitter, s=40, color=style.CONTEXT_GRAY, edgecolor=style.SURFACE, linewidth=1.5, zorder=3)
        ax.plot(vals.median(), yi, "|", ms=18, mew=2.5, color=style.INK)
    lo, hi = ASSUMPTIONS["bump"][:2]
    ax.axvspan(lo * 100, hi * 100, color=style.ARC, alpha=0.12, lw=0)
    ax.text((lo + hi) / 2 * 100, -0.45, "faixa usada para o ARC Raiders", ha="center", va="center", fontsize=8, color=style.INK_2)
    ax.set_ylim(-0.7, len(games) - 0.5)
    ax.set_yticks(range(len(games)), games)
    ax.set_xlim(0, 420)
    ax.grid(axis="y", visible=False)
    ax.grid(axis="x", visible=True)
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"+{v:.0f}%"))
    ax.set_title("Alta de jogadores no mês da grande atualização", fontsize=11)
    ax.text(0, -0.16, f"{len(ev)} eventos desde 2019; traço = mediana do jogo; valores acima de +400% no limite do eixo",
            transform=ax.transAxes, fontsize=8.5, color=style.MUTED)

    # Hype: Tarkov na Twitch, com wipes semestrais
    ax = axes[1]
    tw = pd.read_csv(INTERIM / "twitch_monthly.csv", parse_dates=["month"])
    t = tw[(tw["game"] == "escape_from_tarkov") & (tw["month"] >= "2019-06-01") & ~tw["partial_month"]]
    ax.plot(t["month"], t["avg_viewers"], color=style.SLOTS[1], lw=1.8)
    peaks = t[t["avg_viewers"] > t["avg_viewers"].rolling(5, center=True, min_periods=1).median() * 2.2]
    ax.plot(peaks["month"], peaks["avg_viewers"], "o", ms=6, color=style.SLOTS[1], mec=style.SURFACE, mew=1.5)
    gaps = peaks["month"].diff().dt.days.dropna() / 30.4
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(style.thousands))
    ax.set_title("Hype em ciclos: Escape from Tarkov na Twitch (média de espectadores)", fontsize=11)
    ax.text(0, -0.16, f"Pontos = picos de reset (wipe); intervalo mediano entre picos: {gaps.median():.0f} meses",
            transform=ax.transAxes, fontsize=8.5, color=style.MUTED)
    METRICS["tarkov_intervalo_mediano_picos_meses"] = round(float(gaps.median()), 1)
    fig.tight_layout(rect=(0, 0.03, 1, 0.86), w_pad=4)
    fig.text(0.01, 0.985, "Calibração: o que grandes atualizações fazem em jogos comparáveis", fontsize=14, fontweight="bold", va="top")
    fig.text(0.01, 0.93, "Esquerda: meses com alta de 20%+ na média de jogadores (Steam), confirmados nos anúncios oficiais. "
                         "Direita: o ciclo semestral de hype do Tarkov", color=style.INK_2, fontsize=10, va="top")
    style.source_note(fig, "Fontes: SteamCharts, anúncios oficiais na Steam e TwitchTracker [O]. Comparáveis: extraction shooters, Helldivers 2 (PvE) "
                           "e No Man's Sky (recuperação por atualizações).")
    return style.save(fig, "11a_calibracao_atualizacoes")


# ---------------------------------------------------------------------------
# Simulação de jogadores
# ---------------------------------------------------------------------------
def layer_curve(size: np.ndarray, start: int, r: np.ndarray, survival: np.ndarray) -> np.ndarray:
    """Alta que começa no mês `start`: mantém a fração r após 3 meses e depois segue a queda da base."""
    n, T = survival.shape
    out = np.zeros((n, T))
    for j in range(start, T):
        k = j - start
        if k <= 3:
            out[:, j] = size * r ** (k / 3)
        else:
            out[:, j] = size * r * survival[:, j] / survival[:, start + 3]
    return out


def simulate_players(a: dict, updates: bool, pve: bool) -> dict:
    n, T = N_SIM, len(MONTHS)
    d = a["decline_t"]                          # queda mensal (n x T), constante ou desacelerando
    survival = np.cumprod(1 - d, axis=1)
    base = P0 * survival
    layers = np.zeros((n, T))
    if updates:
        for u_idx, u in enumerate(UPDATES):
            j = MONTHS.get_loc(u)
            size = base[:, j] * a["bump"] * a["quality"][:, u_idx]
            if u_idx == 0:
                size = size + a["veteran_return"] * VETERAN_POOL
            layers += layer_curve(size, j, a["retained"], survival)
    total = base + layers
    pve_players = np.zeros((n, T))
    if pve:
        s = MONTHS.get_loc(PVE_START)
        s1_total = total.copy()  # trajetória sem PvE: referência para o crescimento mês a mês
        launch = layer_curve(total[:, s] * a["pve_launch_bump"], s, a["retained"], survival)  # jogadores cooperativos novos/de volta
        share = a["pve_adoption"]
        pve_level = total[:, s] * share
        pvp_level = total[:, s] * (1 - share) * (1 - 0.34 * a["pvp_loss"])  # só-PvP = 34% da base (Embark)
        for j in range(s, T):
            if j > s:
                growth = s1_total[:, j] / np.maximum(s1_total[:, j - 1], 1)  # dinâmica do S1 (inclui altas de atualização)
                d_pve = d[:, j] * (1 - a["pve_retention"])
                pve_level = pve_level * growth * (1 - d_pve) / (1 - d[:, j])
                pvp_level = pvp_level * growth
            pve_players[:, j] = pve_level + launch[:, j]
            total[:, j] = pvp_level + pve_players[:, j]
    return {"total": total, "pve": pve_players}


def revenue(players: np.ndarray, a: dict, skins: bool) -> dict:
    rev = json.loads((ROOT / "reports" / "metrics_receita.json").read_text(encoding="utf-8"))
    store_q3 = rev["q3_26_loja_interna_usd_mi"][1] * 1e6
    units_q3 = rev["q3_26_unidades_mi"][1] * 1e6
    store_per_pm = store_q3 / Q3_PLAYER_MONTHS * a["store_rate"]
    units_per_pm = units_q3 / Q3_PLAYER_MONTHS
    store = players * store_per_pm[:, None]
    units = players * units_per_pm * a["net_per_unit"][:, None]
    skin = np.zeros_like(players)
    if skins:
        mau = players * ALL_PLATFORMS * a["mau_ratio"][:, None]
        skin = mau * (a["skin_conversion"] * a["skin_spend"] * (1 - a["skin_loss"]))[:, None] * 0.7  # 70% líquido das lojas
    return {"store": store, "units": units, "skins": skin}


def run_scenarios(a: dict) -> dict:
    """a vem de draw(variante)."""
    s0 = simulate_players(a, updates=False, pve=False)
    s1 = simulate_players(a, updates=True, pve=False)
    s2 = simulate_players(a, updates=True, pve=True)
    return {
        "S0": {"players": s0["total"], **revenue(s0["total"], a, skins=False)},
        "S1": {"players": s1["total"], **revenue(s1["total"], a, skins=False)},
        "S2": {"players": s2["total"], "pve": s2["pve"], **revenue(s2["total"], a, skins=False)},
        "S3": {"players": s2["total"], "pve": s2["pve"], **revenue(s2["total"], a, skins=True)},
    }


NAMES = {"S0": "Sem ação", "S1": "Atualizações semestrais", "S2": "+ modo PvE", "S3": "+ skins de armas"}


def fig_players(sc: dict, sc_pess: dict):
    fig, ax = plt.subplots(figsize=(12.5, 6.2))
    hist = pd.read_csv(INTERIM / "players_monthly.csv", parse_dates=["month"])
    arc = hist[(hist["appid"] == 1808500) & (hist["month"] >= "2026-04-01")].set_index("month")["avg_players"]
    ax.plot(arc.index, arc.values, color=style.INK, lw=2.2, label="Histórico")
    x = np.r_[arc.index[-1:], MONTHS]
    joined = lambda v: np.r_[arc.values[-1], v]  # noqa: E731
    labels = []
    series = [("S0", sc, style.SLOTS[7], "Sem ação"), ("S1", sc, style.SLOTS[1], "Atualizações semestrais"),
              ("S2", sc, style.SLOTS[0], "Atualizações + PvE"), ("S2", sc_pess, style.CONTEXT_GRAY, "Atualizações + PvE (pessimista)")]
    for key, source, color, name in series:
        p = source[key]["players"]
        med = np.median(p, 0)
        if name in ("Sem ação", "Atualizações + PvE"):
            ax.fill_between(x, joined(np.percentile(p, 10, 0)), joined(np.percentile(p, 90, 0)), color=color, alpha=0.10, lw=0)
        ax.plot(x, joined(med), color=color, lw=2.4 if name == "Atualizações + PvE" else 1.8, label=name)
        labels.append((MONTHS[-1], med[-1], f"{name}  {style.thousands(med[-1])}", name == "Atualizações + PvE"))
    style.end_labels(ax, labels, x_text=MONTHS[-1] + pd.Timedelta(days=25), min_gap=4500)
    top = float(np.percentile(sc["S2"]["players"], 90, 0).max()) * 1.1
    for u, text in zip(UPDATES, ["Frozen Trail", "atualização + PvE", "atualização"]):
        ax.axvline(u, color=style.AXIS, lw=1, zorder=0)
        ax.text(u, top * 0.98, f" {text}", fontsize=8.5, color=style.INK_2, va="top")
    ax.axhline(P0, color=style.GRID, lw=1, zorder=0)
    ax.text(pd.Timestamp("2026-04-05"), P0, "nível de set/2026", fontsize=8, color=style.MUTED, va="bottom")
    ax.set_xlim(pd.Timestamp("2026-04-01"), MONTHS[-1] + pd.Timedelta(days=10))
    ax.set_ylim(0, top)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(style.thousands))
    ticks = pd.date_range("2026-04-01", "2027-12-01", freq="2MS")
    ax.set_xticks(ticks, [month_label(t) for t in ticks])
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.08), fontsize=8.5, ncols=5, frameon=False)
    ax.set_title("Projeção de jogadores (média mensal na Steam) até dez/2027")
    style.subtitle(ax, "Mediana de 10 mil simulações por cenário; faixas de 80% nos cenários extremos. Valor à direita = dez/2027")
    style.source_note(fig, "Cenário base: retenção calibrada nos comparáveis e queda que desacelera; pessimista: premissas iniciais. "
                           "Todas as plataformas ≈ Steam x 2,06. Skins não mudam o número de jogadores.")
    return style.save(fig, "11b_projecao_jogadores")


def fig_pve(sc: dict):
    total, pve = np.median(sc["S2"]["players"], 0), np.median(sc["S2"]["pve"], 0)
    fig, ax = plt.subplots(figsize=(12.5, 5.2))
    x = np.arange(len(MONTHS))
    ax.bar(x, total - pve, width=0.62, color=style.SLOTS[1], label="PvPvE (modo atual)")
    ax.bar(x, pve, width=0.62, bottom=total - pve, color=style.SLOTS[2], label="Modo PvE", edgecolor=style.SURFACE, linewidth=2)
    for xi, (t, p) in enumerate(zip(total, pve)):
        if p > 0:
            ax.text(xi, t, f"{p / t * 100:.0f}%", ha="center", va="bottom", fontsize=8.5, color=style.INK_2)
    s1 = np.median(sc["S1"]["players"], 0)
    ax.plot(x, s1, color=style.INK_2, lw=1.6, marker="o", ms=4, label="Mesmo cenário sem PvE (S1)")
    ax.set_xticks(x, [month_label(m) for m in MONTHS], fontsize=8.5)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(style.thousands))
    ax.set_ylim(0, total.max() * 1.25)
    ax.legend(loc="upper center", ncols=3, fontsize=9)
    ax.set_title("Modo PvE: composição da base projetada (mediana, cenário S2)")
    style.subtitle(ax, "Rótulo = parcela no modo PvE. O ganho vem sobretudo de jogadores cooperativos que voltam ou chegam no lançamento do modo")
    style.source_note(fig, "Premissas: adoção de 25-45% (Embark: 37% cooperativos, 51% interessados) [G]; alta de 10-40% no lançamento [P]; queda mensal 0-25% menor "
                           "entre quem joga PvE [G]; perda única de 0-10% dos só-PvP [P]. Modo PvE permanente a partir de abr/2027 [P].")
    return style.save(fig, "11c_projecao_pve")


def totals(sc: dict, year=2027) -> pd.DataFrame:
    mask = MONTHS.year == year
    rows = []
    for key, s in sc.items():
        parts = {k: s[k][:, mask].sum(1) / 1e6 for k in ("units", "store", "skins")}
        tot = sum(parts.values())
        rows.append({"cenario": key, "nome": NAMES[key],
                     **{f"{k}_med": float(np.median(v)) for k, v in parts.items()},
                     "total_p10": float(np.percentile(tot, 10)), "total_med": float(np.median(tot)), "total_p90": float(np.percentile(tot, 90)),
                     "jogadores_media_2027": float(np.median(s["players"][:, mask].mean(1))),
                     "jogadores_dez27": float(np.median(s["players"][:, -1])),
                     "prob_dez27_acima_set26": float((s["players"][:, -1] > P0).mean())})
    return pd.DataFrame(rows)


def fig_revenue(t: pd.DataFrame, t_pess: pd.DataFrame):
    fig, ax = plt.subplots(figsize=(12.5, 5.8))
    x = np.arange(len(t))
    w = 0.34
    parts = [("units_med", "Vendas do jogo", style.SLOTS[0]), ("store_med", "Loja interna", style.SLOTS[2]),
             ("skins_med", "Skins de armas", style.SLOTS[3])]
    bottom = np.zeros(len(t))
    for col, label, c in parts:
        ax.bar(x - w / 2 - 0.02, t[col], width=w, bottom=bottom, color=c, label=f"{label} (base)", edgecolor=style.SURFACE, linewidth=2)
        bottom += t[col].values
    ax.bar(x + w / 2 + 0.02, t_pess["total_med"], width=w, color=style.CONTEXT_GRAY, label="Total (pessimista)")
    for df, dx in ((t, -w / 2 - 0.02), (t_pess, w / 2 + 0.02)):
        ax.errorbar(x + dx, df["total_med"], yerr=[df["total_med"] - df["total_p10"], df["total_p90"] - df["total_med"]],
                    fmt="none", ecolor=style.INK_2, elinewidth=1.2, capsize=4)
        for xi, r in df.iterrows():
            ax.text(xi + dx, r["total_p90"], f"{r['total_med']:.0f}", ha="center", va="bottom", fontsize=9, color=style.INK)
    ax.set_xticks(x, t["nome"])
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"US$ {v:.0f} mi"))
    ax.legend(loc="upper left", fontsize=8.5)
    ax.set_title("Receita projetada para 2027 por cenário (US$ milhões)")
    style.subtitle(ax, "Barra colorida = cenário base, por fonte; cinza = pessimista. Número = mediana; linha = faixa de 80% (10 mil simulações)")
    style.source_note(fig, "Receita econômica líquida das lojas [E/P]. Loja e vendas do jogo proporcionais aos jogadores, calibradas no 3º tri/2026 (Etapa 7). "
                           "Não inclui custos de desenvolvimento (Etapa 9).")
    return style.save(fig, "11d_receita_2027_cenarios")


def fig_tornado(sc: dict, a: dict):
    mask = MONTHS.year == 2027
    s = sc["S3"]
    tot = sum(s[k][:, mask].sum(1) for k in ("units", "store", "skins")) / 1e6
    base = np.median(tot)
    rows = []
    for k, (lo, hi, tag, desc) in ASSUMPTIONS.items():
        v = a[k]
        rows.append((f"{desc[:58]} [{tag}]", np.median(tot[v <= np.percentile(v, 10)]) - base, np.median(tot[v >= np.percentile(v, 90)]) - base))
    rows = sorted(rows, key=lambda r: abs(r[2] - r[1]))[-9:]
    fig, ax = plt.subplots(figsize=(12.5, 5.8))
    y = np.arange(len(rows))
    for yi, (label, lo, hi) in zip(y, rows):
        ax.barh(yi, lo, height=0.5, color=style.SLOTS[7])
        ax.barh(yi, hi, height=0.5, color=style.SLOTS[0])
        for v in (lo, hi):
            ax.text(v, yi, f"  {v:+.0f}  ", ha="left" if v >= 0 else "right", va="center", fontsize=8.5, color=style.INK_2)
    ax.axvline(0, color=style.INK_2, lw=1)
    ax.set_yticks(y, [r[0] for r in rows], fontsize=8.5)
    ax.grid(axis="y", visible=False)
    ax.grid(axis="x", visible=True)
    lim = max(max(abs(r[1]), abs(r[2])) for r in rows) * 1.35
    ax.set_xlim(-lim, lim)
    ax.set_xlabel("variação na receita de 2027, cenário completo (US$ milhões)")
    ax.set_title("O que mais move a receita de 2027")
    style.subtitle(ax, f"Mediana do cenário completo: US$ {base:.0f} mi. Vermelho = premissa no 10º percentil; azul = no 90º")
    style.source_note(fig, "Sensibilidade sobre 10 mil simulações; as 9 premissas de maior efeito. [G] calibrada em jogos comparáveis; [P] premissa do projeto; [E] estimativa.")
    return style.save(fig, "11e_sensibilidade_2027")


def main():
    style.apply()
    ev = calibration()
    a = draw("base")
    sc = run_scenarios(a)
    sc_pess = run_scenarios(draw("pessimista"))
    t, t_pess = totals(sc), totals(sc_pess)
    t26 = totals(sc, 2026)
    paths = [fig_calibration(ev), fig_players(sc, sc_pess), fig_pve(sc), fig_revenue(t, t_pess), fig_tornado(sc, a)]
    skins_2027 = sc["S3"]["skins"][:, MONTHS.year == 2027].sum(1) / 1e6
    METRICS.update({
        "premissas": {k: {"min": v[0], "max": v[1], "etiqueta": v[2], "descricao": v[3]} for k, v in ASSUMPTIONS.items()},
        "variantes": {k: {kk: (vv if not isinstance(vv, dict) else {a_: list(b_) for a_, b_ in vv.items()}) for kk, vv in v.items()}
                      for k, v in VARIANTS.items()},
        "cenarios_2027": t.round(2).to_dict(orient="records"),
        "cenarios_2027_pessimista": t_pess.round(2).to_dict(orient="records"),
        "cenarios_out_dez_2026": t26.round(2).to_dict(orient="records"),
        "skins_2027_usd_mi": [float(np.percentile(skins_2027, q)) for q in (10, 50, 90)],
        "pve_parcela_dez27_mediana": float(np.median(sc["S2"]["pve"][:, -1] / sc["S2"]["players"][:, -1])),
        "frozen_trail_mes_jogadores_mediana": float(np.median(sc["S1"]["players"][:, 0])),
    })
    (ROOT / "reports" / "metrics_projecoes.json").write_text(json.dumps(METRICS, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    for p in paths:
        print("figura:", p.name)
    print(json.dumps(METRICS["calibracao"], indent=1))
    print(t.round(1).to_string())
    print(t_pess.round(1).to_string())
    print(t26.round(1)[["nome", "total_med", "jogadores_media_2027"]].to_string())
    print("skins 2027:", METRICS["skins_2027_usd_mi"], "| PvE dez/27:", METRICS["pve_parcela_dez27_mediana"],
          "| out/26 S1:", METRICS["frozen_trail_mes_jogadores_mediana"])


if __name__ == "__main__":
    main()
