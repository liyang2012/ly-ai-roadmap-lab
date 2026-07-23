# 🎨 Month 02: LangGraph 学习指南

> **学习目标**：掌握 LangGraph 图结构框架，学会设计灵活、可扩展的 Agent 工作流，理解 Workflow 与 Agent 模式的选型。
> 
> **学习时间**：4 周，约 12-15 小时
> 
> **最后更新**：2026-07-13

---

## 📖 本月概览

本月你将系统学习 LangGraph，这是一个强大的图结构化 Agent 框架。从基础的图 API 开始，逐步掌握持久化、模块化设计，最终能够设计和对比不同的 Agent 架构模式。

### 学习路线图

```
Week 1: 图 API 基础        Week 2: 持久化与人机       Week 3: 子图与模块化       Week 4: Workflow vs Agent
    ↓                         ↓                         ↓                         ↓
[StateGraph]            [Checkpoint]             [Subgraph]              [两种模式对比]
[节点 + 边]             [时间旅行]               [适配器模式]            [数据驱动选型]
[条件路由]              [Human-in-the-Loop]      [Master Graph]          [综合对比实验]
```

---

## 📚 周文档导航

### Week 1：Graph API 基础

**学习目标**：理解 LangGraph 的核心概念，能够创建基础的图结构，掌握节点、边和状态管理。

**核心内容**：
- StateGraph 基础概念
- 节点（Node）和边（Edge）
- 条件路由（Conditional Edges）
- 状态（State）管理
- 简单客服系统实战

**周文档**：[Week 1 详细文档](src/week1/README.md) | [Week 1 综合笔记](src/week1/week1_comprehensive_notes.md)

**产出代码**：
- `src/week1/simple_graph.py` - 简单图示例
- `src/week1/customer_support_graph.py` - 客服图系统

---

### Week 2：持久化与 Human-in-the-Loop

**学习目标**：掌握 LangGraph 的持久化机制，实现 Checkpoint 和时间旅行，集成人工审核流程。

**核心内容**：
- Checkpoint 机制（MemorySaver / SqliteSaver）
- 时间旅行（Time Travel）
- Human-in-the-Loop 设计
- 中断点（Breakpoint）设置
- 状态恢复和重放

**周文档**：[Week 2 详细文档](doc/Week2-Persistence-Checkpoints.md) | [Week 2 综合笔记](src/week2/week2_comprehensive_notes.md)

**产出代码**：
- `src/week2/checkpoint_demo.py` - Checkpoint 演示
- `src/week2/time_travel_demo.py` - 时间旅行演示
- `src/week2/human_in_the_loop.py` - 人机协作演示

---

### Week 3：Subgraph 与模块化设计

**学习目标**：掌握子图设计，理解模块化架构，学会构建可扩展的 Master Graph。

**核心内容**：
- Subgraph 概念和设计模式
- 适配器模式（Adapter Pattern）
- Master Graph 构建
- 子图间状态传递
- FAQ 和订单子图实战

**周文档**：[Week 3 详细文档](doc/Week3-Subgraph-Modular.md) | [Week 3 综合笔记](src/week3/week3_comprehensive_notes.md)

**产出代码**：
- `src/week3/faq_subgraph.py` - FAQ 子图
- `src/week3/order_subgraph.py` - 订单子图
- `src/week3/master_graph.py` - 主图系统

---

### Week 4：Workflow vs Agent 选型

**学习目标**：通过实际对比实验，深入理解 Workflow 和 Agent 两种模式的优缺点，掌握选型方法。

**核心内容**：
- Workflow 模式（确定性流程）
- Agent 模式（LLM 驱动决策）
- 对比实验设计
- 性能指标评估
- 选型决策框架

**周文档**：[Week 4 详细文档](doc/Week4-Workflow-vs-Agent.md) | [Week 4 综合笔记](src/week4/week4_comprehensive_notes.md)

**产出代码**：
- `src/week4/workflow_version.py` - Workflow 版本
- `src/week4/agent_version.py` - Agent 版本
- `src/week4/comparison.py` - 对比实验

---

## 🎯 本月学习成果

完成本月学习后，你将具备以下能力：

✅ **基础能力**
- 理解 LangGraph 的核心概念和设计理念
- 能够创建基础的 StateGraph
- 掌握节点、边和状态管理

✅ **持久化能力**
- 能够实现 Checkpoint 持久化
- 掌握时间旅行和状态重放
- 能够设计 Human-in-the-Loop 流程

✅ **模块化设计**
- 理解子图的设计原则
- 掌握适配器模式的应用
- 能够构建可扩展的 Master Graph

✅ **架构选型**
- 深入理解 Workflow 和 Agent 的差异
- 能够基于场景选择合适的模式
- 具备数据驱动的决策能力

---

## 📖 深入阅读

- [文档索引](doc/INDEX.md) - 本月文档总导航
- [图设计理念](docs/graph_design.md) - 图设计的最佳实践
- [Workflow vs Agent](docs/workflow_vs_agent.md) - 选型深度分析

---

## 🚀 下一步

完成 Month 02 后，你将继续学习：

**Month 03: RAG (检索增强生成)** - 学习如何让 AI 具备"翻书找答案"的能力，构建知识库问答系统。

---

## 📊 学习进度追踪

| Week | 状态 | 用时 | 完成日期 |
|------|------|------|---------|
| Week 1 | ⬜ | - | - |
| Week 2 | ⬜ | - | - |
| Week 3 | ⬜ | - | - |
| Week 4 | ⬜ | - | - |

---

**开始学习**：[进入 Week 1](src/week1/README.md) 🚀
# 📚 第 2 月 - LangGraph 与编排

**日期**：2026-05-13 至 2026-06-08

**主题**：从「单兵作战」到「团队协作」—— 建立 workflow vs agent 判断力，掌握 Graph API、State、Node、Edge

---

## 🎯 月目标

- 理解 LangGraph 的 Graph API 基本结构
- 掌握 Persistence / Checkpoints（状态持久化、时间旅行、Human-in-the-loop）
- 学会 Subgraph 与模块化设计
- 建立 Workflow vs Agent 的选型判断力

## 📁 目录结构

```
month02-langgraph/
├── README.md                          # 本月学习说明（本文件）
├── src/
│   ├── week1/                         # Week 1: Graph API 入门
│   │   ├── simple_graph.py
│   │   └── customer_support_graph.py
│   ├── week2/                         # Week 2: Persistence / Checkpoints
│   │   └── checkpoint_demo.py
│   ├── week3/                         # Week 3: Subgraph 与模块化 ✅
│   │   ├── order_subgraph.py
│   │   ├── faq_subgraph.py
│   │   ├── master_graph.py
│   │   └── week3_comprehensive_notes.md
│   └── week4/                         # Week 4: Workflow vs Agent 选型
├── docs/
│   ├── graph_design.md
│   ├── workflow_vs_agent.md
│   └── month2_review.md
├── eval/                              # 评测
│   └── golden_cases.csv
└── results/                           # 运行结果
```

---

## 📋 周计划

### Week 1：Graph API 入门
- 理解 StateGraph 基本结构
- 画结构图、实现第一个 graph
- 把 month01 客服流程翻译成 graph
- 增加条件分支 edge

### Week 2：Persistence / Checkpoints
- 理解持久化机制、线程、checkpoint、time travel
- 做 checkpoint_demo.py
- 模拟失败恢复、Human-in-the-loop

### Week 3：Subgraph 与模块化
- 理解 subgraph 概念
- 设计订单处理子图、FAQ 子图
- 主图组合两个子图

### Week 4：Workflow vs Agent 选型
- 总结判定标准
- 同需求分别做 workflow 版和 agent 版
- 对比：成本、延迟、稳定性、调试难度
- 月度复盘

---

## 📊 进度追踪

| 周 | 任务 | 状态 | 用时 |
|----|------|------|------|
| Week 1 | Graph API 入门 | ✅ 已完成 | ~1.5h |
| Week 2 | Persistence / Checkpoints | ✅ 已完成 (3 个文件全通) | ~3h |
| Week 3 | Subgraph 与模块化 | ✅ 已完成 (3 个文件全通，11 个测试用例) | ~3h |
| Week 4 | Workflow vs Agent 选型 | ⬜ 待开始 | __h |

**总用时**: 预计 12 小时 | 实际：~7.5h

---

## 🚀 快速开始

```bash
cd /Users/liyang/dev/python_project/ly-ai-roadmap-lab
source venv/bin/activate
pip install langgraph langchain-openai
```

---

## 📝 Week 3 补充说明 (2026-05-24)

**已完成的代码文件**：
- `src/week3/order_subgraph.py` — 订单处理子图（5 个节点）
- `src/week3/faq_subgraph.py` — FAQ 子图（置信度路由）
- `src/week3/master_graph.py` — 主图组合（11 个测试用例）
- `src/week3/week3_comprehensive_notes.md` — 详细学习笔记

**关键设计**：
- 子图 = 编译后的 graph 作为节点添加到主图
- State 共享：主图 State 是所有子图 State 的超集
- 适配器模式：解决主图/子图字段不一致问题

**下周**：Week 4 — Workflow vs Agent 选型对比
