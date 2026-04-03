"""Tests for chemistry_lab.room."""

from chemistry_lab.room import parse_constraints


class TestParseConstraints:
    def test_basic_placement(self):
        result = parse_constraints("fume hood in upper-right corner")
        assert len(result["placements"]) == 1
        assert result["placements"][0]["item"].lower() == "fume hood"

    def test_multiple_constraints(self):
        result = parse_constraints("fume hood in upper-right corner; sink on north wall")
        assert len(result["placements"]) == 2

    def test_colon_syntax(self):
        result = parse_constraints("Fume Hood: north wall")
        assert len(result["placements"]) == 1
        assert result["placements"][0]["item"] == "Fume Hood"

    def test_empty(self):
        result = parse_constraints("")
        assert result["placements"] == []
        assert result["notes"] == []

    def test_notes_fallback(self):
        result = parse_constraints("ensure good ventilation")
        assert "ensure good ventilation" in result["notes"]
