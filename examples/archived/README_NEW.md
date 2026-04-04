# Chemistry Lab Layout Generator

这是一个用于生成化学实验室布局的智能工具集，能够根据实验需求自动生成设备清单、规划布局方案，并进行可视化展示。

## 系统架构

### 工作流程

```
实验名称
  ↓
[步骤 1] 筛选实验设备
  equipment_filter_by_experiment.py
  (从完整设备库中筛选所需设备)
  ↓
  大型设备文件 + 小型设备文件
  ↓
[步骤 2] 生成布局方案
  chemistry_lab_layout_generator.py
  (考虑空间、安全约束，生成坐标布局)
  ↓
  布局 JSON 文件
  ↓
[步骤 3] 计算边界框
  equipment_bounding_box_generator.py
  (计算设备占用空间，验证非重叠)
  ↓
  边界框数据
  ↓
[步骤 4] 可视化显示
  chemistry_lab_layout_visualizer_v2.py
  (生成 2D 布局图)
  ↓
  布局图像
```

## 核心模块说明

### 1. 设备筛选器 (`equipment_filter_by_experiment.py`)

**功能**：从完整设备库中智能筛选出特定实验需要的设备

**输入**：
- `large_equipment.json` - 所有可用的大型设备库
- `small_equipment.json` - 所有可用的小型设备库
- 实验名称（如 "crude salt purification"）

**输出**：
- `{实验名}_large_equipment_{时间戳}.json` - 筛选后的大型设备
- `{实验名}_small_equipment_{时间戳}.json` - 筛选后的小型设备

**使用方式**：

```powershell
python equipment_filter_by_experiment.py `
  -L large_equipment.json `
  -S small_equipment.json `
  -e "crude salt purification"
```

### 2. 布局生成器 (`chemistry_lab_layout_generator.py`)

**功能**：根据设备和约束条件生成实验室布局方案

**输入**：
- 大型设备 JSON 文件
- 小型设备 JSON 文件
- 约束条件文件（可选）
- 实验名称
- 房间尺寸（可选）

**输出**：
- 布局 JSON 文件（包含每个设备的坐标、方向、clearance 等）

**使用方式**：

```powershell
python chemistry_lab_layout_generator.py `
  -L crude_salt_purification_large_equipment_*.json `
  -S crude_salt_purification_small_equipment_*.json `
  -e "crude salt purification" `
  -C constraints.json `
  -o layout_output.json
```

**关键特性**：
- 自动考虑设备尺寸和安全间隙（`required_clearance`）
- 强制执行非重叠约束（no-overlap rule）
- 支持 dry-run 模式（不调用 API）
- 坐标系统：原点 (0,0) 在房间左下角，x 向东，y 向北

### 3. 边界框生成器 (`equipment_bounding_box_generator.py`)

**功能**：计算每个设备的实际占用空间（包括 clearance），用于验证和可视化

**输入**：
- 布局 JSON 文件
- 设备信息 JSON 文件（包含尺寸）

**输出**：
- 边界框数据 JSON 文件（包含每个设备的中心点、宽高、clearance 信息）

**重要说明**：
设备的实际占用空间 = 物理尺寸 + required_clearance（四周缓冲区）

**使用方式**：

```powershell
python equipment_bounding_box_generator.py
```

### 4. 可视化工具 (`chemistry_lab_layout_visualizer_v2.py`)

**功能**：将布局方案可视化为 2D 图，显示设备位置、方向和安全间隙

**输入**：
- 布局 JSON 文件
- 边界框数据（可选）

**输出**：
- 2D 布局图像（matplotlib）

**特性**：
- 显示设备物理边界（实线）
- 显示安全间隙区（虚线）
- 标注设备名称和方向
- 突出显示潜在的空间问题

## 数据文件格式

### 设备 JSON 格式

```json
{
  "id": "equipment_id",
  "name": "设备名称",
  "category": "SmallApparatus",
  "dimensions_2d": {
    "width": 25,
    "depth": 30
  },
  "properties": {
    "movable": true,
    "required_clearance": {
      "front": 20,
      "sides": 10,
      "rear": 10
    },
    "connections": ["electricity", "water"]
  }
}
```

### 布局 JSON 格式

```json
{
  "room": {
    "width_m": 6.0,
    "depth_m": 4.0,
    "units": "m"
  },
  "placements": [
    {
      "item_name": "设备名称",
      "category": "large",
      "x_m": 0.5,
      "y_m": 1.0,
      "orientation": "north",
      "utilities": ["electricity"],
      "clearance_m": 1.2,
      "justification": "靠北墙，便于通风"
    }
  ],
  "recommendations": "一些设备因空间限制无法放置"
}
```

## 完整使用流程示例

### 场景：为"粗盐提纯"实验规划实验室

**第一步：筛选实验需要的设备**

```powershell
python equipment_filter_by_experiment.py `
  -L large_equipment.json `
  -S small_equipment.json `
  -e "crude salt purification"
```

输出：
- `crude_salt_purification_large_equipment_20251111_165327.json`
- `crude_salt_purification_small_equipment_20251111_165327.json`

**第二步：生成布局方案**

```powershell
python chemistry_lab_layout_generator.py `
  -L crude_salt_purification_large_equipment_20251111_165327.json `
  -S crude_salt_purification_small_equipment_20251111_165327.json `
  -e "crude salt purification" `
  -C crude_salt_purification_constraints.json `
  -o crude_salt_purification_layout_final.json
```

输出：`crude_salt_purification_layout_final.json`

**第三步：计算边界框**

```powershell
python equipment_bounding_box_generator.py
```

输出：`equipment_bounding_boxes3.json`

**第四步：可视化布局**

```powershell
python chemistry_lab_layout_visualizer_v2.py crude_salt_purification_layout_final.json
```

输出：布局图像显示

## 环境配置

### 1. 创建虚拟环境

```bash
python -m venv .venv
source .venv/bin/activate      # Linux/Mac
.venv\Scripts\activate         # Windows
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置 API 密钥

设置 DeepSeek API 密钥环境变量：

```bash
# Linux/Mac
export DEEPSEEK_API_KEY="sk-xxxxx"

# Windows PowerShell
$env:DEEPSEEK_API_KEY="sk-xxxxx"
```

## 关键概念

### 坐标系统

- **原点** (0,0)：房间左下角（西南角）
- **X 轴**：向东（右）方向增大
- **Y 轴**：向北（上）方向增大
- **单位**：米（m）

### 设备尺寸和间隙

- **dimensions_2d**：设备本体的物理尺寸（厘米，转换为米后使用）
- **required_clearance**：设备周围必需的操作/安全空间（厘米）
  - `front`：前方间隙
  - `rear`：后方间隙
  - `sides`：左右间隙

**实际占用空间计算**：

```
占用区 = 本体 + 四周间隙
```

### 非重叠约束

布局生成器会确保：
1. 所有设备的缓冲区（本体 + clearance）不重叠
2. 所有设备完全在房间边界内
3. 如果无法满足，会将设备坐标设为 `null` 并在 recommendations 说明

## 文件清单

### 核心脚本

- `equipment_filter_by_experiment.py` - 设备筛选器
- `chemistry_lab_layout_generator.py` - 布局生成器
- `equipment_bounding_box_generator.py` - 边界框生成器
- `chemistry_lab_layout_visualizer_v2.py` - 可视化工具
- `chemistry_lab_agent_new.py` - AI 设备生成器（辅助工具）

### 数据文件

- `large_equipment.json` - 大型设备库（完整）
- `small_equipment.json` - 小型设备库（完整）
- `constraints.json` - 布局约束模板
- `{实验名}_constraints.json` - 特定实验的约束

## 注意事项

1. **设备库维护**：
   - 确保所有设备都有完整的 `dimensions_2d` 和 `properties` 字段
   - `required_clearance` 应根据设备的操作需求设置

2. **约束条件**：
   - 约束文件应包含房间大小、安全要求、工作流约束等
   - 某些约束可能导致无法将所有设备放入房间

3. **API 调用**：
   - 大多数脚本需要调用 DeepSeek API
   - 使用 `--dry-run` 模式可在不调用 API 的情况下测试流程

4. **性能**：
   - 设备数量过多（>50）可能导致 API 响应缓慢
   - 建议优先在小范围内测试

## 故障排除

### bounding_boxes 为空

**原因**：设备信息文件与布局文件中的设备不匹配

**解决**：
1. 确保使用了正确的设备库文件
2. 如果同时有大小设备，合并两个库后再进行边界框计算

### 设备匹配失败

**原因**：AI 生成的设备名称与库中名称不完全相同

**解决**：
1. 运行 `equipment_filter_by_experiment.py` 而不是依赖自动匹配
2. 或手工修改约束条件中的设备名称

## 更新日志

### v2.0 (2025-11-11)

- ✅ 新增 `equipment_filter_by_experiment.py` - 直接从库筛选设备
- ✅ 改进非重叠约束算法
- ✅ 添加 `required_clearance` 自动计算
- ✅ 完善坐标系统和尺寸单位说明
- ✅ 重构工作流程文档
