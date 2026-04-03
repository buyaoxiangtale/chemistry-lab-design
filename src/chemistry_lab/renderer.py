"""2D lab layout visualisation using matplotlib."""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from typing import Dict, Optional

import matplotlib

matplotlib.use("Agg")  # non-interactive backend
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
from matplotlib.patches import Arrow, Rectangle

# ---------------------------------------------------------------------------
# Colour map
# ---------------------------------------------------------------------------
CATEGORY_COLORS: Dict[str, str] = {
    "Workstation": "#ADD8E6",
    "Storage": "#90EE90",
    "Apparatus": "#FFB6C1",
    "Utility": "#F0E68C",
    "Safety": "#FFA07A",
    "Workstation/Safety": "#E6E6FA",
    "Utility/Safety": "#FFE4B5",
}


def _get_font() -> Optional[FontProperties]:
    """Attempt to locate a CJK-capable font."""
    if sys.platform.startswith("win"):
        path = "C:/Windows/Fonts/msyh.ttc"
        if os.path.exists(path):
            return FontProperties(fname=path)
    elif sys.platform.startswith("linux"):
        path = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
        if os.path.exists(path):
            return FontProperties(fname=path)
    return None


CHINESE_FONT = _get_font()
plt.rcParams["axes.unicode_minus"] = False


def load_layout(json_file: str) -> Dict:
    """Load a layout JSON file."""
    with open(json_file, "r", encoding="utf-8") as fh:
        return json.load(fh)


def _category_color(category: str) -> str:
    main = category.split("/")[0]
    return CATEGORY_COLORS.get(main, "#CCCCCC")


def _draw_orientation_arrow(ax, box: Dict, color: str) -> None:
    """Draw a direction arrow on *ax* for *box*."""
    bb = box["bounding_box"]
    cx, cy = bb["center_x"], bb["center_y"]
    w, h = bb["width"], bb["height"]
    orientation = box.get("orientation", "north")
    arrow_len = min(w, h) * 0.3

    dx, dy = 0.0, 0.0
    base_x, base_y = cx, cy

    if orientation == "north":
        dy = arrow_len
        base_y = cy - h / 4
    elif orientation == "south":
        dy = -arrow_len
        base_y = cy + h / 4
    elif orientation == "east":
        dx = arrow_len
        base_x = cx - w / 4
    elif orientation == "west":
        dx = -arrow_len
        base_x = cx + w / 4

    ax.add_patch(
        Arrow(base_x, base_y, dx, dy, width=arrow_len * 0.5, color=color, alpha=0.6)
    )


def visualize_layout(
    json_file: str,
    output_file: str | None = None,
) -> str:
    """Render a 2D lab layout from a bounding-box JSON file.

    Args:
        json_file: Path to a bounding-box JSON file.
        output_file: Destination path for the PNG.  Auto-generated if ``None``.

    Returns:
        Path to the saved image.
    """
    layout = load_layout(json_file)

    fig, ax = plt.subplots(figsize=(12, 8))
    room_width = layout["room_dimensions"]["width"]
    room_depth = layout["room_dimensions"]["depth"]

    margin = 0.5
    ax.set_xlim(-margin, room_width + margin)
    ax.set_ylim(-margin, room_depth + margin)
    ax.add_patch(Rectangle((0, 0), room_width, room_depth, fill=False, color="black", linewidth=2))

    for box in layout.get("bounding_boxes", []):
        bb = box["bounding_box"]
        x = bb["center_x"] - bb["width"] / 2
        y = bb["center_y"] - bb["height"] / 2
        color = _category_color(box["category"])

        ax.add_patch(Rectangle((x, y), bb["width"], bb["height"], fill=True, color=color, alpha=0.3))
        ax.add_patch(Rectangle((x, y), bb["width"], bb["height"], fill=False, color=color, linewidth=1.5))
        _draw_orientation_arrow(ax, box, color)

        name = box["name"]
        if len(name) > 15:
            name = name.replace(" (", "\n(")
        ax.text(
            bb["center_x"],
            bb["center_y"],
            name,
            ha="center",
            va="center",
            fontsize=8,
            color="black",
            fontproperties=CHINESE_FONT,
        )

        clearance = box.get("clearance", {}).get("value", 0)
        if clearance > 0:
            ax.add_patch(
                Rectangle(
                    (x - clearance, y - clearance),
                    bb["width"] + 2 * clearance,
                    bb["height"] + 2 * clearance,
                    fill=False,
                    color=color,
                    linestyle="--",
                    linewidth=0.8,
                )
            )

    ax.set_xlabel("Width (m)", fontproperties=CHINESE_FONT)
    ax.set_ylabel("Depth (m)", fontproperties=CHINESE_FONT)
    ax.set_title("Lab Layout", fontproperties=CHINESE_FONT)
    ax.grid(True, linestyle="--", alpha=0.3)
    ax.set_aspect("equal")

    legend_cats = list(CATEGORY_COLORS.keys())
    legend_handles = [
        plt.Rectangle((0, 0), 1, 1, facecolor=CATEGORY_COLORS[c], alpha=0.3, label=c)
        for c in legend_cats
    ]
    ax.legend(handles=legend_handles, loc="center left", bbox_to_anchor=(1, 0.5), prop=CHINESE_FONT)

    plt.tight_layout()

    if output_file is None:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"lab_layout_visualization_{ts}.png"

    plt.savefig(output_file, dpi=300, bbox_inches="tight")
    plt.close(fig)
    return output_file
