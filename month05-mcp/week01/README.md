# Week 1：MCP 协议基础与 Server 开发

> **Week 1** of [Month 05: MCP](../README.md)
>
> **用时**：3-4 小时 | **难度**：⭐⭐⭐ | **完成日期**：2026-08-03

---

## 🎯 学习目标

- 理解 MCP 三层架构（Host / Client / Server）与三个原语（Tools / Resources / Prompts）
- 掌握 stdio Transport，能独立开发符合 MCP 标准的 Server
- 实现 LangGraph Agent + MCP Client 的多 Server 集成

---

## 📖 文档导航

| 文档 | 说明 |
|------|------|
| [→ Week 1 完整学习文档](../doc/Week1-MCP-Fundamentals.md) | 理论 + 实战 + 踩坑记录 |
| [→ 综合学习笔记](src/week1_comprehensive_notes.md) | 核心知识点梳理、关键发现、自检清单 |
| [→ 概念速查卡](src/mcp_concepts.md) | 三层架构、三原语、MCP vs Function Call |

---

## 🗂️ 代码文件说明

### 核心代码

| 文件 | 说明 | MCP 能力 | 运行命令 |
|------|------|----------|---------|
| `src/filesystem_mcp_server.py` | Filesystem MCP Server | 4 个 Tools | 由 Client 通过 stdio 启动 |
| `src/weather_mcp_server.py` | Weather MCP Server | 2 个 Tools + 1 个 Resource | 由 Client 通过 stdio 启动 |
| `src/mcp_agent_integration.py` | LangGraph Agent + MCP Client | 多 Server 集成 | 见下方运行说明 |

### 测试代码

| 文件 | 说明 | 测试范围 | 运行命令 |
|------|------|----------|---------|
| `src/test_filesystem_mcp.py` | Filesystem Server 独立测试 | 握手 + 4 个 Tools | `python3 src/test_filesystem_mcp.py` |
| `src/test_weather_mcp.py` | Weather Server 独立测试 | Tools + Resources | `python3 src/test_weather_mcp.py` |
| `tests/test_mcp_integration.py` | 完整集成测试套件 | 8 个场景全部覆盖 | `python3 tests/test_mcp_integration.py` |

### 学习笔记

| 文件 | 说明 |
|------|------|
| `src/week1_comprehensive_notes.md` | 📝 综合学习笔记（核心知识点 + 踩坑 + 自检） |
| `src/mcp_concepts.md` | 🗂️ MCP 协议核心概念速查卡 |

---

## 🚀 快速运行

### 环境准备

```bash
pip install mcp langgraph openai pydantic
```

### 方式 1：单 Server 快速测试（不需要 API Key）

```bash
# 测试 Weather Server
python3 src/test_weather_mcp.py

# 测试 Filesystem Server
python3 src/test_filesystem_mcp.py
```

### 方式 2：多 Server 直连测试（不需要 API Key）

```bash
python3 src/mcp_agent_integration.py --no-llm
```

验证 8 个测试场景：目录列表、文件读写、glob 搜索、路径越界拦截、天气查询、天气预报、资源读取。

### 方式 3：完整 Agent 集成测试（需要 API Key）

```bash
# 使用百炼（国内推荐）
export DASHSCOPE_API_KEY='your-key'
python3 src/mcp_agent_integration.py

# 使用 OpenAI
export OPENAI_API_KEY='your-key'
python3 src/mcp_agent_integration.py
```

---

## 🏗️ 项目架构

```
LangGraph Agent (mcp_agent_integration.py)
    └── MCPToolAdapter（MCP Client 封装）
            │
            ├── stdio → filesystem_mcp_server.py
            │              ├── list_dir
            │              ├── read_file
            │              ├── write_file（沙盒安全）
            │              └── search_files
            │
            └── stdio → weather_mcp_server.py
                           ├── get_current_weather
                           ├── get_forecast
                           └── weather://cities (Resource)
```

---

## ✅ 本周检查点

完成以下所有检查点，说明 Week 1 已掌握：

**概念理解**
- [ ] 能解释 MCP 三层架构（Host / Client / Server）各层职责
- [ ] 能说出 Tools 与 Resources 的核心区别
- [ ] 理解 stdio Transport 的通信原理和局限性
- [ ] 能说出 MCP 相比 Function Call 的 3 个核心优势

**代码实战**
- [ ] 成功运行 `test_weather_mcp.py` 并理解输出
- [ ] 成功运行 `mcp_agent_integration.py --no-llm` 且 8 个测试全部通过
- [ ] 理解路径沙盒安全机制的原理
- [ ] 能独立从零开发一个符合 MCP 标准的 Server

---

## 📊 学习进度

| Day | 任务 | 状态 |
|-----|------|------|
| Day 1-2 | MCP 协议理论（三层架构 + 三原语 + stdio） | ✅ |
| Day 3-4 | Filesystem MCP Server（4 个 Tools + 路径沙盒） | ✅ |
| Day 5 | Weather MCP Server（2 Tools + 1 Resource） | ✅ |
| Day 6 | LangGraph Agent + MCP Client 集成 | ✅ |
| Day 7 | 测试 + 复盘笔记 | ✅ |

---

**继续**：[Week 1 完整文档](../doc/Week1-MCP-Fundamentals.md) | [综合笔记](src/week1_comprehensive_notes.md) | [返回 Month 05](../README.md)
