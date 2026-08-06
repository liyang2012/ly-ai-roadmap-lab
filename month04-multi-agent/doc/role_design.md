# 角色设计与分工：Planner-Executor-Reviewer

## 一句话理解

单个 Agent 啥都干 → 职责混乱、输出不稳定。拆成三个**专才**各司其职，像流水线一样：规划的人只管拆任务，执行的人只管干活，审查的人只管把关质量。

> 类比：餐厅后厨——点菜员（Planner）记录需求并拆成菜品、厨师（Executor）按菜单做菜、质检员（Reviewer）检查出品是否合格。

## 为什么需要多角色？

| 问题 | 单体 Agent（啥都干） | 三角色模式 |
|------|---------------------|-----------|
| 糊弄式回答 | 直接输出不准确结论 | Reviewer 拦截不一致输出 |
| 步骤遗漏 | 跳过中间步骤 | Planner 显式定义每步 |
| 幻觉 | 编造不存在的工具调用 | Executor 只执行，Reviewer 验证 |
| 无法迭代 | 一次生成，质量靠运气 | 反馈循环，直到 Reviewer 批准 |

**核心原则**：关注点分离——每个角色只做一件事，通过 Handoff 协议传递工作。

## 架构总览

```
User → Planner → Executor → Reviewer → User
         ↑                         │
         └─────────────────────────┘ (反馈循环：不合格退回修改)
```

### 三步走流程

| 步骤 | 谁干 | 干什么 | 输入 → 输出 |
|------|------|--------|------------|
| 1. 规划 | Planner | 理解需求，拆成步骤列表 | 用户需求 → 执行计划 |
| 2. 执行 | Executor | 按计划逐步执行，调用工具 | 执行计划 → 执行结果 |
| 3. 审查 | Reviewer | 检查结果是否达标 | 计划 + 结果 → ✅通过 / ❌退回 |

## 核心概念详解

### 1. Planner（规划者）

- **职责**：理解用户需求，分解为可执行的步骤
- **输入**：用户原始需求
- **输出**：结构化的执行计划（编号步骤列表）
- **不负责**：执行步骤、审查质量

> 类比：建筑师——画蓝图，但不亲自搬砖。

### 2. Executor（执行者）

- **职责**：按计划一步步执行，调用工具，产生中间结果
- **输入**：Planner 的计划
- **输出**：每步的执行结果
- **不负责**：规划、审查质量

> 类比：施工队——按图纸施工，但不改设计。

### 3. Reviewer（审查者）

- **职责**：检查执行结果是否满足计划要求，给出通过/修改意见
- **输入**：Planner 的计划 + Executor 的结果
- **输出**：✅ 通过（输出给用户）或 ❌ 退回修改（含具体意见）
- **不负责**：规划、执行

> 类比：质检员——只管检查，不管怎么修。

### 4. Handoff 协议

角色之间通过 Handoff（交接）传递工作：

```
Planner → Executor：  handoff(plan, context)
Executor → Reviewer： handoff(plan, execution_results)
Reviewer → Executor： handoff(plan, feedback)    // 退回修改
Reviewer → User：     final_output               // 最终交付
```

这是 OpenAI Agents SDK 内置的机制——Agent 之间通过 `handoff` 函数传递控制权，每个 Agent 只看到自己需要的上下文。

## 关键设计决策

### Q: 为什么不直接用一个大 Agent 干所有事？

单体 Agent 的问题是**职责串扰**：
- 它可能在规划时就开始执行（跳过必要分析）
- 在执行时自我审查导致输出不稳定
- 出错时不知道是规划问题还是执行问题

三角色模式让每个阶段**可独立调试**：规划有问题看 Planner，执行有问题看 Executor，质量有问题看 Reviewer。

### Q: Reviewer 退回了，Executor 怎么知道改什么？

Reviewer 退回时会附带**具体修改意见**（feedback），Executor 根据意见修改后再次提交。  
这个循环直到 Reviewer 通过为止，确保输出质量。

```python
# 简化版循环逻辑
while True:
    result = await executor.run(plan)
    review = await reviewer.run(plan, result)
    if review.approved:
        break  # 通过，输出给用户
    # 否则带上 feedback 重新执行
```

### Q: 和 Week 3 的 Supervisor 模式有什么区别？

| | Week 1：三角色串行 | Week 3：Supervisor 并行 |
|---|---|---|
| 架构 | P → E → R 直线 | Supervisor → Workers 星型 |
| 执行方式 | 串行，一个做完交给下一个 | 并行，多个同时执行 |
| 适用场景 | 单任务需要规划+执行+审查 | 复杂任务可拆分为独立子任务 |
| 容错 | 一环出错全链停 | 一个 Worker 失败不影响其他 |

> Week 1 是基础，Week 3 在此基础上升级为并行模式。

## 代码结构

```
src/week1/
└── planner_executor_reviewer.py    # 完整实现，约 305 行
```

### 代码分层

```
第 1 层：工具定义
  └── search_knowledge()        # 知识库搜索工具

第 2 层：角色 Agent 定义
  ├── planner_agent             # 规划者：分解任务为步骤
  ├── executor_agent            # 执行者：按计划逐步执行
  └── reviewer_agent            # 审查者：检查质量，通过/退回

第 3 层：协作流程
  └── run_collaboration()       # 串联 P→E→R 流程（含反馈循环）

第 4 层：用户接口
  ├── interactive_mode()        # 交互式：输入需求
  └── run_tests()               # 自动测试用例
```

## 运行方式

```bash
# 交互模式：输入需求，三角色自动协作
python src/week1/planner_executor_reviewer.py

# 单次任务：直接传入需求
python src/week1/planner_executor_reviewer.py --task "写一篇 200 字关于 AI 的文章"

# 运行测试：执行预设测试用例
python src/week1/planner_executor_reviewer.py --test
```

## 本周学习目标

1. **理解** 为什么单体 Agent 不够用（职责串扰、输出不稳定）
2. **掌握** Planner-Executor-Reviewer 三角色的职责划分
3. **理解** Handoff 协议：角色之间如何传递控制权和数据
4. **掌握** 反馈循环：Reviewer 退回 → Executor 修改 → 再次审查
5. **理解** 关注点分离原则：每个角色只做一件事，便于调试和扩展

## 扩展思考

- **更多角色**：如果任务更复杂，能不能加 Researcher（调研员）、Editor（编辑）？
- **动态路由**：能不能根据需求类型，自动决定走哪些角色？
- **并行执行**：如果步骤之间互不依赖，能不能同时执行？（提示：这就是 Week 3 的 Supervisor 模式）
- **跨 Agent 委托**：如果 Executor 需要调用其他系统的 Agent 怎么办？（提示：这就是 Week 2 的 A2A 协议）

> 这些问题的答案，分别在 Week 2、Week 3 中揭晓。
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
