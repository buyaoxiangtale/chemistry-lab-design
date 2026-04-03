"""Unified CLI entry point for the chemistry-lab package."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime

from chemistry_lab.client import create_client
from chemistry_lab.equipment import generate_equipment
from chemistry_lab.layout import generate_layout, normalize_equipment
from chemistry_lab.room import parse_constraints


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="chemistry-lab",
        description="Chemistry Lab Layout Generator",
    )
    sub = parser.add_subparsers(dest="command", help="Available sub-commands")

    # ---- equipment ----------------------------------------------------------
    eq = sub.add_parser("equipment", help="Generate equipment list for an experiment")
    eq.add_argument("experiment", help="Experiment name")
    eq.add_argument("--output", "-o", help="Output JSON path")

    # ---- layout -------------------------------------------------------------
    lo = sub.add_parser("layout", help="Generate a lab layout")
    lo.add_argument("--experiment", "-e", required=True, help="Experiment name")
    lo.add_argument("--large-equipment-file", "-L", help="Path to large equipment JSON")
    lo.add_argument("--small-equipment-file", "-S", help="Path to small equipment JSON")
    lo.add_argument("--constraints", "-c", help="Constraints string (semicolon-separated)")
    lo.add_argument("--constraints-file", "-C", help="Path to constraints JSON")
    lo.add_argument("--width", type=float, default=6.0, help="Room width (m)")
    lo.add_argument("--depth", type=float, default=4.0, help="Room depth (m)")
    lo.add_argument("--output", "-o", help="Output JSON path")
    lo.add_argument("--dry-run", action="store_true", help="Placeholder layout (no API call)")

    return parser


def _cmd_equipment(args: argparse.Namespace) -> None:
    client = create_client()
    large, small = generate_equipment(args.experiment, client)

    result = {"experiment": args.experiment, "large_equipment": large, "small_equipment": small}
    out_path = args.output or f"{args.experiment.replace(' ', '_').lower()}_equipment.json"
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(result, fh, ensure_ascii=False, indent=2)
    print(f"Equipment list saved to: {out_path}")


def _cmd_layout(args: argparse.Namespace) -> None:
    client = create_client()

    large_equipment: dict = {}
    small_equipment: dict = {}

    if args.large_equipment_file and os.path.exists(args.large_equipment_file):
        with open(args.large_equipment_file, "r", encoding="utf-8") as fh:
            large_equipment = normalize_equipment(json.load(fh))

    if args.small_equipment_file and os.path.exists(args.small_equipment_file):
        with open(args.small_equipment_file, "r", encoding="utf-8") as fh:
            small_equipment = normalize_equipment(json.load(fh))

    constraints: dict = {"raw": ""}
    if args.constraints_file and os.path.exists(args.constraints_file):
        with open(args.constraints_file, "r", encoding="utf-8") as fh:
            try:
                constraints = json.load(fh)
            except Exception:
                constraints = {"raw": fh.read()}
    elif args.constraints:
        constraints = parse_constraints(args.constraints)

    room_size = {"width_m": args.width, "depth_m": args.depth}

    layout = generate_layout(
        args.experiment,
        large_equipment,
        small_equipment,
        constraints,
        client,
        room_size=room_size,
        dry_run=args.dry_run,
    )

    out_path = args.output
    if not out_path:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe = args.experiment.replace(" ", "_").lower()
        out_path = f"{safe}_layout_{ts}.json"

    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(layout, fh, ensure_ascii=False, indent=2)
    print(f"Layout saved to: {out_path}")


def main(argv: list[str] | None = None) -> None:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "equipment":
        _cmd_equipment(args)
    elif args.command == "layout":
        _cmd_layout(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
