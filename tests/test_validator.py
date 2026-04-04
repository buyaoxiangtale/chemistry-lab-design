"""Unit tests for collision detection and schema validation."""

import pytest

from chemistry_lab.models import Layout, Placement, Room
from chemistry_lab.validator import (
    _rectangles_overlap,
    check_collisions,
    validate_layout_dict,
)


# ---------------------------------------------------------------------------
# Collision detection tests
# ---------------------------------------------------------------------------


class TestRectanglesOverlap:
    """Tests for the low-level rectangle overlap helper."""

    def test_no_overlap_separate(self):
        a = (0, 0, 1, 1)
        b = (2, 2, 3, 3)
        assert not _rectangles_overlap(a, b)

    def test_no_overlap_adjacent_edge(self):
        a = (0, 0, 1, 1)
        b = (1, 0, 2, 1)
        assert not _rectangles_overlap(a, b)  # touching edge = not overlapping

    def test_overlap_partial(self):
        a = (0, 0, 2, 2)
        b = (1, 1, 3, 3)
        assert _rectangles_overlap(a, b)

    def test_overlap_contained(self):
        a = (0, 0, 4, 4)
        b = (1, 1, 2, 2)
        assert _rectangles_overlap(a, b)

    def test_no_overlap_vertical(self):
        a = (0, 0, 1, 1)
        b = (0, 2, 1, 3)
        assert not _rectangles_overlap(a, b)


class TestCheckCollisions:
    """Tests for the high-level collision checker."""

    def _make_layout(self, placements):
        return Layout(
            room=Room(width_m=6.0, depth_m=4.0),
            placements=placements,
        )

    def test_no_collisions_normal_spacing(self):
        layout = self._make_layout([
            Placement(item_name="bench_a", category="large", x_m=0.0, y_m=0.0, clearance_m=0.0),
            Placement(item_name="bench_b", category="large", x_m=3.0, y_m=0.0, clearance_m=0.0),
        ])
        dims = {
            "bench_a": {"width_m": 1.5, "depth_m": 0.8},
            "bench_b": {"width_m": 1.5, "depth_m": 0.8},
        }
        assert check_collisions(layout, dims) == []

    def test_overlapping_items(self):
        layout = self._make_layout([
            Placement(item_name="hood_a", category="large", x_m=0.0, y_m=0.0, clearance_m=0.0),
            Placement(item_name="hood_b", category="large", x_m=0.5, y_m=0.0, clearance_m=0.0),
        ])
        dims = {
            "hood_a": {"width_m": 1.5, "depth_m": 0.8},
            "hood_b": {"width_m": 1.5, "depth_m": 0.8},
        }
        collisions = check_collisions(layout, dims)
        assert len(collisions) == 1
        assert "hood_a" in collisions[0]
        assert "hood_b" in collisions[0]

    def test_edge_touching_no_collision(self):
        layout = self._make_layout([
            Placement(item_name="item_a", category="large", x_m=0.0, y_m=0.0, clearance_m=0.0),
            Placement(item_name="item_b", category="large", x_m=1.0, y_m=0.0, clearance_m=0.0),
        ])
        dims = {
            "item_a": {"width_m": 1.0, "depth_m": 0.5},
            "item_b": {"width_m": 1.0, "depth_m": 0.5},
        }
        assert check_collisions(layout, dims) == []

    def test_clearance_causes_overlap(self):
        layout = self._make_layout([
            Placement(item_name="a", category="large", x_m=0.0, y_m=0.0, clearance_m=0.5),
            Placement(item_name="b", category="large", x_m=1.0, y_m=0.0, clearance_m=0.5),
        ])
        dims = {
            "a": {"width_m": 0.5, "depth_m": 0.5},
            "b": {"width_m": 0.5, "depth_m": 0.5},
        }
        collisions = check_collisions(layout, dims)
        assert len(collisions) == 1

    def test_null_coordinates_skipped(self):
        layout = self._make_layout([
            Placement(item_name="a", category="large", x_m=None, y_m=None),
            Placement(item_name="b", category="large", x_m=1.0, y_m=1.0),
        ])
        assert check_collisions(layout) == []

    def test_default_dims_when_not_provided(self):
        layout = self._make_layout([
            Placement(item_name="x", category="small", x_m=0.0, y_m=0.0, clearance_m=0.0),
            Placement(item_name="y", category="small", x_m=0.3, y_m=0.0, clearance_m=0.0),
        ])
        # default dim is 0.5x0.5 — 0.3 offset means they overlap
        collisions = check_collisions(layout)
        assert len(collisions) == 1


# ---------------------------------------------------------------------------
# Schema validation tests
# ---------------------------------------------------------------------------


class TestValidateLayoutDict:
    def test_valid_layout(self):
        data = {
            "room": {"width_m": 6.0, "depth_m": 4.0, "units": "m"},
            "placements": [
                {
                    "item_name": "bench",
                    "category": "large",
                    "x_m": 1.0,
                    "y_m": 2.0,
                    "clearance_m": 0.5,
                }
            ],
        }
        assert validate_layout_dict(data) == []

    def test_missing_room(self):
        data = {"placements": []}
        issues = validate_layout_dict(data)
        assert any("'room'" in i for i in issues)

    def test_missing_placements(self):
        data = {"room": {"width_m": 6.0, "depth_m": 4.0}}
        issues = validate_layout_dict(data)
        assert any("'placements'" in i for i in issues)

    def test_coord_out_of_range(self):
        data = {
            "room": {"width_m": 6.0, "depth_m": 4.0},
            "placements": [
                {"item_name": "x", "category": "large", "x_m": 10.0, "y_m": 0.5}
            ],
        }
        issues = validate_layout_dict(data, room_width=6.0, room_depth=4.0)
        assert any("exceeds room width" in i for i in issues)

    def test_non_dict_input(self):
        issues = validate_layout_dict("not a dict")
        assert len(issues) > 0
