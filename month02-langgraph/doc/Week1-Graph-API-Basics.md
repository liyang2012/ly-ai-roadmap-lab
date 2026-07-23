# 📘 Week 1 详解 - Graph API 入门：从零构建你的第一个 Graph

> **适合人群**：完全没接触过 LangGraph 的新手
> **前置知识**：会 Python 基础（函数、字典）即可
> **预计时间**：1-1.5 小时

---

## 🎯 学习目标

学完 Week 1，你将掌握：

1. ✅ **LangGraph 是什么** — 和 Agents SDK 有什么不同
2. ✅ **四大核心组件** — State、Node、Edge、Compile
3. ✅ **构建简单 Graph** — 3 个节点的线性流程
4. ✅ **条件路由** — 根据意图走不同分支
5. ✅ **实战电商客服** — 8 个业务节点 + 条件分支

---

## 📚 一、LangGraph 到底是什么？

### 一句话解释

> LangGraph 是一个**画流程图并让程序按流程跑**的框架。你定义"先做什么、再做什么、什么情况下走哪条路"，程序就严格按照你的设计执行。

### 生活类比：银行的自动取号机

想象你去银行办业务：

```
你走进银行
    ↓
取号机问你："办什么业务？"（意图识别）
    ↓
你按了"存款"按钮
    ↓
系统分配你到"存款窗口"（路由）
    ↓
柜员按固定流程帮你存款（执行业务逻辑）
    ↓
办完了，给你回执（输出结果）
```

LangGraph 做的事情就是**把这个流程用代码写出来**。每一步是一个"节点"，步骤之间的连接是"边"。

### 和 Agents SDK 有什么不同？

在 Month 1 中，我们学了 OpenAI Agents SDK。两者的核心区别：

| 维度 | Agents SDK（Month 1） | LangGraph（Month 2） |
|------|----------------------|----------------------|
| **谁控制流程** | LLM 自己决定 | **你**定义流程 |
| **意图识别** | LLM 隐式判断（你看不见过程） | 你写一个专门的节点来判断 |
| **调试难度** | 很难知道 LLM 为什么选了这个工具 | 能精确看到经过了哪些节点 |
| **稳定性** | 受 LLM 随机性影响 | 规则部分每次结果一样 |
| **Token 消耗** | 每次都要传所有工具描述 | 只执行需要的节点 |

**类比**：
- **Agents SDK** = 你雇了一个聪明的实习生，告诉他"你有这些工具可以用"，他自己判断用哪个。有时候他会判断错。
- **LangGraph** = 你自己设计了一套 SOP（标准操作流程），每个人按流程办事，不会出错。

---

## 📖 二、四大核心组件

LangGraph 有四个最基本的概念，搞懂它们就能写任何 Graph。

### 1. State（状态）= 流程中的"共享记事本"

> State 是一个所有节点都能看到的"记事本"。每个节点可以从记事本读信息，也可以往里面写信息。

```python
from typing import TypedDict

class SimpleState(TypedDict):
    question: str      # 用户的问题
    step: int          # 当前执行到第几步
    answer: str        # 最终答案
    messages: list[str]  # 日志消息
```

**小白须知**：
- `TypedDict` 就是"规定了字段名和类型的字典"
- 你可以把它理解为一个**表格**，每列有固定名字
- 每个节点都能读这个表格，也能修改里面的某些列

**关键规则**：节点返回的 dict 只更新需要修改的字段，没返回的字段保持原值。

```python
# 假设当前 state 是：
# {"question": "你好", "step": 0, "answer": "", "messages": []}

# 节点返回：
return {"step": 1, "messages": ["分析完成"]}

# 更新后的 state 变成：
# {"question": "你好", "step": 1, "answer": "", "messages": ["分析完成"]}
#                 ↑ 没变              ↑ 没变              ↑ 被更新了
```

### 2. Node（节点）= 一个干活的"工人"

> 节点就是一个 Python 函数。它读取 State，做点事情，然后返回要更新的字段。

```python
def analyze_node(state: SimpleState) -> dict:
    """分析用户问题是什么类型"""
    q = state["question"].lower()

    if "多少" in q or "计算" in q:
        category = "math"
    elif "代码" in q:
        category = "code"
    else:
        category = "general"

    return {
        "step": 1,
        "messages": [f"分析完成，类型：{category}"],
    }
```

**小白须知**：
- 函数名随意，但要有意义（如 `analyze_node`、`process_node`）
- 参数必须是 `state`（完整的 State 字典）
- 返回值是一个 `dict`，只包含你要更新的字段
- 节点是**纯函数**：只依赖 State，不依赖外部变量（数据库等除外）

### 3. Edge（边）= 节点之间的"箭头"

边决定了执行顺序。有两种：

**普通边**：A 执行完**一定**走 B

```python
graph.add_edge("analyze", "process")
# analyze 执行完 → 必定走 process
```

**条件边**：A 执行完，**根据条件**走不同的节点

```python
graph.add_conditional_edges(
    "router",          # 从哪个节点出发
    route_function,    # 路由函数（返回字符串决定走哪条路）
    {
        "branch_a": "node_a",  # 返回 "branch_a" → 走 node_a
        "branch_b": "node_b",  # 返回 "branch_b" → 走 node_b
    }
)
```

**生活类比**：
- 普通边 = 高速公路，只有一条路，一直走
- 条件边 = 岔路口，根据路牌（路由函数的返回值）选择走哪条

### 4. Compile（编译）= 把蓝图变成可运行的程序

```python
# 1. 创建蓝图
graph = StateGraph(SimpleState)

# 2. 添加节点和边
graph.add_node("analyze", analyze_node)
graph.add_node("process", process_node)
graph.set_entry_point("analyze")
graph.add_edge("analyze", "process")
graph.add_edge("process", END)

# 3. 编译 — 从蓝图变成可运行的 app
app = graph.compile()

# 4. 运行
result = app.invoke({"question": "你好", "step": 0, "answer": "", "messages": []})
```

**小白须知**：
- `StateGraph` 是"蓝图"，不能直接运行
- `compile()` 后才变成可以 `invoke` 的 app
- `END` 是 LangGraph 内置的"结束标记"，走到 END 就停了
- `set_entry_point` 告诉程序"从哪个节点开始"

---

## 💻 三、实战 1：简单线性 Graph

**文件**：`src/week1/simple_graph.py`

这个 demo 有 3 个节点，一条直线走到底：

```
__start__ → analyze → process → format → __end__
```

### 完整执行过程图解

```
用户输入："15 加 27 等于多少"

[analyze 节点]
    输入 state: {question: "15 加 27 等于多少", step: 0, answer: "", messages: ["开始处理"]}
    做什么：分析问题类型 → "math"
    输出 state: {step: 1, messages: ["开始处理", "分析完成，类型：math"]}
        ↓
[process 节点]
    输入 state: {question: "15 加 27 等于多少", step: 1, answer: "", messages: [...]}
    做什么：提取数字 15 和 27，计算 15+27=42
    输出 state: {step: 2, answer: "15 加 27 等于多少 = 42", messages: [..., "处理完成"]}
        ↓
[format 节点]
    输入 state: {question: "15 加 27 等于多少", step: 2, answer: "15 加 27 等于多少 = 42"}
    做什么：把结果格式化为好看的样子
    输出 state: {step: 3, answer: "─── 回答 ───\n15 加 27 等于多少 = 42\n─── 流程 ───\n..."}
        ↓
[END] 结束
```

### 如何运行

```bash
cd month02-langgraph/src/week1
python simple_graph.py
```

---

## 💻 四、实战 2：电商客服 Graph（条件路由）

**文件**：`src/week1/customer_support_graph.py`

这个 demo 把 Month 1 的电商客服 Agent 翻译成了 LangGraph 版本。

### 流程图

```
__start__
    ↓
intent_router（分析用户意图 + 提取订单号等信息）
    ↓
[条件路由] ─┬─ order_query  → 查订单
            ├─ refund       → 查退款政策
            ├─ logistics    → 查物流
            ├─ coupon       → 查优惠券
            ├─ product      → 查产品
            ├─ escalate     → 转人工
            └─ greeting     → 问候
    ↓
summarize（汇总流程日志，格式化输出）
    ↓
__end__
```

### 意图分类的 7 种类型

| 意图 | 关键词 | 对应节点 | 举例 |
|------|--------|----------|------|
| `escalate` | 投诉、举报、转人工 | `escalate_node` | "我要投诉！转人工！" |
| `logistics` | 物流、快递、到哪了 | `logistics_node` | "帮我查一下物流 SF1234567890" |
| `refund` | 退款、退货、退钱 | `refund_node` | "退款需要什么条件？" |
| `coupon` | 优惠、券、折扣 | `coupon_node` | "USER001 有哪些优惠券？" |
| `product` | 保修、介绍、多少钱 | `product_node` | "iPhone 15 Pro 多少钱？" |
| `order_query` | 订单、状态、发货了吗 | `order_query_node` | "查一下订单 ORD... 的状态" |
| `greeting` | 其他 | `greeting_node` | "你好" |

### 条件路由代码详解

```python
def route_by_intent(state: SupportState) -> str:
    """
    这个函数就像一个"路牌"：
    - 读取 state 里的 intent（意图）
    - 返回一个字符串，告诉 Graph 下一步走哪个节点
    """
    mapping = {
        "order_query": "order_query",   # intent 是 order_query → 走 order_query 节点
        "refund": "refund",             # intent 是 refund → 走 refund 节点
        "logistics": "logistics",       # ...
        "coupon": "coupon",
        "product": "product",
        "escalate": "escalate",
        "greeting": "greeting",
    }
    return mapping.get(state["intent"], "greeting")
    # 如果 intent 不在映射表里，默认走 greeting
```

然后把这个函数注册到 Graph 中：

```python
graph.add_conditional_edges(
    "intent_router",     # 从 intent_router 节点出发
    route_by_intent,     # 用这个函数决定走哪条路
    {                    # 映射表：函数返回值 → 节点名
        "order_query": "order_query",
        "refund": "refund",
        # ... 省略
    },
)
```

### 关键踩坑：意图优先级

**Bug**：输入"查物流"被误识别为"查订单"

**原因**：关键词匹配有重叠（"包裹"在 order 和 logistics 都可能出现）

**修复**：越具体的意图越先判断

```python
def classify_intent(user_input: str) -> str:
    q = user_input.lower()

    # 越具体的越先判断！
    if any(k in q for k in ["投诉", "举报", "转人工"]):
        return "escalate"        # 投诉最优先
    if any(k in q for k in ["物流", "快递", "到哪了"]):
        return "logistics"       # 物流第二
    if any(k in q for k in ["退款", "退货"]):
        return "refund"          # 退款第三
    # ... order_query 放后面
    return "greeting"            # 兜底
```

**为什么顺序重要？** 因为 `if-elif` 链是**从上到下匹配**的，匹配到就立即返回，后面的不会再检查。

### 如何运行

```bash
cd month02-langgraph/src/week1
python customer_support_graph.py
```

---

## 🔑 五、关键概念速查表

### API 速查

```python
from langgraph.graph import StateGraph, END
from typing import TypedDict

# 1. 定义 State
class MyState(TypedDict):
    field1: str
    field2: int
    history: list[str]

# 2. 定义节点
def my_node(state: MyState) -> dict:
    return {"field1": "new value", "history": state["history"] + ["done"]}

# 3. 构建 Graph
graph = StateGraph(MyState)
graph.add_node("my_node", my_node)
graph.set_entry_point("my_node")
graph.add_edge("my_node", END)

# 4. 条件路由
graph.add_conditional_edges("router", route_fn, {
    "branch_a": "node_a",
    "branch_b": "node_b",
})

# 5. 编译运行
app = graph.compile()
result = app.invoke({"field1": "initial", "field2": 0, "history": []})

# 6. 查看 graph 结构（Mermaid 格式）
print(app.get_graph().draw_mermaid())
```

### 信息提取正则速查

```python
import re

# 订单号：ORD 开头 + 数字
re.search(r"ORD\d+", "查订单 ORD20260417001")  # → "ORD20260417001"

# 物流单号：SF 或 JD 开头 + 数字
re.search(r"(SF|JD)\d+", "物流 SF1234567890")  # → "SF1234567890"

# 用户 ID：USER 开头 + 数字
re.search(r"USER\d+", "用户 USER001")  # → "USER001"
```

---

## 🧠 六、与 Month 1 的对比总结

| 问题 | Month 1 (Agents SDK) | Month 2 (LangGraph) |
|------|---------------------|---------------------|
| 订单查询一致率 | 70%（LLM 偶尔选错 tool） | 100%（显式路由） |
| 调试难度 | 需要分析 trace 数据 | 看 history 日志即可 |
| Token 消耗 | 每次传 7 个 tool 描述 | 只执行对应节点，0 Token |
| 意图识别 | 隐式在 LLM 内部 | 显式节点，可替换为 LLM |
| 扩展新意图 | 加 tool + 改 instructions | 加节点 + 改路由映射 |

**核心领悟**：
> Graph 思维 = 显式流程设计。不是"告诉 LLM 你能做什么"，而是"设计好每一步，让 LLM 在特定节点发挥"。

---

## 📝 七、学习建议

### 推荐学习步骤

1. **先运行** `simple_graph.py`，看输出理解线性流程
2. **再运行** `customer_support_graph.py`，测试 8 个用例
3. **修改关键词**，观察意图路由如何变化
4. **添加新节点**（比如"售后维修"），练习扩展 Graph

### 常见错误

| 错误 | 原因 | 解决 |
|------|------|------|
| `KeyError: 'xxx'` | State 里没声明这个字段 | 在 TypedDict 中添加字段 |
| 节点没执行 | 没设置 entry_point 或边没连 | 检查 `set_entry_point` 和 `add_edge` |
| 意图识别不对 | 关键词优先级顺序问题 | 调整 if-elif 链的顺序 |

---

> 💡 **记住**：LangGraph 的核心就三个词 — **State 是共享的记事本，Node 是干活的工人，Edge 是工人之间的传话规则**。
