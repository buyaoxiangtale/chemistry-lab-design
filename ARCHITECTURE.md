# Architecture

## Module Relationships

```
cli.py  (entry point)
  ├── equipment.py    (generate equipment lists)
  │     └── client.py (LLM API calls with retry)
  ├── layout.py       (generate layouts, validate, detect collisions)
  │     ├── client.py
  │     ├── parser.py (extract JSON from LLM text)
  │     └── models.py (Placement, Room, Layout dataclasses)
  ├── room.py         (parse constraints, design room)
  │     └── client.py
  └── renderer.py     (2D matplotlib visualization)
        └── models.py

config.py  (centralized settings, used by all modules)
```

## Data Flow

```
1. Equipment Generation
   experiment_name → equipment.py → LLM → parse_equipment_response()
   → {large_equipment, small_equipment} dicts

2. Layout Generation
   equipment + constraints + room_size → layout.py → LLM
   → parser.extract_json_from_text() → JSON layout
   → validate_layout() (schema check)
   → detect_collisions() (overlap check)
   → layout dict with room, placements, recommendations

3. Visualization
   layout JSON → renderer.py → matplotlib 2D PNG
```

## Design Decisions

### `json.JSONDecoder.raw_decode()` for parsing
LLM responses often contain JSON mixed with prose. `raw_decode()` provides standards-compliant extraction starting from a given position, avoiding fragile hand-written bracket matching. A bracket-matching heuristic remains as a fallback for edge cases.

### Exponential backoff retry
LLM API calls are inherently unreliable (rate limits, timeouts). The retry wrapper in `client.call_with_retry()` applies exponential delays (1s, 2s, 4s) with a configurable max of 3 attempts, logging each failure.

### Dataclass models over Pydantic
`models.py` uses stdlib `dataclasses` to avoid an extra dependency. The `Layout.from_dict()` classmethod handles conversion from raw JSON dicts. Schema validation is done explicitly in `layout.validate_layout()`.

### Collision detection algorithm
Each equipment item is modeled as an axis-aligned rectangle (footprint = center ± half-dimensions + clearance buffer). Overlap is checked with standard AABB intersection tests. Items with `None` coordinates are skipped. Time complexity is O(n^2) which is fine for typical lab layouts (< 50 items).

### CLI with subcommands
`cli.py` uses `argparse` subcommands (`equipment`, `layout`) for clean separation. `--dry-run` generates a placeholder layout without calling the LLM, enabling offline testing.

### Logging over print
All modules use `logging.getLogger(__name__)` with configurable levels via `--verbose` flag. No `print()` calls in library code.
