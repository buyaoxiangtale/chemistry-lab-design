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
    
    # Split the response into lines and process each line
    for line in response_text.split('\n'):
        line = line.strip()
        
        # Skip empty lines, headers and separator lines
        if not line or line.startswith('---') or line.startswith('###') or line.startswith('####'):
            continue
            
        # Check for category headers
        if "Category 1" in line:
            current_category = "large"
            continue
        elif "Category 2" in line:
            current_category = "small"
            continue
            
        # Check for new item (usually starts with *)
        if line.startswith('*   **') and '**' in line:
            # Save previous item if exists
            if current_item and current_description:
                description = ' '.join(current_description).strip()
                if current_category == "large":
                    large_equipment[current_item] = description
                elif current_category == "small":
                    small_equipment[current_item] = description
                    
            # Extract new item name (remove the ** markers)
            current_item = line.split('**')[1].strip()
            current_description = []
            
        # Add description lines (skip nested asterisks)
        elif current_item and line and not line.startswith('*   **'):
            # Remove asterisks and clean up the line
            cleaned_line = line.replace('*   ', '').replace('*', '').strip()
            if cleaned_line:
                current_description.append(cleaned_line)
    
    # Save the last item
    if current_item and current_description:
        description = ' '.join(current_description).strip()
        if current_category == "large":
            large_equipment[current_item] = description
        elif current_category == "small":
            small_equipment[current_item] = description
    
    return large_equipment, small_equipment

def generate_chemistry_lab(experiment_name: str) -> Tuple[Dict[str, str], Dict[str, str]]:
    """
    Generate and categorize chemistry lab equipment for a specific experiment
    Returns: Tuple of (large_equipment, small_equipment) dictionaries
    """
    # System message defining the assistant's role
    system_message = """You are an expert chemistry laboratory equipment specialist. Your primary role is to provide detailed categorized information about laboratory equipment and setups for specific chemistry experiments. When responding:

    1. Always categorize equipment into two main categories:
       - Category 1: Large Fixed Equipment and Installations (non-movable fixtures, infrastructure)
       - Category 2: Small Containers and Instruments (movable items used on fixed equipment)
    
    2. For each piece of equipment listed:
       - Provide its specific purpose in the experiment
       - Explain how it relates to other equipment
       - Include any relevant safety considerations
    
    3. Maintain a clear, structured format with detailed explanations
    4. Focus on practical laboratory setup requirements
    
    Please ensure all responses are comprehensive, precise, and organized according to these categories."""

    # Construct user message based on the input experiment
    user_message = f"""What containers and equipment are needed for the {experiment_name} experiment? Please categorize them as follows:

    1. Category 1 - Large Fixed Equipment and Installations:
       - Include laboratory infrastructure items
       - List fixtures that need to be installed during lab setup
       - Specify items that hold or support smaller equipment
    
    2. Category 2 - Small Containers and Instruments:
       - List all movable containers and tools
       - Specify their uses in the experiment process
       - Include measuring and handling equipment
    
    For each item, explain its specific role in the {experiment_name} process."""

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