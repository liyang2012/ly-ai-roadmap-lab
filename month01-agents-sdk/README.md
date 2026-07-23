# 🤖 Month 01: Agents SDK 学习指南

> **学习目标**：掌握 AI Agent 的核心概念和实战应用，从零基础到能够独立开发多 Agent 协作系统。
> 
> **学习时间**：4 周，约 12-15 小时
> 
> **最后更新**：2026-07-13

---

## 📖 本月概览

本月你将系统学习 OpenAI Agents SDK，从第一个简单的 Agent 开始，逐步掌握工具系统、测试评估，最终能够设计和实现多 Agent 协作系统。

### 学习路线图

```
Week 1: 基础入门         Week 2: 工具系统         Week 3: 测试优化         Week 4: 多Agent协作
    ↓                       ↓                       ↓                       ↓
[AI Agent 概念]      [Tool 工具系统]        [测试与评估]           [Handoff 机制]
[环境搭建]          [结构化输出]          [Tracing 调试]         [多Agent设计]
[第一个Agent]       [实战：电商客服]      [Token 优化]           [综合项目]
```

---

## 📚 周文档导航

### Week 1：第一个 Agent

**学习目标**：理解 AI Agent 的基本概念，搭建开发环境，创建第一个可运行的 Agent。

**核心内容**：
- AI Agent 的组成（LLM + Tools + Instructions）
- 开发环境配置（Python + API Key）
- Run Loop 运行机制
- 创建 Hello World Agent

**周文档**：[Week 1 详细文档](src/week1/README.md)

**产出代码**：
- `src/week1/hello_agent.py` - 第一个 Agent
- `src/week1/loop_agent_tools.py` - 带工具的 Agent

---

### Week 2：Tool 工具系统

**学习目标**：掌握 Agent 的工具系统，能够为 Agent 添加多个工具，并实现结构化输出。

**核心内容**：
- Tool 定义和注册
- 多 Tool 协作
- 结构化输出（Structured Output）
- Guardrails 安全防护
- Tracing 追踪调试
- Handoff 初步了解

**周文档**：[Week 2 详细文档](src/week2/README.md)

**产出代码**：
- `src/week2/multi_tool_agent.py` - 多工具 Agent
- `src/week2/ecommerce_support_agent.py` - 电商客服实战
- `src/week2/structured_output.py` - 结构化输出
- `src/week2/guardrails_example.py` - 安全防护
- `src/week2/tracing_debug_example.py` - 追踪调试

---

### Week 3：测试与评估

**学习目标**：掌握 Agent 的测试方法，学会评估和优化 Agent 的性能、一致性和成本。

**核心内容**：
- 一致性测试（多次运行对比）
- Token 使用分析
- 错误场景测试
- 性能优化策略

**周文档**：[Week 3 详细文档](src/week3/README.md)

**产出代码**：
- `src/week3/day15_16_consistency_test.py` - 一致性测试
- `src/week3/day17_18_token_usage.py` - Token 使用分析
- `src/week3/day19_20_error_cases.py` - 错误场景测试
- `src/week3/day21_22_optimization.py` - 优化实践

---

### Week 4：多 Agent 协作

**学习目标**：掌握 Handoff 机制，理解多 Agent 设计模式，完成综合项目。

**核心内容**：
- Handoff 详细机制
- 多 Agent 角色设计
- 协作模式（Sequential / Parallel / Hierarchical）
- 综合项目实战

**周文档**：[Week 4 详细文档](src/week4/README.md)

**产出代码**：
- `src/week4/simple_handoff.py` - 简单 Handoff
- `src/week4/multi_agent_collab.py` - 多 Agent 协作
- `src/week4/capstone_project.py` - 综合项目

---

## 🎯 本月学习成果

完成本月学习后，你将具备以下能力：

✅ **基础能力**
- 理解 AI Agent 的核心概念和工作原理
- 能够独立搭建 Agent 开发环境
- 掌握 Run Loop 的运行机制

✅ **工具系统**
- 能够为 Agent 定义和注册多个工具
- 掌握结构化输出的实现方式
- 理解安全防护和追踪调试

✅ **测试优化**
- 能够设计测试用例评估 Agent
- 掌握 Token 使用分析和优化方法
- 具备错误场景处理能力

✅ **多Agent协作**
- 深入理解 Handoff 机制
- 掌握多种多 Agent 设计模式
- 能够设计和实现复杂的多 Agent 系统

---

## 📖 深入阅读

本月还有两个专题文档，供深入学习：

- [Run Loop 详解](RunLoop.md) - 深入理解 Agent 的运行循环
- [Handoff 机制详解](Handoff.md) - 全面掌握多 Agent 协作机制

---

## 🚀 下一步

完成 Month 01 后，你将继续学习：

**Month 02: LangGraph** - 学习图结构化的 Agent 框架，掌握更灵活的工作流设计。

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
