# 📚 第 2 月 - Week 3：Subgraph 与模块化

> 学习日期：2026-05-22 至 2026-05-24
> 代码位置：`month02-langgraph/src/week3/`
> 状态：3 个文件全部跑通 ✅

---

## 一、Week 2 → Week 3：为什么要拆子图？

### 回顾 Week 2 的问题

Week 1 和 Week 2 写的 graph，**所有节点都在一个 StateGraph 里**：

```python
graph = StateGraph(SupportState)
graph.add_node("intent_router", ...)
graph.add_node("order_query", ...)   # 订单相关
graph.add_node("refund", ...)        # 订单相关
graph.add_node("logistics", ...)     # 订单相关
graph.add_node("coupon", ...)        # 优惠券相关
graph.add_node("product", ...)       # 产品相关
graph.add_node("faq_1", ...)         # FAQ 相关
graph.add_node("faq_2", ...)         # FAQ 相关
# ... 越来越多
```

**当业务增长时，问题暴露了**：
- ❌ 一个 State 要容纳所有字段，越来越臃肿
- ❌ 新增 FAQ 类别要改主图代码
- ❌ 订单子逻辑和 FAQ 子逻辑混在一起，难以独立测试
- ❌ 多人协作时容易冲突

### Week 3 的解决方案

> 把大 graph 拆成**独立的子图**（subgraph），主图只负责编排和路由。

```
主图：接收用户输入 → 判断意图 → 路由到对应子图 → 格式化输出
    ├─ 订单子图（独立）：验证 → 查询/退款/物流 → 返回结果
    ├─ FAQ 子图（独立）：分类 → 检索 → 返回答案
    └─ 问候/fallback（主图直接处理）
```

**类比**：
- 以前的 graph = 一家什么都干的小店（老板身兼数职）
- 现在的 subgraph = 一家公司，有不同部门（订单部、客服部），CEO 只做调度

---

## 二、Subgraph 基本概念

### 2.1 一句话理解

> Subgraph 就是**把一个编译后的 graph 当作节点添加到另一个 graph 中**。

```python
# 子图：独立定义、独立编译
order_subgraph = build_order_subgraph()  # ← 编译后的 graph

# 主图：把子图当节点用
main_graph = StateGraph(MasterState)
main_graph.add_node("order", order_subgraph)  # ← 直接添加
```

**关键点**：子图必须是**编译后的对象**（`graph.compile()` 返回的），不是 `StateGraph` 本身。

### 2.2 State 共享机制

这是 subgraph 最容易踩坑的地方：

> 主图和子图 **共享同一个 State**。子图能读到的，就是主图 State 中同名的字段。

```python
class MasterState(TypedDict, total=False):
    user_input: str
    response: str
    # 订单子图需要的字段
    order_id: str
    action: str
    result: str
    # FAQ 子图需要的字段
    question: str
    answer: str

# 主图 State 必须包含所有子图需要的字段！
# 否则子图执行时拿不到数据 → KeyError
```

### 2.3 三种 subgraph 架构模式

| 模式 | 适用场景 | State 关系 |
|------|---------|-----------|
| **扁平模式** | 子图和主图字段完全一致 | 共用同一个 TypedDict |
| **适配器模式** ⭐ | 子图和主图字段不同 | 主图用适配节点做字段转换 |
| **隔离模式** | 子图完全独立，数据通过专用字段传递 | 主图 State 包含子图的完整 State |

Week 3 采用的是**适配器模式** + **隔离模式**的混合体。

---

## 三、订单子图 (Order Subgraph)

### 3.1 文件：`order_subgraph.py`

**职责**：处理所有订单相关业务（查询、退款、物流状态）。

**子图 State**：
```python
class OrderState(TypedDict, total=False):
    order_id: str          # 订单号
    exists: bool           # 订单是否存在
    order_data: dict       # 订单详情
    action: str            # 操作类型：query/refund/status
    result: str            # 处理结果
    error: str             # 错误信息
```

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

### 3.2 核心设计：验证优先

```python
def validate_order(state: OrderState) -> dict:
    """先验证订单是否存在，再决定后续流程"""
    order = ORDERS_DB.get(state["order_id"])
    if order:
        return {"exists": True, "order_data": order}
    else:
        return {"exists": False, "error": f"❌ 未找到订单 {state['order_id']}"}

def route_order_action(state: OrderState) -> str:
    """条件路由：不存在的订单直接走错误处理"""
    if not state.get("exists"):
        return "error_handler"
    
    mapping = {
        "query": "query_order",
        "refund": "process_refund",
        "status": "check_status",
    }
    return mapping.get(state.get("action", "query"), "query_order")
```

**为什么先验证？**
- 避免每个业务节点都重复写 `if not order: return error`
- 验证失败直接路由到 error_handler，其他节点不用关心异常情况
- 这就是子图的价值——**把复杂逻辑封装在内部，对外提供干净的接口**

### 3.3 测试结果

| 测试场景 | 输入 | 路由 | 结果 |
|---------|------|------|------|
| 查询订单 | `ORD20260417001` + query | validate → query_order | ✅ 显示订单详情 |
| 退款申请 | `ORD20260417001` + refund | validate → process_refund | ✅ 显示退款政策 |
| 物流查询 | `ORD20260417002` + status | validate → check_status | ✅ 显示物流状态 |
| 已签收退款 | `ORD20260417003` + refund | validate → process_refund | ✅ 显示 7 天无理由 |
| 不存在的订单 | `ORD9999999999` + query | validate → error_handler | ✅ 返回错误信息 |

---

## 四、FAQ 子图 (FAQ Subgraph)

### 4.1 文件：`faq_subgraph.py`

**职责**：处理知识型问答（物流政策、退款政策、产品信息、账户操作）。

**子图 State**：
```python
class FAQState(TypedDict, total=False):
    question: str         # 用户问题
    category: str         # 分类：shipping/refund/product/account/unknown
    confidence: float     # 匹配置信度 (0-1)
    answer: str           # 找到的答案
    fallback: bool        # 是否触发 fallback
```

**子图结构**：
```
__start__
    ↓
classify_question (问题分类 + 计算置信度)
    ↓
[置信度路由] ─┬─ confidence ≥ 0.5  → retrieve_answer
              └─ confidence < 0.5  → fallback
    ↓
__end__
```

### 4.2 核心设计：置信度路由

```python
def classify_question(state: FAQState) -> dict:
    """
    关键词分类 + 权重打分
    
    不同关键词有不同权重：
    - 业务核心词（如"退款"、"正品"）权重 = 2
    - 辅助词（如"到"、"地址"）权重 = 1
    
    置信度 = min(score / 2, 1.0)  # 2 个关键词就算 100%
    """
    category_keywords = {
        "shipping": [("快递", 1), ("物流", 1), ("送达", 2), ("多久", 2), ("包邮", 2)],
        "refund":   [("退款", 2), ("退货", 2), ("到账", 2), ("手续费", 1)],
        "product":  [("保修", 2), ("正品", 2), ("发票", 1), ("质量", 1)],
        "account":  [("地址", 2), ("密码", 2), ("注销", 2), ("账户", 1)],
    }
    # ... 选最高分
    return {"category": best_category, "confidence": confidence}

def route_by_confidence(state: FAQState) -> str:
    """置信度 ≥ 50% 才尝试检索答案，否则 fallback"""
    if state.get("confidence", 0) >= 0.5:
        return "retrieve_answer"
    else:
        return "fallback"
```

**为什么用置信度路由？**
- 避免关键词匹配到错误分类时给出错误答案
- fallback 节点可以引导用户换种问法
- 实际项目中这里可以替换为 LLM 分类器，置信度就是 LLM 返回的 probability

### 4.3 知识库设计

```python
FAQ_KB = {
    "shipping": {
        "label": "物流相关",
        "questions": [
            {"q": "多久能到", "a": "一般情况下，下单后 1-3 天发货..."},
            {"q": "快递查询", "a": "您可以在订单详情中查看物流单号..."},
            {"q": "包邮吗", "a": "订单满 ¥99 包邮..."},
        ]
    },
    # ... 其他类别
}
```

**匹配策略**：
1. 双向关键词匹配（问题词在用户输入中 + 用户输入词在问题中）
2. 精确包含加分（KB 问题是用户输入的子串，或反之）
3. 选最高分的答案

### 4.4 测试结果

| 用户问题 | 分类 | 置信度 | 结果 |
|---------|------|--------|------|
| 多久能送到？ | shipping | 100% | ✅ 显示物流时效 |
| 退款多久到账 | refund | 100% | ✅ 显示退款时效 |
| 你们卖的东西是正品吗？ | product | 100% | ✅ 显示正品政策 |
| 怎么修改收货地址 | account | 100% | ✅ 显示修改规则 |
| 今天天气怎么样 | unknown | 0% | ✅ fallback + 引导问题 |
| 包邮有什么条件 | shipping | 100% | ✅ 显示包邮规则 |

---

## 五、主图：组合子图

### 5.1 文件：`master_graph.py`

**职责**：接收用户输入 → 路由到对应子图 → 格式化输出。

**主图结构**：
```
__start__
    ↓
determine_route (判断路由目标)
    ↓
[条件路由] ─┬─ order  → order_adapter → order_subgraph → format_order_result → END
            ├─ faq    → faq_adapter → faq_subgraph → format_faq_result → END
            ├─ greeting → greeting_node → END
            └─ fallback → fallback_node → END
```

### 5.2 主图 State 设计

```python
class MasterState(TypedDict, total=False):
    user_input: str
    route: str
    response: str
    
    # 订单子图需要的字段（子图能读到同名字段）
    order_id: str
    action: str
    exists: bool
    order_data: dict
    result: str
    error: str
    
    # FAQ 子图需要的字段
    question: str
    category: str
    confidence: float
    answer: str
    fallback: bool
```

**关键原则**：主图 State 是**超集**，包含所有子图需要读写的字段。

### 5.3 适配器模式

适配器节点负责在主图 State 和子图 State 之间做字段转换：

```python
def order_adapter(state: MasterState) -> dict:
    """主图 → 订单子图：解析 user_input，提取子图需要的字段"""
    import re
    order_match = re.search(r"ORD\d+", state["user_input"])
    order_id = order_match.group(0) if order_match else "ORD20260417001"
    
    action = "query"
    if any(kw in state["user_input"] for kw in ["退款", "退货"]):
        action = "refund"
    elif any(kw in state["user_input"] for kw in ["物流", "快递"]):
        action = "status"
    
    return {"order_id": order_id, "action": action}

def faq_adapter(state: MasterState) -> dict:
    """主图 → FAQ 子图：直接传递"""
    return {"question": state["user_input"]}
```

**为什么需要适配器？**
- 用户输入是自然语言，子图需要结构化参数
- 主图不需要知道子图内部怎么解析参数，适配器统一处理
- 子图换实现时，只需调整适配器，不影响主图

### 5.4 主图测试结果（11 个测试用例）

| # | 用户输入 | 路由目标 | 子图 | 结果 |
|---|---------|---------|------|------|
| 1 | 帮我查一下订单 ORD20260417001 | order | 订单子图 | ✅ 订单详情 |
| 2 | 我要退款，订单 ORD20260417001 | order | 订单子图 | ✅ 退款政策 |
| 3 | 查物流 ORD20260417003 | order | 订单子图 | ✅ 物流状态 |
| 4 | 不存在的订单 ORD0000000000 | order | 订单子图 | ✅ 错误提示 |
| 5 | 多久能送到？ | faq | FAQ 子图 | ✅ 物流时效 |
| 6 | 退款多久到账？ | order | 订单子图 | ✅ 退款政策 |
| 7 | 你们的东西是正品吗？ | faq | FAQ 子图 | ✅ 正品政策 |
| 8 | 怎么修改收货地址？ | faq | FAQ 子图 | ✅ 修改规则 |
| 9 | 今天天气怎么样？ | fallback | 主图 | ✅ fallback + 引导 |
| 10 | 你好！ | greeting | 主图 | ✅ 问候回复 |
| 11 | Hello! | greeting | 主图 | ✅ 问候回复 |

---

## 六、Subgraph 核心 API 速查

### 6.1 基本用法

```python
from langgraph.graph import StateGraph, END
from typing import TypedDict

# ========== 1. 定义子图 ==========
class SubState(TypedDict, total=False):
    input: str
    result: str

def process_node(state: SubState) -> dict:
    return {"result": f"处理了: {state['input']}"}

subgraph = StateGraph(SubState)
subgraph.add_node("process", process_node)
subgraph.set_entry_point("process")
subgraph.add_edge("process", END)

compiled_subgraph = subgraph.compile()  # ← 必须编译！

# ========== 2. 添加到主图 ==========
class MainState(TypedDict, total=False):
    user_input: str
    response: str
    input: str      # 子图需要的字段
    result: str     # 子图返回的字段

main = StateGraph(MainState)
main.add_node("subgraph", compiled_subgraph)  # ← 编译后的子图当节点用
main.set_entry_point("subgraph")
main.add_edge("subgraph", END)

app = main.compile()

# ========== 3. 运行 ==========
result = app.invoke({"user_input": "你好", "input": "你好", "result": ""})
print(result["result"])  # → "处理了: 你好"
```

### 6.2 关键规则

| 规则 | 说明 |
|------|------|
| 子图必须编译 | `graph.compile()` 返回的对象才能作为节点添加 |
| State 共享 | 子图和主图共享 State，字段名必须一致 |
| 字段传递 | 主图 State 中同名字段自动传递给子图 |
| 结果合并 | 子图输出的字段合并回主图 State |
| 独立测试 | 子图可以单独运行测试，不依赖主图 |

---

## 七、Subgraph 的优势

### 7.1 独立开发与测试

```bash
# 单独测试订单子图
python src/week3/order_subgraph.py

# 单独测试 FAQ 子图
python src/week3/faq_subgraph.py

# 测试主图组合
python src/week3/master_graph.py
```

每个子图可以独立修改、独立测试，不影响其他部分。

### 7.2 可复用性

订单子图可以被多个主图复用：

```python
# 主图 A：客服系统
app_a = build_customer_service_graph()  # 内部使用 order_subgraph

# 主图 B：后台管理系统
app_b = build_admin_dashboard_graph()   # 也使用 order_subgraph
```

### 7.3 职责分离

| 层级 | 职责 | 示例 |
|------|------|------|
| **主图** | 意图路由、编排、结果格式化 | 判断用户想做什么 |
| **子图** | 具体业务逻辑 | 怎么查订单、怎么匹配 FAQ |
| **适配器** | 字段转换、参数解析 | 从自然语言提取结构化参数 |

### 7.4 与 Week 1/2 的对比

| 维度 | Week 1 (扁平) | Week 2 (持久化) | Week 3 (子图) |
|------|-------------|---------------|-------------|
| 节点数量 | 8 个 | 6 个 | 主图 7 个 + 子图 N 个 |
| State 复杂度 | 一个大 TypedDict | 一个大 TypedDict | 多个小 TypedDict |
| 可测试性 | 整体测试 | 整体测试 | 子图独立测试 |
| 可复用性 | 无 | 无 | 子图可复用 |
| 可扩展性 | 改一处动全身 | 改一处动全身 | 改子图不影响主图 |
| 适合场景 | 小型 demo | 需要记忆的客服 | 中大型业务系统 |

---

## 八、本周踩坑记录

### 踩坑 1：子图 State 字段不匹配 → KeyError

**现象**：`KeyError: 'order_id'` in subgraph's validate_order node

**原因**：适配器节点返回的字段名是 `_order_id`，但子图期望 `order_id`。主图 State 和子图 State 通过**同名字段**共享数据。

**解决**：
```python
# ❌ 错误：字段名不一致
def order_adapter(state):
    return {"_order_id": "ORD123", "_order_action": "query"}

# ✅ 正确：字段名必须和子图 State 一致
def order_adapter(state):
    return {"order_id": "ORD123", "action": "query"}
```

### 踩坑 2：主图 State 未包含子图字段 → 子图读不到数据

**现象**：子图执行时某些字段为空，导致逻辑错误。

**原因**：主图 State 只定义了自己的字段，没包含子图需要的字段。子图运行时尝试读取 `state["order_id"]`，但主图 State 里没有这个键。

**解决**：
```python
# ✅ 主图 State 必须包含子图需要的所有字段
class MasterState(TypedDict, total=False):
    user_input: str
    response: str
    # 订单子图字段
    order_id: str
    action: str
    exists: bool
    # FAQ 子图字段
    question: str
    answer: str
    # ... 所有子图的字段
```

### 踩坑 3：FAQ 分类关键词匹配不精确

**现象**："多久能送到？" 分类为 unknown（置信度 0%），触发 fallback。

**原因**：关键词 `"多久能到"` 不是 `"多久能送到？"` 的子串（"到" 和 "送" 的顺序不同）。`in` 操作符要求连续子串匹配。

**解决**：
```python
# ❌ 过于严格的匹配
("多久能到", 2)  # "多久能到" 不是 "多久能送到？" 的子串

# ✅ 拆分为独立关键词
("多久", 2), ("到", 1)  # 分别匹配，更灵活

# 检索时也做双向匹配
score = sum(1 for word in item["q"] if word in q)      # 问题词在用户输入中
score += sum(1 for word in q if word in item["q"])      # 用户输入词在问题中
```

---

## 九、设计原则总结

### 9.1 什么时候该拆子图？

| 判断标准 | 说明 |
|---------|------|
| 职责不同 | 订单处理和 FAQ 查询是两个不同的业务领域 |
| 可以独立测试 | 子图有自己的输入/输出，不依赖主图 |
| 可能复用 | 订单子图可能被其他系统使用 |
| 团队分工 | 不同人负责不同子图 |

### 9.2 什么时候不该拆？

| 判断标准 | 说明 |
|---------|------|
| 节点很少 | 总共 3-4 个节点，拆分反而增加复杂度 |
| 共享 State 太多 | 子图之间要传递大量中间状态 |
| 流程紧密耦合 | 节点之间强依赖，不能独立运行 |

### 9.3 三层架构

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

## 十、学习路径回顾

```
Week 1: Graph API 入门 ✅
  ├── Day 1-2: 简单线性 graph（3 节点）
  ├── Day 3-4: 客服 graph（8 节点 + 条件路由）
  └── Day 5-6: 测试优化 + 思维对比笔记

Week 2: Persistence / Checkpoints ✅
  ├── Day 1: MemorySaver + Thread ID + Time Travel 基础
  ├── Day 2: Human-in-the-Loop + 多步骤审批流
  └── Day 3: API 兼容性 bug 修复（3 个文件全通）

Week 3: Subgraph 与模块化 ✅
  ├── Day 1: 订单子图（验证优先 + 条件路由）
  ├── Day 2: FAQ 子图（置信度分类 + 知识库检索）
  └── Day 3: 主图组合（适配器模式 + 11 个测试用例）

Week 4: Workflow vs Agent 选型 ⬜ 下一步
```

---

> 📝 **写在最后**：Week 3 的核心就一句话 — **把大 graph 拆成小的、可复用的、可独立测试的子模块**。
> 这不是 LangGraph 特有的概念，而是软件工程中的模块化思想在图编排中的具体实践。
> 当你的 graph 超过 10 个节点时，就该考虑拆子图了。
