# Chemistry Lab Layout Generator

AI-powered tool for generating chemistry laboratory equipment lists, planning space layouts, and producing 2D visualizations.

## Features

- Generate categorized equipment lists for chemistry experiments via LLM
- Plan lab space layouts with collision detection and constraint validation
- Produce 2D floor-plan visualizations (PNG)
- Configurable room dimensions, equipment, and safety constraints
- Dry-run mode for testing without API calls

## Installation

```bash
# Clone the repository
git clone <repo-url>
cd chemistry-lab

# Install with dev dependencies (recommended)
python -m pip install -e ".[dev]"

# Or install without dev tools
python -m pip install -e .
```

Requires Python >= 3.10.

## Configuration

Copy `.env.example` to `.env` and fill in your API keys:

```bash
cp .env.example .env
```

| Variable | Required | Description |
|---|---|---|
| `CHEM_LAB_API_KEY` | Yes | DeepSeek LLM API key |
| `CHEM_LAB_BASE_URL` | No | API base URL (default: `https://api.deepseek.com`) |
| `DASHSCOPE_API_KEY` | No | DashScope image generation API key |
| `CHEM_LAB_IMAGE_DIR` | No | Output directory for images (default: `output`) |

## Usage

### Generate equipment list

```bash
chemistry-lab equipment "crude salt purification"
```

### Generate layout (dry-run, no API call)

```bash
chemistry-lab layout -e "crude salt purification" --dry-run
```

### Generate layout with constraints

```bash
chemistry-lab layout \
  -e "crude salt purification" \
  -L large_equipment.json \
  -S small_equipment.json \
  -C constraints.json \
  --width 8 --depth 6 \
  -o my_layout.json
```

### Visualize a layout

```python
from chemistry_lab.renderer import visualize_layout

output_path = visualize_layout("my_layout.json")
print(f"Saved to {output_path}")
```

## Development

```bash
# Run tests
make test

# Lint
make lint

# Auto-fix lint issues
make lint-fix

# Clean build artifacts
make clean
```

## Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) for module relationships, data flow, and design decisions.

## License

MIT
