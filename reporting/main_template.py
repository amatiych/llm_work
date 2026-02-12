"""Template-based report generator with client theming.

Usage:
  python main_template.py --fund alpha_aggressive --template equity_growth
  python main_template.py --fund alpha_aggressive --template equity_growth --theme ember_wealth
  python main_template.py --fund all --auto --theme alpine_capital
  python main_template.py --list-templates
  python main_template.py --list-themes
"""

import argparse
import json
from pathlib import Path

from funds import FUND_REGISTRY, load_fund
from template_engine import list_templates, render
from template_selector import select_template
from theme import list_themes, load_theme


def main():
    parser = argparse.ArgumentParser(description="Template-based report generator")
    parser.add_argument(
        "--fund", choices=list(FUND_REGISTRY.keys()) + ["all"],
        help="Fund to report on",
    )
    parser.add_argument(
        "--template",
        help="Template ID to use (skip LLM selection)",
    )
    parser.add_argument(
        "--auto", action="store_true",
        help="Use LLM tool-use to select the template automatically",
    )
    parser.add_argument(
        "--theme",
        help="Theme ID for client branding (default: built-in)",
    )
    parser.add_argument(
        "--format", choices=["pdf", "pptx", "all"], default="all",
    )
    parser.add_argument(
        "--output-dir", default="output_template",
    )
    parser.add_argument(
        "--model", default="claude-sonnet-4-5-20250929",
    )
    parser.add_argument(
        "--list-templates", action="store_true",
        help="List available templates and exit",
    )
    parser.add_argument(
        "--list-themes", action="store_true",
        help="List available themes and exit",
    )
    args = parser.parse_args()

    # ── List modes ───────────────────────────────────────────────
    if args.list_templates:
        templates = list_templates()
        print(f"\nAvailable templates ({len(templates)}):\n")
        for t in templates:
            print(f"  {t['template_id']:25s} {t['name']}")
            print(f"  {'':25s} {t['description'][:80]}")
            print(f"  {'':25s} Charts: {', '.join(t['charts'])}")
            print()
        return

    if args.list_themes:
        themes = list_themes()
        print(f"\nAvailable themes ({len(themes)}):\n")
        for t in themes:
            print(f"  {t['theme_id']:25s} {t['client_name']}")
        print()
        return

    if not args.fund:
        parser.error("--fund is required (or use --list-templates / --list-themes)")

    if not args.template and not args.auto:
        parser.error("Specify --template <id> or --auto")

    # ── Load theme ───────────────────────────────────────────────
    theme = load_theme(args.theme)
    if args.theme:
        print(f"Theme: {theme['theme_id']} ({theme.get('client_name', '')})")

    funds = list(FUND_REGISTRY.keys()) if args.fund == "all" else [args.fund]

    for fund_id in funds:
        print(f"\n{'='*60}")
        print(f"  Fund: {fund_id}")
        print(f"{'='*60}")

        data = load_fund(fund_id)

        # ── Template selection ───────────────────────────────────
        if args.auto:
            print(f"  LLM selecting template ({args.model})...")
            result = select_template(data, model=args.model)
            template_id = result["template_id"]
            print(f"  Selected: {template_id}")
            print(f"  Rationale: {result['rationale']}")

            fund_dir = f"{args.output_dir}/{fund_id}"
            Path(fund_dir).mkdir(parents=True, exist_ok=True)
            Path(f"{fund_dir}/selection_log.json").write_text(
                json.dumps(result, indent=2)
            )
        else:
            template_id = args.template

        # ── Render report ────────────────────────────────────────
        fund_dir = f"{args.output_dir}/{fund_id}"
        print(f"  Template: {template_id}")
        print(f"  Rendering...")
        outputs = render(template_id, data, fund_dir, fmt=args.format, theme=theme)

        for key, path in outputs.items():
            print(f"  {key:6s}: {path}")

    print(f"\nDone. Output in {args.output_dir}/")


if __name__ == "__main__":
    main()
