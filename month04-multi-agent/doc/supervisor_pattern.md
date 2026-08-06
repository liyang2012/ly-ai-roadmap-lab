# Supervisor 层次化协作模式

## 一句话理解

Supervisor 就像公司的**项目经理**：接到客户需求后，把活儿拆成若干子任务，分给不同的专员（Worker）同时干，最后把大家的成果汇总交付。

## 为什么需要 Supervisor？

Week 1 的 Planner→Executor→Reviewer 是**串行流水线**——一个干完交给下一个，效率低。  
Week 2 的 A2A 委托是**单次一对一**——Client 找到一个 Remote Agent 委托任务。

现实中很多需求可以**拆成互不依赖的子任务同时干**，比如：

> "写一篇 AI Agent 科普文章，并对比分析主流框架的优劣"

这句话天然包含两件**互不依赖**的事：
1. WriterWorker 写文章
2. AnalystWorker 做对比分析

让它们并行执行，总耗时 ≈ max(写文章, 分析)，而不是两者之和。

## 架构总览

```
用户 → Supervisor（分解 + 分发 + 聚合）
          ├── PlannerWorker  — 规划分解
          ├── ExecutorWorker — 执行操作  ┐
          ├── WriterWorker   — 内容写作  ├─ 并行执行
          └── AnalystWorker  — 对比分析  ┘
```

### 三步走流程

| 步骤 | 谁干 | 干什么 | 输入 → 输出 |
|------|------|--------|------------|
| 1. 分解 | SupervisorPlanner | 分析需求，拆成子任务 JSON | 用户需求 → `[{worker, task}, ...]` |
| 2. 并行执行 | 各 Worker | 各自执行分配到的子任务 | 子任务描述 → 执行结果 |
| 3. 聚合 | SupervisorAggregator | 汇总所有结果，生成统一报告 | 所有 Worker 结果 → 最终报告 |

## 核心概念详解

### 1. Supervisor（监督者）

Supervisor 是**管理者**，自己不执行具体任务，只做三件事：
- **分解**：把大需求拆成小任务
- **分发**：把小任务分配给合适的 Worker
- **聚合**：把 Worker 的结果汇总成最终交付

> 类比：餐厅经理——不亲自炒菜，而是把客人的点单拆给不同厨师，最后检查出品。

### 2. Worker（工人）

每个 Worker 是**专才**，只负责自己擅长的事：

| Worker | 擅长 | 可用工具 |
|--------|------|---------|
| PlannerWorker | 任务规划、步骤分解 | search_knowledge |
| ExecutorWorker | 执行操作、数学计算 | search_knowledge, calculate_math |
| WriterWorker | 文章写作、内容生成 | search_knowledge |
| AnalystWorker | 对比分析、给出建议 | search_knowledge |

### 3. Subtask（子任务）

子任务是 Supervisor 和 Worker 之间的**工作单元**：

```python
@dataclass
class Subtask:
    id: str              # 唯一标识
    description: str     # 任务描述
    worker_name: str     # 分配给哪个 Worker
    status: SubtaskStatus  # pending → running → completed/failed
    result: str          # 执行结果
    error: str           # 错误信息
```

### 4. 并行执行

用 Python 的 `asyncio.gather` 实现真正的并行：

```python
# 所有子任务同时开始，谁先完成谁先返回
tasks = [execute_subtask(st) for st in subtasks]
results = await asyncio.gather(*tasks)
```

> 类比：4 个厨师同时做菜，不用等一个做完再做下一个。

## 与 Week 1 三角色的区别

| | Week 1：三角色串行 | Week 3：Supervisor 并行 |
|---|---|---|
| 架构 | P → E → R 直线 | Supervisor → Workers 星型 |
| 执行方式 | 串行，一个做完交给下一个 | 并行，多个同时执行 |
| 适用场景 | 单任务需要规划+执行+审查 | 复杂任务可拆分为独立子任务 |
| 容错 | 一环出错全链停 | 一个 Worker 失败不影响其他 |
| 扩展性 | 加角色要改链路 | 加 Worker 只需注册 |

## 与 Week 2 A2A 的区别

| | Week 2：A2A 委托 | Week 3：Supervisor |
|---|---|---|
| 关系 | 一对一（Client → Remote） | 一对多（Supervisor → Workers） |
| 发现机制 | AgentCard 动态发现 | Worker 注册表静态配置 |
| 任务拆分 | 不拆分，整体委托 | 拆分为子任务，分别执行 |
| 结果处理 | 直接返回 | 聚合为统一报告 |

## 关键设计决策

### Q: 为什么用 LLM 做任务分解，而不用规则？

Week 2 的路由用关键词匹配（确定性），因为那是**选择**——从已有 Agent 里挑一个。  
Week 3 的分解需要**理解需求语义并创造性拆分**，这正是 LLM 擅长的。

但分解结果可能不稳定（LLM 可能输出非 JSON），所以代码里有兜底逻辑：

```python
try:
    subtasks = json.loads(json_str)  # 尝试解析 JSON
except (ValueError, json.JSONDecodeError):
    # 兜底：当作单任务交给 ExecutorWorker
    return [{"worker": "ExecutorWorker", "task": user_request}]
```

### Q: 为什么 Worker 之间不直接通信？

**关注点分离**：Worker 只管执行自己的子任务，不需要知道其他 Worker 在做什么。  
所有协调工作由 Supervisor 负责，这样：
- Worker 可以独立测试
- 加/减 Worker 不影响其他 Worker
- 出问题时容易定位

### Q: 一个 Worker 失败了怎么办？

当前实现是**尽力而为**（best-effort）：
- 失败的 Worker 标记为 `FAILED`，记录错误信息
- 其他 Worker 继续执行，不受影响
- 聚合阶段会标注哪些成功、哪些失败
- 最终报告依然生成，但会体现失败信息

## 代码结构

```
src/week3/
└── supervisor_agent.py    # 完整实现，约 580 行
```

### 代码分层

```
第 1 层：工具定义
  ├── search_knowledge()   # 知识库搜索
  └── calculate_math()     # 数学计算

第 2 层：Worker Agent 定义
  ├── planner_worker       # 规划型 Worker
  ├── executor_worker      # 执行型 Worker
  ├── writer_worker        # 写作型 Worker
  └── analyst_worker       # 分析型 Worker

第 3 层：Supervisor 调度
  ├── supervisor_plan()    # 步骤 1：分解任务
  ├── execute_parallel()   # 步骤 2：并行执行
  └── aggregate_results()  # 步骤 3：聚合结果

第 4 层：完整流程
  └── run_supervisor()     # 串联三步走

第 5 层：用户接口
  ├── interactive_mode()   # 交互式
  └── run_tests()          # 自动测试
```

## 运行方式

```bash
# 交互模式：输入需求，Supervisor 自动分解并执行
python src/week3/supervisor_agent.py

# 单次任务：直接传入需求
python src/week3/supervisor_agent.py --task "介绍 AI Agent 并对比 LangGraph 和 CrewAI"

# 运行测试：执行 4 个预设测试用例
python src/week3/supervisor_agent.py --test
```

## 测试用例

| # | 需求 | 预期 Worker 数 | 验证点 |
|---|------|---------------|--------|
| 1 | 搜索 AI Agent 的知识并总结 | 1 | 简单任务不拆分 |
| 2 | 介绍 AI Agent 并对比 LangGraph 和 CrewAI | 2 | 双任务并行 |
| 3 | 规划架构设计 + 写文章 + 分析框架优劣 | 3 | 多任务并行 |
| 4 | 搜索 Python 知识 + 计算 1234×5678 | 2 | 跨工具并行 |

## 本周学习目标

1. **理解** Supervisor 模式的三步走流程（分解→并行→聚合）
2. **掌握** 与 Week 1 串行模式的区别和适用场景
3. **理解** 为什么 Worker 之间不直接通信（关注点分离）
4. **掌握** `asyncio.gather` 实现并行执行的方法
5. **理解** 容错设计：一个 Worker 失败不影响整体

## 扩展思考

- **动态 Worker 注册**：能不能运行时动态添加新 Worker？
- **带依赖的子任务**：如果子任务 B 依赖子任务 A 的结果怎么办？（提示：拓扑排序 + 分批执行）
- **负载均衡**：如果某类任务特别多，能不能启动多个同类 Worker？
- **结果质量**：聚合阶段能不能加一个 Reviewer 做质量把关？

> 但更重要的问题是：什么时候该上 Supervisor？什么时候一个 MCP Tool 就足够了？这就是 Week 4 架构选型要回答的。
