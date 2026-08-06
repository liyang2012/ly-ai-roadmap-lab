# 🔌 Month 05: MCP (Model Context Protocol) 学习指南

> **学习目标**：掌握 MCP 协议核心概念，能够独立开发 MCP Server，实现 Agent 与外部工具生态的标准化集成。
>
> **学习时间**：4 周，约 12-15 小时
>
> **前置知识**：Month 04 Multi-Agent（理解 Agent 架构、Tool 调用机制）
>
> **最后更新**：2026-08-03

---

## 📖 本月概览

MCP（Model Context Protocol）是 Anthropic 推出的开放协议，为 AI Agent 与外部工具/数据源之间提供标准化的通信接口。本月将从协议原理出发，动手构建 MCP Server，最终实现 LangGraph Agent + MCP Client 的完整集成。

### 学习路线图

```
Week 1: MCP 协议基础        Week 2: 高级 Server 开发       Week 3: Client 集成          Week 4: 生产实践
    ↓                          ↓                          ↓                         ↓
[协议三原语]              [多 Server 管理]           [LangGraph 集成]         [SSE/HTTP Transport]
[stdio Transport]         [Resources/Prompts]        [工具自动发现]           [安全与鉴权]
[Server 开发实战]         [错误处理与重试]           [多 Server 编排]          [生产部署]
```

---

## 📚 周文档导航

### Week 1：MCP 协议基础与 Server 开发

**学习目标**：理解 MCP 三层架构和三原语，掌握 stdio Transport，能独立开发 MCP Server。

**核心内容**：
- MCP 三层架构：Host / Client / Server
- 三个原语：Tools / Resources / Prompts
- stdio Transport 通信机制
- Filesystem MCP Server 实战（4 个工具）
- Weather MCP Server 实战（2 个工具 + 1 个资源）
- LangGraph Agent + MCP Client 集成

**周文档**：[Week 1 详细文档](doc/Week1-MCP-Fundamentals.md)

**产出代码**：
- `week01/src/filesystem_mcp_server.py` - 文件系统 MCP Server
- `week01/src/weather_mcp_server.py` - 天气查询 MCP Server
- `week01/src/mcp_agent_integration.py` - LangGraph Agent + MCP Client 集成
- `week01/src/test_filesystem_mcp.py` - Filesystem Server 独立测试
- `week01/src/test_weather_mcp.py` - Weather Server 独立测试
- `week01/tests/test_mcp_integration.py` - 完整集成测试套件

**学习笔记**：
- `week01/src/week1_comprehensive_notes.md` - 📝 综合学习笔记（核心知识点 + 踩坑 + 自检）
- `week01/src/mcp_concepts.md` - 🗂️ MCP 协议核心概念速查卡

---

### Week 2：高级 Server 开发模式（计划中）

**学习目标**：掌握多 Server 管理、Resources/Prompts 高级原语、错误处理机制。

**核心内容**：
- 多 MCP Server 生命周期管理
- Resources 原语深度实践（动态资源、资源模板）
- Prompts 原语实践（预定义提示模板）
- 错误处理与重试策略
- Server 能力声明（Capabilities）

---

### Week 3：Client 集成与编排（计划中）

**学习目标**：深入 MCP Client SDK，实现多 Server 工具编排。

**核心内容**：
- MCP Client SDK 深度使用
- 工具自动发现与动态注册
- 多 Server 工具编排
- 与 LangGraph Agent 深度集成
- Tool 结果后处理与格式化

---

### Week 4：生产实践与部署（计划中）

**学习目标**：掌握 HTTP/SSE Transport，理解生产级 MCP 系统的设计要点。

**核心内容**：
- Streamable HTTP Transport（替代 SSE）
- 安全与鉴权（OAuth 2.1）
- 生产环境部署方案
- MCP Server 性能优化
- 真实项目实战

---

## 🎯 本月学习成果

完成本月学习后，你将具备以下能力：

✅ **协议理解**
- 深入理解 MCP 三层架构和三原语
- 掌握 MCP 与 Function Call 的本质区别
- 理解 Transport 抽象层的意义

✅ **Server 开发**
- 独立开发符合 MCP 标准的 Server
- 掌握 Tools / Resources / Prompts 三原语实践
- 能够设计安全约束机制（路径沙盒、输入校验）

✅ **Client 集成**
- 掌握 MCP Client SDK 的使用
- 实现 Agent 与多个 MCP Server 的联动
- 能够设计工具发现与编排方案

✅ **生产实践**
- 理解不同 Transport 方式的适用场景
- 具备生产级 MCP 系统的设计能力
- 掌握安全鉴权的基本方案

---

## 📖 核心概念速查

### MCP vs Function Call

| 维度 | Function Call | MCP |
|------|--------------|-----|
| 耦合度 | 紧耦合（定义在 Agent 内） | 松耦合（独立 Server） |
| 复用性 | 每个 Agent 重写一遍 | 一次编写，到处使用 |
| 标准化 | 各家实现不同 | 统一协议，生态共享 |
| 发现机制 | 手工配置 | 自动发现（list_tools） |
| 安全 | 代码内控制 | 进程隔离 + OAuth |

### 三个原语

| 原语 | 用途 | 示例 |
|------|------|------|
| **Tools** | 让 LLM 调用的函数 | read_file, get_weather |
| **Resources** | 暴露只读数据 | 文件内容、数据库 schema |
| **Prompts** | 预定义提示模板 | "帮我总结这段代码" |

---

## 🛠️ 技术栈

- **MCP Python SDK** - `mcp` 包（Server + Client）
- **LangGraph** - Agent 编排框架
- **OpenAI / 百炼 API** - LLM 服务
- **stdio Transport** - 本地进程间通信
- **Python asyncio** - 异步 I/O

---

## 📊 学习进度追踪

| Week | 状态 | 用时 | 完成日期 |
|------|------|------|---------|
| Week 1 | ✅ 完成 | - | 2026-08-03 |
| Week 2 | ⬜ | - | - |
| Week 3 | ⬜ | - | - |
| Week 4 | ⬜ | - | - |

---

**开始学习**：[进入 Week 1](doc/Week1-MCP-Fundamentals.md) 🚀
