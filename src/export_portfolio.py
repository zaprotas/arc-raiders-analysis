"""Exporta os dados da versão enxuta do caso para o site de portfólio.

Uso: python src/export_portfolio.py <pasta de destino>

Gera, sem identificadores nem texto das análises:
  reclamacoes_amostra.csv   60 mil análises com texto: mês, idioma, voto, horas e temas
  autores_amostra.csv       60 mil autores: recência, frequência, engajamento e voto
  decisao_simulacoes.csv    20 mil simulações: jogadores em jan/2027 e ganho de investir
  metricas.json             números consolidados da análise completa (dados inteiros)
Os notebooks do site rodam o método nas amostras; os gráficos usam metricas.json.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from analysis import decision, projections as pj  # noqa: E402
from analysis.complaints_lexicon import TOPICS  # noqa: E402
from config import INTERIM, ROOT  # noqa: E402

SEED = 2026


def main(dest: Path):
    dest.mkdir(parents=True, exist_ok=True)
    reports = ROOT / "reports"

    topics = pd.read_parquet(INTERIM / "arc_review_topics.parquet")
    top = topics["language"].value_counts().index[:8]
    s = topics.sample(60_000, random_state=SEED)
    out = pd.DataFrame({
        "mes": s["month"].dt.strftime("%Y-%m"),
        "idioma": s["language"].where(s["language"].isin(top), "outros"),
        "recomenda": s["voted_up"].astype(int),
        "horas_na_analise": (s["playtime_at_review_min"] / 60).round(1),
        **{k: s[f"t_{k}"].astype(int) for k in TOPICS},
    })
    out.to_csv(dest / "reclamacoes_amostra.csv", index=False)

    seg = pd.read_parquet(INTERIM / "arc_segments.parquet")
    rev = pd.read_parquet(INTERIM / "arc_reviews.parquet", columns=["review_id", "voted_up", "playtime_2weeks_min"])
    a = seg.merge(rev, on="review_id").sample(60_000, random_state=SEED)
    pd.DataFrame({
        "dias_sem_jogar": a["R"].round(0).astype(int), "horas_semana": a["F"].round(2), "horas_total": a["E"].round(1),
        "recomenda": a["voted_up"].astype(int), "jogou_2_semanas": (a["playtime_2weeks_min"] > 0).astype(int),
    }).to_csv(dest / "autores_amostra.csv", index=False)

    d = decision.outcomes()
    d.sample(20_000, random_state=SEED)[["variante", "jogadores_jan27", "ganho_incremental"]].round(1).to_csv(
        dest / "decisao_simulacoes.csv", index=False)

    # Projeção mensal (medianas) para o gráfico de decisão
    base, pess = pj.run_scenarios(pj.draw("base")), pj.run_scenarios(pj.draw("pessimista"))
    hist = pd.read_csv(INTERIM / "players_monthly.csv", parse_dates=["month"])
    hist = hist[(hist["appid"] == 1808500) & (hist["month"] >= "2026-01-01")].set_index("month")["avg_players"]
    projecao = {
        "historico": {m.strftime("%Y-%m"): round(float(v)) for m, v in hist.items()},
        "meses": [m.strftime("%Y-%m") for m in pj.MONTHS],
        "sem_acao": np.median(base["S0"]["players"], 0).round().tolist(),
        "base": np.median(base["S2"]["players"], 0).round().tolist(),
        "base_p10": np.percentile(base["S2"]["players"], 10, 0).round().tolist(),
        "base_p90": np.percentile(base["S2"]["players"], 90, 0).round().tolist(),
        "pessimista": np.median(pess["S2"]["players"], 0).round().tolist(),
    }

    load = lambda name: json.loads((reports / name).read_text(encoding="utf-8"))  # noqa: E731
    comp, segm, dec, proj = load("metrics_reclamacoes.json"), load("metrics_segmentacao.json"), load("metrics_decisao.json"), load("metrics_projecoes.json")
    negativas = {r["tema"]: r["mencao_negativas"] * 100 for r in comp["validacao"]}
    metricas = {
        "voto": [dict(r, negativas=round(negativas[r["tema"]], 1)) for r in comp["efeito_no_voto_pp"]],
        "validacao": comp["validacao"],
        "grupos": segm["perfil"],
        "decisao": {"resumo": dec["resumo"], "limite": dec["limite"]["limite_jan27"]},
        "projecao": projecao,
        "calibracao": proj["calibracao"],
    }
    (dest / "metricas.json").write_text(json.dumps(metricas, ensure_ascii=False, indent=2), encoding="utf-8")
    for f in sorted(dest.iterdir()):
        print(f"{f.name}: {f.stat().st_size / 1024:.0f} KB")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
