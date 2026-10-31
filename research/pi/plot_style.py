"""Shared figure style: thin marks, recessive grid, one chart surface, Korean labels."""
import matplotlib as mpl
import matplotlib.pyplot as plt

INK = "#0b0b0b"
INK2 = "#52514e"
GRID = "#e4e3df"
SURFACE = "#fcfcfb"
# Categorical slots in fixed order, used for designs and versions.
BLUE, ORANGE, AQUA, YELLOW = "#2a78d6", "#eb6834", "#1baf7a", "#eda100"
NEUTRAL = "#8a8983"
# Diverging ramp for temperature departures: cool blue, neutral midpoint, warm orange.
DT_COLORS = {-2: "#1f5fae", -1: "#6fa3e0", 0: "#8a8983", 1: "#f09a75", 2: "#c94a1c"}


def setup():
    mpl.rcParams.update({
        "font.family": "Malgun Gothic",
        "axes.unicode_minus": False,
        "figure.facecolor": SURFACE,
        "axes.facecolor": SURFACE,
        "savefig.facecolor": SURFACE,
        "axes.edgecolor": INK2,
        "axes.labelcolor": INK2,
        "axes.titlecolor": INK,
        "axes.titlesize": 11,
        "axes.titleweight": "bold",
        "axes.titlelocation": "left",
        "axes.labelsize": 9.5,
        "xtick.color": INK2,
        "ytick.color": INK2,
        "xtick.labelsize": 9,
        "ytick.labelsize": 9,
        "axes.grid": True,
        "axes.axisbelow": True,
        "grid.color": GRID,
        "grid.linewidth": 0.7,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "lines.linewidth": 1.6,
        "legend.frameon": False,
        "legend.fontsize": 9,
        "pdf.fonttype": 42,
    })


def save(fig, path_stem):
    fig.savefig(f"{path_stem}.png", dpi=200, bbox_inches="tight")
    fig.savefig(f"{path_stem}.pdf", bbox_inches="tight")
    plt.close(fig)
