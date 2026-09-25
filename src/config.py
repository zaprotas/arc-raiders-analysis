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
