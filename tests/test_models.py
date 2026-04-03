"""Tests for chemistry_lab.models."""

from chemistry_lab.models import Layout, Room


class TestRoom:
    def test_defaults(self):
        room = Room()
        assert room.width_m == 6.0
        assert room.depth_m == 4.0


class TestLayout:
    def test_from_dict(self):
        data = {
            "room": {"width_m": 8.0, "depth_m": 5.0, "units": "m"},
            "placements": [
                {
                    "item_name": "Bench",
                    "category": "large",
                    "x_m": 1.0,
                    "y_m": 2.0,
                    "orientation": "north",
                    "utilities": ["water"],
                    "clearance_m": 0.5,
                    "justification": "test",
                }
            ],
            "recommendations": "none",
        }
        layout = Layout.from_dict(data)
        assert layout.room.width_m == 8.0
        assert len(layout.placements) == 1
        assert layout.placements[0].item_name == "Bench"

    def test_empty_dict(self):
        layout = Layout.from_dict({})
        assert layout.room.width_m == 6.0
        assert layout.placements == []
