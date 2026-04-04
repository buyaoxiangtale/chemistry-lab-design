import json
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Arrow
import numpy as np
import matplotlib
from matplotlib.font_manager import FontProperties
import sys
import os

# 设置中文字体
def get_font():
    if sys.platform.startswith('win'):
        font_path = 'C:/Windows/Fonts/msyh.ttc'  # 微软雅黑
        if os.path.exists(font_path):
            return FontProperties(fname=font_path)
    elif sys.platform.startswith('linux'):
        font_path = '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'
        if os.path.exists(font_path):
            return FontProperties(fname=font_path)
    # 如果找不到系统字体，使用默认配置
    plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'WenQuanYi Micro Hei', 'Arial Unicode MS']
    return None

CHINESE_FONT = get_font()
plt.rcParams['axes.unicode_minus'] = False  # 正常显示负号
from typing import Dict, List, Tuple
import os
from datetime import datetime

def load_layout(json_file: str) -> Dict:
    """加载布局JSON文件"""
    with open(json_file, 'r', encoding='utf-8') as f:
        return json.load(f)

def get_category_color(category: str) -> str:
    """为不同类别的设备分配不同的颜色"""
    color_map = {
        'Workstation': '#ADD8E6',  # 浅蓝色
        'Storage': '#90EE90',      # 浅绿色
        'Apparatus': '#FFB6C1',    # 浅红色
        'Utility': '#F0E68C',      # 浅黄色
        'Safety': '#FFA07A',       # 浅橙色
        'Workstation/Safety': '#E6E6FA',  # 浅紫色
        'Utility/Safety': '#FFE4B5'       # 浅橙黄色
    }
    # 从类别中提取主要类别（如果有多个用/分隔）
    main_category = category.split('/')[0]
    return color_map.get(main_category, '#CCCCCC')  # 默认为灰色

def draw_orientation_arrow(ax, box: Dict, color: str):
    """绘制设备朝向箭头"""
    cx = box['bounding_box']['center_x']
    cy = box['bounding_box']['center_y']
    w = box['bounding_box']['width']
    h = box['bounding_box']['height']
    orientation = box['orientation']
    
    # 根据方向确定箭头位置和方向
    arrow_length = min(w, h) * 0.3  # 箭头长度为设备尺寸的30%
    dx, dy = 0, 0
    
    if orientation == 'north':
        dy = arrow_length
        base_y = cy - h/4
        base_x = cx
    elif orientation == 'south':
        dy = -arrow_length
        base_y = cy + h/4
        base_x = cx
    elif orientation == 'east':
        dx = arrow_length
        base_x = cx - w/4
        base_y = cy
    elif orientation == 'west':
        dx = -arrow_length
        base_x = cx + w/4
        base_y = cy
        
    # 绘制箭头
    ax.add_patch(Arrow(base_x, base_y, dx, dy, 
                      width=arrow_length*0.5, 
                      color=color, 
                      alpha=0.6))

def visualize_layout(json_file: str, output_file: str = None):
    """可视化实验室布局"""
    # 加载布局数据
    layout = load_layout(json_file)
    
    # 创建图形
    fig, ax = plt.subplots(figsize=(12, 8))
    
    # 设置房间边界
    room_width = layout['room_dimensions']['width']
    room_depth = layout['room_dimensions']['depth']
    
    # 设置坐标轴范围，留出一些边距
    margin = 0.5  # 0.5米的边距
    ax.set_xlim(-margin, room_width + margin)
    ax.set_ylim(-margin, room_depth + margin)
    
    # 绘制房间边界
    ax.add_patch(Rectangle((0, 0), room_width, room_depth, 
                         fill=False, color='black', linewidth=2))
    
    # 绘制每个设备的边界框
    for box in layout['bounding_boxes']:
        # 获取边界框信息
        bb = box['bounding_box']
        x = bb['center_x'] - bb['width']/2
        y = bb['center_y'] - bb['height']/2
        
        # 获取设备类别的颜色
        color = get_category_color(box['category'])
        
        # 绘制边界框
        ax.add_patch(Rectangle((x, y), bb['width'], bb['height'],
                             fill=True, color=color, alpha=0.3))
        ax.add_patch(Rectangle((x, y), bb['width'], bb['height'],
                             fill=False, color=color, linewidth=1.5))
        
        # 绘制方向箭头
        draw_orientation_arrow(ax, box, color)
        
        # 添加设备名称标签
        # 将长名称分成多行
        name = box['name']
        if len(name) > 15:
            name = name.replace(' (', '\n(')
        plt.text(bb['center_x'], bb['center_y'], name,
                horizontalalignment='center',
                verticalalignment='center',
                fontsize=8,
                color='black',
                fontproperties=CHINESE_FONT if CHINESE_FONT else None)
        
        # 如果设备有间隙要求，绘制间隙指示（虚线）
        if box['clearance']['value'] > 0:
            clearance = box['clearance']['value']
            x_clear = x - clearance
            y_clear = y - clearance
            w_clear = bb['width'] + 2 * clearance
            h_clear = bb['height'] + 2 * clearance
            ax.add_patch(Rectangle((x_clear, y_clear), w_clear, h_clear,
                                 fill=False, color=color, 
                                 linestyle='--', linewidth=0.8))
    
    # 设置坐标轴标签
    ax.set_xlabel('宽度 (米)', fontsize=10, fontproperties=CHINESE_FONT if CHINESE_FONT else None)
    ax.set_ylabel('深度 (米)', fontsize=10, fontproperties=CHINESE_FONT if CHINESE_FONT else None)
    
    # 添加标题
    plt.title('实验室布局俯视图', fontsize=12, fontproperties=CHINESE_FONT if CHINESE_FONT else None)
    
    # 添加图例
    legend_elements = [plt.Rectangle((0, 0), 1, 1, facecolor=get_category_color(cat), alpha=0.3, 
                                   label=cat) for cat in ['Workstation', 'Storage', 'Apparatus', 
                                                        'Utility', 'Safety', 'Workstation/Safety', 
                                                        'Utility/Safety']]
    ax.legend(handles=legend_elements, loc='center left', bbox_to_anchor=(1, 0.5), 
             prop=CHINESE_FONT if CHINESE_FONT else None)
    
    # 设置坐标轴网格
    ax.grid(True, linestyle='--', alpha=0.3)
    
    # 保持纵横比例一致
    ax.set_aspect('equal')
    
    # 调整布局以适应图例
    plt.tight_layout()
    
    # 如果没有指定输出文件，则生成带时间戳的文件名
    if output_file is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = f'lab_layout_visualization_{timestamp}.png'
    
    # 保存图像
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"Layout visualization saved to: {output_file}")
    
    # 显示图像
    plt.show()

def main():
    # 设置文件路径
    json_file = os.path.join(os.path.dirname(__file__), 'equipment_bounding_boxes.json')
    
    try:
        visualize_layout(json_file)
    except Exception as e:
        print(f"Error visualizing layout: {e}")

if __name__ == '__main__':
    main()