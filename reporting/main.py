"""Main entry point — generates PDF and PowerPoint reports.

Supports two modes:
  python main.py                  # static commentary (no API key needed)
  python main.py --ai             # AI-generated commentary via Claude API
"""

import argparse
import json
import sys
from pathlib import Path

from data import (
    get_asset_allocation_timeseries,
    get_holdings_table,
    get_performance_timeseries,
    get_portfolio_returns,
    get_qualitative_commentary,
    get_risk_scores,
)
from charts import histogram, line_chart, spider_chart, stacked_area_chart
from pdf_report import generate_pdf
from ppt_report import generate_pptx


def build_charts(output_dir: str) -> dict[str, str]:
    """Generate all chart images and return their file paths."""
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    return {
        "histogram": histogram(get_portfolio_returns(), f"{output_dir}/histogram.png"),
        "line_chart": line_chart(get_performance_timeseries(), f"{output_dir}/line_chart.png"),
        "spider_chart": spider_chart(get_risk_scores(), f"{output_dir}/spider_chart.png"),
        "stacked_area": stacked_area_chart(
            get_asset_allocation_timeseries(), f"{output_dir}/stacked_area.png"
        ),
    }


def main():
    parser = argparse.ArgumentParser(description="Generate sample investment reports")
    parser.add_argument(
        "--format", choices=["pdf", "pptx", "all"], default="all",
        help="Output format (default: all)",
    )
    parser.add_argument(
        "--output-dir", default="output",
        help="Output directory (default: output)",
    )
    parser.add_argument(
        "--ai", action="store_true",
        help="Use Claude AI to generate commentary (requires ANTHROPIC_API_KEY)",
    )
    parser.add_argument(
        "--model", default="claude-sonnet-4-5-20250929",
        help="Anthropic model to use with --ai (default: claude-sonnet-4-5-20250929)",
    )
    parser.add_argument(
        "--save-commentary", action="store_true",
        help="Save LLM commentary JSON to output dir (only with --ai)",
    )
    args = parser.parse_args()

    # ── Load data ────────────────────────────────────────────────────
    returns_df = get_portfolio_returns()
    perf_df = get_performance_timeseries()
    risk_scores = get_risk_scores()
    alloc_df = get_asset_allocation_timeseries()
    holdings_df = get_holdings_table()

    # ── Generate charts ──────────────────────────────────────────────
    print("Generating charts...")
    charts = build_charts(args.output_dir)

    # ── Commentary ───────────────────────────────────────────────────
    if args.ai:
        from llm_analyst import analyze_data, format_for_reports

        print(f"Sending data to Claude ({args.model}) for analysis...")
        llm_output = analyze_data(
            returns_df, perf_df, risk_scores, alloc_df, holdings_df,
            model=args.model,
        )
        commentary = format_for_reports(llm_output)
        print("AI commentary generated.")

        if args.save_commentary:
            out = Path(args.output_dir) / "commentary.json"
            out.write_text(json.dumps(commentary, indent=2))
            print(f"Commentary saved: {out}")
    else:
        commentary = get_qualitative_commentary()

    # ── Build reports ────────────────────────────────────────────────
    if args.format in ("pdf", "all"):
        pdf_path = generate_pdf(charts, holdings_df, commentary, f"{args.output_dir}/report.pdf")
        print(f"PDF report:  {pdf_path}")

    if args.format in ("pptx", "all"):
        pptx_path = generate_pptx(charts, holdings_df, commentary, f"{args.output_dir}/report.pptx")
        print(f"PPTX report: {pptx_path}")

    print("Done.")


if __name__ == "__main__":
    main()
