"""Generate simple placeholder logos for each theme. Run once."""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as patches

THEMES_DIR = Path(__file__).parent / "themes"


def _make_logo(text: str, bg_color: str, fg_color: str, path: Path):
    fig, ax = plt.subplots(figsize=(2.4, 0.8))
    ax.add_patch(patches.FancyBboxPatch(
        (0.02, 0.1), 0.96, 0.8, boxstyle="round,pad=0.05",
        facecolor=bg_color, edgecolor="none",
    ))
    ax.text(0.5, 0.5, text, ha="center", va="center",
            fontsize=14, fontweight="bold", color=fg_color,
            fontfamily="sans-serif")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    fig.savefig(path, bbox_inches="tight", dpi=150, transparent=True)
    plt.close(fig)


if __name__ == "__main__":
    THEMES_DIR.mkdir(exist_ok=True)
    _make_logo("ALPINE\nCAPITAL", "#1B3A5C", "#FFFFFF", THEMES_DIR / "logo_alpine.png")
    _make_logo("EMBER\nWEALTH", "#8B2500", "#FFD700", THEMES_DIR / "logo_ember.png")
    _make_logo("VERDANT\nADVISORS", "#1A5C2E", "#FFFFFF", THEMES_DIR / "logo_verdant.png")
    print("Logos generated in themes/")
