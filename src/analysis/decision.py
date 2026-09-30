"""Etapa 9: decisão de investimento no ARC Raiders para 2027.

Compara duas estratégias para 2027, em cada variante de premissas da Etapa 8:
  Investir   equipe completa: grandes atualizações semestrais + modo PvE + skins (cenário S3)
  Mínimo     equipe de manutenção: servidores, anti-cheat e loja, sem conteúdo novo (cenário S0)

O custo da equipe não é público; entra como faixa [P]:
  pessoas no ARC Raiders   investir 150-250 (Embark tinha ~350 em 2025, com The Finals); mínimo 30-60
  custo por pessoa         US$ 95-135 mil/ano (salário bruto de SEK 650-850 mil x ~1,5 de encargos
                           suecos e benefícios, câmbio ~10,5 SEK/US$)
  outros custos            x1,3 a x1,6 sobre a folha (servidores, anti-cheat, marketing, terceiros)
Receita: base econômica líquida das lojas (Etapas 7 e 8).

Uso: python src/analysis/decision.py
"""
import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from analysis import projections as pj  # noqa: E402
from config import ROOT  # noqa: E402
from viz import style  # noqa: E402

COST = {
    "headcount_invest": (150, 250),
    "headcount_min": (30, 60),
    "cost_per_head_usd": (95_000, 135_000),
    "overhead": (1.3, 1.6),
}
METRICS: dict = {}


def costs(n: int, seed: int = 11) -> dict:
    rng = np.random.default_rng(seed)
    c = {k: rng.uniform(lo, hi, n) for k, (lo, hi) in COST.items()}
    per_head = c["cost_per_head_usd"] * c["overhead"]
    return {"invest": c["headcount_invest"] * per_head / 1e6, "min": c["headcount_min"] * per_head / 1e6}


def outcomes() -> pd.DataFrame:
    mask = pj.MONTHS.year == 2027
    jan = pj.MONTHS.get_loc(pd.Timestamp("2027-01-01"))
    rows = []
    for variant in ("base", "pessimista"):
        sc = pj.run_scenarios(pj.draw(variant))
        rev = {k: sum(sc[k][p][:, mask].sum(1) for p in ("units", "store", "skins")) / 1e6 for k in ("S0", "S3")}
        c = costs(pj.N_SIM)
        rows.append(pd.DataFrame({
            "variante": variant,
            "receita_investir": rev["S3"], "receita_minimo": rev["S0"],
            "custo_investir": c["invest"], "custo_minimo": c["min"],
            "jogadores_jan27": sc["S3"]["players"][:, jan],
            "jogadores_media_2027": sc["S3"]["players"][:, mask].mean(1),
        }))
    d = pd.concat(rows, ignore_index=True)
    d["lucro_investir"] = d["receita_investir"] - d["custo_investir"]
    d["lucro_minimo"] = d["receita_minimo"] - d["custo_minimo"]
    d["ganho_incremental"] = d["lucro_investir"] - d["lucro_minimo"]
    return d


def summarize(d: pd.DataFrame) -> dict:
    out = {}
    for v, g in d.groupby("variante"):
        q = lambda s: [round(float(np.percentile(s, p)), 1) for p in (10, 50, 90)]  # noqa: E731
        out[v] = {
            "receita_investir": q(g["receita_investir"]), "custo_investir": q(g["custo_investir"]),
            "lucro_investir": q(g["lucro_investir"]), "lucro_minimo": q(g["lucro_minimo"]),
            "ganho_incremental": q(g["ganho_incremental"]),
            "prob_ganho_incremental_positivo": round(float((g["ganho_incremental"] > 0).mean()), 3),
            "roi_incremental_mediano": round(float(np.median(g["ganho_incremental"] / (g["custo_investir"] - g["custo_minimo"]))), 2),
        }
    return out


def break_even(d: pd.DataFrame) -> dict:
    """Nível de jogadores em jan/2027 a partir do qual investir compensa (ganho incremental > 0 em 70%+ dos casos)."""
    bins = np.arange(8_000, 60_000, 2_000)
    d = d.assign(faixa=pd.cut(d["jogadores_jan27"], bins))
    prob = d.groupby("faixa", observed=True)["ganho_incremental"].apply(lambda s: (s > 0).mean())
    mids = np.array([iv.mid for iv in prob.index])
    ok = mids[prob.values >= 0.7]
    threshold = float(ok.min()) if len(ok) else float("nan")
    return {"limite_jan27": threshold, "curva": {f"{int(m)}": round(float(p), 3) for m, p in zip(mids, prob.values)}}


def fig_profit(d: pd.DataFrame):
    fig, ax = plt.subplots(figsize=(12.5, 5.2))
    items = [("base", "lucro_minimo", "Mínimo: só manutenção"), ("base", "lucro_investir", "Investir: atualizações + PvE + skins"),
             ("pessimista", "lucro_minimo", "Mínimo: só manutenção"), ("pessimista", "lucro_investir", "Investir: atualizações + PvE + skins")]
    y = np.array([3.4, 2.6, 1.0, 0.2])
    for yi, (v, col, label) in zip(y, items):
        s = d.loc[d["variante"] == v, col]
        p10, p50, p90 = np.percentile(s, [10, 50, 90])
        color = style.SLOTS[0] if "investir" in col else style.CONTEXT_GRAY
        ax.plot([p10, p90], [yi, yi], color=color, lw=6, solid_capstyle="round", alpha=0.35)
        ax.plot(p50, yi, "o", ms=11, color=color, mec=style.SURFACE, mew=2)
        ax.text(p90 + 2, yi, f"US$ {p50:.0f} mi  ({p10:.0f} a {p90:.0f})", va="center", fontsize=9, color=style.INK)
    ax.axvline(0, color=style.INK_2, lw=1)
    ax.set_yticks(y, [label for _, _, label in items])
    for yy, text in ((3.95, "CENÁRIO BASE"), (1.55, "PESSIMISTA")):
        ax.text(-0.01, yy, text, transform=ax.get_yaxis_transform(), fontsize=9, fontweight="bold", color=style.INK, ha="right")
    ax.tick_params(axis="y", length=0)
    ax.spines["left"].set_visible(False)
    ax.grid(axis="y", visible=False)
    ax.grid(axis="x", visible=True)
    lo = min(-5, d[["lucro_investir", "lucro_minimo"]].quantile(0.1).min() - 5)
    ax.set_xlim(lo, d[["lucro_investir", "lucro_minimo"]].quantile(0.9).max() + 40)
    ax.set_ylim(-0.4, 4.3)
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"US$ {v:.0f} mi"))
    ax.set_title("Resultado de 2027 (receita − custo) por estratégia")
    style.subtitle(ax, "Ponto = mediana; barra = faixa de 80% de 10 mil simulações. Custo da equipe estimado [P]")
    style.source_note(fig, "Receita das Etapas 7 e 8 (líquida das lojas). Custo: 150-250 pessoas (investir) ou 30-60 (mínimo) x US$ 95-135 mil/ano x 1,3-1,6 "
                           "de outros custos. Não inclui receita de outros títulos nem o valor da marca.")
    return style.save(fig, "12a_resultado_2027_estrategias")


def fig_break_even(d: pd.DataFrame, be: dict):
    fig, ax = plt.subplots(figsize=(12.5, 5.4))
    sample = d.sample(6000, random_state=1)
    colors = np.where(sample["variante"] == "base", style.SLOTS[0], style.SLOTS[1])
    ax.scatter(sample["jogadores_jan27"], sample["ganho_incremental"], s=6, c=colors, alpha=0.35, lw=0)
    ax.axhline(0, color=style.INK_2, lw=1)
    t = be["limite_jan27"]
    ax.axvline(t, color=style.SLOTS[7], lw=1.6)
    ax.text(t, ax.get_ylim()[1] * 0.92, f"  limite de decisão: {style.thousands(t)} jogadores em jan/2027",
            fontsize=9, color=style.INK, va="top")
    ax.scatter([], [], s=30, color=style.SLOTS[0], label="Simulações do cenário base")
    ax.scatter([], [], s=30, color=style.SLOTS[1], label="Simulações do cenário pessimista")
    ax.legend(loc="lower right")
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(style.thousands))
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"US$ {v:.0f} mi"))
    ax.set_xlabel("média de jogadores na Steam em jan/2027 (3 meses depois do Frozen Trail)")
    ax.set_title("Quando investir compensa: ganho de investir sobre a manutenção mínima em 2027")
    style.subtitle(ax, "Cada ponto é uma simulação. À direita da linha vermelha, investir dá ganho positivo em 70%+ dos casos")
    style.source_note(fig, "Ganho incremental = (receita − custo investindo) − (receita − custo só com manutenção). "
                           "Jan/2027 é o primeiro mês em que dá para medir quanto da alta do Frozen Trail ficou.")
    return style.save(fig, "12b_limite_de_decisao")


def main():
    style.apply()
    d = outcomes()
    s = summarize(d)
    be = break_even(d)
    paths = [fig_profit(d), fig_break_even(d, be)]
    METRICS.update({"premissas_custo": {k: list(v) for k, v in COST.items()}, "resumo": s, "limite": be})
    (ROOT / "reports" / "metrics_decisao.json").write_text(json.dumps(METRICS, ensure_ascii=False, indent=2), encoding="utf-8")
    for p in paths:
        print("figura:", p.name)
    print(json.dumps(s, ensure_ascii=False, indent=1))
    print("limite jan/27:", be["limite_jan27"])


if __name__ == "__main__":
    main()
