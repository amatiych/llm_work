"""Template engine — loads templates, hydrates placeholders, and renders reports.

This module is the runtime. It never calls an LLM. Given a template_id and fund
data, it produces a finished PDF/PPTX deterministically.
"""

import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

from chart_library import CHART_REGISTRY, set_theme_colors
from adaptive_report import build_pdf, build_pptx
from theme import DEFAULT_THEME

TEMPLATES_DIR = Path(__file__).parent / "templates"


# ─────────────────────────────────────────────────────────────────────
# Template loading & listing
# ─────────────────────────────────────────────────────────────────────

def list_templates() -> list[dict]:
    """Return summary info for all available templates."""
    templates = []
    for path in sorted(TEMPLATES_DIR.glob("*.json")):
        tpl = json.loads(path.read_text())
        templates.append({
            "template_id": tpl["template_id"],
            "name": tpl["name"],
            "description": tpl["description"],
            "match_criteria": tpl.get("match_criteria", {}),
            "n_sections": len(tpl["sections"]),
            "charts": [s["chart"] for s in tpl["sections"] if s.get("chart")],
        })
    return templates


def load_template(template_id: str) -> dict:
    """Load a template by ID."""
    path = TEMPLATES_DIR / f"{template_id}.json"
    if not path.exists():
        available = [p.stem for p in TEMPLATES_DIR.glob("*.json")]
        raise FileNotFoundError(
            f"Template '{template_id}' not found. Available: {available}"
        )
    return json.loads(path.read_text())


# ─────────────────────────────────────────────────────────────────────
# Data profiling — compute all variables that templates can reference
# ─────────────────────────────────────────────────────────────────────

def _max_drawdown(returns: pd.Series) -> float:
    cumulative = (1 + returns).cumprod()
    running_max = cumulative.cummax()
    drawdown = (cumulative - running_max) / running_max
    return float(drawdown.min())


def compute_template_vars(data: dict) -> dict:
    """Compute every variable that a template might reference."""
    r = data["returns"]["return"]
    perf = data["performance"]
    risk = data["risk_scores"]
    alloc = data["allocation"]
    holdings = data["holdings"]

    # Return stats
    ann_ret = ((1 + r.mean()) ** 12 - 1) * 100
    ann_vol = r.std() * np.sqrt(12) * 100
    sharpe = (r.mean() / r.std()) * np.sqrt(12) if r.std() > 0 else 0
    max_dd = _max_drawdown(r) * 100

    # Performance vs benchmark
    port_total = (perf["Portfolio"].iloc[-1] / perf["Portfolio"].iloc[0] - 1) * 100
    bench_total = (perf["Benchmark"].iloc[-1] / perf["Benchmark"].iloc[0] - 1) * 100
    excess = port_total - bench_total

    # Holdings
    weight_col = [c for c in holdings.columns if "weight" in c.lower()][0]
    return_col = [c for c in holdings.columns if "return" in c.lower()]
    return_col = return_col[0] if return_col else None
    weights = holdings[weight_col]
    top_3 = weights.nlargest(3).sum()

    # Risk
    cats = risk["categories"]
    scores = risk["Fund"]
    sorted_risks = sorted(zip(cats, scores), key=lambda x: x[1], reverse=True)
    score_range = max(scores) - min(scores)

    # Allocation
    alloc_cols = [c for c in alloc.columns if c != "date"]
    last_alloc = alloc.iloc[-1]
    first_alloc = alloc.iloc[0]
    changes = {c: abs(last_alloc[c] - first_alloc[c]) for c in alloc_cols}
    largest_shift = max(changes, key=changes.get)
    largest_alloc = max(alloc_cols, key=lambda c: last_alloc[c])

    # Qualitative assessments (deterministic rules, no LLM needed)
    positive_assessment = (
        "strong consistency in generating positive returns"
        if (r > 0).mean() > 0.6
        else "a balanced mix of positive and negative periods"
        if (r > 0).mean() > 0.45
        else "challenging consistency, with fewer than half of months positive"
    )
    excess_assessment = (
        f"This represents significant outperformance, driven by active management decisions."
        if excess > 10
        else f"The portfolio matched or modestly outperformed the benchmark."
        if excess > 0
        else f"The portfolio underperformed the benchmark, reflecting positioning headwinds."
    )
    recovery_assessment = "swift" if ann_vol > 15 and max_dd > -25 else "moderate"
    tail_assessment = (
        "Positive skewness indicates a desirable right-tail asymmetry."
        if float(r.skew()) > 0.3
        else "Negative skewness suggests greater downside tail risk."
        if float(r.skew()) < -0.3
        else "Near-symmetric distribution with balanced tail behavior."
    )
    consistency_assessment = (
        "strong consistency" if sharpe > 1.0
        else "moderate consistency" if sharpe > 0.5
        else "variable performance"
    )
    risk_adjusted_assessment = (
        "excellent risk-adjusted returns" if sharpe > 1.0
        else "adequate risk-adjusted returns" if sharpe > 0.5
        else "below-target risk-adjusted returns"
    )
    allocation_style = (
        "growth-oriented" if last_alloc.get("Equities", 0) > 60
        else "income-oriented" if ann_vol < 5
        else "balanced"
    )
    risk_balance_assessment = (
        "concentrated" if score_range > 5
        else "moderate" if score_range > 3
        else "well-balanced"
    )
    skew_val = float(r.skew())
    skew_assessment = (
        "a favorable bias toward positive returns"
        if skew_val > 0.3
        else "a slight downside bias"
        if skew_val < -0.3
        else "near-symmetric return behavior"
    )

    # Find cash weight
    cash_cols = [c for c in alloc_cols if "cash" in c.lower()]
    cash_weight = round(last_alloc[cash_cols[0]], 1) if cash_cols else 0

    # Holdings stats
    holding_returns = holdings[return_col].tolist() if return_col else []
    all_positive = all(v >= 0 for v in holding_returns) if holding_returns else True
    positive_holdings_assessment = (
        "All holdings delivered positive trailing returns, reflecting disciplined selection."
        if all_positive
        else "Returns were mixed, with some holdings detracting from overall performance."
    )

    return {
        # Fund
        "fund_name": data["name"],
        # Returns
        "n_months": len(r),
        "annualized_return_pct": round(ann_ret, 2),
        "annualized_vol_pct": round(ann_vol, 2),
        "sharpe_ratio": round(sharpe, 2),
        "mean_monthly_pct": round(r.mean() * 100, 3),
        "max_return_pct": round(r.max() * 100, 2),
        "min_return_pct": round(r.min() * 100, 2),
        "pct_positive_months": round((r > 0).mean() * 100, 1),
        "skewness": round(skew_val, 3),
        "kurtosis": round(float(r.kurtosis()), 3),
        "max_drawdown_pct": round(max_dd, 2),
        # Performance
        "portfolio_total_return_pct": round(port_total, 2),
        "benchmark_total_return_pct": round(bench_total, 2),
        "excess_return_pct": round(excess, 2),
        # Holdings
        "n_holdings": len(holdings),
        "top_holding_weight_pct": round(weights.max(), 1),
        "top_3_concentration_pct": round(top_3, 1),
        "max_holding_return": round(max(holding_returns), 1) if holding_returns else "N/A",
        "min_holding_return": round(min(holding_returns), 1) if holding_returns else "N/A",
        # Risk
        "max_risk_category": sorted_risks[0][0],
        "max_risk_score": sorted_risks[0][1],
        "second_risk_category": sorted_risks[1][0],
        "min_risk_category": sorted_risks[-1][0],
        "min_risk_score": sorted_risks[-1][1],
        "avg_risk_score": round(np.mean(scores), 2),
        "score_range": round(score_range, 1),
        # Allocation
        "n_asset_classes": len(alloc_cols),
        "largest_allocation_name": largest_alloc,
        "largest_allocation_pct": round(last_alloc[largest_alloc], 1),
        "largest_shift_name": largest_shift,
        "largest_shift_magnitude": round(changes[largest_shift], 1),
        "cash_weight_pct": cash_weight,
        # Assessments
        "positive_assessment": positive_assessment,
        "excess_assessment": excess_assessment,
        "recovery_assessment": recovery_assessment,
        "tail_assessment": tail_assessment,
        "consistency_assessment": consistency_assessment,
        "risk_adjusted_assessment": risk_adjusted_assessment,
        "allocation_style": allocation_style,
        "risk_balance_assessment": risk_balance_assessment,
        "skew_assessment": skew_assessment,
        "positive_holdings_assessment": positive_holdings_assessment,
        # Extra data flags
        "has_sector_exposure": "sector_exposure" in data,
        "has_income_stream": "income_stream" in data,
        "has_duration_profile": "duration_profile" in data,
        "has_monthly_pnl": "monthly_pnl" in data,
    }


# ─────────────────────────────────────────────────────────────────────
# Template hydration — fill placeholders with computed variables
# ─────────────────────────────────────────────────────────────────────

def _fill(template_str: str, variables: dict) -> str:
    """Replace {placeholder} tokens with values. Unknown placeholders stay as-is."""
    def replacer(match):
        key = match.group(1)
        if key in variables:
            return str(variables[key])
        return match.group(0)
    return re.sub(r"\{(\w+)\}", replacer, template_str)


def hydrate_template(template: dict, variables: dict, data: dict) -> dict:
    """Convert a template + variables into the plan dict expected by build_pdf/build_pptx.

    Filters out sections whose required data is missing, then fills all
    commentary placeholders with computed values.
    """
    plan = {
        "report_title": _fill(template["report_title"], variables),
        "report_subtitle": _fill(template["report_subtitle"], variables),
        "fund_character": None,
        "sections": [],
    }

    for section in template["sections"]:
        # Skip sections that require data we don't have
        requires = section.get("requires_data")
        if requires and requires not in data:
            continue

        # Skip chart sections where the chart function needs missing data
        chart_id = section.get("chart")
        if chart_id and chart_id == "sector_bar" and "sector_exposure" not in data:
            continue
        if chart_id and chart_id == "income_chart" and "income_stream" not in data:
            continue
        if chart_id and chart_id == "duration_bar" and "duration_profile" not in data:
            continue

        plan["sections"].append({
            "title": section["title"],
            "chart": chart_id,
            "commentary": _fill(section["commentary_template"], variables),
            "priority": "high",
            "include_holdings_table": section.get("include_holdings_table", False),
        })

    return plan


# ─────────────────────────────────────────────────────────────────────
# Chart generation + report building (reuses adaptive_report builders)
# ─────────────────────────────────────────────────────────────────────

def generate_charts(plan: dict, data: dict, output_dir: str) -> dict[str, str]:
    """Generate only the charts referenced in the plan."""
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    chart_paths = {}
    for section in plan["sections"]:
        chart_id = section.get("chart")
        if chart_id and chart_id in CHART_REGISTRY and chart_id not in chart_paths:
            path = f"{output_dir}/{chart_id}.png"
            chart_paths[chart_id] = CHART_REGISTRY[chart_id]["fn"](data, path)
    return chart_paths


def render(template_id: str, data: dict, output_dir: str, fmt: str = "all",
           theme: dict | None = None) -> dict[str, str]:
    """Full pipeline: load template → hydrate → generate charts → build reports.

    Args:
        theme: Optional theme dict (from theme.load_theme). Applies branding
               to charts (color palette) and to PDF/PPTX (colors, logo, fonts).
    Returns dict of output paths.
    """
    theme = theme or DEFAULT_THEME
    template = load_template(template_id)
    variables = compute_template_vars(data)
    plan = hydrate_template(template, variables, data)

    # Save the hydrated plan for inspection
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    plan_path = f"{output_dir}/hydrated_plan.json"
    Path(plan_path).write_text(json.dumps(plan, indent=2))

    # Apply theme colors to chart palette before generating
    set_theme_colors(theme.get("chart_palette"))
    chart_paths = generate_charts(plan, data, output_dir)
    outputs = {"plan": plan_path}

    if fmt in ("pdf", "all"):
        outputs["pdf"] = build_pdf(plan, chart_paths, data,
                                   f"{output_dir}/report.pdf", theme=theme)

    if fmt in ("pptx", "all"):
        outputs["pptx"] = build_pptx(plan, chart_paths, data,
                                     f"{output_dir}/report.pptx", theme=theme)

    return outputs
