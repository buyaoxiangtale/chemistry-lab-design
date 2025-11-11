import json
import os
import argparse
from datetime import datetime
from openai import OpenAI

# Initialize the Deepseek client with API key
api_key = "sk-5e835831541d43e88c2cd882201395ba"
client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")


def load_equipment_library(large_equipment_file: str, small_equipment_file: str) -> tuple:
    """
    加载设备库（大型和小型设备）
    返回: (large_equipment_list, small_equipment_list)
    """
    with open(large_equipment_file, 'r', encoding='utf-8') as f:
        large_equipment = json.load(f)
    
    with open(small_equipment_file, 'r', encoding='utf-8') as f:
        small_equipment = json.load(f)
    
    return large_equipment, small_equipment


def filter_equipment_by_experiment(experiment_name: str, large_equipment: list, small_equipment: list) -> tuple:
    """
    调用 AI 模型，从完整设备库中筛选出该实验需要的设备
    返回: (filtered_large_equipment, filtered_small_equipment)
    """
    
    # 构建大模型的 system prompt
    system_message = """You are an expert chemistry laboratory equipment specialist. Your task is to analyze a given chemistry experiment and select the required equipment from provided equipment libraries.

You will receive:
1. A complete library of large fixed equipment
2. A complete library of small movable equipment
3. An experiment name

Your job is to:
1. Understand what the experiment requires
2. Carefully examine the provided equipment libraries
3. Select ONLY the equipment that is actually needed for this experiment
4. Return two separate JSON arrays: one for required large equipment, one for required small equipment

IMPORTANT:
- Return ONLY valid JSON, no additional text
- For large equipment: return a JSON array of objects selected from the provided large_equipment library
- For small equipment: return a JSON array of objects selected from the provided small_equipment library
- DO NOT create new equipment objects - only select from what is provided
- DO NOT add extra fields or modify the original equipment data
- If equipment is not needed for the experiment, do NOT include it
- Return the complete equipment objects as they appear in the libraries

Format your response as a JSON object with two keys:
{
  "large_equipment": [...selected large equipment objects...],
  "small_equipment": [...selected small equipment objects...]
}"""

    # 构建用户消息，包含完整的设备库和实验名
    user_message = f"""Experiment: {experiment_name}

Complete Large Equipment Library:
{json.dumps(large_equipment, ensure_ascii=False, indent=2)}

Complete Small Equipment Library:
{json.dumps(small_equipment, ensure_ascii=False, indent=2)}

Please analyze the "{experiment_name}" experiment and select the required equipment from the above libraries.
Return the result as valid JSON with "large_equipment" and "small_equipment" arrays."""

    try:
        # 调用 API
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message}
            ],
            temperature=0.3,  # 降低温度以获得更稳定的选择
            max_tokens=4000,
            stream=False
        )
        
        response_text = response.choices[0].message.content
        
        # 提取 JSON
        result = extract_json_from_response(response_text)
        
        if not result or 'large_equipment' not in result or 'small_equipment' not in result:
            raise ValueError("Invalid response format from model")
        
        return result['large_equipment'], result['small_equipment']
        
    except Exception as e:
        print(f"Error calling API: {str(e)}")
        raise


def extract_json_from_response(text: str) -> dict:
    """
    从模型响应中提取 JSON 对象
    """
    import re
    
    # 尝试找到 JSON 对象
    # 先找 code fence
    match = re.search(r'```(?:json)?\s*({.*?})\s*```', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    
    # 如果没有 code fence，尝试直接解析
    try:
        # 找到第一个 { 和最后一个 }
        start = text.find('{')
        end = text.rfind('}')
        if start != -1 and end != -1 and start < end:
            json_str = text[start:end+1]
            return json.loads(json_str)
    except json.JSONDecodeError:
        pass
    
    return None


def save_filtered_equipment(filtered_large: list, filtered_small: list, experiment_name: str, output_dir: str = '.') -> tuple:
    """
    保存筛选后的设备到文件
    返回: (large_equipment_file, small_equipment_file)
    """
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    safe_name = experiment_name.replace(' ', '_').lower()
    
    large_file = os.path.join(output_dir, f"{safe_name}_large_equipment_{timestamp}.json")
    small_file = os.path.join(output_dir, f"{safe_name}_small_equipment_{timestamp}.json")
    
    # 保存大型设备
    with open(large_file, 'w', encoding='utf-8') as f:
        json.dump(filtered_large, f, ensure_ascii=False, indent=2)
    
    # 保存小型设备
    with open(small_file, 'w', encoding='utf-8') as f:
        json.dump(filtered_small, f, ensure_ascii=False, indent=2)
    
    return large_file, small_file


def main():
    parser = argparse.ArgumentParser(
        description='Filter equipment library by experiment requirements using AI'
    )
    parser.add_argument(
        '--large-equipment-file', '-L',
        type=str,
        required=True,
        help='Path to complete large equipment library JSON'
    )
    parser.add_argument(
        '--small-equipment-file', '-S',
        type=str,
        required=True,
        help='Path to complete small equipment library JSON'
    )
    parser.add_argument(
        '--experiment', '-e',
        type=str,
        required=True,
        help='Experiment name (e.g., "crude salt purification")'
    )
    parser.add_argument(
        '--output-dir', '-o',
        type=str,
        default='.',
        help='Output directory for filtered equipment files (default: current directory)'
    )
    
    args = parser.parse_args()
    
    # 检查输入文件
    if not os.path.exists(args.large_equipment_file):
        print(f"Large equipment file not found: {args.large_equipment_file}")
        return
    
    if not os.path.exists(args.small_equipment_file):
        print(f"Small equipment file not found: {args.small_equipment_file}")
        return
    
    # 创建输出目录（如果不存在）
    if not os.path.exists(args.output_dir):
        os.makedirs(args.output_dir)
    
    print(f"\n=== Equipment Filter by Experiment ===")
    print(f"Loading equipment libraries...")
    
    # 加载设备库
    large_equipment, small_equipment = load_equipment_library(
        args.large_equipment_file,
        args.small_equipment_file
    )
    
    print(f"  - Loaded {len(large_equipment)} large equipment items")
    print(f"  - Loaded {len(small_equipment)} small equipment items")
    
    print(f"\nFiltering equipment for experiment: '{args.experiment}'")
    print("  Calling AI model to analyze experiment requirements...")
    
    # 调用 AI 筛选设备
    filtered_large, filtered_small = filter_equipment_by_experiment(
        args.experiment,
        large_equipment,
        small_equipment
    )
    
    print(f"\n✓ Filtering complete:")
    print(f"  - Selected {len(filtered_large)} large equipment items")
    print(f"  - Selected {len(filtered_small)} small equipment items")
    
    if filtered_large:
        print(f"\nSelected large equipment:")
        for item in filtered_large:
            name = item.get('name', item.get('id', 'Unknown'))
            print(f"  • {name}")
    
    if filtered_small:
        print(f"\nSelected small equipment:")
        for item in filtered_small:
            name = item.get('name', item.get('id', 'Unknown'))
            print(f"  • {name}")
    
    # 保存筛选后的设备
    large_file, small_file = save_filtered_equipment(
        filtered_large,
        filtered_small,
        args.experiment,
        args.output_dir
    )
    
    print(f"\n✓ Results saved:")
    print(f"  Large equipment file: {large_file}")
    print(f"  Small equipment file: {small_file}")
    
    return large_file, small_file


if __name__ == '__main__':
    main()
