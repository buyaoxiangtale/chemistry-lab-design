import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Arrow
import numpy as np
from matplotlib.font_manager import FontProperties
import sys
import os

def create_layout_visualization(input_json: str, output_image: str = None):
    """创建实验室布局可视化"""
    import json
    from datetime import datetime
    
    # 加载数据
    with open(input_json, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 创建新的图形
    plt.figure(figsize=(12, 8))
    
    # 设置中文字体
    plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'Arial Unicode MS']
    plt.rcParams['font.family'] = 'sans-serif'
    plt.rcParams['axes.unicode_minus'] = False
    
    # 获取房间尺寸
    room_width = data['room_dimensions']['width']
    room_depth = data['room_dimensions']['depth']
    
    # 创建子图
    ax = plt.gca()
    
    # 绘制房间边界
    ax.add_patch(Rectangle((0, 0), room_width, room_depth, fill=False, color='black', linewidth=2))
    
    # 定义设备类别颜色
    category_colors = {
        'Workstation': '#ADD8E6',      # 浅蓝色
        'Storage': '#90EE90',          # 浅绿色
        'Apparatus': '#FFB6C1',        # 浅红色
        'Utility': '#F0E68C',          # 浅黄色
        'Safety': '#FFA07A',           # 浅橙色
        'Workstation/Safety': '#E6E6FA', # 浅紫色
        'Utility/Safety': '#FFE4B5'    # 浅橙黄色
    }
    
    # 绘制每个设备
    for box in data['bounding_boxes']:
        bb = box['bounding_box']
        category = box['category'].split('/')[0]  # 使用主要类别
        color = category_colors.get(category, '#CCCCCC')
        
        # 计算矩形位置
        x = bb['center_x'] - bb['width']/2
        y = bb['center_y'] - bb['height']/2
        
        # 绘制设备区域
        ax.add_patch(Rectangle((x, y), bb['width'], bb['height'],
                             facecolor=color, alpha=0.3))
        ax.add_patch(Rectangle((x, y), bb['width'], bb['height'],
                             fill=False, edgecolor=color, linewidth=1.5))
        
        # 绘制间隙区域
        if box['clearance']['value'] > 0:
            clearance = box['clearance']['value']
            x_clear = x - clearance
            y_clear = y - clearance
            w_clear = bb['width'] + 2 * clearance
            h_clear = bb['height'] + 2 * clearance
            ax.add_patch(Rectangle((x_clear, y_clear), w_clear, h_clear,
                                 fill=False, edgecolor=color, 
                                 linestyle='--', linewidth=0.8))
        
        # 添加设备标签
        name = box['name']
        if len(name) > 15:  # 长名称分行显示
            name = name.replace(' (', '\n(')
        plt.text(bb['center_x'], bb['center_y'], name,
                horizontalalignment='center',
                verticalalignment='center',
                fontsize=8)
    
    # 设置坐标轴
    plt.xlabel('宽度 (米)')
    plt.ylabel('深度 (米)')
    plt.title('实验室布局俯视图')
    
    # 添加图例
    legend_elements = []
    for category, color in category_colors.items():
        legend_elements.append(plt.Rectangle((0, 0), 1, 1, facecolor=color,
                                          alpha=0.3, label=category))
    plt.legend(handles=legend_elements, loc='center left', 
              bbox_to_anchor=(1, 0.5))
    
    # 设置坐标轴范围和网格
    margin = 0.5
    plt.xlim(-margin, room_width + margin)
    plt.ylim(-margin, room_depth + margin)
    plt.grid(True, linestyle='--', alpha=0.3)
    
    # 保持比例一致
    plt.axis('equal')
    plt.tight_layout()
    
    # 保存图像
    if output_image is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_image = f'lab_layout_visualization_{timestamp}.png'
    
    plt.savefig(output_image, dpi=300, bbox_inches='tight')
    print(f"Layout visualization saved to: {output_image}")
    
    # 显示图像
    plt.show()

def main():
    # 设置文件路径
    input_json = os.path.join(os.path.dirname(__file__), 'equipment_bounding_boxes3.json')
    
    try:
        create_layout_visualization(input_json)
    except Exception as e:
        print(f"Error visualizing layout: {e}")

if __name__ == '__main__':
    main()