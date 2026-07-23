# Multi-Agent 角色拆分设计

## 核心理念

单个 Agent 负责整个任务 → 职责混乱、输出质量不稳定。  
拆分为三个专门化角色，各司其职：

```
User → Planner → Executor → Reviewer → User
         ↑                         │
         └─────────────────────────┘ (反馈循环)
```

## 角色定义

### 1. Planner（规划者）
- **职责**：理解用户需求，分解为可执行的步骤
- **输入**：用户原始需求
- **输出**：结构化的执行计划（步骤列表）
- **不负责**：执行、审查

### 2. Executor（执行者）
- **职责**：按计划一步步执行，调用工具，产生中间结果
- **输入**：Planner 的计划
- **输出**：每步的执行结果
- **不负责**：规划、审查质量

### 3. Reviewer（审查者）
- **职责**：检查执行结果是否满足计划要求，给出通过/修改意见
- **输入**：Planner 的计划 + Executor 的结果
- **输出**：✅ 通过 或 ❌ 退回修改（含具体意见）
- **不负责**：规划、执行

## 为什么这样拆？

| 问题 | 单体 Agent | 三角色模式 |
|------|-----------|-----------|
| 糊弄式回答 | 直接输出不准确结论 | Reviewer 拦截不一致输出 |
| 步骤遗漏 | 跳过中间步骤 | Planner 显式定义步骤 |
| 幻觉 | 编造不存在的工具调用 | Executor 只执行，Reviewer 验证 |
| 无法迭代优化 | 一次生成，质量靠运气 | 反馈循环，直到 Reviewer 批准 |

## Handoff 协议

```
Planner → Executor： handoff(plan, context)
Executor → Reviewer：handoff(plan, execution_results)
Reviewer → Executor：handoff(plan, feedback)  // 退回修改
Reviewer → User：     final_output
```

## 本周实现

使用 OpenAI Agents SDK（已在 month01 安装）的 Agent + handoff 机制：
- 3 个 agent，各有独立的 instructions
- 用 handoff 串联流程
- trace 分析职责是否串扰
