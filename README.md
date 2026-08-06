# 🚀 AI Roadmap Lab - 学习总索引

> **项目定位**：4 个月系统化学习 AI Agent 技术的实践项目
> 
> **技术栈**：OpenAI Agents SDK + LangGraph + RAG + Multi-Agent + MCP
>
> **最后更新**：2026-08-03

---

## 📋 项目概览

这是一个为期 4 个月的 AI Agent 技术学习项目，从零基础开始，逐步深入，最终掌握构建复杂 AI Agent 系统的能力。

### 学习路径

```
Month 01          Month 02          Month 03          Month 04          Month 05
Agents SDK   →    LangGraph    →    RAG         →    Multi-Agent  →   MCP
基础入门          图框架            检索增强          多Agent协作       协议与工具生态
```

---

## 📚 月度导航

### Month 01: Agents SDK

**主题**：AI Agent 基础入门与实战

**核心能力**：
- 理解 AI Agent 的核心概念
- 掌握工具系统（Tools）
- 学会测试和优化 Agent
- 设计多 Agent 协作系统

**月级文档**：[Month 01 学习指南](month01-agents-sdk/README.md)

**周文档**：
- [Week 1: 基础入门](month01-agents-sdk/src/week1/README.md) - 第一个 Agent
- [Week 2: 工具系统](month01-agents-sdk/src/week2/README.md) - Tool + 结构化输出
- [Week 3: 测试优化](month01-agents-sdk/src/week3/README.md) - 测试与评估
- [Week 4: 多Agent协作](month01-agents-sdk/src/week4/README.md) - Handoff 机制

**专题文档**：
- [Run Loop 详解](month01-agents-sdk/doc/RunLoop.md)
- [Handoff 机制详解](month01-agents-sdk/doc/Handoff.md)

---

### Month 02: LangGraph

**主题**：图结构化 Agent 框架

**核心能力**：
- 掌握 StateGraph 基础
- 实现持久化和时间旅行
- 设计模块化的子图系统
- 理解 Workflow vs Agent 选型

**月级文档**：[Month 02 学习指南](month02-langgraph/README.md)

**周文档**：
- [Week 1: Graph API 基础](month02-langgraph/src/week1/README.md) - 节点、边、状态
- [Week 2: 持久化](month02-langgraph/doc/Week2-Persistence-Checkpoints.md) - Checkpoint + 人机协作
- [Week 3: 子图模块化](month02-langgraph/doc/Week3-Subgraph-Modular.md) - 模块化设计
- [Week 4: 对比选型](month02-langgraph/doc/Week4-Workflow-vs-Agent.md) - Workflow vs Agent

**综合笔记**：
- [Week 2 综合笔记](month02-langgraph/src/week2/week2_comprehensive_notes.md)
- [Week 3 综合笔记](month02-langgraph/src/week3/week3_comprehensive_notes.md)
- [Week 4 综合笔记](month02-langgraph/src/week4/week4_comprehensive_notes.md)

---

### Month 03: RAG

**主题**：检索增强生成（Retrieval-Augmented Generation）

**核心能力**：
- 理解 Embedding 和向量数据库
- 掌握文档处理和分块策略
- 实现高级检索（Hybrid Search、Reranking）
- 构建完整 RAG 系统

**月级文档**：[Month 03 学习指南](month03-rag/README.md)

**周文档**：
- [Week 1: Embedding + 向量库](month03-rag/src/week1/week1_notes.md) - 语义检索基础
- [Week 2: 文档处理](month03-rag/doc/Document-Processing.md) - 多格式 + 分块策略
- [Week 3: 高级检索](month03-rag/doc/Advanced-Retrieval.md) - Hybrid + Reranking
- [Week 4: 完整系统](month03-rag/doc/Build-RAG-System.md) - 知识库问答系统

**专题文档**：
- [RAG 基础](month03-rag/doc/RAG-Fundamentals.md)
- [Embedding 与向量数据库](month03-rag/doc/Embedding-VectorDB.md)

---

### Month 04: Multi-Agent

**主题**：多 Agent 协作系统

**核心能力**：
- 设计 Agent 角色和分工（Planner-Executor-Reviewer）
- 掌握 A2A 协议与 Agent 间通信
- 理解 Supervisor 层次化协作模式
- 掌握 Agent vs MCP 架构选型决策

**月级文档**：[Month 04 学习指南](month04-multi-agent/README.md)

**周文档**：
- [Week 1: 角色设计与分工](month04-multi-agent/doc/role_design.md) - Planner-Executor-Reviewer
- [Week 2: A2A 协议](month04-multi-agent/doc/a2a_concepts.md) - Agent-to-Agent 通信
- [Week 3: Supervisor 模式](month04-multi-agent/doc/supervisor_pattern.md) - 层次化并行协作
- [Week 4: 架构选型与 MCP](month04-multi-agent/doc/agent_vs_mcp.md) - Agent vs Tool 决策框架

**复盘笔记**：
- [Week 2 复盘](month04-multi-agent/doc/week2_review.md)

---

### Month 05: MCP (Model Context Protocol)

**主题**：MCP 协议与工具生态

**核心能力**：
- 理解 MCP 三层架构与三原语（Tools / Resources / Prompts）
- 独立开发符合 MCP 标准的 Server
- 实现 LangGraph Agent + MCP Client 的多 Server 集成
- 掌握生产级 MCP 系统的设计要点

**月级文档**：[Month 05 学习指南](month05-mcp/README.md)

**周文档**：
- [Week 1: MCP 协议基础](month05-mcp/doc/Week1-MCP-Fundamentals.md) - Server 开发与 Agent 集成
- Week 2: 高级 Server 开发（计划中）
- Week 3: Client 集成与编排（计划中）
- Week 4: 生产实践与部署（计划中）

---

## 🎯 学习目标总览

完成 4 个月的学习后，你将具备以下能力：

### Month 01: Agents SDK
- ✅ 独立开发 AI Agent 应用
- ✅ 设计多工具协作系统
- ✅ 实现多 Agent 协作

### Month 02: LangGraph
- ✅ 使用图结构设计 Agent 工作流
- ✅ 实现持久化和人机协作
- ✅ 掌握 Workflow 与 Agent 选型

### Month 03: RAG
- ✅ 构建知识库问答系统
- ✅ 实现高级检索策略
- ✅ 掌握文档处理和分块

### Month 04: Multi-Agent
- ✅ 设计多 Agent 角色分工（串行 + 并行）
- ✅ 掌握 A2A 协议与 Agent 间通信
- ✅ 掌握 Supervisor 层次化协作模式
- ✅ 掌握 Agent vs MCP 架构选型决策

### Month 05: MCP
- ✅ 独立开发 MCP Server（Tools + Resources）
- ✅ 掌握 MCP Client SDK 与多 Server 集成
- ✅ 实现 LangGraph Agent + MCP 工具生态联动

---

## 🛠️ 技术栈

### 核心框架
- **OpenAI Agents SDK** - Month 01 学习的 Agent 框架
- **LangGraph** - Month 02 学习的图结构化框架

### 核心技术
- **RAG (Retrieval-Augmented Generation)** - Month 03 核心主题
- **Multi-Agent Systems** - Month 04 核心主题
- **MCP (Model Context Protocol)** - Month 05 核心主题

### 工具和库
- **ChromaDB** - 向量数据库
- **BM25** - 关键词检索
- **Ollama** - 本地 Embedding 模型
- **DeepSeek API** - LLM 服务

---

## 📊 学习进度

| Month | 主题 | 状态 | 完成周数 | 总周数 |
|-------|------|------|---------|--------|
| 01 | Agents SDK | 🔄 进行中 | 0/4 | 4 |
| 02 | LangGraph | 🔄 进行中 | 0/4 | 4 |
| 03 | RAG | 🔄 进行中 | 0/4 | 4 |
| 04 | Multi-Agent | 🔄 进行中 | 0/4 | 4 |
| 05 | MCP | 🔄 进行中 | 1/4 | 4 |

---

## 🚀 快速开始

1. **从 Month 01 开始**：[进入 Month 01](month01-agents-sdk/README.md)
2. **查看项目结构**：阅读各 Month 的 README.md
3. **按顺序学习**：建议按 Month 01 → 04 的顺序进行

---

## 📝 学习建议

### 每周学习时间
- 建议每周投入 3-4 小时
- 包含理论学习和代码实践

### 学习方法
1. **先阅读月级文档**：了解整月学习目标
2. **逐周学习**：按顺序完成每周任务
3. **动手实践**：运行代码，理解原理
4. **复盘总结**：完成每周复盘笔记

### 进阶建议
- 完成基础学习后，尝试自己的项目
- 对比不同框架的优缺点
- 关注最新技术动态

---

## 📖 文档结构说明

```
项目根目录
├── month01-agents-sdk/
│   ├── README.md              ← 月级总览文档（你在这里）
│   ├── doc/                   ← 专题文档
│   └── src/week*/             ← 周级文档和代码
│
├── month02-langgraph/
│   ├── README.md              ← 月级总览文档
│   ├── doc/                   ← 周级详细文档
│   └── src/week*/             ← 代码和笔记
│
├── month03-rag/
│   ├── README.md              ← 月级总览文档
│   ├── doc/                   ← 周级详细文档
│   └── src/week*/             ← 代码和笔记
│
└── month04-multi-agent/
│   ├── README.md              ← 月级总览文档
│   ├── doc/                   ← 周级详细文档
│   └── src/week*/             ← 代码
│
└── month05-mcp/
    ├── README.md              ← 月级总览文档
    ├── doc/                   ← 周级详细文档
    └── week01/src/            ← 代码
```

---

## 🤝 贡献

如果你有改进建议或发现问题，欢迎提交 Issue 或 Pull Request。

---

**开始学习之旅**：[进入 Month 01](month01-agents-sdk/README.md) 🚀

**最新进度**：[进入 Month 05 MCP](month05-mcp/README.md) 🔌
# ly-ai-roadmap-lab
个人学习项目
