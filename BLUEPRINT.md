# Chemistry Lab Layout Generator - Blueprint

## 项目概述

化学实验室布局生成器：根据实验需求，通过 AI 自动生成设备清单、规划实验室空间布局、输出 2D 可视化图纸。

### 当前状态

项目为原型阶段（proof-of-concept），存在以下问题：
- API Key 硬编码在源码中
- 无测试覆盖
- 模块耦合严重（共享全局 client）
- 无错误重试和输出验证
- JSON 解析脆弱
- README 与实际代码不一致
- 无项目结构规范

### 目标

将项目从原型升级为**可维护、可测试、可扩展**的工程化项目。

---

## 执行清单

### Phase 1: 项目结构规范化 ✅
- [x] 创建标准 Python 包结构 `src/chemistry_lab/`，将功能模块化拆分
- [x] 添加 `pyproject.toml`，配置项目元数据、依赖管理、入口点
- [x] 移除 `requirements.txt`，改用 `pyproject.toml` 管理依赖
- [x] 创建 `tests/` 目录，添加基础测试框架（pytest）
- [x] 添加 `.gitignore`（完善现有的，覆盖 `__pycache__/`, `.venv/`, `output/`, `*.pyc`, `.env` 等）
- [x] 添加 `CONTRIBUTING.md` 或 `Makefile`，标准化开发工作流（lint、test、run）

### Phase 2: 安全与配置
- [x] 将所有硬编码 API Key 移至环境变量（`CHEM_LAB_API_KEY`、`CHEM_LAB_BASE_URL`）
- [x] 创建 `config.py` 统一管理配置（API 配置、默认房间尺寸、模型参数等）
- [x] 添加 `.env.example` 文件，列出所有需要的环境变量及说明
- [x] 确保 `.env` 被 `.gitignore` 排除

### Phase 3: 模块解耦与重构 ✅
- [x] 创建 `client.py`：封装 LLM 客户端初始化，支持依赖注入和环境变量配置
- [x] 创建 `equipment.py`：从 `chemistry_lab_agent_new.py` 提取设备清单生成逻辑
- [x] 创建 `layout.py`：从 `chemistry_lab_layout_generator.py` 提取布局生成逻辑
- [x] 创建 `parser.py`：从 `chemistry_lab_layout_generator.py` 提取 `extract_json_from_text()` JSON 解析
- [x] 创建 `room.py`：从 `chemistry_lab_room_designer.py` 提取房间设计和约束解析
- [x] 创建 `renderer.py`：从 `chemistry_lab_layout_to_image.py` 提取可视化渲染逻辑
- [x] 创建 `models.py`：定义设备、布局、房间的数据模型（dataclass 或 Pydantic）
- [x] 创建 `cli.py`：统一 CLI 入口，整合所有子命令
- [x] 删除旧的单体脚本文件（重构完成后）

### Phase 4: 健壮性提升
- [x] 为 `parser.py` 添加健壮的 JSON 解析（使用 `json.JSONDecoder.raw_decode()` 替代手写括号匹配）
- [x] 为 API 调用添加重试逻辑（指数退避，最多 3 次）
- [x] 为 LLM 输出添加 schema 验证（检查字段类型、坐标范围、必填项）
- [x] 添加设备坐标碰撞检测（验证布局中设备不重叠、满足间距要求）
- [x] 为 `main()` 函数添加适当的错误处理和日志输出（使用 `logging` 模块替代 `print`）

### Phase 5: 测试覆盖
- [x] 为 `parser.py` 编写单元测试（正常 JSON、嵌套 JSON、含噪声文本的 JSON）
- [x] 为 `equipment.py` 编写单元测试（设备分类、响应解析）
- [x] 为 `room.py` 编写单元测试（约束解析、默认值）
- [x] 为碰撞检测编写单元测试（重叠、边缘、正常间距）
- [x] 为 CLI 入口编写集成测试（`--dry-run` 模式、参数解析）
- [x] 为 API 调用编写 mock 测试（使用 `unittest.mock` 模拟 LLM 响应）

### Phase 6: 文档完善
- [x] 重写 `README.md`：项目简介、安装步骤、使用示例、架构说明、配置说明
- [x] 添加 `ARCHITECTURE.md`：模块关系图、数据流、设计决策
- [x] 为所有公共函数添加 docstring（Google 或 NumPy 风格）
- [x] 更新 `large_equipment.json`：确保数据结构清晰、字段完整、注释充分
- [x] 清理历史输出文件（`crude_salt_purification_layout_*.json`、`crude_salt_purification_room_design_*.txt`）

### Phase 7: 验证
- [x] `python -m pytest tests/ -q` 全部通过
- [x] `python -m chemistry_lab --dry-run` 正常运行
- [ ] 完整流程测试：设备生成 → 布局生成 → 图像输出（需 API Key）
- [x] 代码风格检查：`ruff check src/`（或 `flake8`）
- [x] 确认无硬编码密钥：`grep -r "sk-" src/` 无结果

---

## 完成条件

所有 checklist 项标记为 `[x]`，且 Phase 7 的所有验证命令通过。
