from http import HTTPStatus
from urllib.parse import urlparse, unquote
from pathlib import PurePosixPath
import requests
from dashscope import ImageSynthesis
import os
import json
from datetime import datetime

def load_layout(layout_file):
    """Load and validate a lab layout JSON file."""
    try:
        with open(layout_file, 'r', encoding='utf-8') as f:
            layout = json.load(f)
            
        # Validate basic structure
        required_keys = ['room', 'placements']
        if not all(key in layout for key in required_keys):
            raise ValueError(f"Layout JSON must contain: {', '.join(required_keys)}")
            
        return layout
    except Exception as e:
        print(f"Error loading layout file: {e}")
        return None

def build_image_prompts(layout):
    """Convert layout JSON into two different image generation prompts: blueprint and realistic."""
    room = layout.get('room', {})
    width = room.get('width_m', 6.0)
    depth = room.get('depth_m', 4.0)
    
    # Common equipment placement text
    equipment_text = []
    for item in layout.get('placements', []):
        name = item.get('item_name', '')
        category = item.get('category', '')
        x = item.get('x_m')
        y = item.get('y_m')
        orientation = item.get('orientation', '')
        
        if x is not None and y is not None:
            equipment_text.append(f"- {name} ({category}) positioned at {x}m from west wall, {y}m from south wall, facing {orientation}.")
        else:
            equipment_text.append(f"- {name} ({category}) in {item.get('justification', 'designated area')}.")
    
    # Blueprint style prompt
    blueprint_parts = [
        "Professional 2D architectural blueprint of a chemistry laboratory layout.",
        "Technical drawing style with clean lines and precise measurements.",
        f"Laboratory dimensions: {width}m wide by {depth}m deep.",
        "Equipment placement:",
    ]
    blueprint_parts.extend(equipment_text)
    blueprint_parts.extend([
        "Style requirements:",
        "- Classic blueprint appearance with white lines on blue background",
        "- Technical drawing conventions and symbols",
        "- Precise measurements and scale indicators",
        "- Clear equipment outlines and labels in technical font",
        "- Include scale bar and north arrow",
        "- Show doors, windows, and utility connections",
        "- Equipment symbols following architectural standards",
        "- Dotted lines for clearance zones",
        "- Grid overlay for reference"
    ])
    
    # Realistic top-down view prompt
    realistic_parts = [
        "Realistic top-down view of a modern chemistry laboratory.",
        "High-quality 3D rendering viewed from ceiling height.",
        f"Laboratory dimensions: {width}m wide by {depth}m deep.",
        "Equipment placement:",
    ]
    realistic_parts.extend(equipment_text)
    realistic_parts.extend([
        "Style requirements:",
        "- Professional 3D rendering with realistic lighting",
        "- Clean white laboratory environment",
        "- Visible equipment details and materials",
        "- Chemical-resistant flooring with subtle pattern",
        "- Stainless steel and glass surfaces with proper reflections",
        "- Clear labels floating above equipment",
        "- Soft shadows for depth perception",
        "- Visible utility connections (water, gas, electric)",
        "- Safety equipment in appropriate colors",
        "- Scale bar and north arrow overlay"
    ])
    
    return {
        "blueprint": " ".join(blueprint_parts),
        "realistic": " ".join(realistic_parts)
    }

def generate_layout_image(layout_json_path, api_key, save_dir='./output'):
    """Generate both blueprint and realistic top-down views from a JSON layout file."""
    # Load and validate the layout
    layout = load_layout(layout_json_path)
    if not layout:
        return None
        
    # Build both prompts
    prompts = build_image_prompts(layout)
    saved_paths = []
    
    # Create output directory if it doesn't exist
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)
    
    # Generate both styles of images
    for style, prompt in prompts.items():
        print(f"\nGenerating {style} view...")
        print("Prompt:", prompt)
        
        try:
            rsp = ImageSynthesis.call(
                api_key=api_key,
                model="wanx2.0-t2i-turbo",
                prompt=prompt,
                n=1,
                size='1024*1024'
            )
        except Exception as e:
            print(f"API call failed for {style} view: {e}")
            continue
            
        print(f'{style} response:', rsp)
        
        if rsp.status_code != HTTPStatus.OK:
            print(f'Image generation failed for {style} view:', rsp)
            continue
            
        try:
            for result in rsp.output.results:
                file_name = PurePosixPath(unquote(urlparse(result.url).path)).parts[-1]
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                base_name = os.path.splitext(os.path.basename(layout_json_path))[0]
                save_path = os.path.join(save_dir, f"{base_name}_{style}_view_{timestamp}.png")
                
                with open(save_path, 'wb+') as f:
                    f.write(requests.get(result.url).content)
                saved_paths.append(save_path)
                print(f"{style.capitalize()} view saved to: {save_path}")
        except Exception as e:
            print(f"Failed to save {style} view: {e}")
    
    return saved_paths if saved_paths else None

def main():
    # Get the layout JSON file path
    while True:
        layout_path = input("请输入实验室布局JSON文件路径: ").strip()
        if os.path.exists(layout_path):
            break
        print(f"文件不存在: {layout_path}")
    
    # Get the API key
    api_key = os.getenv('DASHSCOPE_API_KEY', "sk-bba8d81c77b14d59b41e585570d86e7c")
    
    # Get save directory
    save_dir = input("请输入图片保存的文件夹路径（默认output）：").strip() or './output'
    
    # Generate the image
    result_paths = generate_layout_image(layout_path, api_key, save_dir)
    
    if result_paths:
        print("\n成功生成布局图像！保存在:")
        for path in result_paths:
            print(f"- {path}")
    else:
        print("\n生成布局图像失败。")

if __name__ == '__main__':
    main()