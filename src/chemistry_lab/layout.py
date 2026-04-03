"""Lab layout generation via LLM."""

from __future__ import annotations

import json
from typing import Dict

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from openai import OpenAI

from chemistry_lab.config import DEFAULT_MODEL
from chemistry_lab.parser import extract_json_from_text


def normalize_equipment(equipment) -> Dict:
    """Normalise *equipment* input to a ``{display_name: metadata}`` mapping.

    Accepts either a list of equipment objects or a dict.
    """
    if equipment is None:
        return {}
    if isinstance(equipment, dict):
        return equipment
    if isinstance(equipment, list):
        out: Dict = {}
        for item in equipment:
            if not isinstance(item, dict):
                continue
            key = item.get("name") or item.get("id") or str(item)
            out[key] = item
        return out
    return {}


def build_layout_prompt(
    experiment_name: str,
    large_equipment: dict,
    small_equipment: dict,
    constraints: dict,
    room_size: dict | None = None,
) -> str:
    """Build the prompt sent to the LLM for layout generation."""
    schema = {
        "type": "object",
        "properties": {
            "room": {
                "type": "object",
                "properties": {
                    "width_m": {"type": "number"},
                    "depth_m": {"type": "number"},
                    "units": {"type": "string"},
                },
            },
            "placements": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "item_name": {"type": "string"},
                        "category": {"type": "string"},
                        "x_m": {"type": "number"},
                        "y_m": {"type": "number"},
                        "orientation": {"type": "string"},
                        "utilities": {"type": "array", "items": {"type": "string"}},
                        "clearance_m": {"type": "number"},
                        "justification": {"type": "string"},
                    },
                },
            },
            "recommendations": {"type": "string"},
        },
    }

    lines = [
        "You are a laboratory space planner. Return ONLY a single JSON object "
        "(no additional text) that conforms to the schema below. If you cannot "
        "fully place every item, include best-effort placements and list "
        "remaining items under 'recommendations'. Be concise but precise.",
        "\nJSON schema (informational, do not echo):",
        json.dumps(schema, indent=2),
        "\n",
        f"Experiment: {experiment_name}",
    ]
    if room_size:
        lines.append(
            f"Room size (meters): width={room_size.get('width_m')} "
            f"depth={room_size.get('depth_m')}"
        )
    lines += [
        "\nLarge fixed equipment (Category 1):",
        json.dumps(large_equipment, ensure_ascii=False, indent=2),
        "\nSmall movable equipment (Category 2):",
        json.dumps(small_equipment, ensure_ascii=False, indent=2),
        "\nUser constraints (structured):",
        json.dumps(constraints, ensure_ascii=False, indent=2),
        "\nInstructions:",
        "- Use meters for coordinates; origin (0,0) is the lower-left corner (south-west).",
        "- x increases to the east (right), y increases to the north (up).",
        "- Provide orientation as one of: north, south, east, west, north-east, etc.",
        "- For fixed equipment, place them aligned to walls if appropriate.",
        "- Provide a numeric clearance_m for required operational clearance.",
        "- If exact coordinates aren't feasible, set coordinates to null.",
    ]
    return "\n".join(lines)


_SYSTEM_MESSAGE = """\
You are an expert laboratory planner with knowledge of safety codes, \
ventilation, utilities, and ergonomic placement of laboratory equipment.

IMPORTANT: The JSON layout you will produce must satisfy a strict non-overlap \
constraint for all placed items.

Requirements:
1) All coordinates in meters; origin (0,0) is south-west corner.
2) Each equipment item includes dimensions_2d (width, depth in cm). \
Convert to meters.
3) Non-overlap constraint (hard): for every pair of placed items with numeric \
coordinates, their buffered footprints must NOT intersect.
4) Room bounds: all placed items must lie fully inside room boundaries.
5) Return ONLY a single JSON object conforming to the schema.\
"""


def generate_layout(
    experiment_name: str,
    large_equipment: dict,
    small_equipment: dict,
    constraints: dict,
    client: OpenAI,
    *,
    room_size: dict | None = None,
    model: str = DEFAULT_MODEL,
    dry_run: bool = False,
) -> dict:
    """Generate a lab layout via the LLM.

    Args:
        experiment_name: Name of the experiment.
        large_equipment: Large equipment mapping.
        small_equipment: Small equipment mapping.
        constraints: Structured constraints dict.
        client: An ``OpenAI``-compatible client.
        room_size: Optional ``{"width_m": …, "depth_m": …}``.
        model: Model identifier.
        dry_run: If ``True``, return a placeholder layout without calling the API.

    Returns:
        Parsed layout dict.
    """
    prompt = build_layout_prompt(
        experiment_name, large_equipment, small_equipment, constraints, room_size
    )

    if dry_run:
        sample: dict = {
            "room": {
                "width_m": room_size.get("width_m") if room_size else 6.0,
                "depth_m": room_size.get("depth_m") if room_size else 4.0,
                "units": "m",
            },
            "placements": [],
            "recommendations": "Dry-run: no model call performed.",
        }
        for name in large_equipment:
            sample["placements"].append(
                {
                    "item_name": name,
                    "category": "large",
                    "x_m": None,
                    "y_m": None,
                    "orientation": None,
                    "utilities": [],
                    "clearance_m": 1.0,
                    "justification": "Place against suitable wall.",
                }
            )
        for name in small_equipment:
            sample["placements"].append(
                {
                    "item_name": name,
                    "category": "small",
                    "x_m": None,
                    "y_m": None,
                    "orientation": None,
                    "utilities": [],
                    "clearance_m": 0.5,
                    "justification": "Movable; place on bench near associated equipment.",
                }
            )
        return sample

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": _SYSTEM_MESSAGE},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            max_tokens=1800,
            stream=False,
        )
        text = response.choices[0].message.content
        json_text = extract_json_from_text(text)
        if not json_text:
            raise ValueError("No JSON object found in model response.")
        return json.loads(json_text)
    except Exception as exc:
        raise RuntimeError(f"Failed to generate layout: {exc}") from exc
