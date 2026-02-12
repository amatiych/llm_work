"""LLM Template Selector — uses Claude tool-use to analyze fund data and pick a template.

The LLM receives tools to:
  1. list_templates    — see what templates are available
  2. get_template      — inspect a specific template's sections and criteria
  3. analyze_fund      — get the computed data profile for a fund
  4. select_template   — commit to a choice with a rationale

This is the ONLY module that calls the LLM. Once a template is selected,
the report is generated deterministically by template_engine.render().
"""

import json
import os

import anthropic

from template_engine import list_templates, load_template, compute_template_vars


# ─────────────────────────────────────────────────────────────────────
# Tool definitions (Claude tool-use schema)
# ─────────────────────────────────────────────────────────────────────

TOOLS = [
    {
        "name": "list_templates",
        "description": (
            "List all available report templates with their IDs, names, descriptions, "
            "match criteria, and which charts they include. Call this first to understand "
            "what templates exist."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "get_template",
        "description": (
            "Get full details of a specific template including all section definitions, "
            "chart selections, commentary templates, and match criteria. Use this to "
            "inspect a template before deciding."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "template_id": {
                    "type": "string",
                    "description": "The template ID to inspect",
                },
            },
            "required": ["template_id"],
        },
    },
    {
        "name": "analyze_fund",
        "description": (
            "Get the computed data profile for the fund being reported on. Returns "
            "return statistics, risk metrics, allocation data, holdings summary, and "
            "flags for which extra datasets are available (sector_exposure, income_stream, "
            "duration_profile). Use this to understand the fund's characteristics."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "select_template",
        "description": (
            "Commit to a template selection. Provide the template_id and a rationale "
            "explaining why this template is the best fit for the fund data. "
            "This is the final action — call this once you've analyzed the fund and "
            "reviewed the templates."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "template_id": {
                    "type": "string",
                    "description": "The chosen template ID",
                },
                "rationale": {
                    "type": "string",
                    "description": "2-3 sentence explanation of why this template fits",
                },
            },
            "required": ["template_id", "rationale"],
        },
    },
]

SYSTEM_PROMPT = """\
You are a report template selector for an investment reporting system.

Your job is to analyze a fund's data and choose the most appropriate report template.
You have tools available to:
1. List all available templates
2. Inspect specific templates in detail
3. Analyze the fund's data profile
4. Select the final template

Workflow:
1. First, call analyze_fund to understand the fund's characteristics
2. Then call list_templates to see what templates are available
3. Optionally call get_template to inspect promising templates
4. Finally call select_template with your choice and rationale

Match the template to the fund's actual characteristics:
- High volatility, concentrated equity → equity growth template
- Low volatility, income-focused, bond-heavy → stable income template
- Moderate volatility, diversified → balanced multi-asset template

Make your decision based on the data, not the fund name.
"""


# ─────────────────────────────────────────────────────────────────────
# Tool execution (local — no LLM needed for this part)
# ─────────────────────────────────────────────────────────────────────

def _execute_tool(tool_name: str, tool_input: dict, fund_vars: dict) -> str:
    """Execute a tool call and return the result as a JSON string."""
    if tool_name == "list_templates":
        return json.dumps(list_templates(), indent=2)

    elif tool_name == "get_template":
        template = load_template(tool_input["template_id"])
        return json.dumps(template, indent=2)

    elif tool_name == "analyze_fund":
        # Return the pre-computed variables (safe subset, no DataFrames)
        safe = {k: v for k, v in fund_vars.items() if not isinstance(v, bool) or v}
        return json.dumps(safe, indent=2, default=str)

    elif tool_name == "select_template":
        return json.dumps({
            "status": "selected",
            "template_id": tool_input["template_id"],
            "rationale": tool_input["rationale"],
        })

    else:
        return json.dumps({"error": f"Unknown tool: {tool_name}"})


# ─────────────────────────────────────────────────────────────────────
# Main selector function
# ─────────────────────────────────────────────────────────────────────

def select_template(
    data: dict,
    model: str = "claude-sonnet-4-5-20250929",
    verbose: bool = True,
) -> dict:
    """Use Claude tool-use to select the best template for a fund.

    Returns:
        {
            "template_id": "...",
            "rationale": "...",
            "tool_calls": [list of tool calls made],
        }
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set.")

    # Pre-compute the fund variables so we can serve them from analyze_fund
    fund_vars = compute_template_vars(data)

    client = anthropic.Anthropic(api_key=api_key)
    messages = [
        {
            "role": "user",
            "content": (
                f"Select the best report template for: {data['name']}. "
                f"Use your tools to analyze the fund data, review available templates, "
                f"and make a selection."
            ),
        }
    ]

    tool_log = []
    max_turns = 10
    selected = None

    for turn in range(max_turns):
        response = client.messages.create(
            model=model,
            max_tokens=1500,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages,
        )

        # Process the response
        assistant_content = response.content
        messages.append({"role": "assistant", "content": assistant_content})

        # Check if there are tool calls
        tool_uses = [b for b in assistant_content if b.type == "tool_use"]
        if not tool_uses:
            # No more tool calls — LLM is done
            break

        # Execute each tool call
        tool_results = []
        for tool_use in tool_uses:
            if verbose:
                print(f"    Tool: {tool_use.name}({json.dumps(tool_use.input)[:80]})")

            result = _execute_tool(tool_use.name, tool_use.input, fund_vars)
            tool_log.append({
                "tool": tool_use.name,
                "input": tool_use.input,
            })

            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tool_use.id,
                "content": result,
            })

            # Check if this was the final selection
            if tool_use.name == "select_template":
                selected = tool_use.input

        messages.append({"role": "user", "content": tool_results})

        if selected:
            break

    if not selected:
        raise RuntimeError("LLM did not call select_template within max turns")

    return {
        "template_id": selected["template_id"],
        "rationale": selected["rationale"],
        "tool_calls": tool_log,
    }
