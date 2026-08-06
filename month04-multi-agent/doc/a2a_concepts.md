# A2A 协议：Agent 间通信的标准

## 一句话理解

**Agent-to-Agent (A2A)** 是让不同 Agent **互相发现、委托任务、交换结果**的开放标准——就像 HTTP 让不同网站互通一样，A2A 让不同框架构建的 Agent 能协作。

> 类比：HTTP 对 Web 服务通信 = A2A 对 Agent 间通信。MCP 解决"Agent 怎么调工具"，A2A 解决"Agent 怎么找另一个 Agent 帮忙"。

## 为什么需要 A2A？

现实中 Agent 生态是碎片化的：
- LangGraph 构建的 Agent 和 CrewAI 构建的 Agent 无法直接对话
- 公司内部不同团队各做各的 Agent，互相不知道对方能干什么

A2A 解决的就是**标准化通信**问题：

| | 没有 A2A | 有 A2A |
|---|---------|--------|
| 发现 | 人工对接，口头约定 | Agent Card 自动发现 |
| 通信 | 自定义协议，各不兼容 | 统一 JSON-RPC 2.0 |
| 扩展 | 加一个 Agent 要改所有调用方 | 注册 Agent Card 即可被发现 |

## A2A vs MCP

| | MCP | A2A |
|---|---|---|
| 谁跟谁 | Agent ↔ Tool | Agent ↔ Agent |
| 解决的问题 | 一个 Agent 怎么调用工具 | 多个 Agent 怎么协作 |
| 类比 | USB 协议（设备连接） | TCP/IP（网络通信） |
| 粒度 | 单次函数调用 | 完整任务委托 |
| 状态 | 无状态 | 有状态（Task 生命周期） |

**它们是互补的，不是竞争关系。** MCP 是水管（连接工具），A2A 是快递员（跨 Agent 传递任务）。

## 架构总览

```
Client Agent（发起方）
    │
    ├─ 1. 查看 AgentRegistry → 发现可用 Agent
    ├─ 2. 根据 AgentCard 选择最合适的 Agent
    ├─ 3. 创建 Task → 委托给 Remote Agent
    ├─ 4. Remote Agent 执行 → Task 状态变更
    └─ 5. 获取 Task.result → 返回给用户
```

## 核心概念详解

### 1. Agent Card（数字名片）

Agent 对外公开的 JSON 文档，声明身份、能力、端点。客户端解析 Card 来判断：这个 Agent 能干什么？怎么联系它？

```python
@dataclass
class AgentCard:
    name: str              # Agent 名称
    description: str       # 能力描述
    endpoint: str          # 通信端点
    skills: list[AgentSkill]  # 技能列表
```

> 类比：公司的黄页——名称、主营业务、联系电话，一目了然。

### 2. AgentRegistry（注册中心）

所有 Agent Card 的管理器，客户端通过 Registry 发现可用 Agent。

```python
class AgentRegistry:
    def register(card)          # 注册一个 Agent
    def discover(query) -> list # 根据需求搜索匹配的 Agent
```

> 类比：DNS 服务器——你输入域名，它返回 IP 地址。Registry 接收需求描述，返回匹配的 Agent。

### 3. Task（任务）

有状态的、有唯一 ID 的工作单元。有完整的生命周期：

```
submitted → working → completed  （成功）
                    → failed     （失败）
                    → canceled   （取消）
```

```python
@dataclass
class Task:
    id: str                    # 唯一标识
    status: TaskStatus         # 当前状态
    description: str           # 任务描述
    result: Optional[str]      # 执行结果
```

> 类比：快递单——有单号、有状态（已揽收→运输中→已签收），可以随时查询。

### 4. Message / Part / Artifact

| 概念 | 说明 | 类比 |
|------|------|------|
| Message | 单轮通信单元（包含 role 和 messageId） | 一封邮件 |
| Part | Message 的基本内容单元（text/file/data） | 邮件里的附件 |
| Artifact | Agent 完成任务后的具体成果 | 快递包裹里的商品 |

### 5. 交互模式

| 模式 | 说明 | 适用场景 |
|------|------|---------|
| Polling | 客户端发请求，轮询查状态 | 短任务 |
| SSE 流式 | 实时接收增量结果 | 长文本生成 |
| Webhook 推送 | 服务端主动通知 | 异步长任务 |

## 关键设计决策

### Q: 为什么用规则匹配而不是 LLM 选 Agent？

Agent Discovery（发现）应该是**确定性的**——看 AgentCard 的技能描述是否匹配需求。LLM 在这里会引入不必要的延迟和不确定性。

代码中用关键词匹配 + 评分排序：

```python
def select_agent(query, registry):
    candidates = registry.discover(query)  # 关键词匹配
    best = max(candidates, key=lambda c: c.score_relevance(query))
    return best
```

> 教训：Week 2 开发时发现 LLM 做路由会跳过工具调用、直接用自己的知识回答。路由决策应该是确定性的。

### Q: 为什么不用官方 A2A SDK？

Week 2 的重点是**理解设计思想**，不是调 API。用熟悉的工具链（dataclass + asyncio + Agents SDK）模拟核心概念，理解更深入。

### Q: A2A 的设计哲学是什么？

1. **黑盒原则**：Agent 之间不需要知道对方的内部实现
2. **协商式**：先看 Agent Card 再决定是否委托
3. **标准化但不绑定框架**：LangGraph、CrewAI、自定义都能用
4. **安全优先**：认证通过标准 HTTP header，与协议消息分离

## 代码结构

```
src/week2/
└── a2a_simulator.py    # 完整实现，约 588 行
```

### 代码分层

```
第 1 层：Agent Card + 注册中心
  ├── AgentSkill              # 技能定义（名称、描述、关键词）
  ├── AgentCard               # 数字名片（身份、技能、端点）
  └── AgentRegistry           # 注册中心（注册、发现、评分）

第 2 层：Task 生命周期
  ├── TaskStatus              # 状态枚举（submitted→working→completed/failed）
  ├── Task                    # 任务对象（ID、状态、结果）
  └── TaskManager             # 任务管理器（创建、更新、查询）

第 3 层：Agent 定义 + 工具
  ├── search_knowledge()      # 知识库搜索
  ├── calculate_math()        # 数学计算
  └── 4 个 Remote Agent       # Search/Writer/Math/Analyst

第 4 层：委托流程
  ├── delegate()              # 核心委托（类比 tasks/send）
  ├── select_agent()          # 规则匹配选 Agent
  └── run_delegation()        # 完整流程（发现→委托→执行→返回）

第 5 层：用户接口
  ├── interactive_mode()      # 交互模式
  └── run_tests()             # 5 个测试用例
```

## 运行方式

```bash
# 交互模式：输入需求，自动发现并委托给最合适的 Agent
python src/week2/a2a_simulator.py

# 单次委托
python src/week2/a2a_simulator.py --task "搜索 A2A 协议的知识"

# 运行测试：执行 5 个预设测试用例
python src/week2/a2a_simulator.py --test
```

## 测试用例

| # | 需求 | 委托给 | 验证点 |
|---|------|--------|--------|
| 1 | 搜索 A2A 协议的知识 | SearchAgent | 关键词匹配到搜索技能 |
| 2 | 写 AI Agent 文章 | WriterAgent | 关键词匹配到写作技能 |
| 3 | 计算 1234×5678 | MathAgent | 关键词匹配到计算技能 |
| 4 | 对比 AI vs Multi-Agent | AnalystAgent | 关键词匹配到分析技能 |
| 5 | 搜索 Python 并写总结 | WriterAgent | 多关键词匹配，选最高分 |

## 本周学习目标

1. **理解** A2A 协议解决什么问题（跨框架、跨厂商的 Agent 通信标准）
2. **掌握** Agent Card 的作用：声明身份和能力，支持自动发现
3. **理解** Task 生命周期：submitted → working → completed/failed
4. **掌握** 完整委托流程：发现 → 选择 → 委托 → 执行 → 返回
5. **理解** A2A 与 MCP 的互补关系（Agent↔Tool vs Agent↔Agent）

## 扩展思考

- **多 Agent 协作**：如果一个任务需要多个 Agent 先后完成怎么办？（提示：Week 3 Supervisor 分解后逐个委托）
- **流式传输**：长任务能不能边做边返回结果？（SSE 模式）
- **安全认证**：跨组织委托时怎么验证身份？（OAuth 2.0 + Agent Card 的 securitySchemes）
- **动态注册**：Agent 能不能运行时动态上线/下线？

> 这些就是 Week 3 Supervisor 模式和 Week 4 架构选型要解决的问题。
# A2A 协议核心概念

## A2A 是什么？

**Agent-to-Agent (A2A)** 是 Google 主导、Linux Foundation 维护的**开放标准**，
让不同框架、不同厂商构建的 Agent 能够**互相发现、委托任务、交换结果**。

一句话：A2A 对 Agent 间通信 = HTTP 对 Web 服务通信。

## A2A vs MCP

| | MCP | A2A |
|---|---|---|
| 谁跟谁 | Agent ↔ Tool | Agent ↔ Agent |
| 解决的问题 | 一个 Agent 怎么调用工具 | 多个 Agent 怎么协作 |
| 类比 | USB 协议（设备连接） | TCP/IP（网络通信） |
| 使用场景 | 连接数据库、API、文件系统 | 跨团队/跨服务 Agent 协作 |

**它们是互补的，不是竞争关系。**

## 核心概念

### 1. Agent Card（数字名片）
- JSON 文档，描述 Agent 的身份、能力、端点、技能、认证要求
- 客户端解析 Card 来判断：这个 Agent 能干什么？怎么联系它？

```json
{
  "name": "知识搜索 Agent",
  "description": "提供企业内部知识库搜索",
  "url": "https://kb-agent.company.com",
  "skills": [
    {"name": "搜索文档", "description": "...", "examples": ["..."]}
  ]
}
```

### 2. Task（任务）
- 有状态的、有唯一 ID 的工作单元
- 有生命周期：submitted → working → completed/failed/canceled
- 支持长任务，客户端可以轮询状态

### 3. Message（消息）
- 单轮通信单元
- 包含 role（"user" / "agent"）和 messageId
- 由多个 Part 组成

### 4. Part（内容容器）
- 一条 Message 或 Artifact 的基本内容单元
- 可以是 text / file / url / structured data
- 格式灵活：文本、图片、JSON、二进制都可以

### 5. Artifact（产出物）
- Agent 完成任务后产生的**具体成果**
- 比如：一份生成的文档、一张分析图、一段代码
- 有 artifactId、name、一个或多个 Part

## 交互模式

1. **请求/响应（Polling）**：客户端发请求，服务端返回。长任务靠轮询。
2. **流式（SSE）**：实时接收增量结果
3. **推送通知（Webhook）**：服务端主动通知客户端

## A2A 的设计哲学

1. **黑盒原则**：Agent 之间不需要知道对方的内部实现
2. **协商式**：先看 Agent Card 再决定是否委托
3. **标准化但不绑定框架**：LangGraph、CrewAI、自定义都能用
4. **安全优先**：认证通过标准 HTTP header，与协议消息分离

## 本周学习目标

用我们熟悉的 Python + Agents SDK 模拟 A2A 的 3 个核心概念：

1. **Agent Card**：用 dataclass 定义可发现的 Agent 能力
2. **Task**：实现任务生命周期管理（创建→执行→完成/失败）
3. **委托**：Client Agent 发现 Remote Agent 并委托任务

> 注：不用官方 SDK（太早引入会掩盖核心概念），用我们已有工具链模拟，
> 重点是理解"为什么"和"怎么设计"，而非"怎么调 API"
