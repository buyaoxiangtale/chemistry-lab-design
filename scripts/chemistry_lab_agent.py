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
        
        # Skip empty lines and separator lines
        if not line or line.startswith('---'):
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
                description = ' '.join(current_description)
                if current_category == "large":
                    large_equipment[current_item] = description
                elif current_category == "small":
                    small_equipment[current_item] = description
                    
            # Extract new item name
            current_item = line.split('**')[1]
            current_description = []
            
        # Add description lines
        elif current_item and line:
            current_description.append(line)
    
    # Save the last item
    if current_item and current_description:
        description = ' '.join(current_description)
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
    # System message defining the assistant's role as a chemistry lab expert
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
        
        # Extract and return the generated content
        return response.choices[0].message.content
    except Exception as e:
        return f"Error occurred: {str(e)}"

if __name__ == "__main__":
    print("\n=== Chemistry Laboratory Setup Generator ===\n")
    print("Please enter the name of the chemistry experiment you want to perform (e.g., 'crude salt purification'):")
    experiment_name = input("Experiment name: ").strip()
    
    print(f"\nGenerating equipment list for {experiment_name} experiment...\n")
    lab_setup = generate_chemistry_lab(experiment_name)
    print(lab_setup)