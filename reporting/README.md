# Investment Report Generator

AI-powered PDF and PowerPoint report generation for investment funds. Combines quantitative data analysis with LLM-generated commentary, configurable report templates, and client-specific branding.

## Architecture

The system has four progressively more sophisticated modes:

```
Mode 1: Static          Mode 2: AI Commentary      Mode 3: Adaptive         Mode 4: Template + Theme
─────────────────       ─────────────────────       ─────────────────        ─────────────────────────
Hardcoded text          LLM writes all text         LLM decides structure    LLM picks template once,
+ charts → PDF/PPTX     from data → PDF/PPTX        + text → PDF/PPTX        then reports run without LLM

No API key needed       Needs ANTHROPIC_API_KEY     Needs ANTHROPIC_API_KEY  API key only for --auto mode
```

### Data Flow

```
Fund Data (DataFrames)
    │
    ├──→ Compute Statistics (return, risk, allocation profiles)
    │         │
    │         ├──→ [Mode 2] LLM generates commentary ──────────────────┐
    │         ├──→ [Mode 3] LLM designs full report blueprint ─────────┤
    │         └──→ [Mode 4] LLM picks template (tool-use) ────────────┐│
    │                                                                  ││
    ├──→ Chart Library (11 chart types, themed colors) ────────────────┤│
    │                                                                  ││
    └──→ Template Engine (hydrate placeholders) ◄──────────────────────┘│
              │                                                         │
              └──→ Report Builders (PDF via ReportLab, PPTX via python-pptx)
                        │
                        └──→ Theme (logo, colors, fonts, branding text)
```

## Quick Start

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...   # only needed for AI modes
```

### Mode 1: Static Reports (no API key)

```bash
python main.py                        # PDF + PPTX with hardcoded commentary
python main.py --format pdf           # PDF only
python main.py --output-dir reports   # custom output directory
```

### Mode 2: AI-Generated Commentary

LLM analyzes the raw data and writes all report text (executive summary, risk assessment, market outlook, per-chart insights).

```bash
python main.py --ai                         # Claude writes all commentary
python main.py --ai --save-commentary       # also saves raw JSON
python main.py --ai --model claude-opus-4-6 # use a different model
```

### Mode 3: Adaptive Reports (LLM designs the structure)

The LLM receives the fund's data profile and decides which charts and sections to include. Different funds produce structurally different reports.

```bash
python main_adaptive.py --fund alpha_aggressive   # concentrated equity fund
python main_adaptive.py --fund horizon_income      # conservative bond fund
python main_adaptive.py --fund all                 # both, to compare
```

**Example:** The LLM selects drawdown + sector charts for the volatile equity fund, but income + duration charts for the bond fund.

### Mode 4: Template-Based with Client Themes

JSON templates define report structure. The LLM picks the right template via tool-use (once), then all subsequent reports render instantly without LLM calls.

```bash
# Explicit template selection (no LLM)
python main_template.py --fund alpha_aggressive --template equity_growth

# LLM selects template automatically via tool-use
python main_template.py --fund all --auto

# Apply client branding
python main_template.py --fund alpha_aggressive --template equity_growth --theme alpine_capital
python main_template.py --fund alpha_aggressive --template equity_growth --theme ember_wealth

# List available templates and themes
python main_template.py --list-templates
python main_template.py --list-themes
```

## Chart Library

11 chart types available for the LLM or templates to choose from:

| Chart | ID | Best For |
|---|---|---|
| Histogram | `histogram` | Return distribution shape, fat tails |
| Line Chart | `line_chart` | Performance vs benchmark |
| Spider/Radar | `spider_chart` | Multi-dimensional risk profile |
| Stacked Area | `stacked_area` | Allocation changes over time |
| Drawdown | `drawdown_chart` | High-volatility funds, max loss |
| Pie/Donut | `pie_chart` | Diversified current allocation |
| Rolling Returns | `rolling_returns` | Return consistency over time |
| Contributor Bar | `contributor_bar` | Top/bottom holding performance |
| Income Stream | `income_chart` | Yield-focused funds |
| Duration Buckets | `duration_bar` | Fixed-income rate sensitivity |
| Sector Bar | `sector_bar` | Equity sector concentration |

## Templates

Templates are JSON files in `templates/` that define:
- Section order and titles
- Which chart to include per section
- Commentary templates with `{placeholder}` variables
- Data requirements (sections auto-skip if data is missing)

```
templates/
  equity_growth.json        # 9 sections: drawdown, sector, rolling returns...
  stable_income.json        # 9 sections: income, duration, allocation pie...
  balanced_multi_asset.json # 8 sections: general-purpose balanced fund
```

**Adding a new template:** Create a JSON file in `templates/` following the existing structure. No code changes needed.

## Themes

Themes are JSON files in `themes/` that control visual branding:

```json
{
  "theme_id": "alpine_capital",
  "client_name": "Alpine Capital Management",
  "logo": "themes/logo_alpine.png",
  "colors": {
    "primary": "#1B3A5C",
    "secondary": "#4A90C4",
    "accent": "#D4A843",
    "text_dark": "#1A1A2E",
    "text_light": "#F0F0F5",
    "background_alt": "#EDF2F7",
    "grid": "#CBD5E0"
  },
  "chart_palette": ["#1B3A5C", "#4A90C4", "#D4A843", "#2D8B6F", "#C4543A", "#7B68A8"],
  "pdf": {
    "header_text": "CONFIDENTIAL — Alpine Capital Management",
    "footer_text": "Prepared by Alpine Capital Reporting"
  }
}
```

Theme colors flow through:
- **Charts**: matplotlib color palette
- **PDF**: headings, table headers, alt-row shading, grid lines, header/footer text, logo on cover + every page
- **PPTX**: title slide background, heading color, table styling, logo on title slide

**Adding a new client theme:** Drop a JSON file + logo PNG in `themes/`. No code changes needed.

Available themes: `alpine_capital` (navy/steel), `ember_wealth` (deep red/gold), `verdant_advisors` (forest green)

## Sample Funds

Two funds with contrasting profiles to demonstrate adaptive report generation:

| | Alpha Aggressive Growth | Horizon Stable Income |
|---|---|---|
| Strategy | Concentrated equity, tech-heavy | Diversified fixed income |
| Holdings | 8 positions, 50% top-3 | 10 positions across 5 asset classes |
| Volatility | ~22% annualized | ~2.3% annualized |
| Max Drawdown | ~18% | ~1.2% |
| Extra Data | Sector exposure, monthly P&L | Income stream, duration profile |

## Project Structure

```
reporting/
├── main.py                 # Mode 1 + 2: static or --ai commentary
├── main_ai.py              # Mode 2 standalone: AI commentary only
├── main_adaptive.py        # Mode 3: LLM plans full report structure
├── main_template.py        # Mode 4: template + theme system
│
├── data.py                 # Sample portfolio data (Mode 1/2)
├── funds.py                # Two fund profiles (Mode 3/4)
├── charts.py               # Original chart module (Mode 1/2)
├── chart_library.py        # Extended 11-chart library with theming
│
├── llm_analyst.py          # Mode 2: data → Claude → commentary JSON
├── llm_planner.py          # Mode 3: data → Claude → report blueprint
├── template_selector.py    # Mode 4: Claude tool-use to pick template
│
├── pdf_report.py           # PDF builder (Mode 1/2)
├── ppt_report.py           # PPTX builder (Mode 1/2)
├── adaptive_report.py      # PDF/PPTX builder with theme support (Mode 3/4)
├── template_engine.py      # Template loader, hydrator, renderer
├── theme.py                # Theme loader and defaults
├── logo_gen.py             # Generate placeholder client logos
│
├── templates/              # Report structure definitions
│   ├── equity_growth.json
│   ├── stable_income.json
│   └── balanced_multi_asset.json
│
├── themes/                 # Client branding configs + logos
│   ├── alpine_capital.json
│   ├── ember_wealth.json
│   ├── verdant_advisors.json
│   ├── logo_alpine.png
│   ├── logo_ember.png
│   └── logo_verdant.png
│
├── requirements.txt
└── .gitignore
```

## Requirements

- Python 3.11+
- `matplotlib`, `numpy`, `pandas` - data and charts
- `reportlab` - PDF generation
- `python-pptx` - PowerPoint generation
- `anthropic` - Claude API (only for AI modes)

## LLM Tool-Use (Mode 4)

The template selector gives Claude four tools:

| Tool | Purpose |
|---|---|
| `analyze_fund` | Returns computed data profile (volatility, Sharpe, drawdown, etc.) |
| `list_templates` | Shows available templates with match criteria |
| `get_template` | Inspects a specific template's sections and charts |
| `select_template` | Commits to a choice with rationale |

Typical flow: Claude calls `analyze_fund` → `list_templates` → `get_template` (to verify fit) → `select_template`. The selection and rationale are saved to `selection_log.json` for auditability.
