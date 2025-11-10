# Chemistry Lab Layout Generator

这是一个用于生成化学实验室布局的工具集，包含以下功能：
- 基于实验需求生成设备清单
- 根据空间约束生成实验室布局
- 将布局转换为2D图像（蓝图风格和真实感风格）

## 项目文件说明

主要Python文件：
- `chemistry_lab_agent_new.py`: 设备清单生成器
- `chemistry_lab_layout_generator.py`: 布局生成器
- `chemistry_lab_layout_to_image.py`: 布局可视化工具
- `chemistry_lab_room_designer.py`: 房间设计辅助工具

数据文件：
- `large_equipment.json`: 大型固定设备配置

## 环境配置

1. 创建并激活虚拟环境：
```bash
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# 或
.venv\Scripts\activate  # Windows
```

2. 安装依赖：
```bash
pip install -r requirements.txt
```

3. 配置API密钥：
```bash
# Linux/Mac
export DASHSCOPE_API_KEY="你的DashScope API密钥"

# Windows (CMD)
set DASHSCOPE_API_KEY=你的DashScope API密钥

# Windows (PowerShell)
$env:DASHSCOPE_API_KEY="你的DashScope API密钥"
```

## 使用示例

1. 生成实验室布局：
```bash
python chemistry_lab_layout_generator.py \
  --large-equipment-file large_equipment.json \
  --experiment "crude salt purification" \
  --constraints "Fume hood in upper-right corner; sink on north wall; main door on south wall"
```

2. 将布局转换为图像：
```bash
python chemistry_lab_layout_to_image.py
```

## 注意事项

- 确保已正确设置 API 密钥环境变量
- 建议使用 Python 3.8 或更高版本
- 所有路径输入支持相对路径和绝对路径