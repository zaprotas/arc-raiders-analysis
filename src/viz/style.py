"""Padrão visual único para todos os gráficos do projeto (matplotlib).

Paleta categórica validada para daltonismo (scripts/validate_palette.js do guia de
visualização): ordem fixa, cor segue o jogo, nunca a posição. O ARC Raiders é
sempre azul; nos gráficos de comparação os concorrentes podem ficar em cinza
(ênfase) quando a identidade de cada um não importa.
"""
import matplotlib as mpl
import matplotlib.pyplot as plt

from config import FIGURES

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"
CONTEXT_GRAY = "#b9b8b1"  # concorrentes sem destaque

SLOTS = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]

# Cor fixa por jogo (a ordem dos slots é a garantia de contraste para daltonismo)
GAME_COLORS = {
    "ARC Raiders": SLOTS[0],
    "Escape from Tarkov": SLOTS[1],
    "Hunt: Showdown 1896": SLOTS[2],
    "Battlefield 6": SLOTS[3],
    "Marathon": SLOTS[4],
    "Counter-Strike 2": SLOTS[5],
    "Apex Legends": SLOTS[6],
    "PUBG: Battlegrounds": SLOTS[7],
}
ARC = SLOTS[0]

# Sequencial (azul, claro -> escuro) para magnitude
BLUE_RAMP = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#2a78d6", "#1c5cab", "#104281"]


def apply():
    mpl.rcParams.update({
        "figure.facecolor": SURFACE,
        "axes.facecolor": SURFACE,
        "savefig.facecolor": SURFACE,
        "font.family": ["Segoe UI", "DejaVu Sans", "sans-serif"],
        "font.size": 10,
        "text.color": INK,
        "axes.labelcolor": INK_2,
        "axes.titlesize": 13,
        "axes.titleweight": "semibold",
        "axes.titlelocation": "left",
        "axes.titlepad": 30,
        "axes.edgecolor": AXIS,
        "axes.linewidth": 0.8,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "axes.grid.axis": "y",
        "grid.color": GRID,
        "grid.linewidth": 0.8,
        "grid.linestyle": "-",
        "xtick.color": MUTED,
        "ytick.color": MUTED,
        "xtick.labelcolor": INK_2,
        "ytick.labelcolor": INK_2,
        "legend.frameon": False,
        "legend.fontsize": 9,
        "lines.linewidth": 2,
        "lines.solid_capstyle": "round",
        "lines.solid_joinstyle": "round",
        "figure.dpi": 110,
        "savefig.dpi": 160,
        "savefig.bbox": "tight",
    })


def subtitle(ax, text):
    """Subtítulo em tinta secundária logo abaixo do título."""
    ax.text(0, 1.02, text, transform=ax.transAxes, color=INK_2, fontsize=9.5, va="bottom")


def end_labels(ax, items, x_text, min_gap, log=False):
    """Rótulos numa coluna à direita das linhas, sem sobreposição.

    items: lista de (x_fim, y_fim, texto, destaque). Cada rótulo fica em x_text,
    na altura do fim da sua linha ou deslocado o mínimo para não colidir, com uma
    linha-guia fina até o ponto final. min_gap em unidades do eixo y (em décadas
    quando log=True).
    """
    import numpy as np
    to_axis = np.log10 if log else (lambda v: v)
    from_axis = (lambda v: 10 ** v) if log else (lambda v: v)
    positions = []
    for x, y, text, strong in sorted(items, key=lambda it: it[1]):
        pos = to_axis(y)
        if positions and pos - positions[-1] < min_gap:
            pos = positions[-1] + min_gap
        positions.append(pos)
        ax.annotate(text, xy=(x, y), xytext=(x_text, from_axis(pos)), textcoords="data", va="center",
                    fontsize=8.5, color=INK if strong else INK_2, fontweight="bold" if strong else "normal",
                    annotation_clip=False,
                    arrowprops=dict(arrowstyle="-", color=AXIS, lw=0.7, shrinkA=2, shrinkB=3))


def source_note(fig, text):
    fig.text(0.01, -0.02, text, color=MUTED, fontsize=8, ha="left", va="top")


def save(fig, name):
    FIGURES.mkdir(parents=True, exist_ok=True)
    path = FIGURES / f"{name}.png"
    fig.savefig(path)
    plt.close(fig)
    return path


def thousands(x, _pos=None):
    if abs(x) >= 1e6:
        return f"{x / 1e6:.1f} mi".replace(".", ",")
    if abs(x) >= 1e3:
        return f"{x / 1e3:.0f} mil"
    return f"{x:.0f}"
