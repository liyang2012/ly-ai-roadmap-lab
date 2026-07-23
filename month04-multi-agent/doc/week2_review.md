# 第 4 月 Week 2：A2A 协议入门 — 复盘笔记

## 本周目标
理解 A2A 协议核心概念，用 Python 模拟 Agent Card、Task 生命周期、任务委托。

## 完成情况
- ✅ Day 1-2：Agent Card 定义与注册/发现
- ✅ Day 3-4：Task 生命周期（submitted→working→completed/failed）
- ✅ Day 5-6：委托调度器（关键词匹配选 Agent + 异步执行）
- ✅ Day 7：复盘笔记（本文）
- ✅ 测试：5/5 全部通过

## 核心知识点

### 1. A2A 解决什么问题
不同框架（LangGraph, CrewAI, AutoGen）构建的 Agent 之间的**通信标准**。
类比：A2A 对 Agent 通信 = HTTP 对 Web 服务通信。

### 2. A2A vs MCP
| | MCP | A2A |
|---|---|---|
| 通信对象 | Agent ↔ Tool | Agent ↔ Agent |
| 类比 | USB 协议 | TCP/IP |
| 解决问题 | 工具连接标准化 | 跨 Agent 协作标准化 |

**它们是互补的，不是竞争关系。**

### 3. 五大核心概念

| 概念 | 对应实现 | 说明 |
|------|---------|------|
| AgentCard | `AgentCard` dataclass | 数字名片，声明身份+技能 |
| Task | `Task` + `TaskStatus` 枚举 | 有状态的工作单元 |
| Message | （本周未深入） | 单轮通信，由 Part 组成 |
| Part | （本周未深入） | text/file/data 容器 |
| Artifact | `Task.result` | Agent 产出的具体成果 |

### 4. 关键设计决策

**Q: 为什么用规则匹配而不是 LLM 选 Agent？**
A: 实际系统中 Agent Discovery 是确定性的——看 AgentCard 的技能描述匹配需求。LLM 在这里引入不必要的延迟和不确定性。A2A 协议本身也不要求 LLM 做发现。

**Q: 为什么不用官方 A2A SDK？**
A: Week 2 的重点是理解设计思想，不是调 API。用熟悉的技术栈（dataclass + asyncio + Agents SDK）模拟核心概念，理解更深入。官方 SDK 适合 Week 3-4 实操。

### 5. 测试结果

| 需求 | 委托给 | 耗时 | 结果 |
|------|--------|------|------|
| 搜索 A2A 协议的知识 | SearchAgent | 5.5s | ✅ |
| 写 AI Agent 文章 | WriterAgent | 7.5s | ✅ |
| 计算 1234×5678 | MathAgent | 3.2s | ✅ |
| 对比 AI vs Multi-Agent | AnalystAgent | 19.9s | ✅ |
| 搜索 Python+写总结 | WriterAgent | 13.6s | ✅ |

## 踩坑记录

1. **智谱 GLM-4-Flash 不遵循 tool calling instructions**：第一版用 LLM 做 ClientAgent 调度，LLM 没有调用 discover/delegate 工具，而是用自己的知识回答。改回规则匹配后立即解决。—— **教训：LLM 不做路由决策，路由决策应该是确定性的。**

2. **关键词匹配需要合理设计**：测试 5（"搜索 Python 并写总结"）同时匹配了 SearchAgent(1.0) 和 WriterAgent(2.0)。因为 WriterAgent 同时有"写文章"和"搜索补充"两个技能，关键词"搜索"和"写总结"各命中一个。正确选择了得分更高的 WriterAgent(2.0)。

## 下一步：Week 3 预告
Supervisor/Subagent 层次化协作 — 一个 Supervisor 管理多个 Subagent 并行执行，比本周的单次委托更进一步。
