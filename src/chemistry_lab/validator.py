"""Schema validation and collision detection for lab layouts."""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Tuple

from chemistry_lab.models import Layout

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Schema validation
# ---------------------------------------------------------------------------

def validate_layout_dict(data: dict, *, room_width: float = 6.0, room_depth: float = 4.0) -> List[str]:
    """Validate a raw layout dict against the expected schema.

    Checks for required fields, correct types, and coordinate ranges.

    Args:
        data: The layout dict to validate.
        room_width: Expected room width in metres.
        room_depth: Expected room depth in metres.

    Returns:
        A list of warning / error messages.  Empty means valid.
    """
    issues: list[str] = []

    # Top-level structure
    if not isinstance(data, dict):
        return ["Layout must be a JSON object (dict)."]

    # Room
    room = data.get("room")
    if room is None:
        issues.append("Missing required field: 'room'.")
    elif not isinstance(room, dict):
        issues.append("'room' must be an object.")
    else:
        for key in ("width_m", "depth_m"):
            val = room.get(key)
            if val is None:
                issues.append(f"Room missing '{key}'.")
            elif not isinstance(val, (int, float)):
                issues.append(f"Room '{key}' must be a number, got {type(val).__name__}.")

    # Placements
    placements = data.get("placements")
    if placements is None:
        issues.append("Missing required field: 'placements'.")
    elif not isinstance(placements, list):
        issues.append("'placements' must be an array.")
    else:
        for idx, p in enumerate(placements):
            if not isinstance(p, dict):
                issues.append(f"placements[{idx}] must be an object.")
                continue
            # Required string fields
            for key in ("item_name", "category"):
                val = p.get(key)
                if val is None:
                    issues.append(f"placements[{idx}] missing '{key}'.")
                elif not isinstance(val, str):
                    issues.append(f"placements[{idx}].{key} must be a string.")
            # Numeric fields with range check
            for key in ("x_m", "y_m", "clearance_m"):
                val = p.get(key)
                if val is not None:
                    if not isinstance(val, (int, float)):
                        issues.append(f"placements[{idx}].{key} must be a number.")
                    elif val < 0:
                        issues.append(f"placements[{idx}].{key} is negative: {val}.")
            # x_m should be within room width
            if isinstance(p.get("x_m"), (int, float)) and isinstance(room_width, (int, float)):
                if p["x_m"] > room_width:
                    issues.append(f"placements[{idx}].x_m ({p['x_m']}) exceeds room width ({room_width}).")
            # y_m should be within room depth
            if isinstance(p.get("y_m"), (int, float)) and isinstance(room_depth, (int, float)):
                if p["y_m"] > room_depth:
                    issues.append(f"placements[{idx}].y_m ({p['y_m']}) exceeds room depth ({room_depth}).")

    return issues


# ---------------------------------------------------------------------------
# Collision detection
# ---------------------------------------------------------------------------

def _get_footprint(
    x: float, y: float, width_m: float, depth_m: float, clearance_m: float = 0.0
) -> Tuple[float, float, float, float]:
    """Return (x_min, y_min, x_max, y_max) of a buffered rectangle.

    The placement coordinates *(x, y)* are treated as the lower-left corner.
    """
    return (
        x - clearance_m,
        y - clearance_m,
        x + width_m + clearance_m,
        y + depth_m + clearance_m,
    )


def _rectangles_overlap(
    a: Tuple[float, float, float, float],
    b: Tuple[float, float, float, float],
) -> bool:
    """Check whether two axis-aligned rectangles overlap."""
    return not (a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1])


def check_collisions(
    layout: Layout,
    equipment_dims: Optional[Dict[str, Dict[str, float]]] = None,
) -> List[str]:
    """Detect overlapping equipment placements.

    Args:
        layout: A ``Layout`` model with placements to check.
        equipment_dims: Mapping of item_name to ``{"width_m": …, "depth_m": …}``.
            If omitted, each item is assumed to be a 0.5m x 0.5m square.

    Returns:
        A list of collision descriptions.  Empty means no overlaps.
    """
    default_dim = {"width_m": 0.5, "depth_m": 0.5}
    collisions: list[str] = []

    # Build footprints for all placed items with numeric coordinates
    placed: list[tuple[str, tuple[float, float, float, float]]] = []
    for p in layout.placements:
        if p.x_m is None or p.y_m is None:
            continue
        dims = (equipment_dims or {}).get(p.item_name, default_dim)
        w = dims.get("width_m", default_dim["width_m"])
        d = dims.get("depth_m", default_dim["depth_m"])
        footprint = _get_footprint(p.x_m, p.y_m, w, d, p.clearance_m)
        placed.append((p.item_name, footprint))

    # Pairwise check
    for i in range(len(placed)):
        for j in range(i + 1, len(placed)):
            name_a, fp_a = placed[i]
            name_b, fp_b = placed[j]
            if _rectangles_overlap(fp_a, fp_b):
                collisions.append(
                    f"Collision: '{name_a}' {fp_a} overlaps '{name_b}' {fp_b}"
                )

    return collisions
