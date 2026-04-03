"""Data models for the chemistry-lab package."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class EquipmentItem:
    """A single piece of lab equipment."""

    name: str
    category: str  # "large" or "small"
    description: str = ""
    dimensions_2d: Dict[str, float] = field(default_factory=dict)  # {"width": cm, "depth": cm}
    properties: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Placement:
    """A placement of an equipment item within a room."""

    item_name: str
    category: str
    x_m: Optional[float] = None
    y_m: Optional[float] = None
    orientation: Optional[str] = None
    utilities: List[str] = field(default_factory=list)
    clearance_m: float = 0.0
    justification: str = ""


@dataclass
class Room:
    """Room dimensions."""

    width_m: float = 6.0
    depth_m: float = 4.0
    units: str = "m"


@dataclass
class Layout:
    """A complete lab layout."""

    room: Room = field(default_factory=Room)
    placements: List[Placement] = field(default_factory=list)
    recommendations: str = ""

    @classmethod
    def from_dict(cls, data: dict) -> Layout:
        room_data = data.get("room", {})
        room = Room(
            width_m=room_data.get("width_m", 6.0),
            depth_m=room_data.get("depth_m", 4.0),
            units=room_data.get("units", "m"),
        )
        placements = []
        for p in data.get("placements", []):
            placements.append(
                Placement(
                    item_name=p.get("item_name", ""),
                    category=p.get("category", ""),
                    x_m=p.get("x_m"),
                    y_m=p.get("y_m"),
                    orientation=p.get("orientation"),
                    utilities=p.get("utilities", []),
                    clearance_m=p.get("clearance_m", 0.0),
                    justification=p.get("justification", ""),
                )
            )
        return cls(
            room=room,
            placements=placements,
            recommendations=data.get("recommendations", ""),
        )
