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
