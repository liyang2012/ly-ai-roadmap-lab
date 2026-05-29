# 🧩 Week 3 详解 - Subgraph 与模块化设计

> **小白必看**：本文档用通俗的方式讲解 LangGraph 的子图（Subgraph）概念，帮你理解为什么需要拆分、如何拆分、以及常见的坑

---

## 🎯 学习目标

学完 Week 3，你将掌握：

1. ✅ **为什么要拆子图** - 从"大杂烩"到"模块化"
2. ✅ **Subgraph 概念** - 把 graph 当节点用
3. ✅ **State 共享机制** - 主图和子图如何通信
4. ✅ **三种架构模式** - 扁平、适配器、隔离
5. ✅ **实战实现** - 订单子图 + FAQ 子图 + 主图编排
6. ✅ **避坑指南** - 常见错误和解决方案

---

## 📚 核心概念

### 什么是 Subgraph？

**一句话理解**：把一个编译好的 graph 当作节点，添加到另一个 graph 中。

#### 生活类比

**场景 1：公司组织架构**

```
❌ 小作坊（Week 1-2）：
老板一个人：接单、做产品、发货、客服、财务...
问题：太忙、容易出错、无法扩展

✅ 公司化运营（Week 3）：
CEO（主图）：只负责战略决策和资源分配
    ├─ 订单部（订单子图）：处理所有订单相关
    ├─ 客服部（FAQ 子图）：处理所有咨询问题
    └─ 财务部（财务子图）：处理所有财务问题

好处：
- 各部门可以独立工作
- CEO 只做决策，不干活
- 可以单独考核每个部门
```

**场景 2：餐厅后厨**

```
❌ 小餐厅：
一个厨师：切菜、炒菜、摆盘、洗碗...

✅ 大餐厅：
主厨（主图）：看菜单 → 分配任务 → 最后把关
    ├─ 冷菜间（冷菜子图）：所有凉菜
    ├─ 热菜间（热菜子图）：所有炒菜
    └─ 面点间（面点子图）：所有主食

好处：
- 专业化分工
- 可以同时做多道菜
- 某个厨师请假，其他人能顶上
```

---

## 📖 Week 2 → Week 3：为什么要拆子图？

### 回顾 Week 2 的问题

Week 1 和 Week 2 写的 graph，**所有节点都在一个 StateGraph 里**：

```python
# Week 2 的做法：一个大 graph
graph = StateGraph(SupportState)
graph.add_node("intent_router", ...)
graph.add_node("order_query", ...)   # 订单相关
graph.add_node("refund", ...)        # 订单相关
graph.add_node("logistics", ...)     # 订单相关
graph.add_node("coupon", ...)        # 优惠券相关
graph.add_node("product", ...)       # 产品相关
graph.add_node("faq_1", ...)         # FAQ 相关
graph.add_node("faq_2", ...)         # FAQ 相关
# ... 节点越来越多
```

**当业务增长时，问题暴露了**：

| 问题 | 说明 |
|------|------|
| ❌ State 臃肿 | 一个 State 要容纳所有字段，越来越乱 |
| ❌ 难以维护 | 新增 FAQ 类别要改主图代码 |
| ❌ 难以测试 | 订单逻辑和 FAQ 逻辑混在一起 |
| ❌ 协作困难 | 多人改同一个文件，容易冲突 |
| ❌ 无法复用 | 订单子逻辑不能在其他系统使用 |

### Week 3 的解决方案

> 把大 graph 拆成**独立的子图**（subgraph），主图只负责编排和路由。

```
主图（Master Graph）：
    接收用户输入 → 判断意图 → 路由到对应子图 → 格式化输出
    ├─ 订单子图（Order Subgraph）：验证 → 查询/退款/物流 → 返回结果
    ├─ FAQ 子图（FAQ Subgraph）：分类 → 检索 → 返回答案
    └─ 问候/fallback（主图直接处理）
```

**好处**：

| 维度 | Week 2 | Week 3 |
|------|--------|--------|
| 结构 | 一个大 graph | 主图 + 多个子图 |
| State | 一个大 TypedDict | 多个小 TypedDict |
| 测试 | 整体测试 | 子图独立测试 |
| 复用 | 无法复用 | 子图可复用 |
| 维护 | 改一处动全身 | 改子图不影响主图 |

---

## 🎓 Subgraph 核心机制

### 1. 子图必须是编译后的对象

**关键概念**：子图不是 `StateGraph` 本身，而是 `graph.compile()` 返回的对象。

```python
# ❌ 错误：不能把 StateGraph 当子图
order_graph = StateGraph(OrderState)
# ... 定义节点 ...
main_graph.add_node("order", order_graph)  # 错误！

# ✅ 正确：必须 compile()
order_graph = StateGraph(OrderState)
# ... 定义节点 ...
compiled_order = order_graph.compile()     # 编译
main_graph.add_node("order", compiled_order)  # 正确！
```

**为什么？**
- `StateGraph` 是"蓝图"，还没变成可执行对象
- `compile()` 后变成"成品"，才能被调用

### 2. State 共享机制

**这是 subgraph 最容易踩坑的地方**：

> 主图和子图 **共享同一个 State**。子图能读到的，就是主图 State 中同名的字段。

```python
# 主图 State
class MasterState(TypedDict, total=False):
    user_input: str
    response: str
    # 订单子图需要的字段
    order_id: str        # ← 必须有！
    action: str          # ← 必须有！
    result: str          # ← 必须有！
    # FAQ 子图需要的字段
    question: str        # ← 必须有！
    answer: str          # ← 必须有！

# 订单子图 State
class OrderState(TypedDict, total=False):
    order_id: str        # ← 和主图同名字段
    action: str          # ← 和主图同名字段
    result: str          # ← 和主图同名字段
    exists: bool
    order_data: dict
```

**规则**：
- 子图只能读到主图 State 中**同名字段**
- 主图 State 必须包含**所有子图需要的字段**
- 子图输出的字段，会**合并回主图 State**

### 3. 三种架构模式

| 模式 | 适用场景 | State 关系 | 复杂度 |
|------|---------|-----------|--------|
| **扁平模式** | 子图和主图字段完全一致 | 共用同一个 TypedDict | ⭐ |
| **适配器模式** ⭐ | 子图和主图字段不同 | 主图用适配节点做字段转换 | ⭐⭐ |
| **隔离模式** | 子图完全独立 | 主图 State 包含子图的完整 State | ⭐⭐⭐ |

**Week 3 采用的是适配器模式**：

```python
# 主图 State（面向用户）
class MasterState(TypedDict):
    user_input: str      # 用户原始输入
    response: str        # 最终回复

# 订单子图 State（面向业务）
class OrderState(TypedDict):
    order_id: str        # 结构化数据
    action: str
    result: str

# 适配器节点：从自然语言提取结构化数据
def order_adapter(state: MasterState) -> dict:
    """从用户输入中提取订单号和操作类型"""
    # "帮我查一下订单 ORD001" → order_id="ORD001", action="query"
    import re
    match = re.search(r'ORD\d+', state["user_input"])
    order_id = match.group(0) if match else ""
    
    action = "query"
    if "退款" in state["user_input"]:
        action = "refund"
    
    # 返回子图需要的字段
    return {
        "order_id": order_id,
        "action": action
    }
```

---

## 💻 实战实现

### 文件结构

```
week3/
├── order_subgraph.py      # 订单子图（独立）
├── faq_subgraph.py        # FAQ 子图（独立）
├── master_graph.py        # 主图（编排子图）
└── week3_comprehensive_notes.md  # 详细笔记
```

### 订单子图（Order Subgraph）

**文件**：`order_subgraph.py`

**职责**：处理所有订单相关业务（查询、退款、物流状态）

**子图结构**：

```
__start__
    ↓
validate_order (验证订单是否存在)
    ↓
[条件路由] ─┬─ exists=True, action=query    → query_order
            ├─ exists=True, action=refund   → process_refund
            ├─ exists=True, action=status   → check_status
            └─ exists=False                 → error_handler
    ↓
__end__
```

**核心代码**：

```python
from langgraph.graph import StateGraph, END

class OrderState(TypedDict, total=False):
    order_id: str
    exists: bool
    order_data: dict
    action: str
    result: str
    error: str

def validate_order(state: OrderState) -> dict:
    """节点 1：验证订单是否存在"""
    order = ORDERS_DB.get(state["order_id"])
    if order:
        return {"exists": True, "order_data": order}
    else:
        return {"exists": False, "error": f"❌ 未找到订单 {state['order_id']}"}

def route_order_action(state: OrderState) -> str:
    """条件路由：根据操作类型选择路径"""
    if not state.get("exists"):
        return "error_handler"
    
    mapping = {
        "query": "query_order",
        "refund": "process_refund",
        "status": "check_status",
    }
    return mapping.get(state["action"], "error_handler")

def build_order_subgraph():
    """构建并编译订单子图"""
    graph = StateGraph(OrderState)
    
    # 添加节点
    graph.add_node("validate_order", validate_order)
    graph.add_node("query_order", query_order)
    graph.add_node("process_refund", process_refund)
    graph.add_node("check_status", check_status)
    graph.add_node("error_handler", error_handler)
    
    # 设置入口
    graph.set_entry_point("validate_order")
    
    # 添加条件路由
    graph.add_conditional_edges(
        "validate_order",
        route_order_action,
        {
            "query_order": "query_order",
            "process_refund": "process_refund",
            "check_status": "check_status",
            "error_handler": "error_handler",
        }
    )
    
    # 所有节点都指向 END
    graph.add_edge("query_order", END)
    graph.add_edge("process_refund", END)
    graph.add_edge("check_status", END)
    graph.add_edge("error_handler", END)
    
    # 编译并返回
    return graph.compile()
```

**关键设计**：
- ✅ **验证优先**：先验证订单是否存在，再决定后续流程
- ✅ **条件路由**：根据 `action` 和 `exists` 动态选择路径
- ✅ **错误处理**：不存在的订单直接走错误处理，不浪费时间

---

### FAQ 子图（FAQ Subgraph）

**文件**：`faq_subgraph.py`

**职责**：处理所有常见问题咨询（物流、退款、产品、账户）

**子图结构**：

```
__start__
    ↓
classify_question (问题分类)
    ↓
[条件路由] ─┬─ confidence > 0.5   → retrieve_answer
            └─ confidence <= 0.5  → fallback_handler
    ↓
__end__
```

**核心代码**：

```python
class FAQState(TypedDict, total=False):
    question: str
    category: str
    confidence: float
    answer: str
    fallback: bool

def classify_question(state: FAQState) -> dict:
    """节点 1：问题分类（基于关键词匹配）"""
    q = state["question"].lower()
    
    # 关键词 → 类别映射
    keywords = [
        ("物流", "shipping", 3),
        ("快递", "shipping", 3),
        ("发货", "shipping", 3),
        ("退款", "refund", 3),
        ("退货", "refund", 3),
        ("保修", "product", 3),
        ("正品", "product", 3),
        ("密码", "account", 3),
    ]
    
    scores = {}
    for keyword, category, weight in keywords:
        if keyword in q:
            scores[category] = scores.get(category, 0) + weight
    
    # 选择得分最高的类别
    if scores:
        best_category = max(scores, key=scores.get)
        confidence = min(scores[best_category] / 5.0, 1.0)
    else:
        best_category = "unknown"
        confidence = 0.0
    
    return {
        "category": best_category,
        "confidence": confidence
    }

def route_faq(state: FAQState) -> str:
    """条件路由：置信度 > 0.5 走正常流程，否则 fallback"""
    if state["confidence"] > 0.5:
        return "retrieve_answer"
    else:
        return "fallback_handler"

def build_faq_subgraph():
    """构建并编译 FAQ 子图"""
    graph = StateGraph(FAQState)
    
    graph.add_node("classify_question", classify_question)
    graph.add_node("retrieve_answer", retrieve_answer)
    graph.add_node("fallback_handler", fallback_handler)
    
    graph.set_entry_point("classify_question")
    
    graph.add_conditional_edges(
        "classify_question",
        route_faq,
        {
            "retrieve_answer": "retrieve_answer",
            "fallback_handler": "fallback_handler",
        }
    )
    
    graph.add_edge("retrieve_answer", END)
    graph.add_edge("fallback_handler", END)
    
    return graph.compile()
```

**关键设计**：
- ✅ **置信度评分**：不是简单的"有/无"，而是给出置信度
- ✅ **Fallback 机制**：置信度低时，转人工或返回通用回答
- ✅ **双向匹配**：问题词在知识库中 + 知识库词在问题中

---

### 主图（Master Graph）

**文件**：`master_graph.py`

**职责**：意图路由、编排子图、格式化输出

**主图结构**：

```
__start__
    ↓
determine_route (意图路由)
    ↓
[条件路由] ─┬─ route=order   → order_adapter → order_subgraph
            ├─ route=faq     → faq_adapter → faq_subgraph
            ├─ route=greeting → greeting_handler
            └─ route=fallback → fallback_handler
    ↓
format_response (格式化输出)
    ↓
__end__
```

**核心代码**：

```python
class MasterState(TypedDict, total=False):
    user_input: str
    route: str
    response: str
    # 订单子图字段
    order_id: str
    action: str
    exists: bool
    order_data: dict
    result: str
    error: str
    # FAQ 子图字段
    question: str
    category: str
    confidence: float
    answer: str
    fallback: bool

def determine_route(state: MasterState) -> dict:
    """节点 1：意图路由"""
    q = state["user_input"].lower()
    
    # 1. 问候优先
    greeting_keywords = ["你好", "hello", "hi", "在吗"]
    if any(kw in q for kw in greeting_keywords):
        return {"route": "greeting"}
    
    # 2. 订单操作
    import re
    if re.search(r'ORD\d+', q):
        return {"route": "order"}
    
    # 3. FAQ 咨询
    faq_keywords = ["怎么", "如何", "什么", "为什么", "能", "可以"]
    if any(kw in q for kw in faq_keywords):
        return {"route": "faq"}
    
    # 4. Fallback
    return {"route": "fallback"}

def order_adapter(state: MasterState) -> dict:
    """适配器：从用户输入提取订单信息"""
    import re
    q = state["user_input"]
    
    # 提取订单号
    match = re.search(r'ORD\d+', q)
    order_id = match.group(0) if match else ""
    
    # 判断操作类型
    action = "query"
    if "退款" in q or "退货" in q:
        action = "refund"
    elif "物流" in q or "快递" in q:
        action = "status"
    
    return {
        "order_id": order_id,
        "action": action
    }

def format_response(state: MasterState) -> dict:
    """节点：格式化最终响应"""
    route = state.get("route")
    
    if route == "order":
        result = state.get("result") or state.get("error")
        return {"response": f"【订单查询结果】\n{result}"}
    elif route == "faq":
        answer = state.get("answer") or "抱歉，我暂时无法回答这个问题。"
        return {"response": f"【FAQ】\n{answer}"}
    elif route == "greeting":
        return {"response": "您好！我是客服助手，请问有什么可以帮您？"}
    else:
        return {"response": "抱歉，我暂时无法理解您的问题。"}

def build_master_graph():
    """构建主图"""
    # 编译子图
    order_subgraph = build_order_subgraph()
    faq_subgraph = build_faq_subgraph()
    
    # 创建主图
    graph = StateGraph(MasterState)
    
    # 添加节点
    graph.add_node("determine_route", determine_route)
    graph.add_node("order_adapter", order_adapter)
    graph.add_node("faq_adapter", faq_adapter)
    graph.add_node("order", order_subgraph)      # ← 子图作为节点
    graph.add_node("faq", faq_subgraph)          # ← 子图作为节点
    graph.add_node("greeting_handler", greeting_handler)
    graph.add_node("fallback_handler", fallback_handler)
    graph.add_node("format_response", format_response)
    
    # 设置入口
    graph.set_entry_point("determine_route")
    
    # 添加条件路由
    graph.add_conditional_edges(
        "determine_route",
        lambda state: state["route"],
        {
            "order": "order_adapter",
            "faq": "faq_adapter",
            "greeting": "greeting_handler",
            "fallback": "fallback_handler",
        }
    )
    
    # 连接适配器和子图
    graph.add_edge("order_adapter", "order")
    graph.add_edge("faq_adapter", "faq")
    
    # 所有路径都指向 format_response
    graph.add_edge("order", "format_response")
    graph.add_edge("faq", "format_response")
    graph.add_edge("greeting_handler", "format_response")
    graph.add_edge("fallback_handler", "format_response")
    
    # format_response 指向 END
    graph.add_edge("format_response", END)
    
    return graph.compile()
```

**关键设计**：
- ✅ **适配器模式**：从自然语言提取结构化数据
- ✅ **子图编排**：主图只做路由，具体逻辑交给子图
- ✅ **统一输出**：所有路径都经过 `format_response`，保证格式一致

---

## 🔧 运行与测试

### 单独测试子图

```bash
# 测试订单子图
cd src/week3
python order_subgraph.py

# 测试 FAQ 子图
python faq_subgraph.py
```

**订单子图测试示例**：

```python
# 测试 1：查询存在的订单
result = app.invoke({
    "order_id": "ORD20260417001",
    "action": "query"
})
print(result["result"])
# → "📦 订单详情\n订单号：ORD20260417001\n..."

# 测试 2：查询不存在的订单
result = app.invoke({
    "order_id": "ORD999",
    "action": "query"
})
print(result["error"])
# → "❌ 未找到订单 ORD999"

# 测试 3：退款操作
result = app.invoke({
    "order_id": "ORD20260417001",
    "action": "refund"
})
print(result["result"])
# → "✅ 退款申请已提交\n退款单号：REF..."
```

### 测试主图

```bash
python master_graph.py
```

**主图测试示例**：

```python
test_cases = [
    "你好",                          # → greeting
    "帮我查一下订单 ORD20260417001",  # → order → query
    "订单 ORD20260417001 能退款吗",   # → order → refund
    "多久能送到？",                  # → faq → shipping
    "怎么退款？",                    # → faq → refund
    "今天天气怎么样？",              # → fallback
]

for query in test_cases:
    result = app.invoke({"user_input": query})
    print(f"用户：{query}")
    print(f"客服：{result['response']}\n")
```

---

## ⚠️ 常见踩坑与解决方案

### 坑 1：子图 State 字段不匹配 → KeyError

**现象**：
```
KeyError: 'order_id' in subgraph's validate_order node
```

**原因**：
- 适配器节点返回的字段名是 `_order_id`
- 但子图期望 `order_id`
- 主图和子图通过**同名字段**共享数据

**解决**：

```python
# ❌ 错误：字段名不一致
def order_adapter(state):
    return {
        "_order_id": "ORD123",        # ← 错误！
        "_order_action": "query"      # ← 错误！
    }

# ✅ 正确：字段名必须和子图 State 一致
def order_adapter(state):
    return {
        "order_id": "ORD123",         # ← 正确！
        "action": "query"             # ← 正确！
    }
```

---

### 坑 2：主图 State 未包含子图字段 → 子图读不到数据

**现象**：
- 子图执行时某些字段为空
- 导致逻辑错误

**原因**：
- 主图 State 只定义了自己的字段
- 没包含子图需要的字段
- 子图运行时尝试读取 `state["order_id"]`，但主图 State 里没有

**解决**：

```python
# ❌ 错误：主图 State 缺少子图字段
class MasterState(TypedDict):
    user_input: str
    response: str

# ✅ 正确：主图 State 必须包含子图需要的所有字段
class MasterState(TypedDict, total=False):
    user_input: str
    response: str
    # 订单子图字段
    order_id: str
    action: str
    exists: bool
    order_data: dict
    result: str
    error: str
    # FAQ 子图字段
    question: str
    category: str
    confidence: float
    answer: str
    fallback: bool
```

---

### 坑 3：FAQ 分类关键词匹配不精确

**现象**：
- "多久能送到？" 分类为 unknown（置信度 0%）
- 触发 fallback

**原因**：
- 关键词 `"多久能到"` 不是 `"多久能送到？"` 的子串
- `in` 操作符要求**连续子串匹配**
- "到" 和 "送" 的顺序不同

**解决**：

```python
# ❌ 过于严格的匹配
keywords = [
    ("多久能到", "shipping", 3)  # "多久能到" 不是 "多久能送到？" 的子串
]

# ✅ 拆分为独立关键词
keywords = [
    ("多久", "shipping", 2),
    ("到", "shipping", 1),
    ("送", "shipping", 1)
]

# 检索时也做双向匹配
score = sum(1 for word in item["q"] if word in q)      # 问题词在用户输入中
score += sum(1 for word in q if word in item["q"])      # 用户输入词在问题中
```

---

## 💡 设计原则总结

### 什么时候该拆子图？

| 判断标准 | 说明 |
|---------|------|
| **职责不同** | 订单处理和 FAQ 查询是两个不同的业务领域 |
| **可以独立测试** | 子图有自己的输入/输出，不依赖主图 |
| **可能复用** | 订单子图可能被其他系统使用 |
| **团队分工** | 不同人负责不同子图 |
| **节点数量多** | 总节点数 > 10，就该考虑拆分 |

### 什么时候不该拆？

| 判断标准 | 说明 |
|---------|------|
| **节点很少** | 总共 3-4 个节点，拆分反而增加复杂度 |
| **共享 State 太多** | 子图之间要传递大量中间状态 |
| **流程紧密耦合** | 节点之间强依赖，不能独立运行 |

### 三层架构

```
┌─────────────────────────────────────┐
│           主图 (Master)              │
│  职责：意图路由、编排、格式化          │
├──────────┬──────────┬───────────────┤
│ 适配器   │ 子图 A   │ 子图 B         │
│ 字段转换 │ 订单处理 │ FAQ 问答       │
│          │ 独立测试 │ 独立测试       │
├──────────┴──────────┴───────────────┤
│           共享 State                 │
│  主图 State 是所有子图 State 的超集    │
└─────────────────────────────────────┘
```

---

## 🎯 核心认知总结

### 1. Subgraph 的本质

> Subgraph = 把一个编译后的 graph 当作节点添加到另一个 graph 中

**关键点**：
- 子图必须是 `compile()` 后的对象
- 主图和子图共享 State（同名字段）
- 主图 State 必须包含所有子图需要的字段

### 2. 为什么要拆子图？

- ✅ **模块化**：每个子图独立开发、测试、维护
- ✅ **可复用**：订单子图可以在多个系统使用
- ✅ **可扩展**：新增业务只需添加新子图
- ✅ **易协作**：多人可以同时改不同子图

### 3. 三种架构模式

| 模式 | 适用场景 | 复杂度 |
|------|---------|--------|
| 扁平模式 | 字段完全一致 | ⭐ |
| 适配器模式 ⭐ | 字段需要转换 | ⭐⭐ |
| 隔离模式 | 完全独立 | ⭐⭐⭐ |

### 4. 避坑指南

- ✅ 字段名必须一致（主图和子图）
- ✅ 主图 State 要包含所有子图字段
- ✅ 关键词匹配要灵活（双向匹配）
- ✅ 子图必须 compile()

---

## 🔗 相关资源

- [详细笔记](./week3_comprehensive_notes.md) - 完整的学习笔记
- [订单子图](./order_subgraph.py) - 订单处理子图
- [FAQ 子图](./faq_subgraph.py) - FAQ 问答子图
- [主图](./master_graph.py) - 主图编排

---

## 📝 学习建议

### 1. 先理解概念

- 阅读"为什么要拆子图"
- 理解 State 共享机制
- 掌握三种架构模式

### 2. 再动手实践

```bash
# 1. 运行订单子图
python order_subgraph.py

# 2. 运行 FAQ 子图
python faq_subgraph.py

# 3. 运行主图
python master_graph.py
```

### 3. 修改参数观察

- 改 `order_id`，看不同订单的处理流程
- 改 `action`，看不同操作的路由逻辑
- 改用户输入，看主图如何路由

### 4. 尝试自己设计

- 设计一个新的子图（如优惠券子图）
- 把它集成到主图中
- 测试各种边界情况

---

> 💡 **记住**：Subgraph 的核心思想就是**分而治之**。当你的 graph 超过 10 个节点时，就该考虑拆子图了。这不是 LangGraph 特有的，而是软件工程的模块化思想在图编排中的具体实践。
