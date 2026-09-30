"""Roda o projeto inteiro, na ordem, a partir dos dados brutos.

Uso:
  python src/pipeline.py            # limpeza + análises + notebooks (usa data/raw e data/external)
  python src/pipeline.py --coletar  # refaz também a coleta (as análises da Steam levam algumas horas)

Etapas e tempo aproximado (sem coleta): ~15 minutos.
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable

COLETA = [
    ["src/collect/steamcharts.py"],
    ["src/collect/steam_reviews.py", "summary"],
    ["src/collect/steam_reviews.py", "full", "1808500", "recent", "all"],
    ["src/collect/steam_news.py"],
    ["src/collect/official_posts.py"],
]
LIMPEZA = [
    ["src/clean/players.py"],
    ["src/clean/twitch.py"],
    ["src/clean/events.py"],
    ["src/clean/reviews.py"],
]
ANALISES = [
    ["src/analysis/diagnostics.py"],
    ["src/analysis/complaints.py", "tag"],
    ["src/analysis/complaints.py", "report"],
    ["src/analysis/segmentation.py"],
    ["src/analysis/revenue.py"],
    ["src/analysis/projections.py"],
    ["src/analysis/decision.py"],
]
NOTEBOOKS = ["01_diagnostico", "02_reclamacoes", "03_segmentacao", "04_receita", "05_projecoes", "06_decisao"]


def rodar(args, cwd=ROOT):
    print(">", " ".join(args), flush=True)
    subprocess.run([PY, *args], cwd=cwd, check=True)


def main():
    etapas = (COLETA if "--coletar" in sys.argv else []) + LIMPEZA + ANALISES
    for etapa in etapas:
        rodar(etapa)
    for nb in NOTEBOOKS:
        rodar([f"build_{nb}.py"], cwd=ROOT / "notebooks")
        rodar(["-m", "jupyter", "nbconvert", "--to", "notebook", "--execute", "--inplace",
               "--ExecutePreprocessor.timeout=1800", f"{nb}.ipynb"], cwd=ROOT / "notebooks")
    print("\nPronto: figuras em reports/figures, métricas em reports/*.json, notebooks executados.")


if __name__ == "__main__":
    main()
