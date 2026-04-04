import json
import os
from typing import Dict, List, Tuple, Optional

def load_equipment_info(equipment_file: str) -> Dict:
    """加载大型设备信息文件"""
    with open(equipment_file, 'r', encoding='utf-8') as f:
        equipment_list = json.load(f)
        # 转换为以id为键的字典，方便查询
        return {item['id']: item for item in equipment_list}

def load_layout(layout_file: str) -> Dict:
    """加载布局文件"""
    with open(layout_file, 'r', encoding='utf-8') as f:
        return json.load(f)

def find_equipment_by_name(equipment_info: Dict, name: str) -> Optional[Dict]:
    """根据名称查找设备信息"""
    for equip_id, equip in equipment_info.items():
        if equip['name'] == name:
            return equip
    return None

def calculate_bounding_box(equipment: Dict, placement: Dict) -> Tuple[float, float, float, float]:
    """
    计算设备的边界框
    返回: (cx, cy, width, height)
    cx, cy: 中心点坐标（米）
    width, height: 宽度和高度（厘米转换为米）
    """
    # 从equipment获取尺寸信息（厘米）
    width_cm = equipment['dimensions_2d']['width']
    depth_cm = equipment['dimensions_2d']['depth']
    
    # 转换为米
    width_m = width_cm / 100.0
    depth_m = depth_cm / 100.0
    
    # 从placement获取位置信息（已经是米）
    x_m = float(placement['x_m'])
    y_m = float(placement['y_m'])
    
    # 根据方向调整边界框
    orientation = placement.get('orientation', 'north')
    if orientation in ['east', 'west']:
        width_m, depth_m = depth_m, width_m  # 交换宽度和深度
    
    # 计算中心点坐标
    cx = x_m + width_m/2
    cy = y_m + depth_m/2
    
    return (cx, cy, width_m, depth_m)

def generate_bounding_boxes(equipment_file: str, layout_file: str, output_file: str) -> Dict:
    """生成所有设备的边界框信息"""
    # 加载设备信息和布局信息
    equipment_info = load_equipment_info(equipment_file)
    layout = load_layout(layout_file)
    
    # 存储结果的列表
    bounding_boxes = []
    room_info = layout.get('room', {})
    
    # 处理每个设备
    for placement in layout.get('placements', []):
        equipment = find_equipment_by_name(equipment_info, placement['item_name'])
        if equipment:
            # 计算边界框
            cx, cy, w, h = calculate_bounding_box(equipment, placement)
            
            # 创建结果字典
            box_info = {
                'name': equipment['name'],
                'category': equipment['category'],
                'bounding_box': {
                    'center_x': cx,
                    'center_y': cy,
                    'width': w,
                    'height': h
                },
                'orientation': placement['orientation'],
                'clearance': {
                    'value': placement['clearance_m'],
                    'details': equipment['properties'].get('required_clearance', {})
                },
                'utilities': placement['utilities'],
                'movable': equipment['properties'].get('movable', False),
                'justification': placement['justification']
            }
            bounding_boxes.append(box_info)
    
    # 保存结果
    result = {
        'room_dimensions': {
            'width': room_info.get('width_m', 0),
            'depth': room_info.get('depth_m', 0),
            'units': 'meters'
        },
        'bounding_boxes': bounding_boxes,
        'metadata': {
            'source_layout': os.path.basename(layout_file),
            'source_equipment': os.path.basename(equipment_file),
            'total_items': len(bounding_boxes)
        }
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    return result

def main():
    # 设置文件路径
    equipment_file = os.path.join(os.path.dirname(__file__), 'large_equipment.json')
    layout_file = os.path.join(os.path.dirname(__file__), 'crude_salt_purification_layout_11_11_20_20.json')
    output_file = os.path.join(os.path.dirname(__file__), 'equipment_bounding_boxes3.json')
    
    try:
        result = generate_bounding_boxes(equipment_file, layout_file, output_file)
        print(f"Successfully generated bounding boxes for {len(result['bounding_boxes'])} equipment items.")
        print(f"Results saved to {output_file}")
        
        # 打印房间尺寸
        room = result['room_dimensions']
        print(f"\nRoom dimensions: {room['width']}m x {room['depth']}m")
        
        # 打印每个设备的位置概述
        print("\nEquipment placements:")
        for box in result['bounding_boxes']:
            bb = box['bounding_box']
            print(f"- {box['name']}: center at ({bb['center_x']:.2f}m, {bb['center_y']:.2f}m), "
                  f"size {bb['width']:.2f}m x {bb['height']:.2f}m, facing {box['orientation']}")
        
    except Exception as e:
        print(f"Error processing files: {e}")

if __name__ == '__main__':
    main()