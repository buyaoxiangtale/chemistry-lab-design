"""Tests for chemistry_lab.layout."""

from chemistry_lab.layout import normalize_equipment, generate_layout
from unittest.mock import MagicMock


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
