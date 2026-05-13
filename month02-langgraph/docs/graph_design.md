# Graph 设计笔记：LangGraph vs Agents SDK

> 从 month01（Agents SDK）到 month02（LangGraph）的思维方式转变

---

## 核心差异

### Agents SDK 思维（month01）
```
Agent + Instructions + Tools → LLM 自动决定调用哪个 tool
```
- 你告诉 LLM "你有一个客服助手，可以用这些工具"
- LLM 自己判断用户意图，选择调用哪个 tool
- 流程是 **隐式的**，由 LLM 控制

### LangGraph 思维（month02）
```
State + Nodes + Edges → 你显式定义每一步做什么
```
- 你定义状态 schema、每个节点做什么、条件边怎么路由
- 意图识别也是你写的一个节点
- 流程是 **显式的**，由你控制

---

## 对比表

| 维度 | Agents SDK (Tool 模式) | LangGraph (StateGraph) |
|------|----------------------|----------------------|
| 控制权 | LLM 决定流程 | 你定义流程 |
| 意图识别 | 隐式（通过 tool 描述） | 显式（独立节点） |
| 调试难度 | 难以追踪为什么选了这个 tool | 可以精确看到经过哪些节点 |
| 稳定性 | 受 LLM 随机性影响 | 规则部分确定性更强 |
| 灵活性 | 适合开放域对话 | 适合结构化流程 |
| Token 消耗 | 每次都要传所有 tool 描述 | 只走需要的节点 |

---

## LangGraph 核心概念

### 1. State（状态）
- 相当于 graph 的"记忆"，所有节点共享
- 用 TypedDict 定义 schema
- 每个节点返回 dict，只更新需要修改的字段

### 2. Node（节点）
- 一个纯函数：接收 state → 返回更新
- 可以做：分析、查询、格式化、调 API...
- 节点之间通过 state 传递数据

### 3. Edge（边）
- **普通边**：`add_edge("A", "B")` → A 执行完必走 B
- **条件边**：`add_conditional_edges("A", route_fn)` → 根据返回值决定走哪条

### 4. Graph 编译
- `graph.compile()` → 得到可运行的 app
- `app.invoke(initial_state)` → 从入口跑到 END

---

## 本次实践：电商客服 Graph 化

### month01 的方式
```python
agent = Agent(
    instructions="你是电商客服...",
    tools=[query_order, query_refund, query_logistics, ...]
)
# LLM 自动选择哪个 tool
```
**问题**：Week 3 测试发现一致率只有 70%，LLM 有时候选错 tool。

### month02 的方式
```python
graph = StateGraph(SupportState)
graph.add_node("intent_router", intent_router)
graph.add_node("order_query", order_query_node)
graph.add_node("refund", refund_node)
# ...
graph.add_conditional_edges("intent_router", route_by_intent, {...})
```
**优势**：意图识别是显式节点，路由逻辑可控，不会"随机"选错。

### Graph 流程图
```
__start__
    ↓
intent_router (分析意图 + 提取参数)
    ↓
[条件边] → order_query / refund / logistics / coupon / product / escalate / greeting
    ↓
summarize (汇总输出)
    ↓
__end__
```

---

## 关键领悟

1. **Graph 思维 = 显式流程设计**
   - 不是"告诉 LLM 你能做什么"
   - 而是"设计好每一步，让 LLM 在特定节点发挥"

2. **意图识别节点化**
   - Agents SDK 里，意图识别混在 LLM 的 tool 选择中
   - LangGraph 里，意图识别是一个独立节点，可以替换为 LLM 或规则

3. **条件边 = 路由表**
   - `route_by_intent()` 函数就是路由表
   - 返回哪个字符串就走对应的节点
   - 比 LLM 的隐式选择更可控

4. **State 是共享上下文**
   - 每个节点读写同一个 state
   - 节点之间不需要直接传参
   - 天然支持"时间旅行"（后续 Week 2 学）

---

## 待深入

- Week 2 学 Checkpoint：状态持久化、断点恢复
- Week 2 学 Human-in-the-loop：人工审核节点
- Week 3 学 Subgraph：把 order_query 和 refund 拆成子图
- Week 4 做对比实验：同一需求分别用 Tool 模式和 Graph 模式实现
