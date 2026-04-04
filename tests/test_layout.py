"""Tests for chemistry_lab.layout – collision detection and layout generation."""

import json

from chemistry_lab.layout import (
    detect_collisions,
    generate_layout,
    normalize_equipment,
    validate_layout,
)
from chemistry_lab.models import Placement, Room
from unittest.mock import MagicMock


# ---------------------------------------------------------------------------
# normalize_equipment
# ---------------------------------------------------------------------------

class TestNormalizeEquipment:
    def test_dict_passthrough(self):
        data = {"Bench": {"size": "large"}}
        assert normalize_equipment(data) == data

    def test_list_of_dicts(self):
        data = [{"name": "Bench", "id": "bench1"}, {"name": "Hood", "id": "hood1"}]
        result = normalize_equipment(data)
        assert "Bench" in result
        assert "Hood" in result

    def test_none(self):
        assert normalize_equipment(None) == {}

    def test_list_uses_id_fallback(self):
        data = [{"id": "item1"}]
        result = normalize_equipment(data)
        assert "item1" in result


# ---------------------------------------------------------------------------
# generate_layout (dry-run)
# ---------------------------------------------------------------------------

class TestGenerateLayoutDryRun:
    def test_dry_run_returns_structure(self):
        layout = generate_layout(
            "test experiment",
            {"Bench": {}},
            {"Beaker": {}},
            {"raw": ""},
            client=MagicMock(),
            dry_run=True,
        )
        assert "room" in layout
        assert "placements" in layout
        assert len(layout["placements"]) == 2

    def test_dry_run_with_room_size(self):
        layout = generate_layout(
            "test",
            {},
            {},
            {},
            client=MagicMock(),
            room_size={"width_m": 8.0, "depth_m": 5.0},
            dry_run=True,
        )
        assert layout["room"]["width_m"] == 8.0
        assert layout["room"]["depth_m"] == 5.0


# ---------------------------------------------------------------------------
# Collision detection
# ---------------------------------------------------------------------------

class TestDetectCollisions:
    """Tests for the detect_collisions function."""

    def _make_placement(self, name, x, y, clearance=0.0):
        return Placement(
            item_name=name, category="large", x_m=x, y_m=y, clearance_m=clearance
        )

    def test_no_overlap(self):
        """Well-separated items produce no collisions."""
        room = Room(width_m=10.0, depth_m=8.0)
        placements = [
            self._make_placement("A", 1.0, 1.0),
            self._make_placement("B", 5.0, 5.0),
        ]
        assert detect_collisions(placements, room) == []

    def test_overlapping(self):
        """Two items at the same coordinates should collide."""
        room = Room(width_m=10.0, depth_m=8.0)
        placements = [
            self._make_placement("A", 2.0, 2.0),
            self._make_placement("B", 2.0, 2.0),
        ]
        collisions = detect_collisions(placements, room)
        assert len(collisions) > 0
        assert "A" in collisions[0]
        assert "B" in collisions[0]

    def test_edge_touching_no_collision(self):
        """Items exactly touching edges should NOT collide (adjacent, not overlapping)."""
        room = Room(width_m=10.0, depth_m=8.0)
        # default half_w=0.3, so A spans [0.7, 1.3] and B spans [1.3, 1.9]
        placements = [
            self._make_placement("A", 1.0, 1.0),
            self._make_placement("B", 1.6, 1.0),
        ]
        collisions = detect_collisions(placements, room)
        assert collisions == []

    def test_slight_overlap(self):
        """Items slightly overlapping should collide."""
        room = Room(width_m=10.0, depth_m=8.0)
        # default half_w=0.3: A spans [0.7, 1.3], B spans [1.2, 1.8] → overlap
        placements = [
            self._make_placement("A", 1.0, 1.0),
            self._make_placement("B", 1.5, 1.0),
        ]
        collisions = detect_collisions(placements, room)
        assert len(collisions) > 0

    def test_with_clearance(self):
        """Clearance expands the footprint and can cause collisions."""
        room = Room(width_m=10.0, depth_m=8.0)
        # With clearance=2.0, buf=1.0, hw=0.3+1.0=1.3 → A spans [-0.3, 2.3]
        # B at (2.0, 1.0) with no clearance, hw=0.3 → spans [1.7, 2.3]
        # A.x_max=2.3 > B.x_min=1.7 → overlap
        placements = [
            self._make_placement("A", 1.0, 1.0, clearance=2.0),
            self._make_placement("B", 2.0, 1.0, clearance=0.0),
        ]
        collisions = detect_collisions(placements, room)
        assert len(collisions) > 0

    def test_none_coordinates_skipped(self):
        """Placements with None coordinates are ignored."""
        room = Room(width_m=10.0, depth_m=8.0)
        placements = [
            self._make_placement("A", 1.0, 1.0),
            Placement(item_name="B", category="large", x_m=None, y_m=None),
        ]
        assert detect_collisions(placements, room) == []

    def test_empty_placements(self):
        """Empty placement list produces no collisions."""
        room = Room(width_m=10.0, depth_m=8.0)
        assert detect_collisions([], room) == []


# ---------------------------------------------------------------------------
# Schema validation
# ---------------------------------------------------------------------------

class TestValidateLayout:
    def test_valid_layout(self):
        data = {
            "room": {"width_m": 6.0, "depth_m": 4.0},
            "placements": [
                {"item_name": "Bench", "category": "large", "x_m": 1.0, "y_m": 1.0}
            ],
        }
        assert validate_layout(data) == []

    def test_missing_room(self):
        assert len(validate_layout({"placements": []})) > 0

    def test_coordinate_out_of_bounds(self):
        data = {
            "room": {"width_m": 6.0, "depth_m": 4.0},
            "placements": [
                {"item_name": "X", "category": "large", "x_m": 99.0, "y_m": 1.0}
            ],
        }
        warnings = validate_layout(data)
        assert any("outside room" in w for w in warnings)

    def test_missing_required_fields(self):
        data = {
            "room": {"width_m": 6.0, "depth_m": 4.0},
            "placements": [{"x_m": 1.0}],
        }
        warnings = validate_layout(data)
        assert any("missing required" in w for w in warnings)


# ---------------------------------------------------------------------------
# Mock API tests
# ---------------------------------------------------------------------------

class TestGenerateLayoutMockAPI:
    """Test layout generation with a mocked LLM response."""

    def test_mock_api_returns_layout(self):
        """Simulate a successful LLM response."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "room": {"width_m": 6.0, "depth_m": 4.0, "units": "m"},
            "placements": [
                {
                    "item_name": "Fume Hood",
                    "category": "large",
                    "x_m": 1.5,
                    "y_m": 3.0,
                    "orientation": "north",
                    "utilities": ["ventilation"],
                    "clearance_m": 1.0,
                    "justification": "Against north wall",
                }
            ],
            "recommendations": "None",
        })
        mock_client.chat.completions.create.return_value = mock_response

        layout = generate_layout(
            "test",
            {"Fume Hood": {}},
            {},
            {},
            client=mock_client,
        )
        assert layout["room"]["width_m"] == 6.0
        assert len(layout["placements"]) == 1
        assert layout["placements"][0]["item_name"] == "Fume Hood"

    def test_mock_api_retry_on_failure(self):
        """Verify retry logic works when first call fails."""
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = [
            Exception("timeout"),
            Exception("rate limit"),
            MagicMock(
                choices=[MagicMock(
                    message=MagicMock(content='{"room": {"width_m": 6.0, "depth_m": 4.0}, "placements": []}')
                )]
            ),
        ]

        layout = generate_layout(
            "test", {}, {}, {}, client=mock_client,
        )
        assert layout["room"]["width_m"] == 6.0
        assert mock_client.chat.completions.create.call_count == 3
