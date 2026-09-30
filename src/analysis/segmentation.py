"""Etapa 6: modelo RFE (Recência, Frequência, Engajamento) e agrupamento dos jogadores.

Adaptação do RFM para um jogo sem dados de compra por jogador. Cada análise da Steam
traz o perfil de jogo do autor na data da coleta (25/09/2026):

  R  Recência     dias desde a última vez que jogou (menor = mais recente)
  F  Frequência   horas por semana entre o lançamento e a última vez que jogou
  E  Engajamento  horas jogadas no total

Duas camadas, como no projeto de referência:
  1. Notas RFE de 1 a 5 (quintis), para leitura de negócio.
  2. K-Means sobre R, log(F) e log(E) padronizados, para achar os grupos.
Os grupos são depois cruzados com o voto e com as reclamações da Etapa 5.

Viés: quem escreve análise é mais engajado que a média dos compradores. Os grupos
descrevem os autores de análises (416,8 mil, ~5% das unidades na Steam).

Uso: python src/analysis/segmentation.py
"""
import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from analysis.complaints_lexicon import TOPICS  # noqa: E402
from config import INTERIM, ROOT  # noqa: E402
from viz import style  # noqa: E402

LAUNCH = pd.Timestamp("2025-10-30")
SEED = 42
METRICS: dict = {}
LABEL = {k: v["label"] for k, v in TOPICS.items()}


def build_features() -> pd.DataFrame:
    d = pd.read_parquet(INTERIM / "arc_reviews.parquet",
                        columns=["review_id", "created", "month", "language", "voted_up", "last_played",
                                 "days_since_last_played", "playtime_forever_min", "playtime_2weeks_min"])
    d["R"] = d["days_since_last_played"].clip(lower=0)  # 3,3 mil jogaram no próprio dia da coleta
    d["E"] = d["playtime_forever_min"] / 60
    active_weeks = ((d["last_played"] - LAUNCH).dt.days / 7).clip(lower=1)
    d["F"] = (d["E"] / active_weeks).clip(upper=(d["E"] / active_weeks).quantile(0.999))
    d["E"] = d["E"].clip(upper=d["E"].quantile(0.999))
    # Notas de 1 a 5 (5 = melhor): recência invertida (menos dias = nota maior)
    d["R_score"] = pd.qcut(d["R"].rank(method="first"), 5, labels=[5, 4, 3, 2, 1]).astype(int)
    d["F_score"] = pd.qcut(d["F"].rank(method="first"), 5, labels=[1, 2, 3, 4, 5]).astype(int)
    d["E_score"] = pd.qcut(d["E"].rank(method="first"), 5, labels=[1, 2, 3, 4, 5]).astype(int)
    d["RFE"] = d["R_score"] + d["F_score"] + d["E_score"]
    # Tópicos da Etapa 5 (só análises com 20+ caracteres foram classificadas)
    topics = pd.read_parquet(INTERIM / "arc_review_topics.parquet", columns=["review_id"] + [f"t_{k}" for k in TOPICS])
    d = d.merge(topics, on="review_id", how="left")
    for k in TOPICS:
        d[f"t_{k}"] = d[f"t_{k}"].fillna(False).astype(bool)
    d["has_text"] = d["review_id"].isin(topics["review_id"])
    return d


def model_matrix(d: pd.DataFrame) -> np.ndarray:
    X = np.column_stack([d["R"], np.log1p(d["F"]), np.log1p(d["E"])])
    return StandardScaler().fit_transform(X)


def choose_k(X: np.ndarray, ks=range(2, 9)) -> pd.DataFrame:
    rng = np.random.default_rng(SEED)
    sample = X[rng.choice(len(X), size=30_000, replace=False)]
    rows = []
    for k in ks:
        km = KMeans(n_clusters=k, n_init=10, random_state=SEED).fit(X)
        sil = silhouette_score(sample, km.predict(sample), random_state=SEED)
        rows.append({"k": k, "inercia": km.inertia_, "silhueta": sil})
    t = pd.DataFrame(rows)
    METRICS["escolha_k"] = t.round(4).to_dict(orient="records")
    return t


def fig_choose_k(t: pd.DataFrame, k_chosen: int):
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.6))
    for ax, col, title in [(axes[0], "inercia", "Método do cotovelo (inércia)"), (axes[1], "silhueta", "Coeficiente de silhueta")]:
        ax.plot(t["k"], t[col], color=style.ARC, marker="o", ms=6, mec=style.SURFACE, mew=1.5)
        row = t[t["k"] == k_chosen].iloc[0]
        ax.plot(k_chosen, row[col], "o", ms=12, mfc="none", mec=style.SLOTS[7], mew=2)
        ax.set_xticks(t["k"])
        ax.set_xlabel("número de grupos (k)")
        ax.set_title(title, fontsize=11)
        if col == "inercia":
            ax.yaxis.set_major_formatter(mticker.FuncFormatter(style.thousands))
    fig.tight_layout(rect=(0, 0, 1, 0.85), w_pad=4)
    fig.text(0.01, 0.985, f"Escolha do número de grupos: k = {k_chosen}", fontsize=14, fontweight="bold", va="top")
    fig.text(0.01, 0.925, "Círculo vermelho = k escolhido. Critérios: cotovelo da inércia, silhueta e grupos interpretáveis para o negócio",
             color=style.INK_2, fontsize=10, va="top")
    style.source_note(fig, "K-Means sobre recência, log(frequência) e log(engajamento) padronizados; silhueta numa amostra de 30 mil autores.")
    return style.save(fig, "09a_escolha_k")


def name_clusters(profile: pd.DataFrame) -> dict:
    """Nomeia os 4 grupos pela ordem dos centróides (k = 4, escolhido pela silhueta).

    Maior engajamento -> Veteranos ativos; menor -> Desistiram cedo. Dos dois do meio,
    o mais recente (menos dias sem jogar) -> Casuais persistentes; o outro -> Veteranos
    que abandonaram (jogaram muito por semana e pararam há meses).
    """
    if len(profile) != 4:
        return {c: f"Grupo {c}" for c in profile.index}
    by_e = profile.sort_values("E")
    names = {by_e.index[-1]: "Veteranos ativos", by_e.index[0]: "Desistiram cedo"}
    middle = profile.loc[by_e.index[1:3]].sort_values("R")
    names[middle.index[0]] = "Casuais persistentes"
    names[middle.index[1]] = "Veteranos que abandonaram"
    return names


def profile_clusters(d: pd.DataFrame) -> pd.DataFrame:
    g = d.groupby("cluster")
    prof = pd.DataFrame({
        "autores": g.size(),
        "R": g["R"].median(), "F": g["F"].median(), "E": g["E"].median(),
        "ativos_2sem_pct": g["playtime_2weeks_min"].apply(lambda s: (s > 0).mean() * 100),
        "positivas_pct": g["voted_up"].mean() * 100,
        "R_score": g["R_score"].mean(), "F_score": g["F_score"].mean(), "E_score": g["E_score"].mean(),
    })
    prof["pct_autores"] = prof["autores"] / prof["autores"].sum() * 100
    return prof


def complaint_profile(d: pd.DataFrame) -> pd.DataFrame:
    """% das análises negativas com texto de cada grupo que menciona cada tema."""
    neg = d[(~d["voted_up"]) & d["has_text"]]
    return neg.groupby("name")[[f"t_{k}" for k in TOPICS]].mean().rename(columns=lambda c: LABEL[c[2:]]) * 100


def fig_profile(prof: pd.DataFrame):
    prof = prof.sort_values("E", ascending=False)
    cols = [("pct_autores", "% dos autores", "{:.0f}%"), ("R", "Dias sem jogar (mediana)", "{:.0f}"),
            ("F", "Horas por semana (mediana)", "{:.1f}"), ("E", "Horas no total (mediana)", "{:.0f}"),
            ("ativos_2sem_pct", "Jogaram nas últimas 2 semanas", "{:.0f}%"), ("positivas_pct", "Recomendam o jogo", "{:.0f}%")]
    fig, axes = plt.subplots(1, len(cols), figsize=(15, 4.8), sharey=True)
    y = np.arange(len(prof))
    colors = [style.SLOTS[i] for i in range(len(prof))]
    for ax, (col, title, fmt) in zip(axes, cols):
        ax.barh(y, prof[col], height=0.55, color=colors)
        for yi, v in zip(y, prof[col]):
            ax.text(v, yi, "  " + fmt.format(v).replace(".", ","), va="center", fontsize=8.5, color=style.INK_2)
        ax.set_xlim(0, prof[col].max() * 1.45)
        ax.set_title(title, fontsize=9.5)
        ax.grid(axis="y", visible=False)
        ax.grid(axis="x", visible=False)
        ax.set_xticks([])
        ax.spines["bottom"].set_visible(False)
    axes[0].set_yticks(y, prof["name"])
    axes[0].invert_yaxis()
    fig.tight_layout(rect=(0, 0, 1, 0.84), w_pad=1)
    fig.text(0.01, 0.985, "Os grupos de jogadores do ARC Raiders", fontsize=14, fontweight="bold", va="top")
    fig.text(0.01, 0.925, "K-Means sobre recência, frequência e engajamento dos 416,8 mil autores de análises da Steam",
             color=style.INK_2, fontsize=10, va="top")
    style.source_note(fig, "Fonte: análises da Steam, perfil de jogo do autor em 25/09/2026 [O]. Frequência = horas por semana entre o lançamento "
                           "e a última sessão. Autores de análises são mais engajados que a média dos compradores.")
    return style.save(fig, "09b_perfil_grupos")


def fig_complaints_by_cluster(cp: pd.DataFrame, order: list):
    from matplotlib.colors import LinearSegmentedColormap
    cp = cp.loc[order]
    cmap = LinearSegmentedColormap.from_list("blue", style.BLUE_RAMP)
    fig, ax = plt.subplots(figsize=(13, 4.6))
    im = ax.imshow(cp.values, aspect="auto", cmap=cmap, vmin=0, vmax=cp.values.max())
    for i in range(cp.shape[0]):
        for j in range(cp.shape[1]):
            v = cp.values[i, j]
            ax.text(j, i, f"{v:.0f}%", ha="center", va="center", fontsize=9,
                    color="white" if v > cp.values.max() * 0.55 else style.INK)
    short = {"Cheaters e hackers": "Cheaters", "Ratos, campers e traição": "Ratos e\ncampers",
             "Bugs, travamentos e servidores": "Bugs e\nservidores", "Exploits e duplicação de itens": "Exploits",
             "Falta de PvE / excesso de PvP": "Falta de PvE", "Falta de conteúdo e jogo abandonado": "Falta de\nconteúdo",
             "Balanceamento (nerfs e buffs)": "Balancea-\nmento", "Pareamento (matchmaking)": "Pareamento"}
    ax.set_xticks(range(cp.shape[1]), [short.get(c, c) for c in cp.columns], fontsize=9)
    ax.set_yticks(range(cp.shape[0]), cp.index)
    ax.grid(False)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.tick_params(length=0)
    ax.set_title("Do que cada grupo reclama")
    style.subtitle(ax, "% das análises negativas (com texto) de cada grupo que mencionam o tema")
    style.source_note(fig, "Fontes: análises da Steam [O] e classificação da Etapa 5 (precisão de 90%). Uma análise pode ter vários temas.")
    return style.save(fig, "09c_reclamacoes_por_grupo")


def fig_timeline_by_cluster(d: pd.DataFrame, order: list):
    """Quando cada grupo escreveu sua análise e quando jogou pela última vez."""
    fig, axes = plt.subplots(1, 2, figsize=(14, 5), sharey=True)
    months = pd.date_range("2025-11-01", "2026-09-01", freq="MS")
    for ax, col, title in [(axes[0], "month", "Mês da análise"), (axes[1], "last_month", "Mês da última sessão")]:
        tab = d.groupby([col, "name"]).size().unstack(fill_value=0).reindex(months, fill_value=0)[order]
        share = tab.div(tab.sum(axis=0), axis=1) * 100
        for i, n in enumerate(order):
            ax.plot(share.index, share[n], color=style.SLOTS[i], lw=2, label=n)
        ticks = months[::2]
        ax.set_xticks(ticks, [f"{m:%m/%y}" for m in ticks])
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:.0f}%"))
        ax.set_title(title, fontsize=11)
    axes[1].legend(loc="upper left", fontsize=8.5)
    fig.tight_layout(rect=(0, 0, 1, 0.86), w_pad=3)
    fig.text(0.01, 0.985, "Quando cada grupo chegou e quando saiu", fontsize=14, fontweight="bold", va="top")
    fig.text(0.01, 0.93, "Distribuição de cada grupo pelo mês da análise (esquerda) e pelo mês da última sessão (direita)",
             color=style.INK_2, fontsize=10, va="top")
    style.source_note(fig, "Fonte: análises da Steam [O]. Cada linha soma 100% dentro do grupo.")
    return style.save(fig, "09d_grupos_no_tempo")


def main(k: int = 4):
    style.apply()
    d = build_features()
    X = model_matrix(d)
    t = choose_k(X)
    d["cluster"] = KMeans(n_clusters=k, n_init=10, random_state=SEED).fit_predict(X)
    prof = profile_clusters(d)
    names = name_clusters(prof)
    prof["name"] = prof.index.map(names)
    d["name"] = d["cluster"].map(names)
    d["last_month"] = d["last_played"].dt.to_period("M").dt.to_timestamp()
    order = prof.sort_values("E", ascending=False)["name"].tolist()
    cp = complaint_profile(d)

    paths = [fig_choose_k(t, k), fig_profile(prof), fig_complaints_by_cluster(cp, order), fig_timeline_by_cluster(d, order)]
    rfe = d.groupby("name")[["R_score", "F_score", "E_score", "RFE"]].mean().round(2)
    METRICS["k"] = k
    METRICS["perfil"] = prof.set_index("name").round(2).to_dict(orient="index")
    METRICS["notas_rfe_medias"] = rfe.to_dict(orient="index")
    METRICS["reclamacoes_por_grupo_pct"] = cp.round(1).to_dict(orient="index")
    (ROOT / "reports" / "metrics_segmentacao.json").write_text(json.dumps(METRICS, ensure_ascii=False, indent=2), encoding="utf-8")
    d[["review_id", "R", "F", "E", "R_score", "F_score", "E_score", "RFE", "cluster", "name"]].to_parquet(INTERIM / "arc_segments.parquet", index=False)
    for p in paths:
        print("figura:", p.name)
    print(t.round(4).to_string())
    print(prof.round(1).to_string())
    print(cp.round(1).to_string())


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 4)
