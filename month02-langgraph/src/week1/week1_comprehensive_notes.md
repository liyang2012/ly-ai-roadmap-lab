# 📚 第 2 月 - Week 1：Graph API 入门 — 综合笔记

> 学习日期：2026-05-11 至 2026-05-17
> 代码位置：`month02-langgraph/src/week1/`

---

## 一、核心概念速览

### LangGraph 的本质

```
State + Nodes + Edges → 你显式定义每一步做什么
```

对比 Agents SDK：
```
Agent + Instructions + Tools → LLM 自动决定调用哪个 tool
```

| 维度 | Agents SDK | LangGraph |
|------|-----------|-----------|
| 控制权 | LLM 决定流程 | 你定义流程 |
| 意图识别 | 隐式（通过 tool 描述） | 显式（独立节点） |
| 调试 | 难以追踪为什么选了这个 tool | 精确看到经过哪些节点 |
| 稳定性 | 受 LLM 随机性影响（Week 3 测试 70% 一致率） | 规则部分确定性更强 |
| Token 消耗 | 每次传所有 tool 描述 | 只走需要的节点 |

### 四大核心组件

**1. State（TypedDict）**
- 所有节点共享的"记忆"
- 每个节点返回 dict，只更新需要修改的字段

**2. Node（纯函数）**
- 接收 state → 返回更新
- 可以做：分析、查询、格式化、调 API...

**3. Edge（边）**
- 普通边：`add_edge("A", "B")` → A 执行完必走 B
- 条件边：`add_conditional_edges("A", route_fn)` → 根据返回值决定走哪条

**4. Compile**
- `graph.compile()` → 得到可运行的 app
- `app.invoke(initial_state)` → 从入口跑到 END

---

## 二、代码实战解析

### Demo 1：简单线性 Graph（simple_graph.py）

**3 个节点：analyze → process → format → END**

```python
from langgraph.graph import StateGraph, END
from typing import TypedDict

# 1. 定义 State
class SimpleState(TypedDict):
    question: str
    step: int
    answer: str
    messages: list[str]

# 2. 定义节点
def analyze_node(state: SimpleState) -> dict:
    q = state["question"].lower()
    if any(k in q for k in ["多少", "计算", "求"]):
        category = "math"
    elif any(k in q for k in ["代码", "python", "写"]):
        category = "code"
    else:
        category = "general"
    return {"step": 1, "messages": [f"分析完成：{category}"]}

def process_node(state: SimpleState) -> dict:
    # 根据问题类型处理
    return {"step": 2, "answer": "处理结果"}

def format_node(state: SimpleState) -> dict:
    return {"step": 3, "answer": f"格式化输出：{state['answer']}"}

# 3. 构建 Graph
graph = StateGraph(SimpleState)
graph.add_node("analyze", analyze_node)
graph.add_node("process", process_node)
graph.add_node("format", format_node)
graph.set_entry_point("analyze")
graph.add_edge("analyze", "process")
graph.add_edge("process", "format")
graph.add_edge("format", END)

# 4. 编译运行
app = graph.compile()
result = app.invoke({"question": "15 加 27 等于多少", "step": 0, "answer": "", "messages": []})
```

**关键理解**：
- 节点是 **纯函数**，接收完整 state，返回 **部分更新**
- 没返回的字段自动保留原值
- `step` 字段追踪执行进度（调试用）

---

### Demo 2：电商客服 Graph（customer_support_graph.py）

**8 个业务节点 + 1 个条件路由 + 1 个汇总**

```
__start__ → intent_router → [条件路由] → 业务节点 → summarize → __end__
```

**意图分类（7 种）**：
| 意图 | 关键词 | 对应节点 |
|------|--------|----------|
| order_query | 订单、状态、发货了吗 | order_query_node |
| refund | 退款、退货、退钱 | refund_node |
| logistics | 物流、快递、到哪了 | logistics_node |
| coupon | 优惠、券、折扣 | coupon_node |
| product | 保修、介绍、多少钱 | product_node |
| escalate | 投诉、举报、转人工 | escalate_node |
| greeting | 其他 | greeting_node |

**条件路由代码**：
```python
def route_by_intent(state: SupportState) -> str:
    mapping = {
        "order_query": "order_query",
        "refund": "refund",
        "logistics": "logistics",
        "coupon": "coupon",
        "product": "product",
        "escalate": "escalate",
        "greeting": "greeting",
    }
    return mapping.get(state["intent"], "greeting")

graph.add_conditional_edges("intent_router", route_by_intent, mapping)
```

**测试 8 个用例全部通过** ✅

---

## 三、关键踩坑与设计经验

### 1. 意图分类优先级
**Bug 现象**："查物流"被误识别为"查订单"

**原因**：关键词匹配有重叠（"包裹"在 order 和 logistics 都可能出现）

**修复**：越具体的意图越先判断，`escalate` > `logistics` > `refund` > `coupon` > `product` > `order_query` > `greeting`

```python
def classify_intent(user_input: str) -> str:
    q = user_input.lower()
    if any(k in q for k in ["投诉", "举报", "太差", "转人工"]):
        return "escalate"
    if any(k in q for k in ["物流", "快递", "到哪了", "包裹"]):
        return "logistics"  # 先匹配
    # ... order_query 放后面
```

### 2. 信息提取
**订单号**：正则 `ORD\d+`
**物流单号**：正则 `(SF|JD)\d+`
**用户 ID**：正则 `USER\d+`，默认 `USER001`

### 3. State 设计原则
- 只存必要字段（最小化）
- `history` 用 list 记录流程日志（调试神器）
- 节点返回 dict 只更新需要修改的字段

---

## 四、与 Month 1 的对比总结

| 问题 | Month 1 (Agents SDK) | Month 2 (LangGraph) |
|------|---------------------|---------------------|
| 订单查询一致率 | 70%（LLM 偶尔选错 tool） | 100%（显式路由） |
| 调试难度 | 需要分析 trace 数据 | 看 history 日志即可 |
| Token 消耗 | 每次传 7 个 tool 描述 | 只执行对应节点 |
| 意图识别 | 隐式在 LLM 内部 | 显式节点，可替换为 LLM |
| 扩展新意图 | 加 tool + 改 instructions | 加节点 + 改路由映射 |

**核心领悟**：
> Graph 思维 = 显式流程设计，不是"告诉 LLM 你能做什么"，而是"设计好每一步，让 LLM 在特定节点发挥"。

---

## 五、API 速查表

```python
# 导入
from langgraph.graph import StateGraph, END
from typing import TypedDict

# 定义 State
class MyState(TypedDict):
    field1: str
    field2: int
    history: list[str]

# 定义节点
def my_node(state: MyState) -> dict:
    return {"field1": "new value", "history": state["history"] + ["done"]}

# 构建 Graph
graph = StateGraph(MyState)
graph.add_node("my_node", my_node)
graph.set_entry_point("my_node")
graph.add_edge("my_node", END)

# 条件路由
graph.add_conditional_edges("router", route_fn, {"branch_a": "node_a", "branch_b": "node_b"})

# 编译运行
app = graph.compile()
result = app.invoke({"field1": "initial", "field2": 0, "history": []})

# 查看 graph 结构（Mermaid 格式）
print(app.get_graph().draw_mermaid())
```

---

## 六、学习路径回顾

```
Week 1: Graph API 入门 ✅
  ├── Day 1-2: 简单线性 graph（3 节点）
  ├── Day 3-4: 客服 graph（8 节点 + 条件路由）
  └── Day 5-6: 测试优化 + 思维对比笔记

Week 2: Persistence / Checkpoints ✅
  ├── Day 1: MemorySaver + Thread ID + Time Travel
  ├── Day 2: Human-in-the-Loop + 多步骤审批流
  └── Day 3: API 兼容性 bug 修复（3 个文件全通）

Week 3: Subgraph 与模块化 ⬜ 下一步
Week 4: Workflow vs Agent 选型对比 ⬜
```
