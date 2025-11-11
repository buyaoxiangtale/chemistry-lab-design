import argparse
import json
import os
import re
from datetime import datetime

# Import the generator from the existing module
import chemistry_lab_agent_new as cla

# Reuse the same Deepseek client initialized in chemistry_lab_agent_new (cla.client)
client = cla.client


def build_design_prompt(experiment_name: str, large_equipment: dict, small_equipment: dict, constraints: str) -> str:
    """Construct a user prompt that includes equipment lists and user layout constraints.
    The model should return a step-by-step room layout plan and a mapping of equipment to locations.
    """
    prompt_lines = []
    prompt_lines.append(f"You are a laboratory space planner. You will produce a recommended room layout and placement plan for the following chemistry experiment: {experiment_name}.")
    prompt_lines.append("Respond with: (1) high-level placement strategy; (2) explicit placement list that maps each equipment item to a location/zone in the room (e.g., 'Fume hood: north-east corner'); (3) safety & utility hookups needed (electrical, gas, drain, ventilation); (4) key spacing and clearance rules; (5) an ASCII floor plan sketch (approximate) or JSON layout if possible.")
    prompt_lines.append("")
    prompt_lines.append("Large fixed equipment and installations (Category 1):")
    prompt_lines.append(json.dumps(large_equipment, ensure_ascii=False, indent=2))
    prompt_lines.append("")
    prompt_lines.append("Small movable containers and instruments (Category 2):")
    prompt_lines.append(json.dumps(small_equipment, ensure_ascii=False, indent=2))
    prompt_lines.append("")
    prompt_lines.append("User constraints and requirements (raw):")
    prompt_lines.append(constraints if constraints.strip() else "(none)")
    # Attempt to parse constraints into a simple structured form
    try:
        parsed = parse_constraints(constraints)
        prompt_lines.append("")
        prompt_lines.append("User constraints (structured):")
        prompt_lines.append(json.dumps(parsed, ensure_ascii=False, indent=2))
    except Exception:
        # If parsing fails, continue without structured constraints
        pass
    prompt_lines.append("")
    prompt_lines.append("Please be explicit and practical. Use human-readable location descriptors (e.g., 'north wall, 1m from west corner, next to sink') and include a brief justification for each placement. Keep safety first: specify required ventilation, distance from exits, and emergency access.")

    return "\n".join(prompt_lines)


def design_room(experiment_name: str, constraints: str, temperature: float = 0.2, max_tokens: int = 1500) -> str:
    """Generate a room design by calling the Deepseek chat model with equipment lists and constraints."""
    # Get equipment dictionaries from the generator
    large_equipment, small_equipment = cla.generate_chemistry_lab(experiment_name)

    if not large_equipment and not small_equipment:
        return "Failed to retrieve equipment lists from generator."

    # Build a prompt for the layout designer
    user_prompt = build_design_prompt(experiment_name, large_equipment, small_equipment, constraints)

    system_message = """You are an expert laboratory planner with knowledge of safety codes and efficient lab layouts. 
    
    Critical Requirements:
    1. NEVER allow any overlap between large equipment items - ensure each piece has its required clearance space
    2. Consider the dimensions_2d (width and depth) of each large equipment when placing them
    3. Check that the required_clearance values for each item do not overlap with other equipment's space
    4. For any two large equipment items A and B, their positions must satisfy:
       - Distance between A and B >= max(A's clearance + B's clearance)
       - No intersection between their footprints (width × depth)
    
    Provide clear, actionable placement instructions and a JSON layout that explicitly specifies coordinates for each large equipment to prevent any overlap."""

    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_prompt}
            ],
            temperature=temperature,
            max_tokens=max_tokens,
            stream=False
        )

        return response.choices[0].message.content

    except Exception as e:
        return f"Error calling Deepseek API: {e}"


def save_design(experiment_name: str, design_text: str) -> str:
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    safe_name = experiment_name.replace(' ', '_').lower() or 'experiment'
    filename = f"{safe_name}_room_design_{timestamp}.txt"
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(design_text)
    return filename


def parse_constraints(constraints_str: str) -> dict:
    """Parse a simple, human-entered constraints string into a structured dict.

    This is a lightweight parser that looks for phrases like:
      - 'Fume hood in upper-right corner'
      - 'sink on north wall'
      - 'door on south wall'

    Returns a dict with 'raw', 'placements' (list of {item, position}) and any 'notes'.
    """
    result = {'raw': constraints_str, 'placements': [], 'notes': []}
    if not constraints_str or not constraints_str.strip():
        return result

    # Split by semicolon or newlines
    parts = [p.strip() for p in re.split(r"[;\n\r]+", constraints_str) if p.strip()]
    # Pattern to capture 'item in/on/at position' (very permissive)
    pattern = re.compile(r"(?P<item>[\w\s\-]+?)\s+(?:in|on|at|located\s+at)\s+(?P<pos>[\w\-\s]+)", re.IGNORECASE)

    for p in parts:
        m = pattern.search(p)
        if m:
            item = m.group('item').strip().rstrip('.,')
            pos = m.group('pos').strip().rstrip('.,')
            result['placements'].append({'item': item, 'position': pos})
        else:
            # Try simple 'X: Y' pairs
            if ':' in p:
                k, v = [s.strip() for s in p.split(':', 1)]
                result['placements'].append({'item': k, 'position': v})
            else:
                result['notes'].append(p)

    return result


def main():
    parser = argparse.ArgumentParser(description='Chemistry lab room designer using Deepseek model.')
    parser.add_argument('--experiment', '-e', type=str, help='Experiment name (e.g., "crude salt purification").')
    parser.add_argument('--constraints', '-c', type=str, help='Placement constraints (e.g., "Fume hood at top-right corner; sink on north wall").')
    args = parser.parse_args()

    if args.experiment:
        experiment = args.experiment
    else:
        experiment = input("Experiment name: ").strip()

    if args.constraints:
        constraints = args.constraints
    else:
        print("Enter room constraints or placement notes (single line). Example: 'Fume hood in upper-right corner; sink on north wall; door on south wall'.")
        constraints = input("Constraints: ").strip()

    print(f"\nRequesting room design for '{experiment}' with constraints: {constraints}\n")

    design = design_room(experiment, constraints)

    print("=== Room Design Result ===\n")
    print(design)

    out_file = save_design(experiment, design)
    print(f"\nDesign saved to: {out_file}")


if __name__ == '__main__':
    main()
