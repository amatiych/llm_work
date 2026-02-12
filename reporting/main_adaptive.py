"""Adaptive AI report generator — LLM decides report structure based on data.

Usage:
    python main_adaptive.py --fund alpha_aggressive
    python main_adaptive.py --fund horizon_income
    python main_adaptive.py --fund all

Each fund produces a structurally different report.
"""

import argparse
import json
from pathlib import Path

from funds import FUND_REGISTRY, load_fund
from llm_planner import plan_report, build_data_profile
from adaptive_report import generate_planned_charts, build_pdf, build_pptx


def run_fund(fund_id: str, args):
    """Run the full pipeline for one fund."""
    print(f"\n{'='*60}")
    print(f"  Fund: {fund_id}")
    print(f"{'='*60}")

    fund_dir = f"{args.output_dir}/{fund_id}"
    Path(fund_dir).mkdir(parents=True, exist_ok=True)

    # 1. Load data
    print("  Loading data...")
    data = load_fund(fund_id)

    # 2. Save data profile (for transparency)
    profile = build_data_profile(data)
    Path(f"{fund_dir}/data_profile.json").write_text(profile)
    print(f"  Data profile:   {fund_dir}/data_profile.json")

    # 3. LLM plans the report
    print(f"  Asking Claude ({args.model}) to design the report...")
    plan = plan_report(data, model=args.model)
    Path(f"{fund_dir}/report_plan.json").write_text(json.dumps(plan, indent=2))
    print(f"  Report plan:    {fund_dir}/report_plan.json")

    # Show what the LLM decided
    chart_ids = [s["chart"] for s in plan["sections"] if s.get("chart")]
    print(f"  LLM selected {len(plan['sections'])} sections, {len(chart_ids)} charts:")
    for s in plan["sections"]:
        marker = f"[{s['chart']}]" if s.get("chart") else "[text]"
        prio = s.get("priority", "")
        print(f"    {prio:6s} {marker:20s} {s['title']}")

    # 4. Generate only the selected charts
    print("  Generating charts...")
    chart_paths = generate_planned_charts(plan, data, fund_dir)
    print(f"  Charts generated: {list(chart_paths.keys())}")

    # 5. Build reports
    if args.format in ("pdf", "all"):
        pdf_path = build_pdf(plan, chart_paths, data, f"{fund_dir}/report.pdf")
        print(f"  PDF:  {pdf_path}")

    if args.format in ("pptx", "all"):
        pptx_path = build_pptx(plan, chart_paths, data, f"{fund_dir}/report.pptx")
        print(f"  PPTX: {pptx_path}")


def main():
    parser = argparse.ArgumentParser(description="Adaptive AI-powered report generator")
    parser.add_argument(
        "--fund", default="all",
        choices=list(FUND_REGISTRY.keys()) + ["all"],
        help="Fund to generate report for (default: all)",
    )
    parser.add_argument(
        "--format", choices=["pdf", "pptx", "all"], default="all",
    )
    parser.add_argument(
        "--output-dir", default="output_adaptive",
    )
    parser.add_argument(
        "--model", default="claude-sonnet-4-5-20250929",
    )
    args = parser.parse_args()

    funds = list(FUND_REGISTRY.keys()) if args.fund == "all" else [args.fund]

    for fund_id in funds:
        run_fund(fund_id, args)

    print(f"\nDone. Reports in {args.output_dir}/")


if __name__ == "__main__":
    main()
