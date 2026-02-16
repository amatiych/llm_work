"""FastAPI backend for the Prompt Report Builder UI."""

import asyncio
import json
import re
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from adaptive_report import build_pdf, generate_planned_charts
from chart_library import set_theme_colors
from funds import FUND_REGISTRY, load_fund
from prompt_report_builder import run_prompt_report
from theme import list_themes, load_theme

app = FastAPI(title="Report Builder API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

OUTPUT_DIR = "output_prompt"
TEMPLATES_DIR = Path(__file__).parent / "report_templates"

_TEMPLATE_NAME_RE = re.compile(r"^[a-zA-Z0-9_]+$")


class GenerateRequest(BaseModel):
    fund_id: str
    prompt: str
    theme_id: str | None = None


class SaveTemplateRequest(BaseModel):
    name: str
    plan: dict


class ReplayTemplateRequest(BaseModel):
    fund_id: str
    theme_id: str | None = None


@app.get("/api/funds")
def get_funds():
    return [
        {"id": fund_id, "name": info["name"]}
        for fund_id, info in FUND_REGISTRY.items()
    ]


@app.get("/api/themes")
def get_themes():
    return list_themes()


@app.post("/api/generate")
async def generate_report(req: GenerateRequest):
    if req.fund_id not in FUND_REGISTRY:
        raise HTTPException(status_code=400, detail=f"Unknown fund: {req.fund_id}")

    try:
        result = await asyncio.to_thread(
            run_prompt_report,
            fund_id=req.fund_id,
            prompt=req.prompt,
            output_dir=OUTPUT_DIR,
            default_theme_id=req.theme_id,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    # Read tool log if available
    tool_log_path = Path(result["output_dir"]) / "tool_log.json"
    tool_log = []
    if tool_log_path.exists():
        tool_log = json.loads(tool_log_path.read_text())

    # Use only charts from the current run (not stale files from previous runs)
    chart_files = result.get("charts", [])

    # Read the saved plan so the frontend can offer "Save as Template"
    plan = None
    plan_path = Path(result["output_dir"]) / "report_plan.json"
    if plan_path.exists():
        plan = json.loads(plan_path.read_text())

    return {
        **result,
        "tool_log": tool_log,
        "chart_files": chart_files,
        "plan": plan,
    }


@app.get("/api/report/{fund_id}/pdf")
def get_pdf(fund_id: str):
    pdf_path = Path(OUTPUT_DIR) / fund_id / "report.pdf"
    if not pdf_path.exists():
        raise HTTPException(status_code=404, detail="PDF not found")
    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename=f"{fund_id}_report.pdf",
    )


@app.get("/api/report/{fund_id}/charts/{chart_id}")
def get_chart(fund_id: str, chart_id: str):
    # Validate no path traversal
    if ".." in chart_id or "/" in chart_id or "\\" in chart_id:
        raise HTTPException(status_code=400, detail="Invalid chart ID")

    chart_path = Path(OUTPUT_DIR) / fund_id / f"{chart_id}.png"
    if not chart_path.exists():
        raise HTTPException(status_code=404, detail="Chart not found")
    return FileResponse(chart_path, media_type="image/png")


# ─────────────────────────────────────────────────────────────────────
# Template endpoints
# ─────────────────────────────────────────────────────────────────────

def _validate_template_name(name: str):
    if not _TEMPLATE_NAME_RE.match(name):
        raise HTTPException(
            status_code=400,
            detail="Template name must be alphanumeric with underscores only.",
        )


@app.get("/api/templates")
def list_templates():
    TEMPLATES_DIR.mkdir(exist_ok=True)
    templates = []
    for path in sorted(TEMPLATES_DIR.glob("*.json")):
        data = json.loads(path.read_text())
        templates.append({
            "name": path.stem,
            "title": data.get("report_title", path.stem),
            "subtitle": data.get("report_subtitle", ""),
            "sections": len(data.get("sections", [])),
        })
    return templates


@app.post("/api/templates")
def save_template(req: SaveTemplateRequest):
    _validate_template_name(req.name)
    TEMPLATES_DIR.mkdir(exist_ok=True)
    path = TEMPLATES_DIR / f"{req.name}.json"
    path.write_text(json.dumps(req.plan, indent=2))
    return {"status": "ok", "name": req.name}


@app.delete("/api/templates/{name}")
def delete_template(name: str):
    _validate_template_name(name)
    path = TEMPLATES_DIR / f"{name}.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Template not found")
    path.unlink()
    return {"status": "ok"}


@app.post("/api/templates/{name}/generate")
async def replay_template(name: str, req: ReplayTemplateRequest):
    _validate_template_name(name)
    template_path = TEMPLATES_DIR / f"{name}.json"
    if not template_path.exists():
        raise HTTPException(status_code=404, detail="Template not found")

    if req.fund_id not in FUND_REGISTRY:
        raise HTTPException(status_code=400, detail=f"Unknown fund: {req.fund_id}")

    plan = json.loads(template_path.read_text())

    try:
        result = await asyncio.to_thread(
            _run_template_replay, plan, req.fund_id, req.theme_id,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return result


def _run_template_replay(plan: dict, fund_id: str, theme_id: str | None) -> dict:
    """Replay a template plan against a fund — no Claude call needed."""
    data = load_fund(fund_id)
    theme = load_theme(theme_id)
    set_theme_colors(theme.get("chart_palette"))

    fund_dir = f"{OUTPUT_DIR}/{fund_id}"
    Path(fund_dir).mkdir(parents=True, exist_ok=True)

    chart_paths = generate_planned_charts(plan, data, fund_dir)
    pdf_path = build_pdf(plan, chart_paths, data, f"{fund_dir}/report.pdf", theme=theme)

    # Save the plan for consistency
    Path(f"{fund_dir}/report_plan.json").write_text(json.dumps(plan, indent=2))

    return {
        "fund_id": fund_id,
        "output_dir": fund_dir,
        "sections": len(plan.get("sections", [])),
        "charts": list(chart_paths.keys()),
        "chart_files": list(chart_paths.keys()),
        "tool_calls": 0,
        "tool_log": [],
        "plan": plan,
    }


# Mount static files for production SPA serving
web_dist = Path(__file__).parent / "web" / "dist"
if web_dist.exists():
    app.mount("/", StaticFiles(directory=web_dist, html=True), name="spa")
