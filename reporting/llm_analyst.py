"""LLM-powered data analyst — feeds portfolio data to Claude and gets back report commentary."""

import json
import os

import anthropic
import numpy as np
import pandas as pd


def _serialize_returns(df: pd.DataFrame) -> dict:
    """Compute summary statistics from returns data for the LLM."""
    r = df["return"]
    return {
        "period": f"{df['date'].min():%Y-%m} to {df['date'].max():%Y-%m}",
        "n_months": len(r),
        "mean_monthly_return_pct": round(r.mean() * 100, 3),
        "std_monthly_pct": round(r.std() * 100, 3),
        "annualized_return_pct": round(((1 + r.mean()) ** 12 - 1) * 100, 2),
        "annualized_vol_pct": round(r.std() * np.sqrt(12) * 100, 2),
        "sharpe_ratio": round((r.mean() / r.std()) * np.sqrt(12), 2),
        "max_monthly_return_pct": round(r.max() * 100, 2),
        "min_monthly_return_pct": round(r.min() * 100, 2),
        "pct_positive_months": round((r > 0).mean() * 100, 1),
        "skewness": round(float(r.skew()), 3),
        "kurtosis": round(float(r.kurtosis()), 3),
    }


def _serialize_performance(df: pd.DataFrame) -> dict:
    """Compute portfolio vs benchmark summary."""
    port_total = df["Portfolio"].iloc[-1] / df["Portfolio"].iloc[0] - 1
    bench_total = df["Benchmark"].iloc[-1] / df["Benchmark"].iloc[0] - 1
    return {
        "period": f"{df['date'].min():%Y-%m} to {df['date'].max():%Y-%m}",
        "portfolio_cumulative_return_pct": round(port_total * 100, 2),
        "benchmark_cumulative_return_pct": round(bench_total * 100, 2),
        "excess_return_pct": round((port_total - bench_total) * 100, 2),
        "portfolio_final_value": round(df["Portfolio"].iloc[-1], 2),
        "benchmark_final_value": round(df["Benchmark"].iloc[-1], 2),
    }


def _serialize_risk_scores(risk: dict) -> dict:
    """Pass risk scores as-is with some derived fields."""
    result = {cat: {} for cat in risk["categories"]}
    for fund in ["Fund A", "Fund B"]:
        for cat, score in zip(risk["categories"], risk[fund]):
            result[cat][fund] = score
    avg_a = round(np.mean(risk["Fund A"]), 2)
    avg_b = round(np.mean(risk["Fund B"]), 2)
    return {
        "scores": result,
        "fund_a_avg_risk": avg_a,
        "fund_b_avg_risk": avg_b,
        "fund_a_highest_risk": risk["categories"][int(np.argmax(risk["Fund A"]))],
        "fund_b_highest_risk": risk["categories"][int(np.argmax(risk["Fund B"]))],
    }


def _serialize_allocation(df: pd.DataFrame) -> dict:
    """Summarize allocation changes over time."""
    first = df.iloc[0]
    last = df.iloc[-1]
    cols = ["Equities", "Fixed Income", "Alternatives", "Cash"]
    return {
        "period": f"{df['date'].min():%Y-%m} to {df['date'].max():%Y-%m}",
        "start_allocation": {c: round(first[c], 1) for c in cols},
        "end_allocation": {c: round(last[c], 1) for c in cols},
        "change": {c: round(last[c] - first[c], 1) for c in cols},
        "largest_allocation": max(cols, key=lambda c: last[c]),
    }


def _serialize_holdings(df: pd.DataFrame) -> list[dict]:
    """Convert holdings table to list of dicts."""
    return df.to_dict(orient="records")


def _build_data_package(
    returns_df: pd.DataFrame,
    perf_df: pd.DataFrame,
    risk_scores: dict,
    alloc_df: pd.DataFrame,
    holdings_df: pd.DataFrame,
) -> str:
    """Build the full JSON data package that gets sent to the LLM."""
    package = {
        "return_statistics": _serialize_returns(returns_df),
        "performance_vs_benchmark": _serialize_performance(perf_df),
        "risk_factor_scores": _serialize_risk_scores(risk_scores),
        "asset_allocation_trend": _serialize_allocation(alloc_df),
        "top_holdings": _serialize_holdings(holdings_df),
    }
    return json.dumps(package, indent=2)


SYSTEM_PROMPT = """\
You are a senior investment analyst writing a quarterly report for institutional investors.
You will receive a JSON object containing portfolio analytics. Your task is to produce
professional, data-driven commentary for each section of the report.

Rules:
- Reference specific numbers from the data (returns, Sharpe ratio, allocation weights, etc.)
- Use professional investment language appropriate for institutional audiences
- Be concise — each section should be one solid paragraph (4-6 sentences)
- Do NOT use markdown formatting, bullet points, or headers — output plain prose paragraphs
- Do NOT fabricate data that is not in the input — only interpret what is provided
- Maintain a balanced, analytical tone — highlight positives but acknowledge risks

Return a JSON object with exactly these keys:
{
  "executive_summary": "...",
  "performance_commentary": "...",
  "return_distribution_commentary": "...",
  "allocation_commentary": "...",
  "holdings_commentary": "...",
  "risk_assessment": "...",
  "market_outlook": "..."
}
"""


def analyze_data(
    returns_df: pd.DataFrame,
    perf_df: pd.DataFrame,
    risk_scores: dict,
    alloc_df: pd.DataFrame,
    holdings_df: pd.DataFrame,
    model: str = "claude-sonnet-4-5-20250929",
) -> dict[str, str]:
    """Send portfolio data to Claude and get back structured commentary.

    Requires ANTHROPIC_API_KEY environment variable.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY not set. Export it or pass via environment:\n"
            "  export ANTHROPIC_API_KEY=sk-ant-..."
        )

    data_json = _build_data_package(returns_df, perf_df, risk_scores, alloc_df, holdings_df)

    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model=model,
        max_tokens=2048,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": (
                    f"Here is the portfolio data for Q4 2024:\n\n```json\n{data_json}\n```\n\n"
                    "Please generate the report commentary as specified."
                ),
            }
        ],
    )

    raw = message.content[0].text
    # Extract JSON from response (handles case where LLM wraps in code fences)
    if "```json" in raw:
        raw = raw.split("```json")[1].split("```")[0]
    elif "```" in raw:
        raw = raw.split("```")[1].split("```")[0]

    commentary = json.loads(raw.strip())

    expected_keys = {
        "executive_summary", "performance_commentary",
        "return_distribution_commentary", "allocation_commentary",
        "holdings_commentary", "risk_assessment", "market_outlook",
    }
    missing = expected_keys - set(commentary.keys())
    if missing:
        raise ValueError(f"LLM response missing keys: {missing}")

    return commentary


def format_for_reports(llm_commentary: dict) -> dict:
    """Map LLM output into the commentary dict expected by pdf_report / ppt_report.

    Returns a dict with:
      - executive_summary, risk_assessment, market_outlook  (used by both reports)
      - performance_commentary, return_distribution_commentary,
        allocation_commentary, holdings_commentary  (used as chart captions)
    """
    return llm_commentary
