"""Room design and constraint parsing."""

from __future__ import annotations

import re
from typing import Dict, Tuple

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from openai import OpenAI

from chemistry_lab.config import DEFAULT_MODEL


def parse_constraints(constraints_str: str) -> dict:
    """Parse a free-text constraint string into a structured dict.

    Recognises patterns like ``"fume hood in upper-right corner"`` or
    ``"sink: north wall"``.

    Returns:
        ``{"raw": …, "placements": […], "notes": […]}``
    """
    result: dict = {"raw": constraints_str, "placements": [], "notes": []}
    if not constraints_str or not constraints_str.strip():
        return result

    parts = [p.strip() for p in re.split(r"[;\n\r]+", constraints_str) if p.strip()]
    pattern = re.compile(
        r"(?P<item>[\w\s\-]+?)\s+(?:in|on|at|located\s+at)\s+(?P<pos>[\w\-\s]+)",
        re.IGNORECASE,
    )

    for p in parts:
        m = pattern.search(p)
        if m:
            item = m.group("item").strip().rstrip(".,")
            pos = m.group("pos").strip().rstrip(".,")
            result["placements"].append({"item": item, "position": pos})
        elif ":" in p:
            k, v = [s.strip() for s in p.split(":", 1)]
            result["placements"].append({"item": k, "position": v})
        else:
            result["notes"].append(p)

    return result


def build_design_prompt(
    experiment_name: str,
    large_equipment: dict,
    small_equipment: dict,
    constraints: str,
) -> str:
    """Build the user prompt for room-design generation."""
    import json

    lines = [
        f"You are a laboratory space planner. Produce a recommended room "
        f"layout for the {experiment_name} experiment.",
        "Respond with: (1) placement strategy; (2) placement list mapping "
        "each item to a location/zone; (3) safety & utility hookups; "
        "(4) spacing and clearance rules; (5) an ASCII floor plan sketch.",
        "",
        "Large fixed equipment (Category 1):",
        json.dumps(large_equipment, ensure_ascii=False, indent=2),
        "",
        "Small movable equipment (Category 2):",
        json.dumps(small_equipment, ensure_ascii=False, indent=2),
        "",
        "User constraints:",
        constraints if constraints.strip() else "(none)",
    ]
    try:
        parsed = parse_constraints(constraints)
        lines += [
            "",
            "User constraints (structured):",
            json.dumps(parsed, ensure_ascii=False, indent=2),
        ]
    except Exception:
        pass
    lines.append(
        "\nBe explicit and practical. Use human-readable location descriptors "
        "and include a brief justification for each placement."
    )
    return "\n".join(lines)


_SYSTEM_MESSAGE = """\
You are an expert laboratory planner with knowledge of safety codes and \
efficient lab layouts.

Critical Requirements:
1. NEVER allow overlap between large equipment items.
2. Consider dimensions_2d (width and depth) when placing them.
3. Check that required_clearance values do not overlap.
4. For any two items A and B, their positions must prevent intersection \
of their footprints.

Provide clear, actionable placement instructions and a JSON layout that \
explicitly specifies coordinates for each large equipment item.\
"""


def design_room(
    experiment_name: str,
    constraints: str,
    client: OpenAI,
    *,
    large_equipment: dict | None = None,
    small_equipment: dict | None = None,
    model: str = DEFAULT_MODEL,
    temperature: float = 0.2,
    max_tokens: int = 1500,
) -> str:
    """Generate a room-design text via the LLM.

    Args:
        experiment_name: Name of the experiment.
        constraints: Free-text constraint string.
        client: An ``OpenAI``-compatible client.
        large_equipment: Pre-fetched large equipment dict (optional).
        small_equipment: Pre-fetched small equipment dict (optional).
        model: Model identifier.
        temperature: Sampling temperature.
        max_tokens: Maximum tokens in the response.

    Returns:
        Raw text of the room design.
    """
    if large_equipment is None:
        large_equipment = {}
    if small_equipment is None:
        small_equipment = {}

    prompt = build_design_prompt(
        experiment_name, large_equipment, small_equipment, constraints
    )

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": _SYSTEM_MESSAGE},
                {"role": "user", "content": prompt},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
            stream=False,
        )
        return response.choices[0].message.content
    except Exception as exc:
        return f"Error calling API: {exc}"
