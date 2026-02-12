"""Chart generation for reports."""

import io
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd

# Style constants
COLORS = ["#2E5090", "#E8833A", "#4CAF50", "#9C27B0", "#F44336", "#00BCD4"]
FONT = {"family": "sans-serif", "size": 10}
plt.rcParams.update({
    "font.family": "sans-serif",
    "font.size": 10,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "figure.dpi": 150,
})


def _save(fig: plt.Figure, path: str | None) -> str | io.BytesIO:
    """Save figure to file or return as bytes buffer."""
    fig.tight_layout()
    if path:
        fig.savefig(path, bbox_inches="tight", dpi=150)
        plt.close(fig)
        return path
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=150)
    plt.close(fig)
    buf.seek(0)
    return buf


def histogram(returns: pd.DataFrame, path: str | None = None) -> str | io.BytesIO:
    """Generate a histogram of portfolio returns."""
    fig, ax = plt.subplots(figsize=(7, 4))
    data = returns["return"] * 100
    ax.hist(data, bins=20, color=COLORS[0], edgecolor="white", alpha=0.85)
    mean = data.mean()
    ax.axvline(mean, color=COLORS[1], linewidth=2, linestyle="--", label=f"Mean: {mean:.2f}%")
    ax.set_xlabel("Monthly Return (%)")
    ax.set_ylabel("Frequency")
    ax.set_title("Distribution of Monthly Portfolio Returns", fontsize=12, fontweight="bold")
    ax.legend()
    return _save(fig, path)


def line_chart(perf: pd.DataFrame, path: str | None = None) -> str | io.BytesIO:
    """Generate a line chart of cumulative performance."""
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.plot(perf["date"], perf["Portfolio"], color=COLORS[0], linewidth=2, label="Portfolio")
    ax.plot(perf["date"], perf["Benchmark"], color=COLORS[1], linewidth=2, linestyle="--", label="Benchmark")
    ax.fill_between(perf["date"], perf["Portfolio"], perf["Benchmark"], alpha=0.1, color=COLORS[0])
    ax.set_ylabel("Cumulative Value ($)")
    ax.set_title("Portfolio vs Benchmark Performance", fontsize=12, fontweight="bold")
    ax.legend(loc="upper left")
    ax.yaxis.set_major_formatter(mticker.FormatStrFormatter("$%.0f"))
    fig.autofmt_xdate()
    return _save(fig, path)


def spider_chart(risk_scores: dict, path: str | None = None) -> str | io.BytesIO:
    """Generate a spider/radar web chart for risk factors."""
    categories = risk_scores["categories"]
    n = len(categories)
    angles = np.linspace(0, 2 * np.pi, n, endpoint=False).tolist()
    angles += angles[:1]  # close the polygon

    fig, ax = plt.subplots(figsize=(6, 6), subplot_kw=dict(polar=True))

    for idx, (label, key) in enumerate(
        [("Fund A", "Fund A"), ("Fund B", "Fund B")]
    ):
        values = risk_scores[key] + risk_scores[key][:1]
        ax.plot(angles, values, linewidth=2, color=COLORS[idx], label=label)
        ax.fill(angles, values, alpha=0.15, color=COLORS[idx])

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(categories, size=9)
    ax.set_ylim(0, 10)
    ax.set_yticks([2, 4, 6, 8, 10])
    ax.set_yticklabels(["2", "4", "6", "8", "10"], size=8, color="grey")
    ax.set_title("Risk Factor Comparison", fontsize=12, fontweight="bold", y=1.08)
    ax.legend(loc="upper right", bbox_to_anchor=(1.25, 1.1))
    return _save(fig, path)


def stacked_area_chart(alloc: pd.DataFrame, path: str | None = None) -> str | io.BytesIO:
    """Generate a stacked area chart for asset allocation over time."""
    fig, ax = plt.subplots(figsize=(7, 4))
    cols = ["Equities", "Fixed Income", "Alternatives", "Cash"]
    ax.stackplot(
        alloc["date"],
        *[alloc[c] for c in cols],
        labels=cols,
        colors=COLORS[:4],
        alpha=0.85,
    )
    ax.set_ylabel("Allocation (%)")
    ax.set_title("Asset Allocation Over Time", fontsize=12, fontweight="bold")
    ax.legend(loc="upper left", fontsize=8)
    ax.set_ylim(0, 100)
    ax.yaxis.set_major_formatter(mticker.PercentFormatter())
    fig.autofmt_xdate()
    return _save(fig, path)


def generate_all_charts(output_dir: str = "output") -> dict[str, str]:
    """Generate all charts and save to output directory."""
    from data import (
        get_portfolio_returns,
        get_performance_timeseries,
        get_risk_scores,
        get_asset_allocation_timeseries,
    )

    Path(output_dir).mkdir(parents=True, exist_ok=True)
    paths = {}
    paths["histogram"] = histogram(get_portfolio_returns(), f"{output_dir}/histogram.png")
    paths["line_chart"] = line_chart(get_performance_timeseries(), f"{output_dir}/line_chart.png")
    paths["spider_chart"] = spider_chart(get_risk_scores(), f"{output_dir}/spider_chart.png")
    paths["stacked_area"] = stacked_area_chart(
        get_asset_allocation_timeseries(), f"{output_dir}/stacked_area.png"
    )
    return paths


if __name__ == "__main__":
    paths = generate_all_charts()
    for name, p in paths.items():
        print(f"  {name}: {p}")
