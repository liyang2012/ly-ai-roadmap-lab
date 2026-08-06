# 🤝 Month 04: Multi-Agent 系统学习指南

> **学习目标**：掌握多 Agent 协作系统的设计与实现，理解 A2A 协议，掌握 Agent 角色设计和分工协作模式，学会 Agent vs MCP 架构选型。
> 
> **学习时间**：4 周，约 12-15 小时
> 
> **最后更新**：2026-07-27

---

## 📖 本月概览

本月你将学习如何设计和构建多 Agent 协作系统。这是 Agent 系统的高级主题，从角色设计、A2A 协议、Supervisor 并行协作，到架构选型与 MCP 集成，最终能够根据业务场景选择最合适的架构方案。

### 学习路线图

```
Week 1: 角色设计与分工       Week 2: A2A 协议          Week 3: Supervisor 模式      Week 4: 选型与 MCP
    ↓                        ↓                       ↓                       ↓
[角色拆分]             [协议规范]              [层次化协作]            [架构决策]
[Planner-Executor]     [通信机制]              [并行执行]              [MCP Server]
[Reviewer 模式]        [状态同步]              [结果聚合]              [Agent+MCP]
```

---

## 📚 周文档导航

### Week 1：角色设计与分工

**学习目标**：理解多 Agent 系统中角色设计的原则，掌握 Planner-Executor-Reviewer 模式。

**核心内容**：
- 多 Agent 系统的优势和应用场景
- Agent 角色设计原则
- Planner-Executor-Reviewer 架构
- 角色间通信机制
- 任务分解与分配策略

**周文档**：[Week 1 详细文档](doc/role_design.md)

**产出代码**：
- `src/week1/planner_executor_reviewer.py` - 角色分工系统

---

### Week 2：A2A 协议与通信

**学习目标**：理解 Agent-to-Agent (A2A) 协议，掌握多 Agent 间的通信和状态同步机制。

**核心内容**：
- A2A 协议的核心概念
- Agent Card（能力声明）
- Task 生命周期管理
- 通信协议（JSON-RPC 2.0）
- 状态同步机制
- 错误处理和重试策略

**周文档**：[Week 2 详细文档](doc/a2a_concepts.md) | [Week 2 复盘笔记](doc/week2_review.md)

**产出代码**：
- `src/week2/a2a_simulator.py` - A2A 协议模拟器

---

### Week 3：Supervisor 层次化协作

**学习目标**：掌握 Supervisor/Worker 模式，实现多 Worker 并行执行，理解与串行模式的区别。

**核心内容**：
- Supervisor 三步走：分解 → 并行执行 → 聚合
- Worker 角色设计（Planner/Executor/Writer/Analyst）
- `asyncio.gather` 并行执行
- 容错设计：单 Worker 失败不影响整体
- 与 Week 1 串行模式的对比

**周文档**：[Week 3 详细文档](doc/supervisor_pattern.md)

**产出代码**：
- `src/week3/supervisor_agent.py` - Supervisor 层次化协作系统

---

### Week 4：架构选型与 MCP 集成

**学习目标**：掌握 Agent vs MCP Tool 的决策框架，理解 MCP Server 核心概念，实现 Agent + MCP 的协作集成。

**核心内容**：
- Agent vs Tool 五维决策框架
- MCP Server 核心概念（Tools + Resources）
- Agent 消费 MCP 的三步模式
- 电商订单查询实战（OrderMCPServer + OrderAgent）
- 第 4 月完整回顾与选型口诀

**周文档**：[Week 4 详细文档](doc/agent_vs_mcp.md)

**产出代码**：
- `src/week4/agent_vs_mcp.py` - 架构选型引擎 + MCP Server + Agent 集成

---

## 🎯 本月学习成果

完成本月学习后，你将具备以下能力：

✅ **角色设计**
- 理解多 Agent 系统的优势和应用场景
- 能够设计合理的 Agent 角色
- 掌握任务分解和分配策略

✅ **通信机制**
- 深入理解 A2A 协议
- 掌握 Agent 间通信机制
- 能够设计状态同步方案

✅ **协作模式**
- 掌握多种协作模式的设计
- 理解不同模式的适用场景
- 能够选择合适的协作策略

✅ **系统设计**
- 能够设计完整的多 Agent 系统
- 掌握性能优化方法
- 具备生产级系统的设计能力

✅ **架构选型**
- 掌握 Agent vs MCP Tool 的五维决策框架
- 理解 MCP Server 的核心概念（Tools + Resources）
- 能够实现 Agent + MCP 的协作集成

---

## 📖 深入阅读

- [A2A 协议详解](doc/a2a_concepts.md) - Agent-to-Agent 协议的深入讲解
- [角色设计原则](doc/role_design.md) - 多 Agent 角色设计的最佳实践
- [Supervisor 模式](doc/supervisor_pattern.md) - 层次化协作的设计与实现
- [Week 4 架构选型](doc/agent_vs_mcp.md) - Agent vs MCP 决策框架与集成实战
- [Week 2 复盘](doc/week2_review.md) - A2A 协议的实战复盘

---

## 🚀 下一步

完成 Month 04 后，你已经掌握了 AI Agent 的核心技术栈。接下来可以：

- **深入研究**：探索特定领域的 Agent 应用（如 RPA、客服、数据分析）
- **框架对比**：对比 OpenAI Agents SDK、LangGraph、CrewAI 等框架
- **真实 MCP**：基于 MCP 官方规范构建真实的 MCP Server
- **实际项目**：基于所学知识，开发真实世界的 Agent 应用

---

## 📊 学习进度追踪

| Week | 状态 | 用时 | 完成日期 |
|------|------|------|---------|
| Week 1 | ⬜ | - | - |
| Week 2 | ⬜ | - | - |
| Week 3 | ⬜ | - | - |
| Week 4 | ⬜ | - | - |

---

**开始学习**：[进入 Week 1](doc/role_design.md) 🚀
