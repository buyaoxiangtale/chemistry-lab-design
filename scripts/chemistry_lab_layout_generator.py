import argparse
import json
import os
import re
from datetime import datetime
from typing import Dict, Tuple

# Import existing module that holds client and generator
import chemistry_lab_agent_new as cla

client = cla.client


def extract_json_from_text(text: str) -> str:
    """Extract the first JSON object or array from a text blob using bracket matching."""
    # Find first opening brace/bracket
    starts = [(m.start(), m.group()) for m in re.finditer(r"[\{\[]", text)]
    if not starts:
        return None
    for pos, ch in starts:
        stack = []
        end = None
        for i in range(pos, len(text)):
            c = text[i]
            if c == '{' or c == '[':
                stack.append(c)
            elif c == '}' or c == ']':
                if not stack:
                    break
                opening = stack.pop()
                # simple matching
                if (opening == '{' and c != '}') or (opening == '[' and c != ']'):
                    break
                if not stack:
                    end = i
                    break
        if end:
            return text[pos:end+1]
    return None


def normalize_equipment(equipment):
    """Normalize equipment input to a mapping {display_name: metadata}.

    Accepts either a list of equipment objects or a dict. Returns a dict where
    the key is a human-readable name (prefer 'name', fall back to 'id') and the
    value is the original item object.
    """
    if equipment is None:
        return {}
    if isinstance(equipment, dict):
        # Already a dict; but ensure keys are strings and values are usable
        return equipment
    if isinstance(equipment, list):
        out = {}
        for item in equipment:
            if not isinstance(item, dict):
                continue
            key = item.get('name') or item.get('id') or str(item)
            out[key] = item
        return out
    # Unknown type
    return {}


def build_prompt_for_layout(experiment_name: str, large_equipment: dict, small_equipment: dict, constraints: dict, room_size: dict=None) -> str:
    """Constructs a prompt that requests strictly-formatted JSON layout output from the model."""
    schema = {
        "type": "object",
        "properties": {
            "room": {
                "type": "object",
                "properties": {
                    "width_m": {"type": "number"},
                    "depth_m": {"type": "number"},
                    "units": {"type": "string"}
                }
            },
            "placements": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "item_name": {"type": "string"},
                        "category": {"type": "string"},
                        "x_m": {"type": "number"},
                        "y_m": {"type": "number"},
                        "orientation": {"type": "string"},
                        "utilities": {"type": "array", "items": {"type": "string"}},
                        "clearance_m": {"type": "number"},
                        "justification": {"type": "string"}
                    }
                }
            },
            "recommendations": {"type": "string"}
        }
    }

    lines = []
    lines.append(f"You are a laboratory space planner. Return ONLY a single JSON object (no additional text) that conforms to the schema below. If you cannot fully place every item, include best-effort placements and list remaining items under 'recommendations'. Be concise but precise.")
    lines.append("\nJSON schema (informational, do not echo):")
    lines.append(json.dumps(schema, indent=2))
    lines.append('\n')
    lines.append(f"Experiment: {experiment_name}")
    if room_size:
        lines.append(f"Room size (meters): width={room_size.get('width_m')} depth={room_size.get('depth_m')}")
    lines.append('\nLarge fixed equipment (Category 1):')
    lines.append(json.dumps(large_equipment, ensure_ascii=False, indent=2))
    lines.append('\nSmall movable equipment (Category 2):')
    lines.append(json.dumps(small_equipment, ensure_ascii=False, indent=2))
    lines.append('\nUser constraints (structured):')
    lines.append(json.dumps(constraints, ensure_ascii=False, indent=2))
    lines.append('\nInstructions:')
    lines.append('- Use meters for coordinates; origin (0,0) is the lower-left corner (south-west).')
    lines.append('- x increases to the east (right), y increases to the north (up).')
    lines.append('- Provide orientation as one of: north, south, east, west, north-east, etc.')
    lines.append('- For fixed equipment, place them aligned to walls if appropriate (e.g., fume hood against north wall).')
    lines.append('- Provide a numeric clearance_m for required operational clearance around each placement (minimum recommended).')
    lines.append("- If exact coordinates aren’t feasible for some items, supply a zone label (e.g., 'north-east-corner') in the justification field and set coordinates to null.")

    return "\n".join(lines)


def generate_layout(experiment_name: str, large_equipment: dict, small_equipment: dict, constraints: dict, room_size: dict=None, dry_run: bool=False) -> dict:
    """Call the model to generate a layout JSON. If dry_run=True, return a sample structure without calling the API."""
    prompt = build_prompt_for_layout(experiment_name, large_equipment, small_equipment, constraints, room_size)

    if dry_run:
        # Return a minimal sample JSON structure for testing
        sample = {
            "room": {"width_m": room_size.get('width_m') if room_size else 6.0, "depth_m": room_size.get('depth_m') if room_size else 4.0, "units": "m"},
            "placements": [],
            "recommendations": "Dry-run: no model call performed."
        }
        # Add placements for any fixed items as zones
        for name in large_equipment.keys():
            sample['placements'].append({
                "item_name": name,
                "category": "large",
                "x_m": None,
                "y_m": None,
                "orientation": None,
                "utilities": [],
                "clearance_m": 1.0,
                "justification": "Place against suitable wall as per constraints or safety requirements."
            })
        for name in small_equipment.keys():
            sample['placements'].append({
                "item_name": name,
                "category": "small",
                "x_m": None,
                "y_m": None,
                "orientation": None,
                "utilities": [],
                "clearance_m": 0.5,
                "justification": "Movable; place on bench near associated fixed equipment."
            })
        return sample

    system_message = """You are an expert laboratory planner with knowledge of safety codes, ventilation, utilities, and ergonomic placement of laboratory equipment.

     IMPORTANT: The JSON layout you will produce must satisfy a strict non-overlap constraint for all placed items.

     Requirements (enforce these exactly):
     1) Coordinates and units
         - All coordinates must be provided in meters.
         - Use the lower-left corner of the item's footprint as (x_m, y_m) (origin (0,0) is the room south-west corner).
         - If the model cannot place an item without violating non-overlap or room bounds, set its x_m and y_m to null and explain why in the "recommendations" field.

     2) Footprint and clearance calculation
         - Each equipment item includes dimensions in the large_equipment/small_equipment objects as `dimensions_2d.width` and `dimensions_2d.depth` (units: centimeters).
         - Convert these to meters by dividing by 100.0 before computing footprints.
         - The item's footprint rectangle runs from:
              x_min = x_m
              x_max = x_m + width_m
              y_min = y_m
              y_max = y_m + depth_m
         - Each item also has a per-item clearance value to be applied as an extra buffer (clearance_m). When testing overlaps, expand the footprint by clearance_m on all sides:
              x_min_buf = x_min - clearance_m
              x_max_buf = x_max + clearance_m
              y_min_buf = y_min - clearance_m
              y_max_buf = y_max + clearance_m

     3) Non-overlap constraint (hard requirement)
         - For every pair of placed items A and B with numeric coordinates, their buffered footprints must NOT intersect. In other words, for each pair A,B at least one of the following must be true:
              A.x_max_buf <= B.x_min_buf
              A.x_min_buf >= B.x_max_buf
              A.y_max_buf <= B.y_min_buf
              A.y_min_buf >= B.y_max_buf
         - If any pair would overlap, do NOT place one of them at numeric coordinates; instead set that item's x_m and y_m to null and include it under "recommendations" with a brief explanation.

     4) Room bounds
         - All placed items with numeric coordinates must lie fully inside the room boundaries when considering the buffered footprint. If an item would exceed room bounds, do not place it; set x_m/y_m to null and add to recommendations.

     5) Output format
         - Return ONLY a single JSON object conforming to the schema provided in the user prompt. Do not include any extra commentary or text.
         - For items you do place, supply numeric x_m and y_m (lower-left corner), orientation, utilities and a sensible clearance_m (number). For items you cannot place, set x_m/y_m to null and describe why in recommendations.

     6) Placement strategy hints (follow but don't repeat in output):
         - Place fixed equipment aligned to walls where appropriate.
         - Keep safety-related equipment (eyewash, fire extinguisher) accessible and near exits.
         - Prefer grouping equipment that need the same utilities (water, electricity) but do not violate non-overlap.

     Enforce these constraints deterministically and strictly when generating the JSON layout."""

    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=1800,
            stream=False
        )

        text = response.choices[0].message.content
        json_text = extract_json_from_text(text)
        if not json_text:
            raise ValueError("No JSON object found in model response.")
        return json.loads(json_text)

    except Exception as e:
        raise RuntimeError(f"Failed to generate layout: {e}")


def save_layout(output_path: str, layout: dict) -> str:
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(layout, f, ensure_ascii=False, indent=2)
    return output_path


def calculate_bounding_box(equipment: Dict, placement: Dict) -> Tuple[float, float, float, float]:
    """
    计算设备的实际占用区（本体尺寸+四周required_clearance）
    返回: (cx, cy, width, height)
    """
    # 本体尺寸（厘米）
    width_cm = equipment['dimensions_2d']['width']
    depth_cm = equipment['dimensions_2d']['depth']
    # 四周间隙（厘米），默认为0
    clearance = equipment.get('properties', {}).get('required_clearance', {})
    left = clearance.get('left', clearance.get('sides', 0)) or 0
    right = clearance.get('right', clearance.get('sides', 0)) or 0
    front = clearance.get('front', 0) or 0
    rear = clearance.get('rear', 0) or 0

    # 转换为米
    width_m = width_cm / 100.0
    depth_m = depth_cm / 100.0
    left_m = left / 100.0
    right_m = right / 100.0
    front_m = front / 100.0
    rear_m = rear / 100.0

    # 设备左下角坐标
    x_m = float(placement['x_m'])
    y_m = float(placement['y_m'])

    # 方向调整
    orientation = placement.get('orientation', 'north')
    if orientation in ['east', 'west']:
        width_m, depth_m = depth_m, width_m
        left_m, rear_m, right_m, front_m = rear_m, right_m, front_m, left_m

    # 实际占用区
    x_min = x_m - left_m
    x_max = x_m + width_m + right_m
    y_min = y_m - rear_m
    y_max = y_m + depth_m + front_m

    cx = (x_min + x_max) / 2
    cy = (y_min + y_max) / 2
    actual_width = x_max - x_min
    actual_depth = y_max - y_min

    # 记录本体尺寸
    width_m = equipment['dimensions_2d']['width'] / 100.0
    depth_m = equipment['dimensions_2d']['depth'] / 100.0
    # 创建结果字典
    box_info = {
        'name': equipment['name'],
        'category': equipment['category'],
        'bounding_box': {
            'center_x': cx,
            'center_y': cy,
            'width': actual_width,
            'height': actual_depth,
            'body_width': width_m,
            'body_depth': depth_m
        },
    }

    return box_info


def main():
    parser = argparse.ArgumentParser(description='Generate a lab layout JSON from equipment JSON, constraints and experiment name.')
    parser.add_argument('--large-equipment-file', '-L', type=str, required=True, help='Path to large equipment JSON file')
    parser.add_argument('--small-equipment-file', '-S', type=str, help='Path to small equipment JSON file (optional)')
    parser.add_argument('--experiment', '-e', type=str, help='Experiment name (e.g., "crude salt purification")')
    parser.add_argument('--constraints', '-c', type=str, help='Constraints string (semicolon-separated)')
    parser.add_argument('--constraints-file', '-C', type=str, help='Path to JSON file containing structured constraints (optional)')
    parser.add_argument('--width', type=float, help='Room width in meters')
    parser.add_argument('--depth', type=float, help='Room depth in meters')
    parser.add_argument('--output', '-o', type=str, help='Output JSON file path', default=None)
    parser.add_argument('--dry-run', action='store_true', help='Do not call the model; produce a placeholder layout for testing')

    args = parser.parse_args()

    # Load large equipment
    if not os.path.exists(args.large_equipment_file):
        print(f"Large equipment file not found: {args.large_equipment_file}")
        return
    with open(args.large_equipment_file, 'r', encoding='utf-8') as f:
        large_equipment_raw = json.load(f)
    large_equipment = normalize_equipment(large_equipment_raw)

    # Load small equipment if provided, else try to generate
    small_equipment = {}
    if args.small_equipment_file:
        if os.path.exists(args.small_equipment_file):
            with open(args.small_equipment_file, 'r', encoding='utf-8') as f:
                small_equipment_raw = json.load(f)
            small_equipment = normalize_equipment(small_equipment_raw)
        else:
            print(f"Small equipment file not found: {args.small_equipment_file}; attempting to generate via model.")

    experiment = args.experiment or input('Experiment name: ').strip()

    # Generate experiment-specific equipment list from AI model
    print(f"\nGenerating equipment list for '{experiment}' experiment...")
    try:
        exp_large, exp_small = cla.generate_chemistry_lab(experiment)
        print(f"  - AI generated {len(exp_large)} large equipment items")
        print(f"  - AI generated {len(exp_small)} small equipment items")
    except Exception as e:
        print(f"Warning: Could not generate equipment list via model: {e}")
        exp_large, exp_small = {}, {}

    # Match generated equipment names with available equipment in JSON files
    def match_equipment(exp_equipment_dict, available_equipment, category_name):
        """
        Match experiment-required equipment with available equipment.
        Returns filtered equipment that is in both exp_equipment_dict and available_equipment
        """
        matched = {}
        unmatched = []
        
        for exp_name in exp_equipment_dict.keys():
            # Try exact match first
            if exp_name in available_equipment:
                matched[exp_name] = available_equipment[exp_name]
                continue
            
            # Try case-insensitive match
            found = False
            exp_name_lower = exp_name.lower()
            for avail_name, avail_data in available_equipment.items():
                if exp_name_lower == avail_name.lower():
                    matched[exp_name] = avail_data
                    found = True
                    break
            
            # Try substring match (if exp_name is substring of available name)
            if not found:
                for avail_name, avail_data in available_equipment.items():
                    if exp_name_lower in avail_name.lower():
                        matched[exp_name] = avail_data
                        found = True
                        break
            
            if not found:
                unmatched.append(exp_name)
        
        if unmatched:
            print(f"  Note: Could not find {category_name} items in library: {', '.join(unmatched)}")
        
        return matched

    # Filter equipment based on experiment requirements
    if exp_large:
        large_equipment = match_equipment(exp_large, large_equipment, "large equipment")
        print(f"  Matched {len(large_equipment)} large equipment items from library")

    if exp_small:
        small_equipment = match_equipment(exp_small, small_equipment, "small equipment")
        print(f"  Matched {len(small_equipment)} small equipment items from library")

    # Load constraints: structured file preferred
    constraints = {'raw': ''}
    if args.constraints_file and os.path.exists(args.constraints_file):
        with open(args.constraints_file, 'r', encoding='utf-8') as f:
            try:
                constraints = json.load(f)
            except Exception:
                constraints = {'raw': f.read()}
    else:
        raw_constraints = args.constraints or input('Constraints (semicolon separated): ').strip()
        # Parse into structured form
        from chemistry_lab_room_designer import parse_constraints as pc  # local function
        constraints = pc(raw_constraints)

    # If small_equipment is empty, try to generate via module generator
    if not small_equipment:
        try:
            gen_large, gen_small = cla.generate_chemistry_lab(experiment)
            # prefer provided large_equipment file, but fill small_equipment from generator if missing
            if not small_equipment:
                small_equipment = gen_small
        except Exception as e:
            print(f"Warning: Could not generate small equipment via model: {e}")

    room_size = None
    if args.width or args.depth:
        room_size = {'width_m': args.width or 6.0, 'depth_m': args.depth or 4.0}

    print('\nGenerating layout... (dry_run=' + str(args.dry_run) + ')\n')
    try:
        layout = generate_layout(experiment, large_equipment, small_equipment, constraints, room_size, dry_run=args.dry_run)
    except Exception as e:
        print(str(e))
        return

    # Determine output path
    out_path = args.output
    if not out_path:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        safe_name = (experiment or 'experiment').replace(' ', '_').lower()
        out_path = f"{safe_name}_layout_{timestamp}.json"

    save_layout(out_path, layout)
    print(f"Layout saved to: {out_path}")


if __name__ == '__main__':
    main()
