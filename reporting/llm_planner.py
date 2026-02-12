"""LLM Report Planner — Claude analyzes the data and decides the report structure."""

import json
import os

import anthropic
import numpy as np
import pandas as pd


# ─────────────────────────────────────────────────────────────────────
# Data serialization — build a rich data profile for the LLM
# ─────────────────────────────────────────────────────────────────────

def _profile_returns(df: pd.DataFrame) -> dict:
    r = df["return"]
    return {
        "period": f"{df['date'].min():%Y-%m} to {df['date'].max():%Y-%m}",
        "n_months": len(r),
        "mean_monthly_pct": round(r.mean() * 100, 3),
        "std_monthly_pct": round(r.std() * 100, 3),
        "annualized_return_pct": round(((1 + r.mean()) ** 12 - 1) * 100, 2),
        "annualized_vol_pct": round(r.std() * np.sqrt(12) * 100, 2),
        "sharpe_ratio": round((r.mean() / r.std()) * np.sqrt(12), 2) if r.std() > 0 else 0,
        "max_return_pct": round(r.max() * 100, 2),
        "min_return_pct": round(r.min() * 100, 2),
        "pct_positive_months": round((r > 0).mean() * 100, 1),
        "skewness": round(float(r.skew()), 3),
        "kurtosis": round(float(r.kurtosis()), 3),
        "max_drawdown_pct": round(_max_drawdown(r) * 100, 2),
    }


def _max_drawdown(returns: pd.Series) -> float:
    cumulative = (1 + returns).cumprod()
    running_max = cumulative.cummax()
    drawdown = (cumulative - running_max) / running_max
    return float(drawdown.min())


def _profile_performance(df: pd.DataFrame) -> dict:
    pt = df["Portfolio"].iloc[-1] / df["Portfolio"].iloc[0] - 1
    bt = df["Benchmark"].iloc[-1] / df["Benchmark"].iloc[0] - 1
    return {
        "portfolio_total_return_pct": round(pt * 100, 2),
        "benchmark_total_return_pct": round(bt * 100, 2),
        "excess_return_pct": round((pt - bt) * 100, 2),
    }


def _profile_holdings(df: pd.DataFrame) -> dict:
    weight_col = [c for c in df.columns if "weight" in c.lower()][0]
    weights = df[weight_col]
    top_3_weight = weights.nlargest(3).sum()
    return {
        "n_holdings": len(df),
        "top_3_concentration_pct": round(top_3_weight, 1),
        "top_holding_weight_pct": round(weights.max(), 1),
        "has_negative_returns": bool(any(df[c].min() < 0 for c in df.columns if "return" in c.lower())),
        "columns_available": list(df.columns),
        "sample": df.head(5).to_dict(orient="records"),
    }


def _profile_risk(risk: dict) -> dict:
    scores = risk["Fund"]
    cats = risk["categories"]
    return {
        "scores": dict(zip(cats, scores)),
        "avg_score": round(np.mean(scores), 2),
        "max_score": round(max(scores), 1),
        "max_score_category": cats[int(np.argmax(scores))],
        "min_score": round(min(scores), 1),
        "min_score_category": cats[int(np.argmin(scores))],
        "score_range": round(max(scores) - min(scores), 1),
    }


def _profile_allocation(df: pd.DataFrame) -> dict:
    cols = [c for c in df.columns if c != "date"]
    first = df.iloc[0]
    last = df.iloc[-1]
    changes = {c: round(last[c] - first[c], 1) for c in cols}
    max_shift = max(changes, key=lambda c: abs(changes[c]))
    return {
        "asset_classes": cols,
        "n_asset_classes": len(cols),
        "current": {c: round(last[c], 1) for c in cols},
        "change_over_period": changes,
        "largest_shift": max_shift,
        "largest_shift_magnitude": abs(changes[max_shift]),
    }


def _detect_extra_data(data: dict) -> list[str]:
    """Detect which optional datasets are available."""
    extras = []
    if "sector_exposure" in data:
        extras.append("sector_exposure")
    if "monthly_pnl" in data:
        extras.append("monthly_pnl")
    if "income_stream" in data:
        extras.append("income_stream")
    if "duration_profile" in data:
        extras.append("duration_profile")
    return extras


def build_data_profile(data: dict) -> str:
    """Build a comprehensive JSON data profile for the LLM."""
    profile = {
        "fund_name": data["name"],
        "return_statistics": _profile_returns(data["returns"]),
        "performance_vs_benchmark": _profile_performance(data["performance"]),
        "holdings_profile": _profile_holdings(data["holdings"]),
        "risk_profile": _profile_risk(data["risk_scores"]),
        "allocation_profile": _profile_allocation(data["allocation"]),
        "extra_datasets_available": _detect_extra_data(data),
    }
    return json.dumps(profile, indent=2)


# ─────────────────────────────────────────────────────────────────────
# LLM Planner — prompt + API call
# ─────────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """\
You are a senior investment report architect. You will receive a JSON profile of a fund's
quantitative data. Your job is to DESIGN the report — choosing which sections and charts
to include based on what is most relevant and insightful for THIS specific fund.

## Available Charts (pick 5-7 that best tell this fund's story)

- "histogram"       — Return distribution. Best when distribution has fat tails, skewness, or unusual shape.
- "line_chart"      — Performance vs benchmark. Standard inclusion for most funds.
- "spider_chart"    — Risk factor radar. Best when risk profile is uneven (large range between scores).
- "stacked_area"    — Allocation over time. Best when allocation changed meaningfully.
- "drawdown_chart"  — Drawdown / underwater chart. CRITICAL for high-vol funds or funds with large max drawdown (>10%).
- "pie_chart"       — Current allocation donut. Best for diversified funds with 4+ asset classes.
- "rolling_returns" — Rolling 12M returns. Best for funds with high return variability.
- "contributor_bar" — Top/bottom holding contributors. Best for concentrated funds where individual holdings drive returns.
- "income_chart"    — Income distribution over time. ONLY if "income_stream" is in extra_datasets_available.
- "duration_bar"    — Duration bucket exposure. ONLY if "duration_profile" is in extra_datasets_available.
- "sector_bar"      — Sector concentration. ONLY if "sector_exposure" is in extra_datasets_available.

## Decision Guidelines

- HIGH volatility / fat tails → include drawdown_chart, histogram, rolling_returns
- HIGH concentration (top_3 > 50%) → include contributor_bar, sector_bar (if available)
- INCOME-oriented (has income_stream data) → include income_chart, duration_bar, pie_chart
- DIVERSIFIED allocation (4+ asset classes) → include pie_chart, stacked_area
- UNEVEN risk profile (score_range > 4) → include spider_chart
- STRONG/WEAK benchmark performance → include line_chart
- Do NOT include charts for data that doesn't exist in extra_datasets_available

## Output Format

Return a JSON object with this exact structure:
{
  "report_title": "...",
  "report_subtitle": "...",
  "fund_character": "A 1-sentence description of the fund's character/personality",
  "sections": [
    {
      "title": "Section Title",
      "chart": "chart_id from the list above (or null for text-only sections)",
      "commentary": "2-4 sentence professional commentary for this section. Reference specific data.",
      "priority": "high" or "medium"
    }
  ]
}

Rules:
- Include 6-9 sections total (mix of chart sections and text-only sections)
- The FIRST section should always be an Executive Summary (chart: null)
- The LAST section should always be a Forward-Looking Outlook (chart: null)
- Each chart_id can only appear ONCE
- Reference specific numbers from the data in commentary
- Tailor the tone: aggressive funds get more risk-focused language; income funds get yield-focused language
- Do NOT include charts whose required data (extra_datasets_available) is missing
"""


def plan_report(
    data: dict,
    model: str = "claude-sonnet-4-5-20250929",
) -> dict:
    """Send fund data to Claude and get back a report blueprint."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set.")

    profile_json = build_data_profile(data)

    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model=model,
        max_tokens=3000,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": (
                    f"Design a quarterly report for the following fund:\n\n"
                    f"```json\n{profile_json}\n```\n\n"
                    f"Analyze this data and choose the most relevant charts and sections."
                ),
            }
        ],
    )

    raw = message.content[0].text
    if "```json" in raw:
        raw = raw.split("```json")[1].split("```")[0]
    elif "```" in raw:
        raw = raw.split("```")[1].split("```")[0]

    plan = json.loads(raw.strip())

    # Validate
    assert "sections" in plan, "Plan missing 'sections'"
    assert len(plan["sections"]) >= 3, "Plan has too few sections"

    return plan
