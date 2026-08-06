# Agent vs MCP：架构选型与集成实战

## 一句话理解

前 3 周学了多种 Agent 协作模式，Week 4 回答最关键的问题：**什么时候该用 Agent，什么时候用 MCP Tool 就够了？**

> MCP 是水管（连接数据），Agent 是大脑（推理决策）。你的架构 = 什么时候用大脑 + 什么时候用水管。

## 为什么需要这个决策框架？

学完 W1-W3 容易产生一种错觉：所有问题都该上 Agent。但现实中：

| 需求 | 真的需要 Agent 吗？ |
|------|---------------------|
| "查询订单 ORD-001" | ❌ 一个 API 调用就搞定 |
| "帮我分析最近 3 个月的消费趋势" | ✅ 需要理解意图 + 组合多个工具 |
| "取消我最近的订单" | ⚠️ 需要推理（哪笔是"最近的"）+ 执行 |

**过度使用 Agent 的代价**：响应慢（秒级 vs 毫秒级）、成本高（LLM 调用费）、不稳定（幻觉风险）。  
**正确做法**：能用 Tool 解决的不上 Agent，需要推理时才请出 Agent。

## 架构总览

```
用户需求 → 决策框架（5 维评估）
              ↓
         ┌────┴─────────────────────────────┐
         │  简单确定性    →  MCP Tool        │
         │  固定多步骤    →  Chain/Workflow  │
         │  条件分支      →  Router          │
         │  推理+工具组合 →  Single Agent    │
         │  复杂多任务    →  Multi Agent     │
         └──────────────────────────────────┘
```

## 核心概念详解

### 1. 五维决策框架

评估一个场景该用什么架构，从 5 个维度打分（1-10）：

| 维度 | 权重 | 含义 | 低分 → 高分 |
|------|------|------|-------------|
| 任务不确定性 | 30% | 需要推理还是固定流程 | 确定性操作 → 需要深度推理 |
| 工具需求 | 25% | 需要多少外部系统交互 | 无外部依赖 → 多系统联动 |
| 上下文深度 | 20% | 单次完成还是多轮 | 一问一答 → 多轮对话 |
| 决策需求 | 15% | 需要独立判断吗 | 规则匹配 → 自主决策 |
| 时延要求 | 10% | 秒级还是毫秒级 | 可等几秒 → 必须毫秒级 |

> 类比：选交通工具——距离近骑自行车（Tool），跨城市坐高铁（Single Agent），跨国团队出差需要协调（Multi Agent）。

### 2. 六种架构模式

| 架构 | 一句话 | 适用场景 |
|------|--------|----------|
| MCP Tool | 一次 API 调用 | 查订单、读数据库、发通知 |
| Chain | 固定步骤流水线 | RAG：加载→切分→嵌入→搜索 |
| Router | 条件分支路由 | 根据意图分发到不同服务 |
| Single Agent | 单 Agent + 多 Tool | 自然语言查询 + 工具组合 |
| Multi Agent | 多 Agent 协作 | 复杂任务 + 独立决策角色 |
| Workflow | 确定性编排 | 已知流程的批处理自动化 |

### 3. MCP Server 核心概念

MCP（Model Context Protocol）是让 Agent 发现和调用外部工具的标准协议。一个 MCP Server 暴露两类东西：

| 类型 | 作用 | 类比 |
|------|------|------|
| **Tools** | Agent 可以调用的函数 | 餐厅的菜单（能做什么） |
| **Resources** | Agent 可以读取的数据 | 餐厅的食材清单（有什么） |

```python
# MCP Server 的核心接口
class MCPServer:
    def register_tool(tool)        # 注册一个工具
    def register_resource(resource) # 注册一个资源
    def list_tools() -> list        # Agent 发现可用工具
    def list_resources() -> list    # Agent 发现可用资源
    def call_tool(name, args)       # Agent 调用工具
```

> 实际 MCP 协议基于 JSON-RPC 2.0，代码中简化为 Python 对象调用，核心概念完全一致。

### 4. Agent 消费 MCP 的模式

Agent 通过三步消费 MCP Server：

```
1. 发现 → agent 获取 server.list_tools()，知道有哪些工具可用
2. 选择 → 根据用户需求，决定调用哪个工具（规则匹配或 LLM 推理）
3. 调用 → agent 调用 server.call_tool(name, args)，拿到结果并格式化
```

```python
# OrderAgent 消费 OrderMCPServer 的流程
server = OrderMCPServer()           # 1. 启动 MCP Server
agent = OrderAgent(server)          # 2. Agent 连接 MCP
response = agent.process("查询 Alice 的订单")  # 3. Agent 调用 MCP Tool 并返回
```

## 决策速查表

| 场景 | MCP Tool ✅ | Agent ✅ |
|------|-------------|----------|
| 查询一条订单 | ✓ | |
| 查询订单列表 | ✓ | |
| "我的订单到哪了" | | ✓ |
| "帮我取消最近 3 笔" | | ✓ |
| 生成运营周报 | | ✓ |
| 批量导出订单 | ✓ | |
| 多轮客服对话 | | ✓ |
| 定时同步数据 | ✓ | |
| A/B 价格实验分析 | | ✓ |

**核心原则**：
- MCP Tool → 当"查什么"比"怎么查"更明确时
- Agent → 当"要什么"比"怎么做"更明确时

## 三个典型场景分析

### 场景 1：电商订单查询

```
维度评分：任务不确定性=3, 工具=5, 上下文=4, 决策=3, 时延=8
推荐：MCP Tool + Router
理由：订单查询是确定性操作，MCP Tool + 简单路由即可，不需要 Agent
```

### 场景 2：BI 数据分析助手

```
维度评分：任务不确定性=8, 工具=7, 上下文=7, 决策=6, 时延=4
推荐：Single Agent + MCP Tools
理由：需要理解自然语言、选择分析维度、组合多个 MCP Tool，Agent 合适
```

### 场景 3：智能客服系统

```
维度评分：任务不确定性=7, 工具=6, 上下文=8, 决策=7, 时延=5
推荐：Router + Agent 混合
理由：不同请求需要不同处理逻辑，Router 分发 + Agent 执行
```

## 关键设计决策

### Q: 为什么 MCP Server 要暴露 Resources，不能只有 Tools？

Tools 是"能做什么"（函数），Resources 是"有什么"（数据）。  
比如 `order://statuses` 这个 Resource 告诉 Agent 订单有哪些状态值。  
Agent 可以先读 Resource 了解数据格式，再决定怎么调用 Tool。

### Q: 代码里的 Agent 为什么用规则匹配而不用 LLM？

Week 4 的重点是**架构决策**，不是 LLM 调用。`OrderAgent` 用规则匹配（关键词）演示路由逻辑，因为订单查询场景足够简单。  
如果场景复杂（如自然语言理解），就把规则替换为 LLM Function Calling——架构不变，只是选择器升级了。

### Q: MCP 和 Week 2 的 A2A 有什么区别？

| | MCP | A2A |
|---|---|---|
| 定位 | Agent ↔ Tool 的连接 | Agent ↔ Agent 的连接 |
| 类比 | 水管（连接数据和工具） | 快递员（跨 Agent 传递任务） |
| 粒度 | 单次函数调用 | 完整任务委托 |
| 状态 | 无状态 | 有状态（Task 生命周期） |

### Q: 最佳实践的组合是什么？

```
1. MCP 做数据层  — Resources + Tools 提供数据访问
2. Router 做分发层 — 意图识别 → 路由到不同处理器
3. Agent 做推理层 — 理解需求 + 组合工具 + 解释结果
4. Workflow 做编排层 — 固定流程的自动化
```

## 代码结构

```
src/week4/
└── agent_vs_mcp.py    # 完整实现，约 727 行
```

### 代码分层

```
第 1 层：决策框架
  ├── ArchitectureChoice      # 6 种架构枚举
  ├── DecisionCriteria        # 决策因子（名称、权重）
  └── ArchitectureSelector    # 评分引擎（5 维 → 推荐 Top3）

第 2 层：MCP Server 基础设施
  ├── MCPResource             # 资源定义
  ├── MCPTool                 # 工具定义（含 JSON Schema）
  └── MCPServer               # Server 核心（注册、发现、调用）

第 3 层：电商订单实战
  ├── OrderMCPServer          # 订单 MCP Server（3 个 Tool + 1 个 Resource）
  └── OrderAgent              # 消费 MCP 的 Agent（规则路由 + 格式化输出）

第 4 层：演示与测试
  ├── TEST_SCENARIOS          # 3 个决策分析场景
  ├── run_decision_analysis() # 决策框架演示
  ├── run_mcp_demo()          # MCP + Agent 联调
  ├── run_decision_matrix()   # 决策速查表
  └── run_tests()             # 8 个测试用例
```

## 运行方式

```bash
# 查看决策速查表
python src/week4/agent_vs_mcp.py --matrix

# 场景决策分析（订单/数据分析/客服）
python src/week4/agent_vs_mcp.py --scenario order
python src/week4/agent_vs_mcp.py --scenario data
python src/week4/agent_vs_mcp.py --scenario support

# MCP Server + Agent 联调演示
python src/week4/agent_vs_mcp.py --mcp-demo

# 运行测试（8 个用例）
python src/week4/agent_vs_mcp.py --test

# 第 4 月学习总结
python src/week4/agent_vs_mcp.py --summary
```

## 测试用例

| # | 测试内容 | 验证点 |
|---|---------|--------|
| 1 | 决策框架评分 | 订单查询应推荐 TOOL/ROUTER/WORKFLOW |
| 2 | MCP Tool 注册 | 3 个工具正确注册 |
| 3 | MCP Resource 注册 | Resource URI 正确 |
| 4 | Tool 调用：ID 查询 | 返回正确订单数据 |
| 5 | Tool 调用：用户查询 | Alice 有 2 笔订单 |
| 6 | Tool 调用：统计 | Bob 统计金额正确 |
| 7 | Agent 消费 MCP：ID 查询 | Agent 成功调用 MCP 查订单 |
| 8 | Agent 消费 MCP：统计 | Agent 成功调用 MCP 统计 |

## 本周学习目标

1. **理解** Agent vs MCP Tool 的本质区别：推理 vs 连接
2. **掌握** 五维决策框架，能对任意场景做架构选型评估
3. **理解** MCP Server 的核心概念：Tools（函数）+ Resources（数据）
4. **掌握** Agent 消费 MCP 的三步模式：发现 → 选择 → 调用
5. **理解** 四层组合最佳实践：MCP 数据层 + Router 分发层 + Agent 推理层 + Workflow 编排层

## 第 4 月完整回顾

| 周 | 主题 | 核心模式 | 一句话总结 |
|---|------|----------|-----------|
| W1 | 角色设计与分工 | Planner→Executor→Reviewer 串行 | 三权分立，各司其职 |
| W2 | A2A 协议 | Agent Card + Task 委托 | MCP 是水管，A2A 是快递员 |
| W3 | Supervisor 模式 | 分解→并行执行→聚合 | 一个领导 + N 个工人 |
| W4 | 架构选型 + MCP | 五维评估 + MCP Server | 什么时候用大脑，什么时候用水管 |

### 选型口诀

```
简单查数据     → MCP Tool
固定多步骤     → Workflow / Chain
需要推理+工具  → Single Agent + MCP
复杂多任务     → Multi Agent + MCP
跨系统通信     → A2A
```

## 扩展思考

- **真实 MCP Server**：代码中是模拟实现，真实 MCP 基于 JSON-RPC 2.0 over stdio/SSE，可参考 [MCP 官方规范](https://modelcontextprotocol.io)
- **LLM Function Calling**：`OrderAgent` 用规则匹配路由，升级为 LLM Function Calling 后就能处理自然语言模糊请求
- **多 MCP Server 协作**：一个 Agent 可以同时连接多个 MCP Server（订单、库存、物流），实现跨系统查询
- **安全与鉴权**：生产环境的 MCP Server 需要认证、限流、日志审计

> 这些就是真正生产级系统要面对的问题——也是你下一步实战的方向。
