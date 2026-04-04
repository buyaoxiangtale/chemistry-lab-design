"""Lab layout generation via LLM."""

from __future__ import annotations

import json
import logging
from typing import Dict, List

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from openai import OpenAI

from chemistry_lab.client import call_with_retry
from chemistry_lab.config import DEFAULT_MODEL
from chemistry_lab.models import Layout, Placement, Room
from chemistry_lab.parser import extract_json_from_text

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Equipment normalisation
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Prompt building
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Schema validation
# ---------------------------------------------------------------------------

def validate_layout(data: dict) -> List[str]:
    """Validate a layout dict against the expected schema.

    Returns a list of warning strings (empty if valid).
    """
    warnings: List[str] = []

    room = data.get("room")
    if not isinstance(room, dict):
        warnings.append("Missing or invalid 'room' object.")
    else:
        for key in ("width_m", "depth_m"):
            val = room.get(key)
            if val is not None and not isinstance(val, (int, float)):
                warnings.append(f"room.{key} should be a number, got {type(val).__name__}.")
            if isinstance(val, (int, float)) and val <= 0:
                warnings.append(f"room.{key} must be positive, got {val}.")

    placements = data.get("placements", [])
    if not isinstance(placements, list):
        warnings.append("'placements' should be a list.")
        return warnings

    room_w = room.get("width_m", 0) if isinstance(room, dict) else 0
    room_d = room.get("depth_m", 0) if isinstance(room, dict) else 0

    for i, p in enumerate(placements):
        if not isinstance(p, dict):
            warnings.append(f"placements[{i}] is not a dict.")
            continue
        for req in ("item_name", "category"):
            if not p.get(req):
                warnings.append(f"placements[{i}] missing required field '{req}'.")
        x, y = p.get("x_m"), p.get("y_m")
        if x is not None and isinstance(room_w, (int, float)) and room_w > 0:
            if x < 0 or x > room_w:
                warnings.append(f"placements[{i}] x_m={x} is outside room width [0, {room_w}].")
        if y is not None and isinstance(room_d, (int, float)) and room_d > 0:
            if y < 0 or y > room_d:
                warnings.append(f"placements[{i}] y_m={y} is outside room depth [0, {room_d}].")
        clr = p.get("clearance_m")
        if clr is not None and not isinstance(clr, (int, float)):
            warnings.append(f"placements[{i}] clearance_m should be a number.")

    return warnings


# ---------------------------------------------------------------------------
# Collision detection
# ---------------------------------------------------------------------------

def _footprint(x: float, y: float, half_w: float, half_d: float) -> tuple:
    """Return (x_min, y_min, x_max, y_max) of a rectangular footprint."""
    return (x - half_w, y - half_d, x + half_w, y + half_d)


def _rectangles_overlap(a: tuple, b: tuple) -> bool:
    """Return True if axis-aligned rectangles *a* and *b* overlap."""
    return not (a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1])


def detect_collisions(
    placements: List[Placement],
    room: Room,
    default_half_w: float = 0.3,
    default_half_d: float = 0.3,
) -> List[str]:
    """Check for overlapping equipment footprints.

    Each placement uses its ``clearance_m`` as a buffer around the default
    half-dimensions.  Placements with ``None`` coordinates are skipped.

    Args:
        placements: List of Placement objects.
        room: Room dimensions.
        default_half_w: Default half-width in metres when not available.
        default_half_d: Default half-depth in metres when not available.

    Returns:
        List of collision warning strings.
    """
    footprints: List[tuple[float, float, tuple, str]] = []
    for p in placements:
        if p.x_m is None or p.y_m is None:
            continue
        buf = p.clearance_m / 2 if p.clearance_m else 0
        hw = default_half_w + buf
        hd = default_half_d + buf
        footprints.append((p.x_m, p.y_m, _footprint(p.x_m, p.y_m, hw, hd), p.item_name))

    collisions: List[str] = []
    for i in range(len(footprints)):
        for j in range(i + 1, len(footprints)):
            x1, y1, fp1, name1 = footprints[i]
            x2, y2, fp2, name2 = footprints[j]
            if _rectangles_overlap(fp1, fp2):
                collisions.append(
                    f"Collision: '{name1}' ({x1:.2f},{y1:.2f}) overlaps "
                    f"'{name2}' ({x2:.2f},{y2:.2f})"
                )
    return collisions


# ---------------------------------------------------------------------------
# Layout generation
# ---------------------------------------------------------------------------

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

    text = call_with_retry(
        client,
        model=model,
        messages=[
            {"role": "system", "content": _SYSTEM_MESSAGE},
            {"role": "user", "content": prompt},
        ],
        temperature=0.1,
        max_tokens=1800,
    )
    json_text = extract_json_from_text(text)
    if not json_text:
        raise ValueError("No JSON object found in model response.")
    layout = json.loads(json_text)

    # Schema validation
    schema_warnings = validate_layout(layout)
    for w in schema_warnings:
        logger.warning("Layout schema warning: %s", w)

    # Collision detection
    layout_obj = Layout.from_dict(layout)
    collision_warnings = detect_collisions(layout_obj.placements, layout_obj.room)
    for w in collision_warnings:
        logger.warning("Layout collision: %s", w)

    return layout
