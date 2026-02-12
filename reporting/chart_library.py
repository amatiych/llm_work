"""Extended chart library — each chart is registered by ID and can be invoked by the LLM planner."""

import io
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd

DEFAULT_COLORS = ["#2E5090", "#E8833A", "#4CAF50", "#9C27B0", "#F44336", "#00BCD4", "#795548", "#607D8B"]
COLORS = DEFAULT_COLORS  # module-level default, overridden by set_theme_colors()

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.size": 10,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "figure.dpi": 150,
})


def set_theme_colors(palette: list[str] | None = None):
    """Override the chart color palette for the current session."""
    global COLORS
    COLORS = (palette or DEFAULT_COLORS)[:8]
    # Pad to 8 if fewer provided
    while len(COLORS) < 8:
        COLORS.append(DEFAULT_COLORS[len(COLORS) % len(DEFAULT_COLORS)])


def _save(fig: plt.Figure, path: str) -> str:
    fig.tight_layout()
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, bbox_inches="tight", dpi=150)
    plt.close(fig)
    return path


# ── 1. Histogram ─────────────────────────────────────────────────────

def histogram(data: dict, path: str) -> str:
    """Return distribution histogram."""
    returns = data["returns"]
    fig, ax = plt.subplots(figsize=(7, 4))
    r = returns["return"] * 100
    ax.hist(r, bins=25, color=COLORS[0], edgecolor="white", alpha=0.85)
    mean = r.mean()
    ax.axvline(mean, color=COLORS[1], linewidth=2, linestyle="--", label=f"Mean: {mean:.2f}%")
    # Mark the tails
    q5, q95 = np.percentile(r, [5, 95])
    ax.axvline(q5, color=COLORS[4], linewidth=1, linestyle=":", alpha=0.7, label=f"5th pctl: {q5:.1f}%")
    ax.axvline(q95, color=COLORS[2], linewidth=1, linestyle=":", alpha=0.7, label=f"95th pctl: {q95:.1f}%")
    ax.set_xlabel("Monthly Return (%)")
    ax.set_ylabel("Frequency")
    ax.set_title("Return Distribution", fontsize=12, fontweight="bold")
    ax.legend(fontsize=8)
    return _save(fig, path)


# ── 2. Line chart (performance vs benchmark) ────────────────────────

def line_chart(data: dict, path: str) -> str:
    """Cumulative performance vs benchmark."""
    perf = data["performance"]
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.plot(perf["date"], perf["Portfolio"], color=COLORS[0], linewidth=2, label="Portfolio")
    ax.plot(perf["date"], perf["Benchmark"], color=COLORS[1], linewidth=2, linestyle="--", label="Benchmark")
    ax.fill_between(perf["date"], perf["Portfolio"], perf["Benchmark"], alpha=0.08, color=COLORS[0])
    ax.set_ylabel("Cumulative Value ($)")
    ax.set_title("Portfolio vs Benchmark", fontsize=12, fontweight="bold")
    ax.legend(loc="upper left")
    ax.yaxis.set_major_formatter(mticker.FormatStrFormatter("$%.0f"))
    fig.autofmt_xdate()
    return _save(fig, path)


# ── 3. Spider / Radar chart ─────────────────────────────────────────

def spider_chart(data: dict, path: str) -> str:
    """Risk factor radar chart."""
    risk = data["risk_scores"]
    cats = risk["categories"]
    vals = risk["Fund"]
    n = len(cats)
    angles = np.linspace(0, 2 * np.pi, n, endpoint=False).tolist()
    angles += angles[:1]
    vals_closed = vals + vals[:1]
    fig, ax = plt.subplots(figsize=(6, 6), subplot_kw=dict(polar=True))
    ax.plot(angles, vals_closed, linewidth=2, color=COLORS[0])
    ax.fill(angles, vals_closed, alpha=0.2, color=COLORS[0])
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(cats, size=9)
    ax.set_ylim(0, 10)
    ax.set_title("Risk Factor Profile", fontsize=12, fontweight="bold", y=1.08)
    return _save(fig, path)


# ── 4. Stacked area (allocation over time) ──────────────────────────

def stacked_area(data: dict, path: str) -> str:
    """Asset allocation over time."""
    alloc = data["allocation"]
    cols = [c for c in alloc.columns if c != "date"]
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.stackplot(alloc["date"], *[alloc[c] for c in cols], labels=cols, colors=COLORS[:len(cols)], alpha=0.85)
    ax.set_ylabel("Allocation (%)")
    ax.set_title("Allocation Over Time", fontsize=12, fontweight="bold")
    ax.legend(loc="upper left", fontsize=8)
    ax.set_ylim(0, 100)
    ax.yaxis.set_major_formatter(mticker.PercentFormatter())
    fig.autofmt_xdate()
    return _save(fig, path)


# ── 5. Drawdown chart ────────────────────────────────────────────────

def drawdown_chart(data: dict, path: str) -> str:
    """Underwater / drawdown chart."""
    perf = data["performance"]
    cumulative = perf["Portfolio"]
    running_max = cumulative.cummax()
    drawdown = (cumulative - running_max) / running_max * 100
    fig, ax = plt.subplots(figsize=(7, 3.5))
    ax.fill_between(perf["date"], drawdown, 0, color=COLORS[4], alpha=0.4)
    ax.plot(perf["date"], drawdown, color=COLORS[4], linewidth=1)
    ax.set_ylabel("Drawdown (%)")
    ax.set_title("Drawdown Analysis", fontsize=12, fontweight="bold")
    max_dd = drawdown.min()
    max_dd_date = perf["date"].iloc[drawdown.argmin()]
    ax.annotate(
        f"Max: {max_dd:.1f}%", xy=(max_dd_date, max_dd),
        xytext=(max_dd_date, max_dd - 2),
        fontsize=9, color=COLORS[4], fontweight="bold",
        arrowprops=dict(arrowstyle="->", color=COLORS[4]),
    )
    fig.autofmt_xdate()
    return _save(fig, path)


# ── 6. Pie chart (current allocation) ───────────────────────────────

def pie_chart(data: dict, path: str) -> str:
    """Current allocation pie/donut chart."""
    alloc = data["allocation"]
    cols = [c for c in alloc.columns if c != "date"]
    latest = alloc.iloc[-1]
    values = [latest[c] for c in cols]
    fig, ax = plt.subplots(figsize=(6, 6))
    wedges, texts, autotexts = ax.pie(
        values, labels=cols, autopct="%1.1f%%",
        colors=COLORS[:len(cols)], pctdistance=0.8,
        wedgeprops=dict(width=0.45, edgecolor="white"),
    )
    for t in autotexts:
        t.set_fontsize(9)
    ax.set_title("Current Allocation", fontsize=12, fontweight="bold")
    return _save(fig, path)


# ── 7. Rolling returns ───────────────────────────────────────────────

def rolling_returns(data: dict, path: str) -> str:
    """Rolling 12-month return chart."""
    returns = data["returns"]
    r = returns["return"]
    rolling_12m = r.rolling(12).apply(lambda x: (1 + x).prod() - 1) * 100
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.plot(returns["date"], rolling_12m, color=COLORS[0], linewidth=2)
    ax.axhline(0, color="grey", linewidth=0.8, linestyle="--")
    ax.fill_between(returns["date"], rolling_12m, 0, where=(rolling_12m >= 0), color=COLORS[2], alpha=0.2)
    ax.fill_between(returns["date"], rolling_12m, 0, where=(rolling_12m < 0), color=COLORS[4], alpha=0.2)
    ax.set_ylabel("Rolling 12M Return (%)")
    ax.set_title("Rolling 12-Month Returns", fontsize=12, fontweight="bold")
    fig.autofmt_xdate()
    return _save(fig, path)


# ── 8. Top/Bottom contributors bar chart ─────────────────────────────

def contributor_bar(data: dict, path: str) -> str:
    """Top and bottom return contributors (horizontal bar)."""
    holdings = data["holdings"]
    name_col = holdings.columns[0]
    if "1Y Return (%)" in holdings.columns:
        ret_col = "1Y Return (%)"
    else:
        ret_col = [c for c in holdings.columns if "return" in c.lower()][0]
    df = holdings[[name_col, ret_col]].sort_values(ret_col)
    colors_list = [COLORS[4] if v < 0 else COLORS[2] for v in df[ret_col]]
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.barh(df[name_col], df[ret_col], color=colors_list, edgecolor="white")
    ax.axvline(0, color="grey", linewidth=0.8)
    ax.set_xlabel("1Y Return (%)")
    ax.set_title("Holding Performance: Winners & Losers", fontsize=12, fontweight="bold")
    return _save(fig, path)


# ── 9. Yield / Income stream chart ──────────────────────────────────

def income_chart(data: dict, path: str) -> str:
    """Income per unit over time (for income-oriented funds)."""
    if "income_stream" not in data:
        return _placeholder(path, "Income Stream (no data)")
    inc = data["income_stream"]
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.bar(inc["date"], inc["income_per_unit"], width=60, color=COLORS[0], alpha=0.7, edgecolor="white")
    ax.plot(inc["date"], inc["income_per_unit"], color=COLORS[1], linewidth=2, marker="o", markersize=4)
    ax.set_ylabel("Income per Unit ($)")
    ax.set_title("Quarterly Income Distribution", fontsize=12, fontweight="bold")
    fig.autofmt_xdate()
    return _save(fig, path)


# ── 10. Duration profile bar chart ──────────────────────────────────

def duration_bar(data: dict, path: str) -> str:
    """Duration bucket exposure (for fixed-income funds)."""
    if "duration_profile" not in data:
        return _placeholder(path, "Duration Profile (no data)")
    dur = data["duration_profile"]
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.bar(dur["Bucket"], dur["Weight (%)"], color=COLORS[0], edgecolor="white", alpha=0.85)
    ax.set_ylabel("Weight (%)")
    ax.set_title("Duration Bucket Exposure", fontsize=12, fontweight="bold")
    for i, v in enumerate(dur["Weight (%)"]):
        ax.text(i, v + 0.5, f"{v:.1f}%", ha="center", fontsize=9)
    return _save(fig, path)


# ── 11. Sector concentration bar chart ───────────────────────────────

def sector_bar(data: dict, path: str) -> str:
    """Sector concentration breakdown."""
    if "sector_exposure" not in data:
        return _placeholder(path, "Sector Exposure (no data)")
    sec = data["sector_exposure"]
    fig, ax = plt.subplots(figsize=(7, 4))
    bars = ax.barh(sec["Sector"], sec["Weight (%)"], color=COLORS[:len(sec)], edgecolor="white")
    ax.set_xlabel("Weight (%)")
    ax.set_title("Sector Concentration", fontsize=12, fontweight="bold")
    ax.invert_yaxis()
    for bar, val in zip(bars, sec["Weight (%)"]):
        ax.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height() / 2,
                f"{val:.1f}%", va="center", fontsize=9)
    return _save(fig, path)


# ── Placeholder ──────────────────────────────────────────────────────

def _placeholder(path: str, label: str) -> str:
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.text(0.5, 0.5, label, ha="center", va="center", fontsize=14, color="grey")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    return _save(fig, path)


# ── Registry ─────────────────────────────────────────────────────────

CHART_REGISTRY: dict[str, dict] = {
    "histogram": {
        "fn": histogram,
        "label": "Return Distribution Histogram",
        "description": "Shows frequency distribution of monthly returns with mean and percentile markers. Use when return distribution shape matters (fat tails, skewness).",
    },
    "line_chart": {
        "fn": line_chart,
        "label": "Performance vs Benchmark",
        "description": "Cumulative performance line chart comparing portfolio to benchmark. Standard for any fund with a benchmark.",
    },
    "spider_chart": {
        "fn": spider_chart,
        "label": "Risk Factor Radar",
        "description": "Radar/spider chart showing scores across risk dimensions. Use when risk profile is uneven or has notable outliers.",
    },
    "stacked_area": {
        "fn": stacked_area,
        "label": "Allocation Over Time",
        "description": "Stacked area showing how asset allocation changed over time. Best when allocation has shifted meaningfully.",
    },
    "drawdown_chart": {
        "fn": drawdown_chart,
        "label": "Drawdown Analysis",
        "description": "Underwater chart showing peak-to-trough losses. Critical for high-volatility funds or those with significant drawdowns.",
    },
    "pie_chart": {
        "fn": pie_chart,
        "label": "Current Allocation Breakdown",
        "description": "Donut chart of current allocation. Best for funds with many distinct asset classes or diversified portfolios.",
    },
    "rolling_returns": {
        "fn": rolling_returns,
        "label": "Rolling 12-Month Returns",
        "description": "Rolling 12-month return over time. Shows return consistency/volatility. Use for funds with variable performance.",
    },
    "contributor_bar": {
        "fn": contributor_bar,
        "label": "Top/Bottom Contributors",
        "description": "Horizontal bar chart of holding-level returns. Best for concentrated portfolios with wide return dispersion.",
    },
    "income_chart": {
        "fn": income_chart,
        "label": "Income Distribution",
        "description": "Quarterly income per unit over time. Only for income-oriented funds with yield data.",
    },
    "duration_bar": {
        "fn": duration_bar,
        "label": "Duration Bucket Exposure",
        "description": "Bar chart of fixed-income duration profile. Only for bond-heavy funds with duration data.",
    },
    "sector_bar": {
        "fn": sector_bar,
        "label": "Sector Concentration",
        "description": "Horizontal bar chart of sector weights. Use for equity-heavy funds with sector concentration.",
    },
}
