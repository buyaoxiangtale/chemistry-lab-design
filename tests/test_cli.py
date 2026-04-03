"""Tests for chemistry_lab.cli."""

from chemistry_lab.cli import _build_parser


class TestCLIParser:
    def test_layout_subcommand(self):
        parser = _build_parser()
        args = parser.parse_args(["layout", "-e", "test experiment", "--dry-run"])
        assert args.experiment == "test experiment"
        assert args.dry_run is True

    def test_equipment_subcommand(self):
        parser = _build_parser()
        args = parser.parse_args(["equipment", "crude salt purification"])
        assert args.experiment == "crude salt purification"

    def test_layout_room_dimensions(self):
        parser = _build_parser()
        args = parser.parse_args(["layout", "-e", "test", "--width", "8", "--depth", "5"])
        assert args.width == 8.0
        assert args.depth == 5.0
