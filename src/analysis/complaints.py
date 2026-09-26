"""Etapa 5: temas de reclamação nas análises da Steam.

Uso:
  python src/analysis/complaints.py tag      -> marca os temas e gera a amostra de validação
  python src/analysis/complaints.py report   -> gráficos e métricas (depois da validação)
"""
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from analysis.complaints_lexicon import LANGUAGE_EXCLUDE, TOPICS, to_regex  # noqa: E402
from config import INTERIM, ROOT  # noqa: E402

MIN_CHARS = 20  # análises mais curtas ("gg", "10/10") não carregam tema
SAMPLE_FILE = INTERIM / "validation_sample.csv"
LABELS_FILE = ROOT / "data" / "external" / "complaint_validation_labels.csv"


def compile_topics() -> dict[str, re.Pattern]:
    return {k: re.compile(to_regex(v["pattern"]), re.IGNORECASE) for k, v in TOPICS.items()}


def tag(df: pd.DataFrame) -> pd.DataFrame:
    patterns = compile_topics()
    text = df["text"].fillna("")
    for name, pat in patterns.items():
        topic_text = text
        for lang, excl in LANGUAGE_EXCLUDE.get(name, {}).items():
            mask = df["language"] == lang
            topic_text = topic_text.where(~mask, topic_text[mask].str.replace(excl, " ", regex=True, flags=re.I))
        df[f"t_{name}"] = topic_text.map(lambda s, p=pat: bool(p.search(s)))
    df["t_any"] = df[[f"t_{k}" for k in TOPICS]].any(axis=1)
    return df


def validation_sample(df: pd.DataFrame, per_topic=20, unflagged=60, seed=2026) -> pd.DataFrame:
    """Amostra para leitura manual. Só análises negativas: a reclamação é definida como
    análise negativa que menciona o tema (nas positivas os termos aparecem sobretudo em
    elogios, como "sem bugs" ou "boa mistura de PvE e PvP").
    seed=42 foi a amostra de ajuste do dicionário; seed=2026 é a amostra de teste.
    """
    df = df[~df["voted_up"]]
    rng = np.random.default_rng(seed)
    rows = []
    for name in TOPICS:
        pool = df[df[f"t_{name}"]]
        pick = pool.sample(n=min(per_topic, len(pool)), random_state=int(rng.integers(1e9)))
        rows.append(pick.assign(sample_group=f"flagged:{name}"))
    neg = df[(~df["t_any"]) & (df["text_len"] >= 80)]
    rows.append(neg.sample(n=unflagged, random_state=seed).assign(sample_group="unflagged_negative"))
    out = pd.concat(rows)
    out["text_short"] = out["text"].str.replace(r"\s+", " ", regex=True).str.slice(0, 450)
    cols = ["review_id", "sample_group", "language", "voted_up", "text_short"] + [f"t_{k}" for k in TOPICS]
    return out[cols]


def cmd_tag():
    df = pd.read_parquet(INTERIM / "arc_reviews.parquet",
                         columns=["review_id", "created", "month", "language", "voted_up", "text", "text_len",
                                  "playtime_forever_min", "playtime_at_review_min", "playtime_2weeks_min",
                                  "days_since_last_played"])
    df = df[df["text_len"] >= MIN_CHARS].copy()
    df = tag(df)
    df.drop(columns=["text"]).to_parquet(INTERIM / "arc_review_topics.parquet", index=False)
    print(f"{len(df):,} análises com {MIN_CHARS}+ caracteres")
    share = pd.DataFrame({
        "todas_%": df[[f"t_{k}" for k in TOPICS]].mean() * 100,
        "negativas_%": df.loc[~df["voted_up"], [f"t_{k}" for k in TOPICS]].mean() * 100,
        "positivas_%": df.loc[df["voted_up"], [f"t_{k}" for k in TOPICS]].mean() * 100,
    }).round(2)
    print(share.to_string())
    print("negativas sem nenhum tema:", f"{(~df.loc[~df['voted_up'], 't_any']).mean():.1%}")
    validation_sample(df).to_csv(SAMPLE_FILE, index=False, encoding="utf-8")
    print("amostra de validação em", SAMPLE_FILE)


# ---------------------------------------------------------------------------
# Relatório (depois da validação manual)
# ---------------------------------------------------------------------------
import json  # noqa: E402

import matplotlib.pyplot as plt  # noqa: E402
import matplotlib.ticker as mticker  # noqa: E402
import statsmodels.formula.api as smf  # noqa: E402

from analysis.complaints_lexicon import CONTEXT, REQUESTED  # noqa: E402
from analysis.diagnostics import month_label  # noqa: E402
from viz import style  # noqa: E402

LABEL = {k: v["label"] for k, v in TOPICS.items()}
METRICS: dict = {}


def validation_table(df: pd.DataFrame) -> pd.DataFrame:
    """Precisão (amostra de teste) e cobertura estimada de cada tema nas análises negativas.

    Cobertura = verdadeiros positivos / (verdadeiros positivos + temas perdidos), com os
    perdidos estimados pela amostra de negativas sem tema (60 análises).
    """
    labels = pd.read_csv(LABELS_FILE, keep_default_na=False)
    neg = df[~df["voted_up"]]
    no_topic_share = (~neg["t_any"]).mean()
    unflagged = labels[labels["sample_group"] == "unflagged_negative"]
    rows = []
    for k in TOPICS:
        g = labels[labels["sample_group"] == f"flagged:{k}"]
        precision = pd.to_numeric(g["correct"]).mean()
        flagged_share = neg[f"t_{k}"].mean()
        missed_rate = unflagged["missed_topics"].str.contains(k).mean()
        tp, fn = flagged_share * precision, no_topic_share * missed_rate
        rows.append({"tema": LABEL[k], "precisao": precision, "n_amostra": len(g),
                     "mencao_negativas": flagged_share, "cobertura_estimada": tp / (tp + fn)})
    t = pd.DataFrame(rows)
    METRICS["validacao"] = t.round(3).to_dict(orient="records")
    return t


def monthly_shares(df: pd.DataFrame) -> pd.DataFrame:
    neg = df[~df["voted_up"]]
    m = neg.groupby("month")[[f"t_{k}" for k in TOPICS]].mean() * 100
    m.columns = list(TOPICS)
    m["n_negativas"] = neg.groupby("month").size()
    m["pct_negativas"] = (1 - df.groupby("month")["voted_up"].mean()) * 100
    return m


def fig_heatmap(m: pd.DataFrame):
    topics = REQUESTED + CONTEXT
    data = m[topics].T
    fig, ax = plt.subplots(figsize=(13, 5.6))
    from matplotlib.colors import LinearSegmentedColormap
    cmap = LinearSegmentedColormap.from_list("blue", style.BLUE_RAMP)
    im = ax.imshow(data.values, aspect="auto", cmap=cmap, vmin=0, vmax=np.nanmax(data.values))
    for i in range(data.shape[0]):
        for j in range(data.shape[1]):
            v = data.values[i, j]
            ax.text(j, i, f"{v:.0f}", ha="center", va="center", fontsize=8.5,
                    color="white" if v > np.nanmax(data.values) * 0.55 else style.INK)
    ax.set_xticks(range(data.shape[1]), [month_label(c) for c in data.columns])
    ax.set_yticks(range(len(topics)), [LABEL[t] for t in topics])
    ax.axhline(len(REQUESTED) - 0.5, color=style.SURFACE, lw=4)
    ax.grid(False)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.tick_params(length=0)
    cb = fig.colorbar(im, ax=ax, fraction=0.025, pad=0.01)
    cb.outline.set_visible(False)
    cb.ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:.0f}%"))
    ax.set_title("O que as análises negativas reclamam, mês a mês")
    style.subtitle(ax, "% das análises negativas do mês que mencionam cada tema. Acima da linha branca: temas do escopo; abaixo: temas de contexto")
    style.source_note(fig, "Fonte: 416,8 mil análises da Steam [O]; análises negativas com 20+ caracteres. Classificação multilíngue por dicionário, "
                           "precisão de 90% numa amostra lida à mão. Uma análise pode ter vários temas. Out/2025 = 2 dias.")
    return style.save(fig, "08a_reclamacoes_mapa_de_calor")


def fig_trends(m: pd.DataFrame, df: pd.DataFrame):
    """Temas ao longo do tempo em pequenos múltiplos, com a taxa de análises negativas como painel de referência."""
    topics = REQUESTED + ["content"]
    m = m[m.index >= "2025-11-01"]
    fig, axes = plt.subplots(2, 4, figsize=(14, 6.8), sharex=True)
    ref = axes.flat[0]
    ref.plot(m.index, m["pct_negativas"], color=style.INK_2, lw=2)
    ref.set_title("Análises negativas (% do mês)", fontsize=10)
    ref.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:.0f}%"))
    ref.set_ylim(0, 60)
    for ax, t in zip(list(axes.flat)[1:], topics + ["balance"]):
        ax.plot(m.index, m[t], color=style.ARC, lw=2)
        ax.fill_between(m.index, m[t], color=style.ARC, alpha=0.1)
        first, last = m[t].iloc[0], m[t].iloc[-1]
        ax.set_title(f"{LABEL[t]}", fontsize=10)
        ax.text(1, 0.97, f"{first:.0f}% → {last:.0f}%", transform=ax.transAxes, ha="right", va="top", fontsize=9, color=style.INK_2)
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:.0f}%"))
        ax.set_ylim(0, max(45, m[t].max() * 1.2))
    for ax in axes[-1]:
        ticks = m.index[::3]
        ax.set_xticks(ticks, [month_label(x) for x in ticks], fontsize=8.5)
    fig.tight_layout(rect=(0, 0, 1, 0.88), h_pad=2.5)
    fig.text(0.01, 0.985, "Como cada reclamação evoluiu (% das análises negativas do mês)", fontsize=14, fontweight="bold", va="top")
    fig.text(0.01, 0.935, f"Primeiro painel: a parcela de análises negativas foi de {m['pct_negativas'].iloc[0]:.0f}% para "
                          f"{m['pct_negativas'].iloc[-1]:.0f}%; os demais mostram do que elas passaram a falar",
             color=style.INK_2, fontsize=10, va="top")
    style.source_note(fig, "Fonte: análises da Steam [O]. Valor no canto = nov/2025 → set/2026 (parcial).")
    return style.save(fig, "08b_reclamacoes_tendencia")


def impact_models(df: pd.DataFrame):
    """Dois modelos logísticos com controles (mês da análise, horas jogadas, idioma):

    1. Voto: quanto mencionar cada tema reduz a chance de recomendar o jogo.
    2. Abandono: entre quem fez análise negativa, quanto cada tema se associa a não ter
       jogado nas duas semanas antes da coleta (proxy de abandono).
    Efeitos em pontos percentuais (efeito marginal médio). Associação, não causa.
    """
    d = df.copy()
    d["log_horas"] = np.log1p(d["playtime_at_review_min"] / 60)
    d["log_horas_total"] = np.log1p(d["playtime_forever_min"] / 60)
    top_langs = d["language"].value_counts().index[:8]
    d["idioma"] = d["language"].where(d["language"].isin(top_langs), "outros")
    d["mes"] = d["month"].dt.strftime("%Y-%m")
    d["positivo"] = d["voted_up"].astype(int)
    d["abandonou"] = (d["playtime_2weeks_min"] == 0).astype(int)
    terms = " + ".join(f"t_{k}" for k in TOPICS)
    for k in TOPICS:
        d[f"t_{k}"] = d[f"t_{k}"].astype(int)

    vote = smf.logit(f"positivo ~ {terms} + log_horas + C(idioma) + C(mes)", data=d).fit(disp=False)
    vote_me = vote.get_margeff(at="overall").summary_frame()
    neg = d[d["positivo"] == 0]
    churn = smf.logit(f"abandonou ~ {terms} + log_horas_total + C(idioma) + C(mes)", data=neg).fit(disp=False)
    churn_me = churn.get_margeff(at="overall").summary_frame()

    def tidy(me):
        rows = me.loc[[f"t_{k}" for k in TOPICS]]
        return pd.DataFrame({"tema": [LABEL[k] for k in TOPICS], "efeito_pp": rows["dy/dx"].values * 100,
                             "ic_baixo": rows["Conf. Int. Low"].values * 100, "ic_alto": rows["Cont. Int. Hi."].values * 100})
    v, c = tidy(vote_me), tidy(churn_me)
    METRICS["efeito_no_voto_pp"] = v.round(2).to_dict(orient="records")
    METRICS["efeito_no_abandono_pp"] = c.round(2).to_dict(orient="records")
    METRICS["abandono_base_negativas_pct"] = round(neg["abandonou"].mean() * 100, 1)
    return v, c


def fig_impact(v: pd.DataFrame, c: pd.DataFrame):
    fig, axes = plt.subplots(1, 2, figsize=(14, 6), sharey=True)
    order = v.sort_values("efeito_pp", ascending=False)["tema"].tolist()
    panels = [(axes[0], v, "Chance de recomendar o jogo", "Todas as análises (273 mil)"),
              (axes[1], c, "Chance de ter parado de jogar", "Só análises negativas (70 mil)")]
    for ax, t, title, sub in panels:
        t = t.set_index("tema").loc[order]
        y = np.arange(len(t))
        colors = [style.SLOTS[7] if e < 0 else style.SLOTS[0] for e in t["efeito_pp"]]
        ax.hlines(y, t["ic_baixo"], t["ic_alto"], color=style.AXIS, lw=2)
        ax.scatter(t["efeito_pp"], y, s=70, color=colors, edgecolor=style.SURFACE, linewidth=2, zorder=3)
        for yi, e in zip(y, t["efeito_pp"]):
            ax.text(e, yi - 0.32, f"{e:+.1f}".replace(".", ",") + " p.p.", ha="center", fontsize=8.5, color=style.INK_2)
        ax.axvline(0, color=style.AXIS, lw=1)
        ax.set_yticks(y, t.index)
        ax.invert_yaxis()
        ax.grid(axis="y", visible=False)
        ax.grid(axis="x", visible=True)
        ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:+.0f}"))
        ax.set_xlabel("pontos percentuais")
        ax.set_title(f"{title}\n", fontsize=11)
        ax.text(0, 1.02, sub, transform=ax.transAxes, fontsize=9, color=style.INK_2)
    fig.tight_layout(rect=(0, 0, 1, 0.87), w_pad=3)
    fig.text(0.01, 0.985, "Quanto cada reclamação pesa no voto e no abandono", fontsize=14, fontweight="bold", va="top")
    fig.text(0.01, 0.935, "Efeito de mencionar o tema, com os mesmos controles: mês da análise, horas jogadas e idioma. Linha = intervalo de 95%",
             color=style.INK_2, fontsize=10, va="top")
    style.source_note(fig, "Regressões logísticas, efeito marginal médio [O]. 'Parou de jogar' = 0 minutos nas duas semanas antes da coleta (25/09/2026). "
                           "Associação, não causa: quem já ia sair pode reclamar mais.")
    return style.save(fig, "08c_impacto_voto_e_abandono")


def fig_validation(t: pd.DataFrame):
    t = t.sort_values("precisao")
    fig, ax = plt.subplots(figsize=(11, 5))
    y = np.arange(len(t))
    ax.hlines(y, t["cobertura_estimada"] * 100, t["precisao"] * 100, color=style.GRID, lw=3)
    ax.scatter(t["precisao"] * 100, y, s=80, color=style.SLOTS[0], edgecolor=style.SURFACE, linewidth=2, zorder=3, label="Precisão (amostra de teste)")
    ax.scatter(t["cobertura_estimada"] * 100, y, s=80, color=style.SLOTS[1], edgecolor=style.SURFACE, linewidth=2, zorder=3, label="Cobertura estimada")
    ax.set_yticks(y, t["tema"])
    ax.grid(axis="y", visible=False)
    ax.grid(axis="x", visible=True)
    ax.set_xlim(0, 105)
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:.0f}%"))
    ax.legend(loc="lower left")
    ax.set_title("Qualidade da classificação por tema")
    style.subtitle(ax, "Precisão: quando o dicionário marca o tema, acerta? Cobertura: das análises sobre o tema, quantas ele encontra?")
    style.source_note(fig, "Amostra de teste independente: 160 análises marcadas (20 por tema) + 60 negativas sem tema, lidas uma a uma. "
                           "Com n = 20 por tema, cada ponto tem margem de erro de ±10 a ±20 p.p.")
    return style.save(fig, "08d_validacao_classificacao")


def complaint_rate(df: pd.DataFrame) -> pd.DataFrame:
    """Reclamações por 100 análises do mês: análise negativa que menciona o tema / todas.

    Diferente da composição (fig 08b), mede a intensidade: combina o aumento de
    análises negativas com o que elas dizem.
    """
    rate = pd.DataFrame({k: (~df["voted_up"] & df[f"t_{k}"]).groupby(df["month"]).mean() * 100 for k in TOPICS})
    return rate[rate.index >= "2025-11-01"]


def fig_rate_vs_players(rate: pd.DataFrame):
    players = pd.read_csv(INTERIM / "players_monthly.csv", parse_dates=["month"])
    arc = players[players["appid"] == 1808500].set_index("month")["avg_players"]
    change = arc.pct_change() * 100
    fig, axes = plt.subplots(1, 2, figsize=(14, 5.8), gridspec_kw={"width_ratios": [1.6, 1]})
    ax = axes[0]
    topics = REQUESTED
    labels = []
    for i, t in enumerate(topics):
        ax.plot(rate.index, rate[t], color=style.SLOTS[i], lw=2, marker="o", ms=4, mec=style.SURFACE, mew=1)
        labels.append((rate.index[-1], rate[t].iloc[-1], f"{LABEL[t].split(' /')[0].split(',')[0]}  {rate[t].iloc[-1]:.0f}", False))
    style.end_labels(ax, labels, x_text=rate.index[-1] + pd.Timedelta(days=18), min_gap=1.3)
    ax.set_xlim(rate.index[0] - pd.Timedelta(days=10), rate.index[-1] + pd.Timedelta(days=10))
    ticks = rate.index[::2]
    ax.set_xticks(ticks, [month_label(x) for x in ticks])
    ax.legend([LABEL[t] for t in topics], loc="upper left", fontsize=8.5)
    ax.set_title("Reclamações a cada 100 análises do mês", fontsize=11)

    # Correlação: taxa de reclamação no mês t x variação de jogadores no mês t+1
    ax = axes[1]
    rows = []
    for t in TOPICS:
        joined = pd.concat([rate[t].rename("rate"), change.shift(-1).rename("next_change"), change.rename("change")], axis=1).dropna()
        rows.append({"tema": LABEL[t], "mesmo_mes": joined["rate"].corr(joined["change"]),
                     "mes_seguinte": joined["rate"].corr(joined["next_change"]), "n": len(joined)})
    corr = pd.DataFrame(rows).sort_values("mes_seguinte")
    y = np.arange(len(corr))
    ax.barh(y, corr["mes_seguinte"], height=0.5, color=[style.SLOTS[7] if v < 0 else style.SLOTS[0] for v in corr["mes_seguinte"]])
    for yi, v in zip(y, corr["mes_seguinte"]):
        ax.text(v + (0.03 if v >= 0 else -0.03), yi, f"{v:+.2f}".replace(".", ","), va="center",
                ha="left" if v >= 0 else "right", fontsize=8.5, color=style.INK_2)
    ax.axvline(0, color=style.AXIS, lw=1)
    ax.set_yticks(y, corr["tema"], fontsize=9)
    ax.set_xlim(-1, 1)
    ax.grid(axis="y", visible=False)
    ax.grid(axis="x", visible=True)
    ax.set_title("Correlação com a variação de jogadores\nno mês seguinte", fontsize=11)
    fig.tight_layout(rect=(0, 0, 1, 0.88), w_pad=4)
    fig.text(0.01, 0.985, "Reclamações e queda de jogadores", fontsize=14, fontweight="bold", va="top")
    fig.text(0.01, 0.935, "Esquerda: análise negativa que cita o tema, por 100 análises. Direita: correlação da taxa de cada mês com a variação "
                          "de jogadores do mês seguinte", color=style.INK_2, fontsize=10, va="top")
    style.source_note(fig, f"Fontes: análises da Steam e SteamCharts [O]. Correlação exploratória com n = {int(corr['n'].iloc[0])} meses: "
                           "indica associação temporal, não causa. Negativo = mais reclamação precede queda maior.")
    METRICS["taxa_reclamacao_por_100"] = rate.round(2).reset_index().assign(month=lambda x: x["month"].dt.strftime("%Y-%m")).to_dict(orient="records")
    METRICS["correlacao_taxa_x_variacao_jogadores"] = corr.round(3).to_dict(orient="records")
    return style.save(fig, "08e_reclamacoes_x_jogadores")


def balance_weeks(df: pd.DataFrame):
    """Nas semanas após patches de balanceamento, a queixa de balanceamento sobe?"""
    events = pd.read_csv(INTERIM / "arc_events.csv", parse_dates=["date"])
    patches = events[(events["kind"].isin(["live_update", "major_update"])) & (events["n_balance"] > 0) & (events["date"] >= "2025-11-01")]
    neg = df[~df["voted_up"]].copy()
    neg["day"] = neg["created"].dt.normalize()
    after = pd.Series(False, index=neg.index)
    for d in patches["date"]:
        after |= neg["day"].between(d, d + pd.Timedelta(days=6))
    res = {"semanas_pos_patch": round(neg.loc[after, "t_balance"].mean() * 100, 2),
           "demais_semanas": round(neg.loc[~after, "t_balance"].mean() * 100, 2),
           "n_patches": int(len(patches))}
    METRICS["balanceamento_semanas_pos_patch_pct"] = res
    return res


def cmd_report():
    style.apply()
    df = pd.read_parquet(INTERIM / "arc_review_topics.parquet")
    t = validation_table(df)
    m = monthly_shares(df)
    METRICS["mensal_negativas_pct"] = m.round(2).reset_index().assign(month=lambda x: x["month"].dt.strftime("%Y-%m")).to_dict(orient="records")
    v, c = impact_models(df)
    paths = [fig_heatmap(m), fig_trends(m, df), fig_impact(v, c), fig_validation(t), fig_rate_vs_players(complaint_rate(df))]
    balance_weeks(df)
    (ROOT / "reports" / "metrics_reclamacoes.json").write_text(json.dumps(METRICS, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    for p in paths:
        print("figura:", p.name)
    print(t.round(3).to_string())
    print(v.round(2).to_string())
    print(c.round(2).to_string())
    print(METRICS["balanceamento_semanas_pos_patch_pct"], "abandono base:", METRICS["abandono_base_negativas_pct"])


if __name__ == "__main__":
    {"tag": cmd_tag, "report": cmd_report}[sys.argv[1] if len(sys.argv) > 1 else "tag"]()
