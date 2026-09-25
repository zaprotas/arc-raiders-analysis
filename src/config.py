"""Configuração compartilhada: caminhos e lista de jogos comparados."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
INTERIM = ROOT / "data" / "interim"
PROCESSED = ROOT / "data" / "processed"
FIGURES = ROOT / "reports" / "figures"

USER_AGENT = "arc-raiders-portfolio-analysis/1.0 (estudo acadêmico)"

ARC_RAIDERS = 1808500

# appid da Steam -> (nome, grupo)
GAMES = {
    1808500: ("ARC Raiders", "arc_raiders"),
    # Extraction shooters
    3932890: ("Escape from Tarkov", "extraction"),
    4091290: ("Escape from Tarkov: PVE Zone", "extraction_pve"),
    594650: ("Hunt: Showdown 1896", "extraction"),
    3065800: ("Marathon", "extraction"),
    2016590: ("Dark and Darker", "extraction"),
    868270: ("The Cycle: Frontier", "extraction"),
    2479810: ("Gray Zone Warfare", "extraction"),
    2507950: ("Delta Force", "extraction_hybrid"),
    # FPS consolidados
    730: ("Counter-Strike 2", "fps"),
    1172470: ("Apex Legends", "fps"),
    578080: ("PUBG: Battlegrounds", "fps"),
    2807960: ("Battlefield 6", "fps"),
    359550: ("Tom Clancy's Rainbow Six Siege", "fps"),
    # Referências para ciclo de atualizações e PvE
    553850: ("HELLDIVERS 2", "reference_pve"),
    275850: ("No Man's Sky", "reference_updates"),
}

# Mês de estreia na Steam (0 = mês de lançamento). Alinha os ciclos de vida.
# Observações: Apex chegou à Steam em 2020, já gratuito e lançado em outra loja;
# Tarkov chegou à Steam em nov/2025 (o jogo existe desde 2016); CS2 herda o
# histórico do CS:GO (2012) e fica fora das comparações de ciclo de vida.
STEAM_LAUNCH = {
    1808500: "2025-10", 3932890: "2025-11", 594650: "2018-02", 3065800: "2026-03",
    2016590: "2024-06", 868270: "2022-06", 2479810: "2024-04", 2507950: "2024-12",
    1172470: "2020-11", 578080: "2017-03", 2807960: "2025-10", 359550: "2015-12",
    553850: "2024-02", 275850: "2016-08",
}
LIFECYCLE_EXCLUDE = {730, 1172470, 3932890}  # sem lançamento comparável na Steam
