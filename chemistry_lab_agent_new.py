import os
from openai import OpenAI
from typing import Dict, Tuple

# Initialize the Deepseek client with API key
api_key = "sk-5e835831541d43e88c2cd882201395ba"
client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")

def parse_equipment_response(response_text: str) -> Tuple[Dict[str, str], Dict[str, str]]:
    """
    Parse the API response and extract equipment into two categories
    Returns: Tuple of (large_equipment, small_equipment) dictionaries
    """
    large_equipment = {}
    small_equipment = {}
    
    current_category = None
    current_item = None
    current_description = []
    
    # More robust parsing to handle different bullet formats and languages
    lines = [l.rstrip() for l in response_text.split('\n')]
    # flags whether we saw explicit category headers
    saw_category = False
    for raw in lines:
        line = raw.strip()
        # Skip decorative/empty lines
        if not line or set(line).issubset({'-', '=', '#', ' '}):
            continue

        low = line.lower()
        # Detect category headers (various possible phrasings)
        if any(header in low for header in ["category 1", "large fixed equipment", "large equipment and installations", "category one"]):
            current_category = "large"
            saw_category = True
            current_item = None
            current_description = []
            continue
        if any(header in low for header in ["category 2", "small containers", "small equipment and instruments", "category two"]):
            current_category = "small"
            saw_category = True
            current_item = None
            current_description = []
            continue

        # Detect item headings using bold markdown **Name** or bullet patterns
        m_bold = None
        try:
            m_bold = __import__('re').search(r"\*\*\s*(?P<name>[^*]+?)\s*\*\*", line)
        except Exception:
            m_bold = None

        m_bullet_inline = __import__('re').match(r"^[\*\-\u2022\d\. ]+\s*(?P<name>[^:：\-–—]+?)\s*[:：\-–—]\s*(?P<desc>.+)$", line)
        m_bullet_name_only = __import__('re').match(r"^[\*\-\u2022\d\. ]+\s*(?P<name>.+?)$", line)

        if m_bold:
            # Save previous
            if current_item and current_description:
                desc = ' '.join(current_description).strip()
                if current_category == 'large':
                    large_equipment[current_item] = desc
                elif current_category == 'small':
                    small_equipment[current_item] = desc
                else:
                    # no category yet: keep in small by default
                    small_equipment[current_item] = desc

            current_item = m_bold.group('name').strip()
            # check for inline description after bold
            post = line.split(m_bold.group(0), 1)[1].strip() if m_bold.group(0) in line else ''
            if post.startswith('-') or post.startswith(':'):
                post = post.lstrip('-:： ').strip()
            current_description = [post] if post else []
            continue

        if m_bullet_inline:
            # Save previous
            if current_item and current_description:
                desc = ' '.join(current_description).strip()
                if current_category == 'large':
                    large_equipment[current_item] = desc
                elif current_category == 'small':
                    small_equipment[current_item] = desc
                else:
                    small_equipment[current_item] = desc

            current_item = m_bullet_inline.group('name').strip()
            current_description = [m_bullet_inline.group('desc').strip()]
            continue

        # If line looks like a bullet with a name only
        if m_bullet_name_only and (line.startswith('*') or line.startswith('-') or line[0].isdigit()):
            # treat as new item name
            # Save previous
            if current_item and current_description:
                desc = ' '.join(current_description).strip()
                if current_category == 'large':
                    large_equipment[current_item] = desc
                elif current_category == 'small':
                    small_equipment[current_item] = desc
                else:
                    small_equipment[current_item] = desc

            current_item = m_bullet_name_only.group('name').strip()
            current_description = []
            continue

        # Otherwise, this is a continuation/description line for current item
        if current_item:
            cleaned = line.replace('*', '').strip()
            if cleaned:
                current_description.append(cleaned)
            continue

        # As a last resort, try to extract bold names anywhere in the document
        # (will be handled after the main loop)
        continue
    
    # Save the last item
    if current_item and current_description:
        description = ' '.join(current_description).strip()
        if current_category == 'large':
            large_equipment[current_item] = description
        elif current_category == 'small':
            small_equipment[current_item] = description
        else:
            small_equipment[current_item] = description

    # If we found nothing, attempt a fallback robust extraction using bold markers
    if not large_equipment and not small_equipment:
        # find all bold names and surrounding text
        import re
        bolds = re.findall(r"\*\*\s*([^*]+?)\s*\*\*", response_text)
        if bolds:
            # split by bold occurrences
            parts = re.split(r"\*\*\s*([^*]+?)\s*\*\*", response_text)
            # parts: pre, name1, post1, name2, post2...
            it = iter(parts)
            _ = next(it)
            for name, post in zip(it, it):
                nm = name.strip()
                desc = post.strip().split('\n')[:3]
                desc = ' '.join([d.strip() for d in desc if d.strip()])
                # heuristic: if name contains keywords -> large
                lname = nm.lower()
                if any(k in lname for k in ['bench', 'hood', 'fume', 'cabinet', 'bench', '台', '柜', 'hood']):
                    large_equipment[nm] = desc
                else:
                    small_equipment[nm] = desc
    
    return large_equipment, small_equipment

def generate_chemistry_lab(experiment_name: str) -> Tuple[Dict[str, str], Dict[str, str]]:
    """
    Generate and categorize chemistry lab equipment for a specific experiment
    Returns: Tuple of (large_equipment, small_equipment) dictionaries
    """
    # System message defining the assistant's role
    system_message = """You are an expert chemistry laboratory equipment specialist. Your primary role is to provide detailed categorized information about laboratory equipment and setups for specific chemistry experiments. When responding:

    1. Always categorize equipment into two main categories:
       Category 1: Large Fixed Equipment and Installations
       - Lab benches, fume hoods, sinks
       - Storage cabinets, safety showers
       - Fixed electrical, water, or gas connections
       - Any equipment that requires permanent installation
       
       Category 2: Small Containers and Instruments
       - Glassware (beakers, flasks, test tubes)
       - Measuring instruments (thermometers, scales)
       - Heating/cooling equipment (hot plates, ice baths)
       - Safety equipment (goggles, gloves)
       - Tools and accessories (spatulas, tongs)
    
    2. For each piece of equipment listed:
       - Start with "* **Equipment Name**"
       - Describe its specific purpose in the experiment
       - Mention required specifications or sizes
       - Note any safety considerations

    3. Always include basic safety equipment:
       - Personal protective equipment
       - Emergency equipment
       - Waste disposal containers
    
    Format each equipment entry as:
    * **Equipment Name** - Brief description of purpose, specifications, and safety considerations"""


    
    user_message = f"""Provide a complete list of laboratory equipment needed for the {experiment_name} experiment. 
    
    Categorize ALL equipment into:

    1. Category 1 - Large Fixed Equipment and Installations:
       - Laboratory infrastructure (benches, hoods, sinks)
       - Fixed storage units and safety equipment
       - Permanently installed utilities
       - Support structures and mounting points

    2. Category 2 - Small Containers and Instruments:
       - All glassware and containers
       - Measuring and handling tools
       - Portable heating/cooling equipment
       - Safety equipment and PPE
       - Small tools and accessories

    List each piece of equipment with:
    * **Equipment Name** - Purpose, specifications, and safety considerations"""

    try:
        # Call the API
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message}
            ],
            temperature=0.7,
            max_tokens=2000,
            stream=False
        )
        
        # Parse the response and return categorized equipment
        return parse_equipment_response(response.choices[0].message.content)
        
    except Exception as e:
        print(f"Error occurred: {str(e)}")
        return {}, {}

def print_equipment_lists(large_equipment: Dict[str, str], small_equipment: Dict[str, str]):
    """Print the categorized equipment lists in a formatted way"""
    print("\n=== Large Fixed Equipment and Installations ===")
    print(f"Number of items: {len(large_equipment)}")
    for item, description in large_equipment.items():
        print(f"\n• {item}:")
        print(f"  {description}")
    
    print("\n=== Small Containers and Instruments ===")
    print(f"Number of items: {len(small_equipment)}")
    for item, description in small_equipment.items():
        print(f"\n• {item}:")
        print(f"  {description}")

def save_equipment_to_file(experiment_name: str, large_equipment: Dict[str, str], small_equipment: Dict[str, str]):
    """Save the equipment lists to a text file"""
    filename = f"{experiment_name.replace(' ', '_').lower()}_equipment.txt"
    
    with open(filename, 'w') as f:
        f.write(f"Equipment List for {experiment_name}\n")
        f.write("=" * 50 + "\n\n")
        
        f.write("Large Fixed Equipment and Installations:\n")
        f.write("-" * 40 + "\n")
        for item, desc in large_equipment.items():
            f.write(f"\n{item}:\n{desc}\n")
        
        f.write("\nSmall Containers and Instruments:\n")
        f.write("-" * 40 + "\n")
        for item, desc in small_equipment.items():
            f.write(f"\n{item}:\n{desc}\n")
    
    return filename

if __name__ == "__main__":
    print("\n=== Chemistry Laboratory Setup Generator ===\n")
    print("Please enter the name of the chemistry experiment you want to perform (e.g., 'crude salt purification'):")
    experiment_name = input("Experiment name: ").strip()
    
    print(f"\nGenerating equipment list for {experiment_name} experiment...\n")
    
    # Generate and categorize the equipment lists
    large_equipment, small_equipment = generate_chemistry_lab(experiment_name)
    
    # Print the categorized lists
    print_equipment_lists(large_equipment, small_equipment)
    
    # Save to file
    output_file = save_equipment_to_file(experiment_name, large_equipment, small_equipment)
    print(f"\nTotal number of equipment items: {len(large_equipment) + len(small_equipment)}")
    print(f"Equipment list has been saved to: {output_file}")